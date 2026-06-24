"""
Browser control module - Playwright-based browser automation.
"""
import asyncio
import os
from typing import Dict, Any, List, Optional
from pathlib import Path

from utils.logger import get_logger
from utils.config import get_data_dir

log = get_logger("browser")

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    log.warning("Playwright not installed - browser module disabled")


def register(executor, config: dict):
    if not PLAYWRIGHT_AVAILABLE:
        log.warning("Browser module not registered - Playwright missing")
        return
    
    mod = BrowserModule(config)
    executor.register_handler("browser.open", mod.open_url)
    executor.register_handler("browser.click", mod.click)
    executor.register_handler("browser.fill", mod.fill)
    executor.register_handler("browser.screenshot", mod.screenshot)
    executor.register_handler("browser.extract", mod.extract)
    executor.register_handler("browser.scroll", mod.scroll)
    executor.register_handler("browser.evaluate", mod.evaluate)
    executor.register_handler("browser.close", mod.close)


class BrowserModule:
    
    def __init__(self, config: dict):
        self.config = config.get("browser", {})
        self.browser_type = self.config.get("browser", "chromium")
        self.headless = self.config.get("headless", False)
        self.user_data_dir = os.path.expandvars(
            os.path.expanduser(self.config.get("user_data_dir", ""))
        )
        Path(self.user_data_dir).mkdir(parents=True, exist_ok=True)
        self.timeout = self.config.get("timeout", 30000)
        
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
    
    async def _ensure_browser(self):
        """Lazily start the browser if needed."""
        if self._page is not None:
            return self._page
        
        if self._playwright is None:
            self._playwright = await async_playwright().start()
        
        browser_launcher = getattr(self._playwright, self.browser_type)
        self._browser = await browser_launcher.launch(headless=self.headless)
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="fr-FR",
        )
        self._page = await self._context.new_page()
        self._page.set_default_timeout(self.timeout)
        log.info(f"Browser started: {self.browser_type}")
        return self._page
    
    async def open_url(self, url: str, wait_until: str = "domcontentloaded",
                        **kwargs) -> Dict[str, Any]:
        """Open a URL in the browser."""
        try:
            page = await self._ensure_browser()
            await page.goto(url, wait_until=wait_until)
            title = await page.title()
            log.info(f"Opened: {url} ({title})")
            return {"success": True, "url": url, "title": title}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def click(self, selector: str, wait: bool = True, **kwargs) -> Dict[str, Any]:
        """Click an element by CSS selector."""
        try:
            page = await self._ensure_browser()
            if wait:
                await page.wait_for_selector(selector, timeout=self.timeout)
            await page.click(selector)
            log.info(f"Clicked: {selector}")
            return {"success": True, "selector": selector}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def fill(self, selector: str, value: str, **kwargs) -> Dict[str, Any]:
        """Fill an input field."""
        try:
            page = await self._ensure_browser()
            await page.wait_for_selector(selector, timeout=self.timeout)
            await page.fill(selector, value)
            log.info(f"Filled {selector}: {value[:30]}...")
            return {"success": True, "selector": selector, "value_length": len(value)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def screenshot(self, full_page: bool = False, **kwargs) -> Dict[str, Any]:
        """Take a screenshot of the current page."""
        try:
            page = await self._ensure_browser()
            shot_dir = os.path.join(get_data_dir(), "screenshots")
            Path(shot_dir).mkdir(parents=True, exist_ok=True)
            path = os.path.join(shot_dir, f"browser_{int(asyncio.get_event_loop().time() * 1000)}.png")
            await page.screenshot(path=path, full_page=full_page)
            return {"success": True, "screenshot": path}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def extract(self, selector: str = "body", attribute: str = "text_content",
                       **kwargs) -> Dict[str, Any]:
        """Extract content from the page."""
        try:
            page = await self._ensure_browser()
            element = await page.query_selector(selector)
            if not element:
                return {"success": False, "error": f"Element not found: {selector}"}
            
            if attribute == "text_content":
                content = await element.text_content()
            elif attribute == "inner_html":
                content = await element.inner_html()
            elif attribute == "href":
                content = await element.get_attribute("href")
            else:
                content = await element.get_attribute(attribute)
            
            return {"success": True, "content": content, "selector": selector,
                    "attribute": attribute, "length": len(content) if content else 0}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def scroll(self, direction: str = "down", amount: int = 500,
                      **kwargs) -> Dict[str, Any]:
        """Scroll the page."""
        try:
            page = await self._ensure_browser()
            delta = amount if direction == "down" else -amount
            await page.mouse.wheel(0, delta)
            return {"success": True, "direction": direction, "amount": amount}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def evaluate(self, script: str, **kwargs) -> Dict[str, Any]:
        """Evaluate JavaScript on the page."""
        try:
            page = await self._ensure_browser()
            result = await page.evaluate(script)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def close(self, **kwargs) -> Dict[str, Any]:
        """Close the browser."""
        try:
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
