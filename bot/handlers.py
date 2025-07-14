
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from bot.localization import get_message
from bot.keyboards import (main_menu_keyboard, platform_selection_keyboard, settings_keyboard,
                           language_keyboard, profile_list_keyboard, confirmation_keyboard,
                           admin_menu_keyboard, mon_account_platform_selection_keyboard,
                           monitoring_account_list_keyboard)
from bot.states import States
from db.db_utils import (get_or_create_user, update_user_language, add_target_account,
                         get_user_target_accounts, delete_target_account, get_target_account_by_url,
                         get_target_account_by_id, update_target_account_status, get_latest_snapshot,
                         add_monitoring_account, get_all_monitoring_accounts, delete_monitoring_account,
                         get_monitoring_account)
from bot.utils import is_valid_tiktok_url, is_valid_instagram_url, extract_username_from_url, format_datetime
from config.settings import ADMIN_TELEGRAM_IDS, HEADLESS_MODE, COOKIES_DIR
from monitor.tiktok_monitor import TikTokMonitor
from monitor.instagram_monitor import InstagramMonitor
import logging
import asyncio
import json
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# --- Helper Functions ---
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_TELEGRAM_IDS

# --- General Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    lang_code = update.effective_user.language_code or 'en'
    db_session = context.bot_data['db_session']
    with db_session() as db:
        user = get_or_create_user(db, user_id, lang_code)
        context.user_data['lang'] = user.language_code

    message = get_message(context.user_data['lang'], 'start')
    if user.created_at == user.updated_at: # Check if it's a new user (first time created)
        message = get_message(context.user_data['lang'], 'welcome_new_user') + '\n\n' + message

    await update.message.reply_text(message, reply_markup=main_menu_keyboard(context.user_data['lang'], is_admin(user_id)))
    return States.MAIN_MENU

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang_code = context.user_data.get('lang', 'en')
    user_id = update.effective_user.id
    await query.edit_message_text(get_message(lang_code, 'main_menu'), reply_markup=main_menu_keyboard(lang_code, is_admin(user_id)))
    return States.MAIN_MENU

# --- Add Profile Flow (for regular users) ---
async def add_profile_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang_code = context.user_data.get('lang', 'en')
    await query.edit_message_text(get_message(lang_code, 'choose_platform'), reply_markup=platform_selection_keyboard(lang_code))
    return States.ADD_PROFILE_PLATFORM

async def add_profile_platform_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    platform = query.data.split('_')[-1]
    context.user_data['platform_to_add'] = platform
    lang_code = context.user_data.get('lang', 'en')
    await query.edit_message_text(get_message(lang_code, 'enter_profile_url'))
    return States.ADD_PROFILE_URL

async def add_profile_url_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    profile_url = update.message.text.strip()
    platform = context.user_data.get('platform_to_add')
    lang_code = context.user_data.get('lang', 'en')
    db_session = context.bot_data['db_session']

    is_valid = False
    if platform == 'tiktok':
        is_valid = is_valid_tiktok_url(profile_url)
    elif platform == 'instagram':
        is_valid = is_valid_instagram_url(profile_url)

    if not is_valid:
        await update.message.reply_text(get_message(lang_code, 'invalid_url'))
        return States.ADD_PROFILE_URL # Stay in the same state to re-enter URL

    with db_session() as db:
        user = get_or_create_user(db, user_id, lang_code)
        existing_account = get_target_account_by_url(db, profile_url)
        if existing_account and existing_account.user_id == user.id:
            await update.message.reply_text(get_message(lang_code, 'profile_already_added'), reply_markup=main_menu_keyboard(lang_code, is_admin(user_id)))
            return States.MAIN_MENU

        username = extract_username_from_url(profile_url)
        new_account = add_target_account(db, user.id, platform, profile_url)
        new_account.username = username # Update username after creation
        db.commit()
        db.refresh(new_account)

    await update.message.reply_text(get_message(lang_code, 'profile_added', platform=platform.capitalize(), username=username or profile_url), reply_markup=main_menu_keyboard(lang_code, is_admin(user_id)))
    return States.MAIN_MENU

# --- Remove Profile Flow ---
async def remove_profile_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    lang_code = context.user_data.get('lang', 'en')
    db_session = context.bot_data['db_session']

    with db_session() as db:
        user = get_or_create_user(db, user_id, lang_code)
        profiles = get_user_target_accounts(db, user.id)

    if not profiles:
        await query.edit_message_text(get_message(lang_code, 'no_profiles_to_remove'), reply_markup=main_menu_keyboard(lang_code, is_admin(user_id)))
        return States.MAIN_MENU

    context.user_data['profiles_to_manage'] = {p.id: p for p in profiles}
    await query.edit_message_text(get_message(lang_code, 'select_profile_to_remove'), reply_markup=profile_list_keyboard(lang_code, profiles, 'remove_profile_select'))
    return States.REMOVE_PROFILE_CONFIRM

async def remove_profile_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    profile_id = int(query.data.split('_')[-1])
    lang_code = context.user_data.get('lang', 'en')
    profile = context.user_data['profiles_to_manage'].get(profile_id)
    user_id = update.effective_user.id

    if not profile:
        await query.edit_message_text(get_message(lang_code, 'error_occured'), reply_markup=main_menu_keyboard(lang_code, is_admin(user_id)))
        return States.MAIN_MENU

    context.user_data['profile_id_to_remove'] = profile_id
    await query.edit_message_text(get_message(lang_code, 'confirm_remove', username=profile.username or profile.profile_url), 
                                  reply_markup=confirmation_keyboard(lang_code, 'confirm_remove_yes', 'confirm_remove_no'))
    return States.REMOVE_PROFILE_CONFIRM

async def remove_profile_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang_code = context.user_data.get('lang', 'en')
    db_session = context.bot_data['db_session']
    profile_id = context.user_data.get('profile_id_to_remove')
    user_id = update.effective_user.id

    if query.data == 'confirm_remove_yes':
        with db_session() as db:
            profile = get_target_account_by_id(db, profile_id)
            if profile and delete_target_account(db, profile_id):
                await query.edit_message_text(get_message(lang_code, 'profile_removed', username=profile.username or profile.profile_url), reply_markup=main_menu_keyboard(lang_code, is_admin(user_id)))
            else:
                await query.edit_message_text(get_message(lang_code, 'error_occured'), reply_markup=main_menu_keyboard(lang_code, is_admin(user_id)))
    else: # confirm_remove_no
        await query.edit_message_text(get_message(lang_code, 'main_menu'), reply_markup=main_menu_keyboard(lang_code, is_admin(user_id)))

    return States.MAIN_MENU

# --- Pause/Resume Monitoring Flow ---
async def pause_resume_monitoring_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    lang_code = context.user_data.get('lang', 'en')
    db_session = context.bot_data['db_session']

    with db_session() as db:
        user = get_or_create_user(db, user_id, lang_code)
        profiles = get_user_target_accounts(db, user.id)

    if not profiles:
        await query.edit_message_text(get_message(lang_code, 'no_active_monitoring'), reply_markup=main_menu_keyboard(lang_code, is_admin(user_id)))
        return States.MAIN_MENU

    context.user_data['profiles_to_manage'] = {p.id: p for p in profiles}
    await query.edit_message_text(get_message(lang_code, 'select_profile_to_pause_resume'), reply_markup=profile_list_keyboard(lang_code, profiles, 'pause_resume_select'))
    return States.PAUSE_RESUME_PROFILE_CONFIRM

async def pause_resume_monitoring_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    profile_id = int(query.data.split('_')[-1])
    lang_code = context.user_data.get('lang', 'en')
    profile = context.user_data['profiles_to_manage'].get(profile_id)
    user_id = update.effective_user.id

    if not profile:
        await query.edit_message_text(get_message(lang_code, 'error_occured'), reply_markup=main_menu_keyboard(lang_code, is_admin(user_id)))
        return States.MAIN_MENU

    context.user_data['profile_id_to_pause_resume'] = profile_id
    action_key = 'confirm_pause' if profile.is_monitoring_active else 'confirm_resume'
    callback_yes = 'confirm_pause_resume_yes'
    callback_no = 'confirm_pause_resume_no'

    await query.edit_message_text(get_message(lang_code, action_key, username=profile.username or profile.profile_url), 
                                  reply_markup=confirmation_keyboard(lang_code, callback_yes, callback_no))
    return States.PAUSE_RESUME_PROFILE_CONFIRM

async def pause_resume_monitoring_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang_code = context.user_data.get('lang', 'en')
    db_session = context.bot_data['db_session']
    profile_id = context.user_data.get('profile_id_to_pause_resume')
    user_id = update.effective_user.id

    if query.data == 'confirm_pause_resume_yes':
        with db_session() as db:
            profile = get_target_account_by_id(db, profile_id)
            if profile:
                new_status = not profile.is_monitoring_active
                updated_profile = update_target_account_status(db, profile_id, new_status)
                message_key = 'monitoring_paused' if not new_status else 'monitoring_resumed'
                await query.edit_message_text(get_message(lang_code, message_key, username=updated_profile.username or updated_profile.profile_url), reply_markup=main_menu_keyboard(lang_code, is_admin(user_id)))
            else:
                await query.edit_message_text(get_message(lang_code, 'error_occured'), reply_markup=main_menu_keyboard(lang_code, is_admin(user_id)))
    else: # confirm_pause_resume_no
        await query.edit_message_text(get_message(lang_code, 'main_menu'), reply_markup=main_menu_keyboard(lang_code, is_admin(user_id)))

    return States.MAIN_MENU

# --- Get Latest Report Flow ---
async def get_latest_report_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    lang_code = context.user_data.get('lang', 'en')
    db_session = context.bot_data['db_session']

    with db_session() as db:
        user = get_or_create_user(db, user_id, lang_code)
        profiles = get_user_target_accounts(db, user.id)

    if not profiles:
        await query.edit_message_text(get_message(lang_code, 'no_profiles_monitored'), reply_markup=main_menu_keyboard(lang_code, is_admin(user_id)))
        return States.MAIN_MENU

    context.user_data['profiles_to_manage'] = {p.id: p for p in profiles}
    await query.edit_message_text(get_message(lang_code, 'select_profile_for_report'), reply_markup=profile_list_keyboard(lang_code, profiles, 'get_report_select'))
    return States.GET_REPORT_SELECT_PROFILE

async def get_latest_report_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    profile_id = int(query.data.split('_')[-1])
    lang_code = context.user_data.get('lang', 'en')
    db_session = context.bot_data['db_session']
    user_id = update.effective_user.id

    with db_session() as db:
        profile = get_target_account_by_id(db, profile_id)
        if not profile:
            await query.edit_message_text(get_message(lang_code, 'error_occured'), reply_markup=main_menu_keyboard(lang_code, is_admin(user_id)))
            return States.MAIN_MENU
        latest_snapshot = get_latest_snapshot(db, profile_id)

    if not latest_snapshot:
        await query.edit_message_text(get_message(lang_code, 'no_changes'), reply_markup=main_menu_keyboard(lang_code, is_admin(user_id)))
        return States.MAIN_MENU

    report_text = get_message(lang_code, 'report_header', username=profile.username or profile.profile_url, platform=profile.platform.capitalize())
    report_text += get_message(lang_code, 'followers_count', count=latest_snapshot.followers_count) + '\n'
    report_text += get_message(lang_code, 'following_count', count=latest_snapshot.following_count) + '\n'
    report_text += get_message(lang_code, 'last_checked', last_checked=format_datetime(latest_snapshot.timestamp, lang_code)) + '\n'

    await query.edit_message_text(report_text, reply_markup=main_menu_keyboard(lang_code, is_admin(user_id)))
    return States.MAIN_MENU

# --- Check Now Flow (similar to Get Latest Report, but triggers a check) ---
async def check_now_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    lang_code = context.user_data.get('lang', 'en')
    db_session = context.bot_data['db_session']

    with db_session() as db:
        user = get_or_create_user(db, user_id, lang_code)
        profiles = get_user_target_accounts(db, user.id)

    if not profiles:
        await query.edit_message_text(get_message(lang_code, 'no_profiles_monitored'), reply_markup=main_menu_keyboard(lang_code, is_admin(user_id)))
        return States.MAIN_MENU

    context.user_data['profiles_to_manage'] = {p.id: p for p in profiles}
    await query.edit_message_text(get_message(lang_code, 'select_profile_for_check'), reply_markup=profile_list_keyboard(lang_code, profiles, 'check_now_select'))
    return States.CHECK_NOW_SELECT_PROFILE

async def check_now_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    profile_id = int(query.data.split('_')[-1])
    lang_code = context.user_data.get('lang', 'en')
    db_session = context.bot_data['db_session']
    user_id = update.effective_user.id

    with db_session() as db:
        profile = get_target_account_by_id(db, profile_id)
        if not profile:
            await query.edit_message_text(get_message(lang_code, 'error_occured'), reply_markup=main_menu_keyboard(lang_code, is_admin(user_id)))
            return States.MAIN_MENU

    await query.edit_message_text(get_message(lang_code, 'checking_now', platform=profile.platform.capitalize(), username=profile.username or profile.profile_url), reply_markup=main_menu_keyboard(lang_code, is_admin(user_id)))
    # Trigger the monitoring job for this specific profile
    context.bot_data['scheduler'].add_job(
        func=context.bot_data['monitor_single_profile_func'], # Pass the actual function
        trigger='date',
        run_date=datetime.now(),
        args=[context.bot, context.bot_data['db_session'], profile_id],
        id=f'on_demand_check_{profile_id}_{datetime.now().timestamp()}',
        replace_existing=True # Replace if a job with same ID exists (unlikely with timestamp)
    )
    return States.MAIN_MENU

# --- Settings Flow ---
async def settings_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang_code = context.user_data.get('lang', 'en')
    await query.edit_message_text(get_message(lang_code, 'settings_menu'), reply_markup=settings_keyboard(lang_code))
    return States.SETTINGS_MENU

async def select_language_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang_code = context.user_data.get('lang', 'en')
    await query.edit_message_text(get_message(lang_code, 'choose_language'), reply_markup=language_keyboard(lang_code))
    return States.SELECT_LANGUAGE

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    new_lang_code = query.data.split('_')[-1]
    user_id = update.effective_user.id
    db_session = context.bot_data['db_session']

    with db_session() as db:
        updated_user = update_user_language(db, user_id, new_lang_code)
        if updated_user:
            context.user_data['lang'] = new_lang_code
            await query.edit_message_text(get_message(new_lang_code, 'language_changed'), reply_markup=main_menu_keyboard(new_lang_code, is_admin(user_id)))
        else:
            await query.edit_message_text(get_message(context.user_data.get('lang', 'en'), 'error_occured'), reply_markup=main_menu_keyboard(context.user_data.get('lang', 'en'), is_admin(user_id)))

    return States.MAIN_MENU

# --- Admin Handlers ---
async def admin_menu_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    lang_code = context.user_data.get('lang', 'en')

    if not is_admin(user_id):
        await query.edit_message_text(get_message(lang_code, 'not_authorized'), reply_markup=main_menu_keyboard(lang_code, is_admin(user_id)))
        return States.MAIN_MENU

    await query.edit_message_text(get_message(lang_code, 'admin_menu'), reply_markup=admin_menu_keyboard(lang_code))
    return States.ADMIN_MENU

# --- Add Monitoring Account Flow (Admin Only) ---
async def admin_add_mon_account_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    lang_code = context.user_data.get('lang', 'en')

    if not is_admin(user_id):
        await query.edit_message_text(get_message(lang_code, 'not_authorized'), reply_markup=main_menu_keyboard(lang_code, is_admin(user_id)))
        return States.MAIN_MENU

    await query.edit_message_text(get_message(lang_code, 'enter_mon_account_platform'), reply_markup=mon_account_platform_selection_keyboard(lang_code))
    return States.ADD_MON_ACCOUNT_PLATFORM

async def admin_add_mon_account_platform_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    lang_code = context.user_data.get('lang', 'en')

    if not is_admin(user_id):
        await query.edit_message_text(get_message(lang_code, 'not_authorized'), reply_markup=main_menu_keyboard(lang_code, is_admin(user_id)))
        return States.MAIN_MENU

    platform = query.data.split('_')[-1]
    context.user_data['new_mon_account_platform'] = platform
    await query.edit_message_text(get_message(lang_code, 'enter_mon_account_username'))
    return States.ADD_MON_ACCOUNT_USERNAME

async def admin_add_mon_account_username_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    lang_code = context.user_data.get('lang', 'en')

    if not is_admin(user_id):
        await update.message.reply_text(get_message(lang_code, 'not_authorized'), reply_markup=main_menu_keyboard(lang_code, is_admin(user_id)))
        return States.MAIN_MENU

    username = update.message.text.strip()
    context.user_data['new_mon_account_username'] = username
    await update.message.reply_text(get_message(lang_code, 'enter_mon_account_password'))
    return States.ADD_MON_ACCOUNT_PASSWORD

async def admin_add_mon_account_password_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    lang_code = context.user_data.get('lang', 'en')

    if not is_admin(user_id):
        await update.message.reply_text(get_message(lang_code, 'not_authorized'), reply_markup=main_menu_keyboard(lang_code, is_admin(user_id)))
        return States.MAIN_MENU

    password = update.message.text.strip()
    platform = context.user_data.get('new_mon_account_platform')
    username = context.user_data.get('new_mon_account_username')
    db_session = context.bot_data['db_session']

    await update.message.reply_text(get_message(lang_code, 'processing_request'))

    monitor_class = None
    if platform == 'tiktok':
        monitor_class = TikTokMonitor
    elif platform == 'instagram':
        monitor_class = InstagramMonitor

    if not monitor_class:
        await update.message.reply_text(get_message(lang_code, 'error_occured'), reply_markup=admin_menu_keyboard(lang_code))
        return States.ADMIN_MENU

    # Create a dummy ID for the monitor instance, it will get a real ID from DB later
    temp_account_id = 0 # This ID is just for the monitor instance, not the DB record
    monitor = monitor_class(account_id=temp_account_id, username=username, password=password)

    try:
        # Attempt to log in and save cookies
        login_result = await monitor.run(headless=HEADLESS_MODE) # Force headless for bot-driven login

        if login_result and login_result.get("status") == "logged_in":
            cookies_path = login_result.get("cookies_path")
            with db_session() as db:
                new_mon_account = add_monitoring_account(db, platform, username, password, cookies_path=cookies_path)
                await update.message.reply_text(get_message(lang_code, 'mon_account_added_success', username=username, platform=platform.capitalize()), reply_markup=admin_menu_keyboard(lang_code))
        else:
            await update.message.reply_text(get_message(lang_code, 'mon_account_login_failed'), reply_markup=admin_menu_keyboard(lang_code))
    except Exception as e:
        logger.error(f"Error adding monitoring account: {e}", exc_info=True)
        await update.message.reply_text(get_message(lang_code, 'mon_account_add_failed'), reply_markup=admin_menu_keyboard(lang_code))

    return States.ADMIN_MENU

# --- List Monitoring Accounts Flow (Admin Only) ---
async def admin_list_mon_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    lang_code = context.user_data.get('lang', 'en')

    if not is_admin(user_id):
        await query.edit_message_text(get_message(lang_code, 'not_authorized'), reply_markup=main_menu_keyboard(lang_code, is_admin(user_id)))
        return States.MAIN_MENU

    db_session = context.bot_data['db_session']
    with db_session() as db:
        mon_accounts = get_all_monitoring_accounts(db)

    if not mon_accounts:
        await query.edit_message_text(get_message(lang_code, 'no_monitoring_accounts'), reply_markup=admin_menu_keyboard(lang_code))
        return States.ADMIN_MENU

    response_text = get_message(lang_code, 'mon_account_list_header')
    for acc in mon_accounts:
        cookies_status = "Yes" if acc.cookies_path and os.path.exists(acc.cookies_path) else "No"
        last_used_str = format_datetime(acc.last_used_at, lang_code) if acc.last_used_at else "Never"
        response_text += get_message(lang_code, 'mon_account_details',
                                     id=acc.id,
                                     platform=acc.platform.capitalize(),
                                     username=acc.username,
                                     active=get_message(lang_code, 'status_active') if acc.is_active else get_message(lang_code, 'status_paused'),
                                     last_used=last_used_str,
                                     cookies_status=cookies_status)
        response_text += "\n"

    await query.edit_message_text(response_text, reply_markup=admin_menu_keyboard(lang_code))
    return States.ADMIN_MENU

# --- Remove Monitoring Account Flow (Admin Only) ---
async def admin_remove_mon_account_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    lang_code = context.user_data.get('lang', 'en')

    if not is_admin(user_id):
        await query.edit_message_text(get_message(lang_code, 'not_authorized'), reply_markup=main_menu_keyboard(lang_code, is_admin(user_id)))
        return States.MAIN_MENU

    db_session = context.bot_data['db_session']
    with db_session() as db:
        mon_accounts = get_all_monitoring_accounts(db)

    if not mon_accounts:
        await query.edit_message_text(get_message(lang_code, 'no_monitoring_accounts'), reply_markup=admin_menu_keyboard(lang_code))
        return States.ADMIN_MENU

    context.user_data['mon_accounts_to_manage'] = {acc.id: acc for acc in mon_accounts}
    await query.edit_message_text(get_message(lang_code, 'select_mon_account_to_remove'), reply_markup=monitoring_account_list_keyboard(lang_code, mon_accounts, 'admin_remove_mon_select'))
    return States.REMOVE_MON_ACCOUNT_SELECT

async def admin_remove_mon_account_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    lang_code = context.user_data.get('lang', 'en')

    if not is_admin(user_id):
        await query.edit_message_text(get_message(lang_code, 'not_authorized'), reply_markup=main_menu_keyboard(lang_code, is_admin(user_id)))
        return States.MAIN_MENU

    mon_account_id = int(query.data.split('_')[-1])
    mon_account = context.user_data['mon_accounts_to_manage'].get(mon_account_id)

    if not mon_account:
        await query.edit_message_text(get_message(lang_code, 'error_occured'), reply_markup=admin_menu_keyboard(lang_code))
        return States.ADMIN_MENU

    context.user_data['mon_account_id_to_remove'] = mon_account_id
    await query.edit_message_text(get_message(lang_code, 'confirm_remove_mon_account', username=mon_account.username, platform=mon_account.platform.capitalize()),
                                  reply_markup=confirmation_keyboard(lang_code, 'admin_confirm_remove_mon_yes', 'admin_confirm_remove_mon_no'))
    return States.REMOVE_MON_ACCOUNT_CONFIRM

async def admin_remove_mon_account_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    lang_code = context.user_data.get('lang', 'en')

    if not is_admin(user_id):
        await query.edit_message_text(get_message(lang_code, 'not_authorized'), reply_markup=main_menu_keyboard(lang_code, is_admin(user_id)))
        return States.MAIN_MENU

    mon_account_id = context.user_data.get('mon_account_id_to_remove')
    db_session = context.bot_data['db_session']

    if query.data == 'admin_confirm_remove_mon_yes':
        with db_session() as db:
            mon_account = get_monitoring_account(db, mon_account_id)
            if mon_account and delete_monitoring_account(db, mon_account_id):
                # Optionally delete cookies file
                if mon_account.cookies_path and os.path.exists(mon_account.cookies_path):
                    try:
                        os.remove(mon_account.cookies_path)
                        logger.info(f"Deleted cookies file: {mon_account.cookies_path}")
                    except Exception as e:
                        logger.warning(f"Could not delete cookies file {mon_account.cookies_path}: {e}")

                await query.edit_message_text(get_message(lang_code, 'mon_account_removed', username=mon_account.username, platform=mon_account.platform.capitalize()), reply_markup=admin_menu_keyboard(lang_code))
            else:
                await query.edit_message_text(get_message(lang_code, 'mon_account_remove_failed'), reply_markup=admin_menu_keyboard(lang_code))
    else: # admin_confirm_remove_mon_no
        await query.edit_message_text(get_message(lang_code, 'admin_menu'), reply_markup=admin_menu_keyboard(lang_code))

    return States.ADMIN_MENU

# --- Fallback Handler ---
async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang_code = context.user_data.get('lang', 'en')
    user_id = update.effective_user.id
    if update.message:
        await update.message.reply_text(get_message(lang_code, 'select_action'), reply_markup=main_menu_keyboard(lang_code, is_admin(user_id)))
    elif update.callback_query:
        await update.callback_query.edit_message_text(get_message(lang_code, 'select_action'), reply_markup=main_menu_keyboard(lang_code, is_admin(user_id)))
    return States.MAIN_MENU


