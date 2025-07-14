import os
from dotenv import load_dotenv
import json

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./db/bot.db')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
MONITORING_INTERVAL_HOURS = int(os.getenv('MONITORING_INTERVAL_HOURS', 6))
PROXY_LIST_PATH = os.getenv('PROXY_LIST_PATH', 'config/proxies.txt')

# List of Telegram User IDs who are admins and can add monitoring accounts
# Example: ADMIN_TELEGRAM_IDS = [123456789, 987654321]
ADMIN_TELEGRAM_IDS = json.loads(os.getenv('ADMIN_TELEGRAM_IDS', '[]'))

# Playwright settings
HEADLESS_MODE = os.getenv('HEADLESS_MODE', 'true').lower() == 'true'
USER_AGENT = os.getenv('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')

# Paths
COOKIES_DIR = 'monitor/cookies'


