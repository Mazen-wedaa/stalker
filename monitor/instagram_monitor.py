
import asyncio
import random
from playwright.async_api import Playwright, async_playwright, expect
import logging
from monitor.base_monitor import BaseMonitor
import re
import json

logger = logging.getLogger(__name__)

class InstagramMonitor(BaseMonitor):
    def __init__(self, account_id: int, username: str, password: str, proxy: str = None, cookies_path: str = None):
        super().__init__(account_id, username, password, proxy, cookies_path)
        self.base_url = 'https://www.instagram.com'

    async def perform_login(self) -> bool:
        logger.info(f'Attempting Instagram login for {self.username}')
        try:
            await self.page.goto(f'{self.base_url}/accounts/login/')
            await asyncio.sleep(random.uniform(3, 5))

            # Fill in username and password
            await self.page.fill('input[name="username"]', self.username)
            await self.page.fill('input[name="password"]', self.password)
            await asyncio.sleep(random.uniform(1, 2))

            # Click login button
            await self.page.locator('button[type="submit"]').click()
            await asyncio.sleep(random.uniform(5, 10)) # Wait for navigation and potential 2FA/security checks

            # Check for 'Not Now' on 'Save Your Login Info?' or 'Turn On Notifications'
            try:
                await self.page.locator('button:has-text("Not Now")').click(timeout=5000)
                await asyncio.sleep(random.uniform(1, 2))
            except Exception:
                logger.info('Save login info prompt not found or handled.')

            try:
                await self.page.locator('button:has-text("Not Now")').click(timeout=5000)
                await asyncio.sleep(random.uniform(1, 2))
            except Exception:
                logger.info('Turn on notifications prompt not found or handled.')

            return await self.check_login_status()

        except Exception as e:
            logger.error(f'Error during Instagram login for {self.username}: {e}')
            return False

    async def check_login_status(self) -> bool:
        """Checks if the current Playwright session is logged into Instagram."""
        try:
            # Navigate to a page that requires login (e.g., home feed)
            await self.page.goto(f'{self.base_url}/', wait_until='domcontentloaded')
            await asyncio.sleep(random.uniform(2, 3))
            # Check for an element that is only present when logged in (e.g., a home icon)
            # This selector might need to be updated if Instagram's UI changes.
            is_logged_in = await self.page.locator('a[href="/"] svg[aria-label="Home"]').is_visible(timeout=5000)
            if is_logged_in:
                logger.info(f'Instagram session for {self.username} is active.')
            else:
                logger.warning(f'Instagram session for {self.username} is NOT active.')
            return is_logged_in
        except Exception as e:
            logger.warning(f'Could not verify Instagram login status for {self.username}: {e}')
            return False

    async def get_followers_and_following(self, profile_url: str) -> dict:
        logger.info(f'Navigating to Instagram profile: {profile_url}')
        try:
            await self.page.goto(profile_url, wait_until='domcontentloaded')
            await asyncio.sleep(random.uniform(3, 6)) # Wait for page to load and dynamic content

            # Check if profile is private or not found
            if await self.page.locator('text=This Account is Private').is_visible(timeout=5000):
                logger.warning(f'Instagram profile {profile_url} is private.')
                return {'followers_count': 0, 'following_count': 0, 'followers_list': '[]', 'following_list': '[]', 'private': True}
            if await self.page.locator('text=Sorry, this page isn\'t available.').is_visible(timeout=5000):
                logger.warning(f'Instagram profile {profile_url} not found.')
                return {'followers_count': 0, 'following_count': 0, 'followers_list': '[]', 'following_list': '[]', 'not_found': True}

            # Extract follower/following counts
            followers_count = 0
            following_count = 0

            try:
                followers_text = await self.page.locator('a[href$="/followers/"] span[title]').first.text_content()
                followers_count = self._parse_count(followers_text)
            except Exception:
                logger.warning('Could not find Instagram followers count using primary selector. Trying alternative.')
                try:
                    followers_aria_label = await self.page.locator('a[href$="/followers/"]').first.get_attribute('aria-label')
                    if followers_aria_label:
                        match = re.search(r'(\d[\d,\.]*) Followers', followers_aria_label)
                        if match: followers_count = self._parse_count(match.group(1))
                except Exception: pass

            try:
                following_text = await self.page.locator('a[href$="/following/"] span[title]').first.text_content()
                following_count = self._parse_count(following_text)
            except Exception:
                logger.warning('Could not find Instagram following count using primary selector. Trying alternative.')
                try:
                    following_aria_label = await self.page.locator('a[href$="/following/"]').first.get_attribute('aria-label')
                    if following_aria_label:
                        match = re.search(r'(\d[\d,\.]*) Following', following_aria_label)
                        if match: following_count = self._parse_count(match.group(1))
                except Exception: pass

            logger.info(f'Instagram profile {profile_url}: Followers={followers_count}, Following={following_count}')

            followers_list = [] # Placeholder
            following_list = [] # Placeholder

            return {
                'followers_count': followers_count,
                'following_count': following_count,
                'followers_list': json.dumps(followers_list),
                'following_list': json.dumps(following_list),
            }

        except Exception as e:
            logger.error(f'Error getting Instagram data for {profile_url}: {e}')
            return None

    def _parse_count(self, count_str: str) -> int:
        count_str = count_str.replace(',', '').replace('.', '').strip().lower()
        if 'k' in count_str:
            return int(float(count_str.replace('k', '')) * 1000)
        elif 'm' in count_str:
            return int(float(count_str.replace('m', '')) * 1000000)
        return int(count_str)


