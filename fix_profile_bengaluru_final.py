import asyncio
from wellfound_agent.browser.session import create_browser_context

async def main():
    p,c = await create_browser_context(headless=False)
    try:
        page = c.pages[0] if c.pages else await c.new_page()
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        print("Current profile location fix to Bengaluru, India...")
        # Find the location field - use get_by_placeholder
        loc = page.get_by_placeholder("e.g. San Francisco").first
        cnt = await loc.count()
        print(f"Placeholder e.g. San Francisco count: {cnt}")
        if cnt==0:
            # Try downshift
            loc = page.locator('input[id^="downshift-"]').first
            cnt2 = await loc.count()
            print(f"downshift count: {cnt2}")
            if cnt2==0:
                print("No location input found via placeholder/downshift, trying label")
                # Find via label
                loc = page.locator('label:has-text("Where are you based")').locator('..').locator('input').first
                print(f"Via label count: {await loc.count()}")
        # Check current chips
        has_india = await page.evaluate("() => document.body.innerText.includes('India, India')")
        print(f"Has India, India chip: {has_india}")
        if has_india:
            # Click x on India, India chip - find the specific chip
            # The chip is a div with text India, India and a button with ×
            # Use JS to find and click
            clicked = await page.evaluate("""() => {
                const all = [...document.querySelectorAll('div')];
                for(const div of all){
                    if(div.innerText.trim() === 'India, India'){
                        // Find x inside
                        const x = div.querySelector('span') || div.querySelector('button') || [...div.parentElement.querySelectorAll('*')].find(e=>e.innerText.trim()==='×');
                        if(x){x.click(); return true;}
                        // Try parent
                        let p=div.parentElement;
                        for(let i=0;i<3;i++){
                            if(!p) break;
                            const xs = [...p.querySelectorAll('*')].filter(e=>e.innerText.trim()==='×');
                            if(xs.length>0){xs[0].click(); return true;}
                            p=p.parentElement;
                        }
                    }
                }
                // Alternative: find any × near India, India
                const india = [...document.querySelectorAll('*')].find(e=>e.innerText.includes('India, India'));
                if(india){
                    const parent = india.closest('div');
                    if(parent){
                        const x = parent.querySelector('span');
                        if(x){x.click(); return true;}
                    }
                }
                return false;
            }""")
            print(f"Clicked x for India, India: {clicked}")
            await page.wait_for_timeout(1000)
            # Also try direct: find the x button for the chip
            # The chip's x is a span with ×
            x_btn = page.locator('span').filter(has_text="×").first
            # But there are many ×, need the one near India, India
            # For now, just after clicking, check

        # Now locate the location input again (should be empty now)
        # After clearing, the input should be visible
        loc = page.get_by_placeholder("e.g. San Francisco").first
        if await loc.count()==0:
            loc = page.locator('input[id^="downshift-"]').first
        await loc.scroll_into_view_if_needed()
        await loc.click()
        await page.wait_for_timeout(500)
        # Clear
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await page.wait_for_timeout(300)
        # Type Bengaluru
        await loc.type("Bengaluru", delay=30)
        await page.wait_for_timeout(2000)
        opts = page.locator('[role="option"]')
        cnt_o = await opts.count()
        print(f"Options for Bengaluru: {cnt_o}")
        for i in range(min(cnt_o,6)):
            txt = await opts.nth(i).inner_text()
            print(f" {i}: {txt[:80]}")
        # Try to select Bengaluru, Karnataka, India or similar
        # Look for Bengaluru
        target = page.get_by_role("option").filter(has_text="Bengaluru").first
        if await target.count():
            txt = await target.inner_text()
            print(f"Found Bengaluru option: {txt[:80]}")
            await target.click()
            print("Clicked Bengaluru")
        else:
            # Try Bangalore
            t2 = page.get_by_role("option").filter(has_text="Bangalore").first
            if await t2.count():
                txt = await t2.inner_text()
                print(f"Found Bangalore: {txt[:80]}")
                await t2.click()
                print("Clicked Bangalore")
            else:
                # Try any option with comma (city)
                for i in range(cnt_o):
                    txt = await opts.nth(i).inner_text()
                    if "," in txt and "India" in txt and len(txt) < 50:
                        print(f"Selecting city-like {txt}")
                        await opts.nth(i).click()
                        break
                else:
                    if cnt_o>0:
                        await opts.first.click()
                        print(f"Selected first: {await opts.first.inner_text()}")
                    else:
                        await page.keyboard.press("Enter")
        await page.wait_for_timeout(1000)
        # Check value
        try:
            val = await loc.input_value()
            print(f"Input value after: '{val}'")
        except:
            val = await page.evaluate("() => document.querySelector('input[placeholder=\"e.g. San Francisco\"]')?.value || ''")
            print(f"Value via JS: '{val}'")
        # Check body has Bengaluru chip
        has_beng = await page.evaluate("() => document.body.innerText.includes('Bengaluru')")
        print(f"Body has Bengaluru: {has_beng}")
        # Save
        saves = page.locator('button:has-text("Save")')
        cnt_s = await saves.count()
        print(f"Save buttons: {cnt_s}")
        for i in range(cnt_s):
            b = saves.nth(i)
            if await b.is_visible():
                box = await b.bounding_box()
                if box and box['y'] < 700:
                    print(f" Clicking Save {i} y={box['y']}")
                    await b.scroll_into_view_if_needed()
                    await b.click()
                    await page.wait_for_timeout(3000)
                    break
        # Verify
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        final_has_beng = await page.evaluate("() => document.body.innerText.includes('Bengaluru')")
        final_has_india = await page.evaluate("() => document.body.innerText.includes('India, India')")
        print(f"Final - Has Bengaluru: {final_has_beng}, Has India, India: {final_has_india}")
        body = await page.evaluate("() => document.body.innerText.slice(0,1200)")
        print(body[:600])
        await page.screenshot(path="fix_bengaluru_correct_final.png", full_page=True)
        print("Keeping open 10 sec...")
        await page.wait_for_timeout(10000)
    finally:
        await c.close()
        await p.stop()
        print("Done")

if __name__ == "__main__":
    asyncio.run(main())
