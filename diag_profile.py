import asyncio
from wellfound_agent.browser.session import create_browser_context

async def main():
    playwright, context = await create_browser_context(headless=False)
    try:
        page = context.pages[0] if context.pages else await context.new_page()
        # Check current state at /jobs
        await page.goto("https://wellfound.com/jobs", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        print(f"Jobs URL: {page.url}")
        await page.screenshot(path="diag_profile_jobs.png")
        print("Saved diag_profile_jobs.png")
        # Try to find profile link
        profile_link = await page.evaluate("""() => {
            const links = [...document.querySelectorAll('a')].map(a => ({text: a.innerText.trim().slice(0,80), href: a.href})).filter(x => x.text.length>0);
            return links.slice(0,40);
        }""")
        import json
        print(json.dumps(profile_link, indent=2)[:4000])
        # Check for profile URLs
        for url in ["https://wellfound.com/profile", "https://wellfound.com/settings", "https://wellfound.com/candidate/profile", "https://wellfound.com/talent/profile", "https://wellfound.com/account"]:
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(2000)
                print(f"Try {url} -> final {page.url} title {await page.title()}")
                await page.screenshot(path=f"diag_profile_{url.split('/')[-1]}.png")
            except Exception as e:
                print(f"Failed {url}: {e}")
        print("Keeping open 20 sec...")
        await page.wait_for_timeout(20000)
    finally:
        await context.close()
        await playwright.stop()

if __name__ == "__main__":
    asyncio.run(main())
