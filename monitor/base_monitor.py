import asyncio
from playwright.async_api import Playwright, async_playwright, expect
import logging
import os
import json
from config.settings import HEADLESS_MODE, USER_AGENT, COOKIES_DIR
from datetime import datetime

logger = logging.getLogger(__name__)

class BaseMonitor:
    def __init__(self, account_id: int, username: str, password: str, proxy: str = None, cookies_path: str = None):
        self.account_id = account_id
        self.username = username
        self.password = password
        self.proxy = proxy
        self.cookies_path = cookies_path or os.path.join(COOKIES_DIR, f'{self.account_id}_cookies.json')
        self.browser = None
        self.context = None
        self.page = None

        os.makedirs(COOKIES_DIR, exist_ok=True)

    async def launch_browser(self, playwright: Playwright, headless: bool = HEADLESS_MODE):
        launch_options = {
            'headless': headless, # Allow overriding headless for manual login via bot
            'args': ['--no-sandbox', '--disable-setuid-sandbox'],
        }
        if self.proxy:
            launch_options['proxy'] = {'server': self.proxy}
            logger.info(f'Using proxy {self.proxy} for account {self.username}')

        self.browser = await playwright.chromium.launch(**launch_options)
        logger.info(f'Browser launched for account {self.username} (headless: {headless})')

    async def create_context(self):
        context_options = {
            'user_agent': USER_AGENT,
            'viewport': {'width': 1280, 'height': 720}, # Common desktop resolution
            'locale': 'en-US',
            'timezone_id': 'America/New_York',
        }

        if os.path.exists(self.cookies_path):
            try:
                self.context = await self.browser.new_context(storage_state=self.cookies_path, **context_options)
                logger.info(f'Loaded cookies for account {self.username} from {self.cookies_path}')
            except Exception as e:
                logger.warning(f'Could not load cookies for {self.username}: {e}. Starting fresh.')
                self.context = await self.browser.new_context(**context_options)
        else:
            self.context = await self.browser.new_context(**context_options)

        # Add stealth options (basic ones, more advanced might need external libraries like playwright-stealth)
        await self.context.add_init_script('Object.defineProperty(navigator, "webdriver", {get: () => undefined})')
        await self.context.add_init_script('window.chrome = {runtime: {}, csi: function(){}, loadTimes: function(){}, app: {}}')
        await self.context.add_init_script('Object.defineProperty(navigator, "plugins", {get: () => [1, 2, 3, 4, 5]})')
        await self.context.add_init_script('Object.defineProperty(navigator, "languages", {get: () => ["en-US", "en"]})')

        self.page = await self.context.new_page()
        logger.info(f'New page created for account {self.username}')

    async def save_cookies(self):
        if self.context:
            await self.context.storage_state(path=self.cookies_path)
            logger.info(f'Saved cookies for account {self.username} to {self.cookies_path}')

    async def close_browser(self):
        if self.browser:
            await self.browser.close()
            logger.info(f'Browser closed for account {self.username}')

    async def perform_login(self) -> bool:
        """
        Abstract method for logging into the platform.
        Must be implemented by subclasses.
        Returns True if login is successful, False otherwise.
        """
        raise NotImplementedError

    async def check_login_status(self) -> bool:
        """
        Abstract method to check if the current session is logged in.
        Must be implemented by subclasses.
        Returns True if logged in, False otherwise.
        """
        raise NotImplementedError

    async def get_followers_and_following(self, profile_url: str) -> dict:
        """
        Abstract method for getting follower/following data.
        Must be implemented by subclasses.
        Returns a dict with 'followers_count', 'following_count', 'followers_list', 'following_list'.
        """
        raise NotImplementedError

    async def run(self, profile_url: str = None, headless: bool = HEADLESS_MODE) -> dict:
        """
        Main method to run the monitoring process or perform login.
        If profile_url is None, it's assumed to be a login-only run.
        """
        async with async_playwright() as playwright:
            try:
                await self.launch_browser(playwright, headless=headless)
                await self.create_context()

                is_logged_in = await self.check_login_status()
                if not is_logged_in:
                    logger.info(f'Account {self.username} not logged in. Attempting login.')
                    if not await self.perform_login():
                        logger.error(f'Failed to log in with account {self.username}.')
                        return None
                    await self.save_cookies()
                    # Re-check login status after attempting login
                    is_logged_in = await self.check_login_status()
                    if not is_logged_in:
                        logger.error(f'Login attempt for {self.username} failed to establish a valid session.')
                        return None
                else:
                    logger.info(f'Account {self.username} already logged in.')

                if profile_url:
                    data = await self.get_followers_and_following(profile_url)
                    return data
                else:
                    # If no profile_url, it means we just wanted to log in and save cookies
                    return {"status": "logged_in", "cookies_path": self.cookies_path}

            except Exception as e:
                logger.error(f'Error during monitoring/login for {self.username}: {e}', exc_info=True)
                return None
            finally:
                await self.close_browser()


