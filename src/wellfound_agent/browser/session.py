"""Persistent Edge session and Wellfound navigation."""

import asyncio
import sys
from typing import Any

from playwright.async_api import BrowserContext, Page, async_playwright

from wellfound_agent.config import (
    BROWSER_CHANNEL,
    BROWSER_DATA_DIR,
    HEADLESS,
    PAGE_LOAD_DELAY_SEC,
)


async def is_page_blocked(page: Page) -> bool:
    """Detect DataDome / bot block (empty page or captcha)."""
    return await page.evaluate(
        """() => {
            const bodyLen = document.body?.innerText?.trim().length || 0;
            const title = document.title || '';
            const hasNext = !!document.getElementById('__NEXT_DATA__');
            const hasJobs = document.querySelectorAll('a[href*="/jobs/"]').length > 0;
            if (hasNext || hasJobs || bodyLen > 500) return false;
            if (title === 'wellfound.com' || bodyLen === 0) return true;
            const text = document.body.innerText.toLowerCase();
            return text.includes('verify you are human') || text.includes('access denied');
        }"""
    )


async def wait_for_wellfound_content(page: Page, timeout_ms: int = 90000) -> bool:
    """Wait until job data or __NEXT_DATA__ is present."""
    try:
        await page.wait_for_function(
            """() => {
                const hasNext = !!document.getElementById('__NEXT_DATA__');
                const jobLinks = document.querySelectorAll('a[href*="/jobs/"]').length;
                const bodyLen = document.body?.innerText?.trim().length || 0;
                return hasNext || jobLinks > 0 || bodyLen > 500;
            }""",
            timeout=timeout_ms,
        )
        return True
    except Exception:
        return False


async def handle_block_if_needed(page: Page) -> None:
    """Pause for manual CAPTCHA / unblock when DataDome blocks the session."""
    if not await is_page_blocked(page):
        return

    if HEADLESS:
        raise RuntimeError(
            "Wellfound blocked this session (DataDome). Run "
            "`python -m wellfound_agent scrape` interactively with Edge, "
            "complete any CAPTCHA, then retry."
        )

    print("\n" + "!" * 60)
    print("Wellfound appears to be blocking automated access (DataDome).")
    print(f"In the Edge window ({BROWSER_CHANNEL}):")
    print("  1. Complete any CAPTCHA / verification if shown")
    print("  2. Wait until you see job listings")
    print("  Auto-continuing in 35 seconds... (press Enter in terminal if you already see jobs)")
    print("!" * 60 + "\n")
    if sys.stdin.isatty():
        try:
            await asyncio.wait_for(asyncio.to_thread(input), timeout=35)
        except (asyncio.TimeoutError, EOFError):
            print("Continuing automatically...")
        except Exception:
            print("Continuing automatically...")
    else:
        print("Non-interactive mode - waiting 35 seconds for you to complete CAPTCHA in Edge...")
        await asyncio.sleep(35)

    ready = await wait_for_wellfound_content(page, timeout_ms=120000)
    if not ready:
        raise RuntimeError("Page still blocked after manual intervention.")


async def create_browser_context(headless: bool | None = None) -> tuple[Any, BrowserContext]:
    """
    Launch a persistent browser context.

    Uses system Edge by default — Wellfound's DataDome blocks Playwright's
    bundled Chromium, but real Edge/Chrome with a saved profile works.
    """
    if headless is None:
        headless = HEADLESS

    playwright = await async_playwright().start()
    BROWSER_DATA_DIR.mkdir(parents=True, exist_ok=True)

    launch_kwargs: dict[str, Any] = {
        "user_data_dir": str(BROWSER_DATA_DIR),
        "headless": headless,
        "viewport": {"width": 1280, "height": 900},
        "args": ["--disable-blink-features=AutomationControlled"],
        "ignore_default_args": ["--enable-automation"],
    }

    if BROWSER_CHANNEL:
        launch_kwargs["channel"] = BROWSER_CHANNEL

    context = await playwright.chromium.launch_persistent_context(**launch_kwargs)
    await context.add_init_script(
        """
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        window.chrome = window.chrome || { runtime: {} };
        """
    )
    return playwright, context


async def navigate_wellfound(page: Page, url: str) -> None:
    """Navigate and wait for Wellfound content, handling blocks."""
    await page.goto(url, wait_until="domcontentloaded", timeout=90000)
    await page.wait_for_timeout(PAGE_LOAD_DELAY_SEC * 1000)

    if not await wait_for_wellfound_content(page, timeout_ms=60000):
        await handle_block_if_needed(page)

    if await is_page_blocked(page):
        await handle_block_if_needed(page)


async def ensure_logged_in(page: Page) -> None:
    """Open Wellfound jobs page and pause for manual login on first run."""
    await navigate_wellfound(page, "https://wellfound.com/jobs")

    logged_in = await page.evaluate(
        """() => {
            const text = document.body?.innerText?.toLowerCase() || '';
            const hasSignIn = text.includes('log in') && !text.includes('log out');
            const hasProfile = !!document.querySelector('[data-test="NavBarProfile"], a[href*="/profile"]');
            return hasProfile || !hasSignIn;
        }"""
    )

    if not logged_in:
        if HEADLESS:
            raise RuntimeError(
                "Not logged in to Wellfound. Run `python -m wellfound_agent scrape` once "
                "interactively to log in and save your session before using headless/cron mode."
            )
        print("\n" + "=" * 60)
        print(f"Please log in to Wellfound in the Edge window ({BROWSER_CHANNEL}) - optional but recommended.")
        print("You have 120 seconds (2 minutes) to log in with Google (your account) if you want to apply.")
        print("Press Enter when ready, or wait to continue automatically.")
        print("=" * 60 + "\n")
        if sys.stdin.isatty():
            try:
                await asyncio.wait_for(asyncio.to_thread(input), timeout=120)
            except (asyncio.TimeoutError, EOFError):
                print("No input - continuing. If not logged in, applying will be skipped.")
            except Exception:
                print("Continuing...")
        else:
            print("Non-interactive mode - waiting 120 seconds for manual login in Edge...")
            await asyncio.sleep(120)
        await page.wait_for_timeout(2000)
