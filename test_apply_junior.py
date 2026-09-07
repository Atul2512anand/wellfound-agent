import asyncio
from wellfound_agent.browser.session import create_browser_context

async def test_job(url, title):
    p,c = await create_browser_context(headless=False)
    try:
        page = c.pages[0] if c.pages else await c.new_page()
        print(f"\n=== Testing {title} ===")
        print(url)
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        apply_btn = page.get_by_role("button", name="Apply").first
        if await apply_btn.count()==0:
            apply_btn = page.locator('button.styles_applyButton__7gnpI').first
        if await apply_btn.count()==0 or not await apply_btn.is_visible():
            print("  Apply not visible")
            return
        await apply_btn.click()
        await page.wait_for_timeout(3000)
        # Check modal
        modal_text = await page.evaluate("() => { const m=document.querySelector('[role=\"dialog\"]') || document.body; return (m.innerText||'').slice(0,1200); }")
        print(f"Modal preview: {modal_text[:600]}")
        # Check Send enabled
        send = page.get_by_role("button", name="Send application").first
        if await send.count()==0:
            send = page.locator('button:has-text("Send application")').first
        if await send.count():
            enabled = await send.is_enabled()
            print(f"  Send enabled: {enabled}, text: {await send.inner_text()}")
            # Check why disabled - look for required fields
            required = await page.evaluate("""() => {
                const req = [...document.querySelectorAll('input[required], textarea[required], select[required], [aria-required=\"true\"]')].map(e => e.outerHTML.slice(0,300));
                const labels = [...document.querySelectorAll('*')].filter(e=>e.innerText.includes('*') && e.innerText.length<100).slice(0,10).map(e=>e.innerText.trim());
                return {req, labels, body: document.body.innerText.slice(0,800)}
            }""")
            import json
            print(f"  Required: {json.dumps(required, indent=2)[:600]}")
            # Try to find error message
            err = await page.evaluate("() => { const el=[...document.querySelectorAll('*')].find(e=>e.innerText.toLowerCase().includes('complete')||e.innerText.toLowerCase().includes('required')); return el?el.innerText.slice(0,300):'none'; }")
            print(f"  Error hint: {err}")
        else:
            print("  Send not found")
        await page.screenshot(path=f"test_junior_{title.replace(' ','_')}.png")
        await page.wait_for_timeout(5000)
    finally:
        await c.close()
        await p.stop()

async def main():
    # Test a few jobs from scraped list - pick junior ones
    jobs = [
        ("https://wellfound.com/jobs/4658689-manual-tester-qa-engineer-mumbai-work-from-office", "Manual Tester QA"),
        ("https://wellfound.com/jobs/4658733-android-developer-kotlin", "Android Developer"),
        ("https://wellfound.com/jobs/4658554-senior-machine-learning-engineer-ai-computer-vision", "Senior ML Engineer"),
    ]
    for url, title in jobs:
        await test_job(url, title)
        await asyncio.sleep(2)

asyncio.run(main())
