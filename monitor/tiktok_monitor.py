
import asyncio
import random
from playwright.async_api import Playwright, async_playwright, expect
import logging
from monitor.base_monitor import BaseMonitor
import re
import json

logger = logging.getLogger(__name__)

class TikTokMonitor(BaseMonitor):
    def __init__(self, account_id: int, username: str, password: str, proxy: str = None, cookies_path: str = None):
        super().__init__(account_id, username, password, proxy, cookies_path)
        self.base_url = 'https://www.tiktok.com'

    async def perform_login(self) -> bool:
        logger.info(f'Attempting TikTok login for {self.username}')
        try:
            await self.page.goto(f'{self.base_url}/login')
            await asyncio.sleep(random.uniform(2, 4))

            # Try to click 'Use phone / email / username'
            try:
                await self.page.locator('text=Use phone / email / username').click(timeout=5000)
                await asyncio.sleep(random.uniform(1, 2))
            except Exception:
                logger.info('Phone/email/username option not found or already selected.')

            # Fill in username and password
            await self.page.fill('input[name="username"]', self.username)
            await self.page.fill('input[name="password"]', self.password)
            await asyncio.sleep(random.uniform(1, 2))

            # Click login button
            await self.page.locator('button[type="submit"]').click()
            await asyncio.sleep(random.uniform(5, 10)) # Wait for navigation and potential CAPTCHA

            return await self.check_login_status()

        except Exception as e:
            logger.error(f'Error during TikTok login for {self.username}: {e}')
            return False

    async def check_login_status(self) -> bool:
        """Checks if the current Playwright session is logged into TikTok."""
        try:
            # Navigate to a page that requires login (e.g., For You page)
            await self.page.goto(f'{self.base_url}/foryou', wait_until='domcontentloaded')
            await asyncio.sleep(random.uniform(2, 3))
            # Check for an element that is only present when logged in (e.g., a profile icon or feed tab)
            # This selector might need to be updated if TikTok's UI changes.
            is_logged_in = await self.page.locator('div[data-e2e="feed-tab"]').is_visible(timeout=5000)
            if is_logged_in:
                logger.info(f'TikTok session for {self.username} is active.')
            else:
                logger.warning(f'TikTok session for {self.username} is NOT active.')
            return is_logged_in
        except Exception as e:
            logger.warning(f'Could not verify TikTok login status for {self.username}: {e}')
            return False

    async def get_followers_and_following(self, profile_url: str) -> dict:
        logger.info(f'Navigating to TikTok profile: {profile_url}')
        try:
            await self.page.goto(profile_url, wait_until='domcontentloaded')
            await asyncio.sleep(random.uniform(3, 6)) # Wait for page to load and dynamic content

            # Scroll down to ensure all elements are loaded (if necessary)
            await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(random.uniform(1, 2))

            # Extract follower/following counts
            followers_count_text = await self.page.locator('strong[data-e2e="followers-count"]').text_content()
            following_count_text = await self.page.locator('strong[data-e2e="following-count"]').text_content()

            followers_count = self._parse_count(followers_count_text)
            following_count = self._parse_count(following_count_text)

            logger.info(f'TikTok profile {profile_url}: Followers={followers_count}, Following={following_count}')

            # Attempt to get follower/following lists (this is more complex and might require scrolling/clicking)
            followers_list = [] # Placeholder
            following_list = [] # Placeholder

            return {
                'followers_count': followers_count,
                'following_count': following_count,
                'followers_list': json.dumps(followers_list),
                'following_list': json.dumps(following_list),
            }

        except Exception as e:
            logger.error(f'Error getting TikTok data for {profile_url}: {e}')
            return None

    def _parse_count(self, count_str: str) -> int:
        count_str = count_str.replace(',', '').replace('.', '').strip().lower()
        if 'k' in count_str:
            return int(float(count_str.replace('k', '')) * 1000)
        elif 'm' in count_str:
            return int(float(count_str.replace('m', '')) * 1000000)
        return int(count_str)


