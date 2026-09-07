import asyncio
from wellfound_agent.browser.session import create_browser_context

async def main():
    p,c = await create_browser_context(headless=False)
    try:
        page = c.pages[0] if c.pages else await c.new_page()
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        print("Fixing location to Bengaluru...")
        # Find Where are you based input - try multiple selectors
        loc = None
        for sel in ['input[placeholder="e.g. San Francisco"]', 'input[id^="downshift-"]', 'input[placeholder*="San Francisco"]']:
            loc = page.locator(sel).first
            cnt = await loc.count()
            print(f" selector {sel} count {cnt}")
            if cnt>0:
                try:
                    # Check if visible
                    if await loc.is_visible():
                        print(f"  Using {sel}")
                        break
                except:
                    pass
        if await loc.count()==0:
            print("No location input found, trying by label")
            # Find label
            label = page.locator('label:has-text("Where are you based")').first
            await label.scroll_into_view_if_needed()
            # Find input near label
            loc = page.locator('label:has-text("Where are you based")').locator('..').locator('input').first
            print(f"By label count {await loc.count()}")

        await loc.scroll_into_view_if_needed()
        await loc.click()
        await page.wait_for_timeout(500)
        # Check current value
        try:
            cur = await loc.input_value()
            print(f"Current: '{cur}'")
        except:
            cur = ""
            print("Could not get current value")
        # Clear - click x if exists
        clear_btn = page.locator('button:has-text("×"), span:has-text("×")').first
        # Actually the location chip has an 'x' - look for it near loc
        # Try to press Control+A and Backspace
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await page.wait_for_timeout(300)
        # Also try clicking the x
        x_btn = page.locator('div:has-text("India, India")').locator('..').locator('text=×').first
        if await x_btn.count() and await x_btn.is_visible():
            await x_btn.click()
            print("Clicked x to clear India, India")
            await page.wait_for_timeout(500)

        # Now type Bengaluru
        await loc.click()
        await loc.type("Bengaluru", delay=30)
        await page.wait_for_timeout(1800)
        opts = page.locator('[role="option"]')
        cnt = await opts.count()
        print(f"Options for Bengaluru: {cnt}")
        for i in range(min(cnt,6)):
            txt = await opts.nth(i).inner_text()
            print(f" {i}: {txt[:80]}")
        # Try to select Bengaluru, Karnataka, India
        target = None
        for term in ["Bengaluru, Karnataka", "Bengaluru", "Bangalore"]:
            t = page.get_by_role("option").filter(has_text=term).first
            if await t.count():
                target = t
                print(f"Found {term}")
                break
        if target and await target.count():
            await target.click()
            print(f"Selected {term}")
        else:
            if cnt>0:
                # Try first that contains Bengaluru
                for i in range(cnt):
                    txt = await opts.nth(i).inner_text()
                    if "Bengaluru" in txt or "Bangalore" in txt:
                        await opts.nth(i).click()
                        print(f"Selected {txt}")
                        break
                else:
                    await opts.first.click()
                    print(f"Selected first: {await opts.first.inner_text()}")
            else:
                await page.keyboard.press("Enter")
        await page.wait_for_timeout(1000)
        # Check value
        try:
            new_val = await loc.input_value()
            print(f"New value: '{new_val}'")
        except:
            new_val = await page.evaluate("() => document.querySelector('input[placeholder=\"e.g. San Francisco\"]')?.value || document.querySelector('input[id^=\"downshift-\"]')?.value || ''")
            print(f"New value via JS: '{new_val}'")

        # Also check the displayed chip
        chip = await page.evaluate("() => document.body.innerText.includes('Bengaluru')")
        print(f"Body has Bengaluru: {chip}")

        # Save
        # Find Save near top (About section)
        saves = page.locator('button:has-text("Save")')
        cnt_s = await saves.count()
        print(f"Save buttons: {cnt_s}")
        for i in range(cnt_s):
            b = saves.nth(i)
            if await b.is_visible():
                box = await b.bounding_box()
                if box:
                    print(f" Save {i} y={box['y']} text={await b.inner_text()}")
                    if box['y'] < 700:
                        await b.scroll_into_view_if_needed()
                        await b.click()
                        print(f"Clicked Save {i}")
                        await page.wait_for_timeout(3000)
                        break
        # Verify
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        final = await page.evaluate("() => { const el=document.querySelector('input[placeholder=\"e.g. San Francisco\"]') || document.querySelector('input[id^=\"downshift-\"]'); return el?el.value:document.body.innerText.slice(0,500); }")
        print(f"Final check: {final[:200]}")
        has_beng = await page.evaluate("() => document.body.innerText.includes('Bengaluru')")
        has_mumbai = await page.evaluate("() => document.body.innerText.includes('University Of Mumbai')")
        print(f"Has Bengaluru: {has_beng}, Has Mumbai: {has_mumbai}")
        await page.screenshot(path="fix_bengaluru_v2_final.png", full_page=True)
        print("Keeping open 10 sec...")
        await page.wait_for_timeout(10000)
    finally:
        await c.close()
        await p.stop()
        print("Done")

if __name__ == "__main__":
    asyncio.run(main())
