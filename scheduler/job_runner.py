import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable, List
import json

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from sqlalchemy.orm import Session

from db.db_utils import (
    get_user_target_accounts, get_available_monitoring_account,
    update_monitoring_account_usage, add_follower_snapshot, get_last_two_snapshots,
    get_target_account_by_id
)
from db.models import TargetAccount, MonitoringAccount
from config.settings import MONITORING_INTERVAL_HOURS
from monitor.tiktok_monitor import TikTokMonitor
from monitor.instagram_monitor import InstagramMonitor
from monitor.diff_checker import compare_followers
from bot.localization import get_message
from bot.utils import format_datetime

logger = logging.getLogger(__name__)

async def monitor_single_profile(bot: Bot, db_session_factory: Callable[[], Session], target_account_id: int):
    logger.info(f'Starting monitoring for target_account_id: {target_account_id}')
    with db_session_factory() as db:
        target_account = get_target_account_by_id(db, target_account_id)
        if not target_account or not target_account.is_monitoring_active:
            logger.info(f'Skipping monitoring for {target_account_id}: not found or not active.')
            return

        # Get user for localization
        user_telegram_id = target_account.user.telegram_id # Assuming user relationship is loaded
        user_lang_code = target_account.user.language_code # Assuming user relationship is loaded

        # Get an available monitoring account
        mon_account = get_available_monitoring_account(db, target_account.platform)
        if not mon_account:
            logger.warning(f'No available monitoring account for {target_account.platform}. Cannot monitor {target_account.profile_url}')
            await bot.send_message(chat_id=user_telegram_id, text=get_message(user_lang_code, 'error_occured'))
            return

        monitor_class = None
        if target_account.platform == 'tiktok':
            monitor_class = TikTokMonitor
        elif target_account.platform == 'instagram':
            monitor_class = InstagramMonitor

        if not monitor_class:
            logger.error(f'Unknown platform: {target_account.platform}')
            return

        monitor = monitor_class(
            account_id=mon_account.id,
            username=mon_account.username,
            password=mon_account.password,
            proxy=mon_account.proxy,
            cookies_path=mon_account.cookies_path
        )

        try:
            # Update monitoring account usage timestamp before running
            update_monitoring_account_usage(db, mon_account.id)

            scraped_data = await monitor.run(profile_url=target_account.profile_url)

            if scraped_data:
                # Save new snapshot
                new_snapshot = add_follower_snapshot(
                    db,
                    target_account_id=target_account.id,
                    followers_count=scraped_data.get('followers_count', 0),
                    following_count=scraped_data.get('following_count', 0),
                    followers_list=scraped_data.get('followers_list', '[]'),
                    following_list=scraped_data.get('following_list', '[]'),
                )
                logger.info(f'New snapshot saved for {target_account.profile_url}')

                # Get last two snapshots for comparison
                snapshots = get_last_two_snapshots(db, target_account.id)
                if len(snapshots) >= 2: # Changed to >= 2
                    old_snapshot_data = {
                        'followers_count': snapshots[1].followers_count,
                        'following_count': snapshots[1].following_count,
                        'followers_list': snapshots[1].followers_list,
                        'following_list': snapshots[1].following_list,
                    }
                    new_snapshot_data = {
                        'followers_count': snapshots[0].followers_count,
                        'following_count': snapshots[0].following_count,
                        'followers_list': snapshots[0].followers_list,
                        'following_list': snapshots[0].following_list,
                    }
                    diff = compare_followers(old_snapshot_data, new_snapshot_data)

                    # Prepare and send notification
                    report_message = get_message(user_lang_code, 'report_header', username=target_account.username or target_account.profile_url, platform=target_account.platform.capitalize())
                    report_message += get_message(user_lang_code, 'followers_count', count=new_snapshot.followers_count) + '\n'
                    report_message += get_message(user_lang_code, 'following_count', count=new_snapshot.following_count) + '\n'
                    report_message += get_message(user_lang_code, 'last_checked', last_checked=format_datetime(new_snapshot.timestamp, user_lang_code)) + '\n\n'

                    has_changes = False
                    if diff['new_followers']:
                        report_message += get_message(user_lang_code, 'new_followers', count=len(diff['new_followers']), list='\n'.join(diff['new_followers'])) + '\n'
                        has_changes = True
                    if diff['unfollowers']:
                        report_message += get_message(user_lang_code, 'unfollowers', count=len(diff['unfollowers']), list='\n'.join(diff['unfollowers'])) + '\n'
                        has_changes = True
                    if diff['potential_blockers']:
                        report_message += get_message(user_lang_code, 'possible_blockers', count=len(diff['potential_blockers']), list='\n'.join(diff['potential_blockers'])) + '\n'
                        has_changes = True

                    if not has_changes:
                        report_message += get_message(user_lang_code, 'no_changes')

                    await bot.send_message(chat_id=user_telegram_id, text=report_message)
                else:
                    logger.info(f'Not enough snapshots to compare for {target_account.profile_url}. Sending initial report.')
                    # Send initial report if it's the first snapshot
                    report_message = get_message(user_lang_code, 'report_header', username=target_account.username or target_account.profile_url, platform=target_account.platform.capitalize())
                    report_message += get_message(user_lang_code, 'followers_count', count=new_snapshot.followers_count) + '\n'
                    report_message += get_message(user_lang_code, 'following_count', count=new_snapshot.following_count) + '\n'
                    report_message += get_message(user_lang_code, 'last_checked', last_checked=format_datetime(new_snapshot.timestamp, user_lang_code)) + '\n\n'
                    report_message += get_message(user_lang_code, 'no_changes') # Initial report has no changes yet
                    await bot.send_message(chat_id=user_telegram_id, text=report_message)

            else:
                logger.error(f'Failed to scrape data for {target_account.profile_url}')
                await bot.send_message(chat_id=user_telegram_id, text=get_message(user_lang_code, 'error_generating_report'))

        except Exception as e:
            logger.error(f'Error in monitor_single_profile for {target_account.profile_url}: {e}', exc_info=True)
            await bot.send_message(chat_id=user_telegram_id, text=get_message(user_lang_code, 'error_generating_report'))

async def scheduled_monitoring_job(bot: Bot, db_session_factory: Callable[[], Session]):
    logger.info('Running scheduled monitoring job...')
    with db_session_factory() as db:
        # Get all active target accounts
        all_target_accounts = db.query(TargetAccount).filter(TargetAccount.is_monitoring_active == True).all()
        logger.info(f'Found {len(all_target_accounts)} active target accounts to monitor.')

        # Distribute monitoring tasks
        tasks = []
        for account in all_target_accounts:
            tasks.append(monitor_single_profile(bot, db_session_factory, account.id))

        # Run tasks concurrently (up to a limit if needed, e.g., based on available monitoring accounts)
        await asyncio.gather(*tasks)
    logger.info('Scheduled monitoring job finished.')

def setup_monitoring_jobs(scheduler: AsyncIOScheduler, db_session_factory: Callable[[], Session], bot: Bot):
    # Add the main scheduled job
    scheduler.add_job(
        scheduled_monitoring_job,
        'interval',
        hours=MONITORING_INTERVAL_HOURS,
        args=[bot, db_session_factory],
        id='full_monitoring_job',
        replace_existing=True,
        next_run_time=datetime.now() + timedelta(seconds=10) # Run shortly after startup
    )
    logger.info(f'Scheduled full monitoring job to run every {MONITORING_INTERVAL_HOURS} hours.')


