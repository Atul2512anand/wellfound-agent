import asyncio
from wellfound_agent.browser.session import create_browser_context, wait_for_wellfound_content

async def main():
    from wellfound_agent.config import BROWSER_CHANNEL, BROWSER_DATA_DIR
    print(f"CHANNEL={BROWSER_CHANNEL} DIR={BROWSER_DATA_DIR}")
    playwright, context = await create_browser_context(headless=False)
    try:
        page = context.pages[0] if context.pages else await context.new_page()
        print("Goto https://wellfound.com/jobs")
        await page.goto("https://wellfound.com/jobs", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        print(f"URL after goto: {page.url}")
        print(f"Title: {await page.title()}")
        await page.screenshot(path="diag_jobs.png", full_page=False)
        print("Screenshot saved to diag_jobs.png")
        body = await page.evaluate("() => document.body.innerText.slice(0,1200)")
        print("Body preview (1200 chars):")
        print(body[:1200])
        # Check for location selector
        count = await page.locator(".styles_roleAndLocation__TcRMj").count()
        print(f"Location selector count: {count}")
        count2 = await page.locator('a[href*="/jobs/"]').count()
        print(f"Job links count: {count2}")
        has_login = await page.evaluate("() => document.body.innerText.toLowerCase().includes('log in')")
        print(f"Has 'log in' text: {has_login}")
        print("Keeping open 25 sec for manual check...")
        await page.wait_for_timeout(25000)
    finally:
        await context.close()
        await playwright.stop()

if __name__ == "__main__":
    asyncio.run(main())
