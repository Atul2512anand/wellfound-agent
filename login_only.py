"""Open Edge for 2 minutes for manual login - saves session for future runs."""
import asyncio
from wellfound_agent.browser.session import create_browser_context

async def main():
    from wellfound_agent.config import BROWSER_CHANNEL, BROWSER_DATA_DIR
    print(f"Opening Edge ({BROWSER_CHANNEL}) for manual login...")
    print(f"Profile dir: {BROWSER_DATA_DIR}")
    print(f"Your normal Edge logins are NOT shared - this is an isolated automation profile.")
    print(f"Please log in to Wellfound with Google (your account) in the Edge window.")
    print("You have 120 seconds (2 minutes). After login, wait for Wellfound jobs page to load.")
    playwright, context = await create_browser_context(headless=False)
    try:
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://wellfound.com/jobs", wait_until="domcontentloaded", timeout=60000)
        print(f"Opened: {page.url}")
        print("Timer: 120 seconds... complete CAPTCHA/login/password reset if asked.")
        print("DO NOT close Edge manually - it will close automatically after 120 sec.")
        try:
            await page.wait_for_timeout(120000)
        except Exception as e:
            print(f"Window closed early: {e}")
        try:
            print(f"Final URL: {page.url}")
            await page.screenshot(path="login_check.png")
            print("Screenshot saved to login_check.png - check if logged in (profile icon vs Log in).")
        except Exception as e:
            print(f"Could not capture final state: {e}")
        print("Session saved. Future runs will reuse this login.")
    finally:
        try:
            await context.close()
        except Exception:
            pass
        try:
            await playwright.stop()
        except Exception:
            pass
        print("Closed. You can now run: python -m wellfound_agent run")

if __name__ == "__main__":
    asyncio.run(main())
