import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
from config.settings import TELEGRAM_BOT_TOKEN, DATABASE_URL, LOG_LEVEL
from db.models import init_db, SessionLocal
from scheduler.job_runner import setup_monitoring_jobs, monitor_single_profile # Import monitor_single_profile
from bot.handlers import (start, main_menu, add_profile_start, add_profile_platform_selected,
                          add_profile_url_received, remove_profile_start, remove_profile_selected,
                          remove_profile_confirm, pause_resume_monitoring_start, pause_resume_monitoring_selected,
                          pause_resume_monitoring_confirm, get_latest_report_start, get_latest_report_selected,
                          check_now_start, check_now_selected, settings_start, select_language_start, set_language,
                          admin_menu_start, admin_add_mon_account_start, admin_add_mon_account_platform_selected,
                          admin_add_mon_account_username_received, admin_add_mon_account_password_received,
                          admin_list_mon_accounts, admin_remove_mon_account_start, admin_remove_mon_account_selected,
                          admin_remove_mon_account_confirm, fallback)
from bot.states import States
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update # Import Update for allowed_updates

logging.basicConfig(
    format=\'%(asctime)s - %(name)s - %(levelname)s - %(message)s\', level=getattr(logging, LOG_LEVEL.upper())
)
logger = logging.getLogger(__name__)

def main() -> None:
    # Initialize database
    init_db()

    # Create the Application and pass your bot\'s token.
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Store db_session factory and monitor_single_profile func in bot_data for easy access in handlers
    application.bot_data[\'db_session\'] = SessionLocal
    application.bot_data[\'monitor_single_profile_func\'] = monitor_single_profile # Pass the function itself

    # Setup APScheduler
    scheduler = AsyncIOScheduler()
    application.bot_data[\'scheduler\'] = scheduler
    setup_monitoring_jobs(scheduler, application.bot_data[\'db_session\'], application.bot)
    scheduler.start()

    # Conversation Handler for managing states
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler(\'start\', start)],
        states={
            States.MAIN_MENU: [
                CallbackQueryHandler(add_profile_start, pattern=\'^add_profile$\'),
                CallbackQueryHandler(get_latest_report_start, pattern=\'^get_latest_report$\'),
                CallbackQueryHandler(check_now_start, pattern=\'^check_now$\'),
                CallbackQueryHandler(pause_resume_monitoring_start, pattern=\'^pause_monitoring$\'),
                CallbackQueryHandler(remove_profile_start, pattern=\'^remove_account$\'), # Corrected from remove_profile_start
                CallbackQueryHandler(settings_start, pattern=\'^settings$\'),
                CallbackQueryHandler(admin_menu_start, pattern=\'^admin_menu$\'), # Admin menu entry
            ],
            States.ADD_PROFILE_PLATFORM: [
                CallbackQueryHandler(add_profile_platform_selected, pattern=\'^select_platform_(tiktok|instagram)$\'),
                CallbackQueryHandler(main_menu, pattern=\'^main_menu$\'),
            ],
            States.ADD_PROFILE_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_profile_url_received),
                CallbackQueryHandler(main_menu, pattern=\'^main_menu$\'), # Allow going back from URL input
            ],
            States.REMOVE_PROFILE_CONFIRM: [
                CallbackQueryHandler(remove_profile_selected, pattern=\'^remove_profile_select_\\d+$\'),
                CallbackQueryHandler(remove_profile_confirm, pattern=\'^(confirm_remove_yes|confirm_remove_no)$\'),
                CallbackQueryHandler(main_menu, pattern=\'^main_menu$\'),
            ],
            States.PAUSE_RESUME_PROFILE_CONFIRM: [
                CallbackQueryHandler(pause_resume_monitoring_selected, pattern=\'^pause_resume_select_\\d+$\'),
                CallbackQueryHandler(pause_resume_monitoring_confirm, pattern=\'^confirm_pause_resume_yes|confirm_pause_resume_no$\'),
                CallbackQueryHandler(main_menu, pattern=\'^main_menu$\'),
            ],
            States.GET_REPORT_SELECT_PROFILE: [
                CallbackQueryHandler(get_latest_report_selected, pattern=\'^get_report_select_\\d+$\'),
                CallbackQueryHandler(main_menu, pattern=\'^main_menu$\'),
            ],
            States.CHECK_NOW_SELECT_PROFILE: [
                CallbackQueryHandler(check_now_selected, pattern=\'^check_now_select_\\d+$\'),
                CallbackQueryHandler(main_menu, pattern=\'^main_menu$\'),
            ],
            States.SETTINGS_MENU: [
                CallbackQueryHandler(select_language_start, pattern=\'^select_language$\'),
                CallbackQueryHandler(main_menu, pattern=\'^main_menu$\'),
            ],
            States.SELECT_LANGUAGE: [
                CallbackQueryHandler(set_language, pattern=\'^set_lang_(en|ar)$\'),
                CallbackQueryHandler(main_menu, pattern=\'^main_menu$\'),
            ],
            # Admin States
            States.ADMIN_MENU: [
                CallbackQueryHandler(admin_add_mon_account_start, pattern=\'^admin_add_mon_account$\'),
                CallbackQueryHandler(admin_list_mon_accounts, pattern=\'^admin_list_mon_accounts$\'),
                CallbackQueryHandler(admin_remove_mon_account_start, pattern=\'^admin_remove_mon_account$\'),
                CallbackQueryHandler(main_menu, pattern=\'^main_menu$\'),
            ],
            States.ADD_MON_ACCOUNT_PLATFORM: [
                CallbackQueryHandler(admin_add_mon_account_platform_selected, pattern=\'^admin_add_mon_(tiktok|instagram)$\'),
                CallbackQueryHandler(admin_menu_start, pattern=\'^admin_menu$\'), # Back to admin menu
            ],
            States.ADD_MON_ACCOUNT_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_mon_account_username_received),
                CallbackQueryHandler(admin_menu_start, pattern=\'^admin_menu$\'), # Back to admin menu
            ],
            States.ADD_MON_ACCOUNT_PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_mon_account_password_received),
                CallbackQueryHandler(admin_menu_start, pattern=\'^admin_menu$\'), # Back to admin menu
            ],
            States.REMOVE_MON_ACCOUNT_SELECT: [
                CallbackQueryHandler(admin_remove_mon_account_selected, pattern=\'^admin_remove_mon_select_\\d+$\'),
                CallbackQueryHandler(admin_menu_start, pattern=\'^admin_menu$\'), # Back to admin menu
            ],
            States.REMOVE_MON_ACCOUNT_CONFIRM: [
                CallbackQueryHandler(admin_remove_mon_account_confirm, pattern=\'^(admin_confirm_remove_mon_yes|admin_confirm_remove_mon_no)$\'),
                CallbackQueryHandler(admin_menu_start, pattern=\'^admin_menu$\'), # Back to admin menu
            ],
        },
        fallbacks=[MessageHandler(filters.TEXT | filters.COMMAND, fallback), CallbackQueryHandler(fallback)],
    )

    application.add_handler(conv_handler)

    # Run the bot until the user presses Ctrl-C
    logger.info(\'Bot started polling...\')
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == \'__main__\':
    main()


