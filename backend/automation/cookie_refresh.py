"""
Gemini Ultra Gateway - Cookie Refresh Manager
Automatic cookie refresh using email verification and browser session maintenance

Combines best features from:
- business-gemini-x (Python Playwright automation)
- business2api (Go browser registration)

Features:
- Automatic cookie refresh using temporary email
- Browser session maintenance (keeps session alive)
- Verification code extraction from email
- Multi-provider tempmail support
"""

import re
import time
import json
import logging
import asyncio
import threading
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..core.config import Config, BEIJING_TZ
from ..core.account_pool import Account, get_account_pool
from .tempmail_api import TempMailClient

logger = logging.getLogger("gemini.automation.cookie_refresh")

# Check Playwright availability
PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    logger.warning("Playwright not installed. Auto cookie refresh not available.")
    logger.warning("Install: pip install playwright && playwright install chromium")

# Common words to filter out when extracting verification codes
VERIFICATION_CODE_EXCLUDES = {
    "VERIFY", "GOOGLE", "UPDATE", "MOBILE", "DEVICE",
    "SUBMIT", "RESEND", "CANCEL", "DELETE", "REMOVE",
    "SEARCH", "VIDEOS", "IMAGES", "GMAIL", "EMAIL",
    "ACCOUNT", "CHROME"
}


def extract_verification_code(content: str) -> Optional[str]:
    """Extract 6-character verification code from email content"""
    # Find all 6-character alphanumeric codes
    codes = re.findall(r'\b[A-Z0-9]{6}\b', content)
    
    # Filter out common words
    for code in codes:
        if code not in VERIFICATION_CODE_EXCLUDES:
            # Prefer codes with numbers
            if re.search(r'[0-9]', code):
                return code
    
    # If no code with numbers, return first valid code
    for code in codes:
        if code not in VERIFICATION_CODE_EXCLUDES:
            return code
    
    # Try alternative pattern: "code is: XXXXXX"
    match = re.search(r'code\s*[:is]\s*([A-Z0-9]{6})', content, re.IGNORECASE)
    if match:
        return match.group(1)
    
    return None


@dataclass
class RefreshResult:
    """Result of a cookie refresh attempt"""
    success: bool
    account_name: str
    new_secure_c_ses: Optional[str] = None
    new_host_c_oses: Optional[str] = None
    new_csesidx: Optional[str] = None
    new_config_id: Optional[str] = None
    authorization: Optional[str] = None
    error: Optional[str] = None
    refresh_time: Optional[datetime] = None
    cookie_expires_at: Optional[datetime] = None


@dataclass
class BrowserSession:
    """Represents an active browser session for an account"""
    account_index: int
    account_name: str
    browser: Any = None
    context: Any = None
    page: Any = None
    last_refresh_time: float = 0
    latest_cookies: Dict[str, str] = field(default_factory=dict)
    is_active: bool = False


class CookieRefreshManager:
    """
    Manages automatic cookie refresh for Gemini Business accounts
    
    Uses temporary email services to automatically retrieve verification codes
    and complete the login flow to refresh expired cookies.
    """
    
    # Login URLs
    GEMINI_LOGIN_URL = "https://auth.business.gemini.google/login?continueUrl=https://business.gemini.google/"
    
    def __init__(self):
        self._account_pool = get_account_pool()
        self._playwright = None
        self._browser = None
    
    async def _ensure_browser(self):
        """Ensure Playwright browser is available"""
        if self._browser is not None:
            return
        
        try:
            from playwright.async_api import async_playwright
            
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            logger.info("Browser initialized for cookie refresh")
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            raise
    
    async def refresh_account_cookies(
        self,
        account: Account,
        tempmail_url: str,
        tempmail_name: Optional[str] = None,
    ) -> RefreshResult:
        """
        Refresh cookies for a specific account
        
        Args:
            account: The account to refresh
            tempmail_url: URL for the temporary email service (with JWT)
            tempmail_name: Optional display name for the email
            
        Returns:
            RefreshResult with new cookies or error
        """
        logger.info(f"Starting cookie refresh for account: {account.name}")
        
        try:
            await self._ensure_browser()
            
            # Create browser context
            context = await self._browser.new_context()
            page = await context.new_page()
            
            try:
                # Get email address from tempmail
                tempmail_client = TempMailClient(tempmail_url)
                email_address = tempmail_client.get_email_address()
                
                if not email_address:
                    return RefreshResult(
                        success=False,
                        account_name=account.name,
                        error="Could not get email address from tempmail URL"
                    )
                
                logger.info(f"Using email: {email_address}")
                
                # Navigate to login page
                logger.info("Navigating to Gemini login page...")
                await page.goto(self.GEMINI_LOGIN_URL, wait_until="networkidle")
                await asyncio.sleep(2)
                
                # Enter email address
                logger.info("Entering email address...")
                email_input = page.locator('input[type="email"]').first
                await email_input.fill(email_address)
                await asyncio.sleep(1)
                
                # Click continue/next button
                continue_button = page.locator('button:has-text("Continue"), button:has-text("Next")').first
                await continue_button.click()
                await asyncio.sleep(3)
                
                # Wait for verification code
                logger.info("Waiting for verification code...")
                verification_code = tempmail_client.get_verification_code(
                    timeout=120,
                    retry_mode=False
                )
                
                if not verification_code:
                    return RefreshResult(
                        success=False,
                        account_name=account.name,
                        error="Verification code not received"
                    )
                
                logger.info(f"Got verification code: {verification_code}")
                
                # Enter verification code
                code_input = page.locator('input[type="text"], input[name="code"]').first
                await code_input.fill(verification_code)
                await asyncio.sleep(1)
                
                # Submit verification
                verify_button = page.locator('button:has-text("Verify"), button:has-text("Submit")').first
                await verify_button.click()
                
                # Wait for redirect to Gemini Business
                logger.info("Waiting for login completion...")
                await page.wait_for_url("**/business.gemini.google/**", timeout=30000)
                await asyncio.sleep(3)
                
                # Extract cookies
                cookies = await context.cookies()
                
                new_secure_c_ses = None
                new_host_c_oses = None
                
                for cookie in cookies:
                    if cookie['name'] == '__Secure-C_SES':
                        new_secure_c_ses = cookie['value']
                    elif cookie['name'] == '__Host-C_OSES':
                        new_host_c_oses = cookie['value']
                
                if not new_secure_c_ses:
                    return RefreshResult(
                        success=False,
                        account_name=account.name,
                        error="Failed to get new cookies after login"
                    )
                
                # Update account
                account.secure_c_ses = new_secure_c_ses
                if new_host_c_oses:
                    account.host_c_oses = new_host_c_oses
                
                # Reset account state
                account.reset_cooldown()
                account.cookie_status = "valid"
                account.cookie_expires_at = None  # Will be updated on next JWT refresh
                
                logger.info(f"Cookie refresh successful for {account.name}")
                
                return RefreshResult(
                    success=True,
                    account_name=account.name,
                    new_secure_c_ses=new_secure_c_ses,
                    new_host_c_oses=new_host_c_oses,
                    refresh_time=datetime.now(BEIJING_TZ),
                )
                
            finally:
                await context.close()
                tempmail_client.close()
                
        except Exception as e:
            logger.error(f"Cookie refresh failed for {account.name}: {e}")
            return RefreshResult(
                success=False,
                account_name=account.name,
                error=str(e)
            )
    
    async def refresh_all_expired(
        self,
        tempmail_configs: Dict[str, str],
    ) -> List[RefreshResult]:
        """
        Refresh cookies for all accounts with expired or invalid cookies
        
        Args:
            tempmail_configs: Dict mapping account names to tempmail URLs
            
        Returns:
            List of RefreshResults
        """
        results = []
        
        for account in self._account_pool.accounts:
            # Check if account needs refresh
            if account.cookie_status == "valid" and account.is_available():
                continue
            
            # Get tempmail URL for this account
            tempmail_url = tempmail_configs.get(account.name)
            if not tempmail_url:
                logger.warning(f"No tempmail URL configured for {account.name}")
                continue
            
            # Refresh this account
            result = await self.refresh_account_cookies(account, tempmail_url)
            results.append(result)
            
            # Small delay between accounts
            await asyncio.sleep(5)
        
        return results
    
    async def close(self):
        """Close browser and cleanup"""
        if self._browser:
            await self._browser.close()
            self._browser = None
        
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None


# Global cookie refresh manager
_cookie_refresh_manager: Optional[CookieRefreshManager] = None


def get_cookie_refresh_manager() -> CookieRefreshManager:
    """Get or create the global cookie refresh manager"""
    global _cookie_refresh_manager
    if _cookie_refresh_manager is None:
        _cookie_refresh_manager = CookieRefreshManager()
    return _cookie_refresh_manager
