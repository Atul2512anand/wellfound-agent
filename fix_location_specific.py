import asyncio
from wellfound_agent.browser.session import create_browser_context

async def main():
    p,c = await create_browser_context(headless=False)
    try:
        page = c.pages[0] if c.pages else await c.new_page()
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        print("Fixing location to be more specific...")
        # Find Where are you based? input
        loc = page.locator('input[placeholder="e.g. San Francisco"]').first
        if await loc.count()==0:
            loc = page.locator('input[id^="downshift-"]').first
        await loc.scroll_into_view_if_needed()
        await loc.click()
        await page.wait_for_timeout(500)
        # Clear
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await page.wait_for_timeout(300)
        # Try Dharwad, Karnataka, India
        for city in ["Bengaluru, India", "Dharwad, India", "Mumbai, India"]:
            print(f"Trying {city}...")
            await loc.fill("")
            await loc.type(city, delay=30)
            await page.wait_for_timeout(1800)
            opts = page.locator('[role="option"]')
            cnt = await opts.count()
            print(f"  Options: {cnt}")
            for i in range(min(cnt,5)):
                txt = await opts.nth(i).inner_text()
                print(f"   {i}: {txt[:80]}")
            # Try to select the city
            target = page.get_by_role("option").filter(has_text=city.split(",")[0]).first
            if await target.count():
                await target.click()
                print(f"  Selected {city}")
                await page.wait_for_timeout(1000)
                # Check value
                val = await loc.input_value()
                print(f"  Value now: '{val}'")
                if city.split(",")[0] in val:
                    break
                # If not, try next city
                await loc.click()
                await page.wait_for_timeout(500)
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
            else:
                # Press Enter
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(1000)
                val = await loc.input_value()
                print(f"  After Enter value: '{val}'")
                if val and len(val) > 5 and "India" in val and val != "India, India":
                    break
        # Save location - find Save near top
        saves = page.locator('button:has-text("Save")')
        cnt_s = await saves.count()
        print(f"Save buttons: {cnt_s}")
        for i in range(cnt_s):
            b = saves.nth(i)
            if await b.is_visible():
                box = await b.bounding_box()
                if box and box['y'] < 600:
                    print(f" Clicking Save {i} y={box['y']}")
                    await b.scroll_into_view_if_needed()
                    await b.click()
                    await page.wait_for_timeout(3000)
                    break
        # Verify
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        val2 = await page.locator('input[placeholder="e.g. San Francisco"]').first.input_value()
        print(f"Final location value: '{val2}'")
        # Also check the display text for Where are you based?
        loc_display = await page.evaluate("() => { const el=document.querySelector('input[placeholder=\"e.g. San Francisco\"]'); return el ? el.value : 'not found'; }")
        print(f"Display: {loc_display}")
        await page.screenshot(path="fix_location_final.png", full_page=True)
        print("Keeping open 10 sec...")
        await page.wait_for_timeout(10000)
    finally:
        await c.close()
        await p.stop()
        print("Done")

if __name__ == "__main__":
    asyncio.run(main())
