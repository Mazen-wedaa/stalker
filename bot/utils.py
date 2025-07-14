
import re
from datetime import datetime

def is_valid_tiktok_url(url: str) -> bool:
    # Basic regex for TikTok profile URLs
    return re.match(r"^https?://(www\.)?tiktok\.com/@([a-zA-Z0-9_\.-]+)/?$", url) is not None

def is_valid_instagram_url(url: str) -> bool:
    # Basic regex for Instagram profile URLs
    return re.match(r"^https?://(www\.)?instagram\.com/([a-zA-Z0-9_\.-]+)/?$", url) is not None

def extract_username_from_url(url: str) -> str:
    match_tiktok = re.match(r"^https?://(www\.)?tiktok\.com/@([a-zA-Z0-9_\.-]+)/?$", url)
    if match_tiktok: 
        return match_tiktok.group(2)
    
    match_instagram = re.match(r"^https?://(www\.)?instagram\.com/([a-zA-Z0-9_\.-]+)/?$", url)
    if match_instagram:
        return match_instagram.group(2)
        
    return ""

def format_datetime(dt: datetime, lang_code: str) -> str:
    if lang_code == 'ar':
        # Example for Arabic formatting, can be more sophisticated with babel
        return dt.strftime('%Y-%m-%d %H:%M:%S') # Or use a library for proper localization
    else:
        return dt.strftime('%Y-%m-%d %H:%M:%S')


