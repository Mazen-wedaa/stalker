
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bot.localization import get_message
from typing import List
from db.models import TargetAccount, MonitoringAccount

def main_menu_keyboard(lang_code: str, is_admin: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(get_message(lang_code, 'add_profile'), callback_data='add_profile')],
        [InlineKeyboardButton(get_message(lang_code, 'get_latest_report'), callback_data='get_latest_report')],
        [InlineKeyboardButton(get_message(lang_code, 'check_now'), callback_data='check_now')],
        [InlineKeyboardButton(get_message(lang_code, 'pause_monitoring'), callback_data='pause_monitoring')],
        [InlineKeyboardButton(get_message(lang_code, 'remove_account'), callback_data='remove_account')],
        [InlineKeyboardButton(get_message(lang_code, 'settings'), callback_data='settings')],
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(get_message(lang_code, 'admin_menu'), callback_data='admin_menu')])
    return InlineKeyboardMarkup(buttons)

def platform_selection_keyboard(lang_code: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(get_message(lang_code, 'tiktok'), callback_data='select_platform_tiktok')],
        [InlineKeyboardButton(get_message(lang_code, 'instagram'), callback_data='select_platform_instagram')],
        [InlineKeyboardButton(get_message(lang_code, 'back_to_main_menu'), callback_data='main_menu')],
    ]
    return InlineKeyboardMarkup(buttons)

def settings_keyboard(lang_code: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(get_message(lang_code, 'language_selection'), callback_data='select_language')],
        [InlineKeyboardButton(get_message(lang_code, 'back_to_main_menu'), callback_data='main_menu')],
    ]
    return InlineKeyboardMarkup(buttons)

def language_keyboard(lang_code: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton('English 🇬🇧', callback_data='set_lang_en')],
        [InlineKeyboardButton('العربية 🇸🇦', callback_data='set_lang_ar')],
        [InlineKeyboardButton(get_message(lang_code, 'back_to_main_menu'), callback_data='main_menu')],
    ]
    return InlineKeyboardMarkup(buttons)

def profile_list_keyboard(lang_code: str, profiles: List[TargetAccount], action_prefix: str) -> InlineKeyboardMarkup:
    buttons = []
    if not profiles:
        return InlineKeyboardMarkup([[InlineKeyboardButton(get_message(lang_code, 'back_to_main_menu'), callback_data='main_menu')]])

    for profile in profiles:
        status_key = 'status_active' if profile.is_monitoring_active else 'status_paused'
        status_text = get_message(lang_code, status_key)
        button_text = f'{profile.username or profile.profile_url.split("/")[-2]} ({profile.platform.capitalize()}) - {status_text}'
        buttons.append([InlineKeyboardButton(button_text, callback_data=f'{action_prefix}_{profile.id}')])

    buttons.append([InlineKeyboardButton(get_message(lang_code, 'back_to_main_menu'), callback_data='main_menu')])
    return InlineKeyboardMarkup(buttons)

def confirmation_keyboard(lang_code: str, callback_data_yes: str, callback_data_no: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(get_message(lang_code, 'yes'), callback_data=callback_data_yes),
         InlineKeyboardButton(get_message(lang_code, 'no'), callback_data=callback_data_no)],
    ]
    return InlineKeyboardMarkup(buttons)

# --- Admin Keyboards ---
def admin_menu_keyboard(lang_code: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(get_message(lang_code, 'add_monitoring_account'), callback_data='admin_add_mon_account')],
        [InlineKeyboardButton(get_message(lang_code, 'list_monitoring_accounts'), callback_data='admin_list_mon_accounts')],
        [InlineKeyboardButton(get_message(lang_code, 'remove_monitoring_account'), callback_data='admin_remove_mon_account')],
        [InlineKeyboardButton(get_message(lang_code, 'back_to_main_menu'), callback_data='main_menu')],
    ]
    return InlineKeyboardMarkup(buttons)

def mon_account_platform_selection_keyboard(lang_code: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(get_message(lang_code, 'tiktok'), callback_data='admin_add_mon_tiktok')],
        [InlineKeyboardButton(get_message(lang_code, 'instagram'), callback_data='admin_add_mon_instagram')],
        [InlineKeyboardButton(get_message(lang_code, 'back_to_main_menu'), callback_data='admin_menu')],
    ]
    return InlineKeyboardMarkup(buttons)

def monitoring_account_list_keyboard(lang_code: str, accounts: List[MonitoringAccount], action_prefix: str) -> InlineKeyboardMarkup:
    buttons = []
    if not accounts:
        return InlineKeyboardMarkup([[InlineKeyboardButton(get_message(lang_code, 'back_to_main_menu'), callback_data='admin_menu')]])

    for account in accounts:
        button_text = f'{account.username} ({account.platform.capitalize()})'
        buttons.append([InlineKeyboardButton(button_text, callback_data=f'{action_prefix}_{account.id}')])

    buttons.append([InlineKeyboardButton(get_message(lang_code, 'back_to_main_menu'), callback_data='admin_menu')])
    return InlineKeyboardMarkup(buttons)


