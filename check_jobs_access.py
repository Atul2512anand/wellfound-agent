import asyncio
from wellfound_agent.browser.session import create_browser_context

async def main():
    playwright, context = await create_browser_context(headless=False)
    try:
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://wellfound.com/jobs", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        print(f"URL after goto /jobs: {page.url}")
        await page.screenshot(path="check_jobs.png", full_page=False)
        # Check if redirected to profile
        if "profile" in page.url:
            print("REDIRECTED to profile - still incomplete")
        else:
            print("STAYED on jobs - profile sufficient for browsing")
        # Count jobs
        cnt = await page.locator('a[href*="/jobs/"]').count()
        print(f"Job links: {cnt}")
        body = await page.evaluate("() => document.body.innerText.slice(0,800)")
        print(body[:600])
        await page.wait_for_timeout(15000)
    finally:
        await context.close()
        await playwright.stop()

if __name__ == "__main__":
    asyncio.run(main())
