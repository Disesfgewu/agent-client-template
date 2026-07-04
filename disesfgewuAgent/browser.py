"""Optional browser automation support for AgentClient.

This module intentionally keeps Playwright optional. Importing disesfgewuAgent
must not require browser binaries; callers opt in with AgentClient(enableBrowser=True)
and install the optional browser dependency when they need real UI E2E actions.
"""

from __future__ import annotations

import os
from typing import Optional


class BrowserSession:
    """Small async wrapper around Playwright browser/page operations."""

    def __init__(self, headless: bool = False, timeout: int = 30):
        self._headless = headless
        self._timeout_ms = int(timeout * 1000)
        self._playwright = None
        self._browser = None
        self._page = None

    async def _ensure_page(self):
        if self._page is not None:
            return self._page
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Playwright is not installed. Install the browser extra with "
                "`pip install disesfgewu-agent[browser]` or install playwright, "
                "then run `playwright install chromium`."
            ) from exc

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self._headless)
        self._page = await self._browser.new_page()
        self._page.set_default_timeout(self._timeout_ms)
        return self._page

    async def run(self, action: str, **params) -> dict:
        action = (action or "").lower().strip()
        if action in ("close", "shutdown"):
            await self.close()
            return {"ok": True, "action": action, "message": "browser closed"}

        page = await self._ensure_page()
        result = {"ok": True, "action": action}

        if action in ("goto", "open", "navigate"):
            url = params.get("url") or params.get("target")
            if not url:
                return {"ok": False, "action": action, "message": "url is required"}
            response = await page.goto(url, wait_until=params.get("waitUntil", "domcontentloaded"))
            result.update({
                "url": page.url,
                "title": await page.title(),
                "status_code": response.status if response else None,
            })
            return result

        if action == "click":
            selector = params.get("selector")
            if not selector:
                return {"ok": False, "action": action, "message": "selector is required"}
            await page.click(selector)
            result.update({"url": page.url, "title": await page.title()})
            return result

        if action in ("fill", "type"):
            selector = params.get("selector")
            text = params.get("text", "")
            if not selector:
                return {"ok": False, "action": action, "message": "selector is required"}
            if action == "fill":
                await page.fill(selector, text)
            else:
                await page.type(selector, text)
            result.update({"url": page.url, "title": await page.title()})
            return result

        if action == "press":
            selector = params.get("selector")
            key = params.get("key")
            if not selector or not key:
                return {"ok": False, "action": action, "message": "selector and key are required"}
            await page.press(selector, key)
            result.update({"url": page.url, "title": await page.title()})
            return result

        if action in ("wait", "wait_for_selector"):
            selector = params.get("selector")
            if selector:
                await page.wait_for_selector(selector)
            else:
                await page.wait_for_timeout(int(params.get("ms", 1000)))
            result.update({"url": page.url, "title": await page.title()})
            return result

        if action == "screenshot":
            path = params.get("path") or "browser-screenshot.png"
            await page.screenshot(path=path, full_page=bool(params.get("fullPage", True)))
            result.update({
                "path": os.path.abspath(path),
                "url": page.url,
                "title": await page.title(),
            })
            return result

        if action in ("text", "inner_text"):
            selector = params.get("selector") or "body"
            text = await page.inner_text(selector)
            result.update({
                "selector": selector,
                "text": text[: params.get("limit", 4000)],
                "url": page.url,
                "title": await page.title(),
            })
            return result

        return {
            "ok": False,
            "action": action,
            "message": (
                "Unsupported browser action. Use goto, click, fill, type, press, "
                "wait_for_selector, wait, screenshot, text, or close."
            ),
        }

    async def close(self) -> None:
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
            self._page = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None