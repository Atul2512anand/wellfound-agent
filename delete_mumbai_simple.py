import asyncio
from wellfound_agent.browser.session import create_browser_context
async def main():
    p,c = await create_browser_context(headless=False)
    try:
        page = c.pages[0] if c.pages else await c.new_page()
        await page.goto('https://wellfound.com/profile/edit', wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(3500)
        edits = page.get_by_text('Edit')
        cnt = await edits.count()
        print(f'Edits: {cnt}')
        # List edits
        for i in range(cnt):
            txt = await page.evaluate(f"() => {{ const btn=[...document.querySelectorAll('button, a')].filter(b=>b.innerText.trim()==='Edit')[{i}]; if(!btn) return 'no'; let p=btn.parentElement; for(let k=0;k<5;k++){{if(!p)break; if(p.innerText.includes('University')) return p.innerText.slice(0,120); p=p.parentElement;}} return 'unknown'; }}")
            print(f" Edit {i}: {txt[:80]}")
        if cnt >= 3:
            print('Clicking Mumbai Edit index 2')
            await edits.nth(2).click()
            await page.wait_for_timeout(2500)
            await page.screenshot(path='mumbai_target.png')
            print('Clicked Mumbai Edit')
            rem = page.get_by_text('Remove education').first
            if await rem.count():
                await rem.scroll_into_view_if_needed()
                await rem.click()
                print('Clicked Remove education')
                await page.wait_for_timeout(2500)
                await page.screenshot(path='mumbai_after_remove.png')
            # Verify
            await page.goto('https://wellfound.com/profile/edit', wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(3000)
            has = await page.evaluate("() => document.body.innerText.includes('University Of Mumbai')")
            print(f'Has Mumbai after: {has}')
            await page.screenshot(path='mumbai_verify.png', full_page=True)
            await page.wait_for_timeout(10000)
    finally:
        await c.close()
        await p.stop()
asyncio.run(main())
