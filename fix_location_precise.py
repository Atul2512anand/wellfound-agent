import asyncio
from wellfound_agent.browser.session import create_browser_context

async def main():
    p,c = await create_browser_context(headless=False)
    try:
        page = c.pages[0] if c.pages else await c.new_page()
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        print("Fixing location precisely...")
        # Note: Skills currently have Bengaluru etc. as extra chips due to earlier mis-targeting, but leaving them for now as they don't block applying
        # Focus on fixing Where are you based?

        # Now fix Where are you based? - find the correct input via label
        label = page.locator('label:has-text("Where are you based")').first
        await label.scroll_into_view_if_needed()
        await page.wait_for_timeout(500)
        # The input is near the label
        loc = page.locator('label:has-text("Where are you based")').locator('..').locator('input').first
        cnt = await loc.count()
        print(f"Location input via label count: {cnt}")
        if cnt==0:
            # Fallback: find input with placeholder near label
            loc = page.locator('div:has-text("Where are you based")').locator('input').first
            print(f"Fallback count: {await loc.count()}")
        if await loc.count()==0:
            print("Still not found, trying JS")
            loc = page.locator('input[placeholder="e.g. San Francisco"]').first
            print(f"Placeholder count: {await loc.count()}")
        await loc.scroll_into_view_if_needed()
        # Check current value
        try:
            cur = await loc.input_value()
            print(f"Current location value: '{cur}'")
        except:
            cur = await page.evaluate("() => document.querySelector('label:has-text(\"Where are you based\")')?.parentElement.querySelector('input')?.value || ''")
            print(f"Current via JS: '{cur}'")
        # Clear existing "India, India" chip - click x
        # The chip has text India, India with an x
        # Find the chip close button
        x_btn = page.locator('div:has-text("India, India")').locator('..').locator('text=×').first
        # Actually the chip is a div with text India, India and an x
        # Use get_by_text
        chip_x = page.get_by_text("India, India").first
        # The x is near
        # Try to find the x button for India, India
        has_india = await page.evaluate("() => document.body.innerText.includes('India, India')")
        print(f"Has India, India chip: {has_india}")
        if has_india:
            # Click the x on the chip
            # The chip structure: <div>India, India <span>×</span></div>
            clicked_x = await page.evaluate("""() => {
                const chips = [...document.querySelectorAll('div')].filter(d => d.innerText.trim() === 'India, India' || d.innerText.includes('India, India'));
                for(const chip of chips){
                    const x = chip.querySelector('span') || chip.querySelector('button') || [...chip.querySelectorAll('*')].find(e=>e.innerText.trim()==='×');
                    if(x){x.click(); return true;}
                    // Try parent
                    let p=chip.parentElement;
                    for(let i=0;i<3;i++){
                        if(!p) break;
                        const xs = [...p.querySelectorAll('*')].filter(e=>e.innerText.trim()==='×');
                        if(xs.length>0){xs[0].click(); return true;}
                        p=p.parentElement;
                    }
                }
                // Also try finding any × near India, India
                const india = [...document.querySelectorAll('*')].find(e=>e.innerText.includes('India, India'));
                if(india){
                    const parent = india.closest('div');
                    if(parent){
                        const x = parent.querySelector('span');
                        if(x) {x.click(); return true;}
                    }
                }
                return false;
            }""")
            print(f"Clicked x for India, India: {clicked_x}")
            await page.wait_for_timeout(1000)

        # Now click the location input to add new
        await loc.click()
        await page.wait_for_timeout(500)
        # Type Bengaluru, Karnataka, India - try a specific city that Wellfound recognizes
        # Let's try "Bengaluru, Karnataka, India" or just "Bengaluru"
        for city in ["Bengaluru", "Bangalore", "Bengaluru, Karnataka"]:
            print(f"Trying city '{city}'...")
            await loc.click()
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Backspace")
            await loc.type(city, delay=30)
            await page.wait_for_timeout(2000)
            opts = page.locator('[role="option"]')
            cnt_o = await opts.count()
            print(f"  Options: {cnt_o}")
            for i in range(min(cnt_o,6)):
                txt = await opts.nth(i).inner_text()
                print(f"   {i}: {txt[:80]}")
            # Look for Bengaluru
            target = page.get_by_role("option").filter(has_text="Bengaluru").first
            if await target.count():
                await target.click()
                print(f"  Selected Bengaluru option")
                await page.wait_for_timeout(1000)
                break
            else:
                target2 = page.get_by_role("option").filter(has_text="Bangalore").first
                if await target2.count():
                    await target2.click()
                    print("  Selected Bangalore")
                    break
                elif cnt_o > 0:
                    # Try first option that looks like a city (contains comma)
                    for i in range(cnt_o):
                        txt = await opts.nth(i).inner_text()
                        if "," in txt and len(txt) < 50:
                            await opts.nth(i).click()
                            print(f"  Selected city-like {txt}")
                            break
                    else:
                        # Press Enter
                        await page.keyboard.press("Enter")
                        print("  Pressed Enter")
                    break
                else:
                    await page.keyboard.press("Enter")
                    print("  No options, pressed Enter")
                    await page.wait_for_timeout(500)
            # Check if value set
            try:
                val = await loc.input_value()
                print(f"  Value after: '{val}'")
                if "Bengaluru" in val or "Bangalore" in val:
                    break
            except:
                pass
            # If failed, try next city
            await page.wait_for_timeout(500)
            # Clear for next try
            await loc.click()
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Backspace")

        # Check final location
        final_loc = await page.evaluate("() => { const el=document.querySelector('label:has-text(\"Where are you based\")')?.parentElement.querySelector('input'); return el?el.value:document.body.innerText.slice(0,500); }")
        print(f"Final location check via JS: {final_loc[:100]}")
        has_beng = await page.evaluate("() => document.body.innerText.includes('Bengaluru')")
        print(f"Body has Bengaluru now: {has_beng}")

        # Also check skills still has Bengaluru incorrectly? Remove if so again
        # Save - find Save
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

        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        final2 = await page.evaluate("() => document.body.innerText.slice(0,1000)")
        print(f"\nFinal body snippet:\n{final2[:600]}")
        await page.screenshot(path="fix_location_precise_final.png", full_page=True)
        print("Keeping open 10 sec...")
        await page.wait_for_timeout(10000)
    finally:
        await c.close()
        await p.stop()
        print("Done")

if __name__ == "__main__":
    asyncio.run(main())
