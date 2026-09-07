import asyncio
from wellfound_agent.browser.session import create_browser_context
async def main():
    p,c = await create_browser_context(headless=False)
    try:
        page = c.pages[0] if c.pages else await c.new_page()
        await page.goto('https://wellfound.com/profile/edit', wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(4000)
        has_mumbai = await page.evaluate("() => document.body.innerText.includes('University Of Mumbai')")
        has_nfsu = await page.evaluate("() => document.body.innerText.includes('National Forensic')")
        steps = await page.evaluate("() => { const m=document.body.innerText.match(/(\\d+) steps to complete/); return m?m[0]:'no steps'; }")
        print(f'Has Mumbai: {has_mumbai}')
        print(f'Has NFSU: {has_nfsu}')
        print(f'Steps: {steps}')
        body = await page.evaluate("() => document.body.innerText.slice(0,1200)")
        print(body[:800])
        await page.screenshot(path='verify_after_manual.png', full_page=True)
        print('Screenshot verify_after_manual.png')
        await page.wait_for_timeout(10000)
    finally:
        await c.close()
        await p.stop()
asyncio.run(main())
