import asyncio
from wellfound_agent.browser.session import create_browser_context

async def try_location(page, term):
    print(f"\nTrying '{term}'...")
    loc = page.locator('input[placeholder="e.g. San Francisco"]').first
    if await loc.count()==0:
        loc = page.locator('input[id^="downshift-"]').first
    await loc.scroll_into_view_if_needed()
    await loc.click()
    await page.wait_for_timeout(400)
    await page.keyboard.press("Control+A")
    await page.keyboard.press("Backspace")
    await loc.type(term, delay=30)
    await page.wait_for_timeout(1800)
    opts = page.locator('[role="option"]')
    cnt = await opts.count()
    print(f"  Options: {cnt}")
    for i in range(min(cnt,6)):
        txt = await opts.nth(i).inner_text()
        print(f"   {i}: {txt[:80].replace(chr(10),' | ')}")
    # Try to find Bengaluru
    for i in range(cnt):
        txt = await opts.nth(i).inner_text()
        if "Bengaluru" in txt or "Bangalore" in txt:
            await opts.nth(i).click()
            print(f"  -> Selected {txt[:50]}")
            await page.wait_for_timeout(1000)
            return True
    # If no Bengaluru, try first India-related that is specific (like India, India is too broad, but maybe Bengaluru is not in list, try typing just Bengaluru)
    if cnt>0:
        # Don't select India, instead try to press Enter to see if it creates
        # First, check if any option is more specific than just India
        # Look for option with comma and city
        for i in range(cnt):
            txt = await opts.nth(i).inner_text()
            if "," in txt and "India" in txt and txt.count(",")>=1 and len(txt) < 40 and "India, India" not in txt:
                await opts.nth(i).click()
                print(f"  -> Selected specific {txt}")
                return True
    # If still not, try Enter
    await page.keyboard.press("Enter")
    print("  Pressed Enter")
    await page.wait_for_timeout(800)
    val = await loc.input_value()
    print(f"  Value after: '{val}'")
    return val and "Bengaluru" in val

async def main():
    p,c = await create_browser_context(headless=False)
    try:
        page = c.pages[0] if c.pages else await c.new_page()
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3500)
        print("Current location:")
        cur = await page.locator('input[placeholder="e.g. San Francisco"]').first.input_value()
        print(f" '{cur}'")
        # Try variations
        for term in ["Bengaluru", "Bengaluru, Karnataka, India", "Bangalore", "Bengaluru, India", "Karnataka, India"]:
            success = await try_location(page, term)
            if success:
                print(f"Success with {term}")
                break
            # If failed, clear and try next
            await page.wait_for_timeout(500)
            # Need to re-locate input
        # Save
        saves = page.locator('button:has-text("Save")')
        cnt_s = await saves.count()
        print(f"\nSave buttons: {cnt_s}")
        for i in range(cnt_s):
            b = saves.nth(i)
            if await b.is_visible():
                box = await b.bounding_box()
                if box and box['y'] < 650:
                    print(f" Clicking Save {i} y={box['y']}")
                    await b.scroll_into_view_if_needed()
                    await b.click()
                    await page.wait_for_timeout(3000)
                    break
        # Verify
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        final = await page.locator('input[placeholder="e.g. San Francisco"]').first.input_value()
        print(f"Final location: '{final}'")
        await page.screenshot(path="fix_bengaluru_final.png", full_page=True)
        print("Keeping open 10 sec...")
        await page.wait_for_timeout(10000)
    finally:
        await c.close()
        await p.stop()
        print("Done")

if __name__ == "__main__":
    asyncio.run(main())
