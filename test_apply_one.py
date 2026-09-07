import asyncio
from wellfound_agent.browser.session import create_browser_context

async def main():
    p,c = await create_browser_context(headless=False)
    try:
        page = c.pages[0] if c.pages else await c.new_page()
        url = "https://wellfound.com/jobs/4658727-senior-ai-ml-engineer-lead-clone"
        print(f"Testing apply for {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        # Find Apply
        apply_btn = page.get_by_role("button", name="Apply").first
        if await apply_btn.count() == 0:
            apply_btn = page.locator('button.styles_applyButton__7gnpI').first
        print(f"Apply count: {await apply_btn.count()}, visible: {await apply_btn.is_visible() if await apply_btn.count() else False}")
        txt = await apply_btn.inner_text() if await apply_btn.count() else "none"
        print(f"Apply text: {txt}")
        await apply_btn.click()
        print("Clicked Apply")
        await page.wait_for_timeout(3000)
        await page.screenshot(path="test_apply_after_apply.png")
        # Check for Send application
        # List all buttons after
        btns = await page.evaluate("() => [...document.querySelectorAll('button')].map(b=>b.innerText.trim()).filter(t=>t.length>0)")
        print(f"Buttons after Apply: {btns[:20]}")
        # Check for textarea
        note = page.locator('textarea[name="userNote"]').first
        print(f"userNote count: {await note.count()}, visible: {await note.is_visible() if await note.count() else False}")
        if await note.count() and await note.is_visible():
            await note.fill("Hi — I'm a Generative AI Engineer with production experience in Python, FastAPI, LangChain, RAG, and LLM systems. Excited about this role and happy to share more about my work.")
            print("Filled note")
        # Find Send
        send = page.get_by_role("button", name="Send application").first
        print(f"Send count: {await send.count()}, visible: {await send.is_visible() if await send.count() else False}")
        if await send.count() == 0:
            send = page.locator('button:has-text("Send application")').first
            print(f"Fallback Send count: {await send.count()}")
        if await send.count():
            print(f"Send text: {await send.inner_text()}")
            # Try to click
            # Check if its enabled
            is_enabled = await send.is_enabled()
            print(f"Send enabled: {is_enabled}")
            if is_enabled:
                # Don't actually send to avoid spamming, just log
                print("Would click Send application now (skipping actual send for test)")
                # await send.click()
                # await page.wait_for_timeout(3000)
                # await page.screenshot(path="test_apply_after_send.png")
            else:
                print("Send disabled - maybe profile incomplete or already applied?")
                # Check for disabled reason
                disabled_reason = await page.evaluate("() => { const btn=[...document.querySelectorAll('button')].find(b=>b.innerText.includes('Send')); return btn ? btn.outerHTML.slice(0,500) : 'not found'; }")
                print(disabled_reason)
        else:
            # Check for other buttons like Apply now
            apply_now = page.get_by_role("button", name="Apply now").first
            print(f"Apply now count: {await apply_now.count()}")
            if await apply_now.count():
                print(f"Apply now text: {await apply_now.inner_text()}")
            # Check for any button with Send
            send2 = page.locator('button').filter(has_text="Send").first
            print(f"Send filter count: {await send2.count()}")
        await page.screenshot(path="test_apply_final.png", full_page=True)
        print("Keeping open 15 sec...")
        await page.wait_for_timeout(15000)
    finally:
        await c.close()
        await p.stop()
asyncio.run(main())
