import asyncio
from wellfound_agent.browser.session import create_browser_context

async def main():
    p,c = await create_browser_context(headless=False)
    try:
        page = c.pages[0] if c.pages else await c.new_page()
        # Test one of the failed jobs
        url = "https://wellfound.com/jobs/4658727-senior-ai-ml-engineer-lead-clone"
        print(f"Opening {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        print(f"URL: {page.url}")
        print(f"Title: {await page.title()}")
        await page.screenshot(path="diag_apply_job.png", full_page=False)
        # Check for Apply button
        body = await page.evaluate("() => document.body.innerText.slice(0,1500)")
        print(body[:1000])
        # Find buttons
        btns = await page.evaluate("""() => {
            return [...document.querySelectorAll('button')].map(b => ({text: b.innerText.trim().slice(0,80), classes: b.className.slice(0,150), visible: !!(b.offsetWidth || b.offsetHeight)})).filter(x=>x.text.length>0).slice(0,20)
        }""")
        import json
        print(json.dumps(btns, indent=2))
        # Check for external apply
        is_ext = await page.evaluate("""() => {
            const t=document.body.innerText.toLowerCase();
            return t.includes("company's website") || t.includes("apply on company") || t.includes("apply on the company");
        }""")
        print(f"Is external: {is_ext}")
        # Check for profile incomplete blocker
        has_block = await page.evaluate("() => document.body.innerText.toLowerCase().includes('complete the required fields') || document.body.innerText.toLowerCase().includes('profile is incomplete')")
        print(f"Has profile block: {has_block}")
        # Try to find Apply button via locators
        apply_btn = page.locator('button.styles_applyButton__7gnpI').first
        print(f"ApplyButton count: {await apply_btn.count()}")
        apply2 = page.get_by_role("button", name="Apply").first
        print(f"Apply role count: {await apply2.count()}")
        if await apply2.count():
            txt = await apply2.inner_text()
            print(f"Apply2 text: {txt}")
            # Try clicking
            try:
                await apply2.click()
                print("Clicked Apply")
                await page.wait_for_timeout(3000)
                await page.screenshot(path="diag_apply_after_click.png", full_page=False)
                body2 = await page.evaluate("() => document.body.innerText.slice(0,1500)")
                print(body2[:1000])
                btns2 = await page.evaluate("""() => [...document.querySelectorAll('button')].map(b=>b.innerText.trim()).filter(t=>t.length>0).slice(0,20)""")
                print(btns2)
            except Exception as e:
                print(f"Click failed: {e}")
        await page.wait_for_timeout(15000)
    finally:
        await c.close()
        await p.stop()
asyncio.run(main())
