import asyncio
from wellfound_agent.browser.session import create_browser_context

async def main():
    playwright, context = await create_browser_context(headless=False)
    try:
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3500)
        # Close any open edit form first
        cancel = page.get_by_text("Cancel").first
        if await cancel.count() and await cancel.is_visible():
            await cancel.click()
            print("Cancelled open edit")
            await page.wait_for_timeout(1000)

        # Find Mumbai card and delete it precisely
        print("Finding Mumbai card...")
        # Use locator that contains Mumbai text
        mumbai_card = page.locator('div').filter(has_text="University Of Mumbai").first
        # Check if found
        cnt = await mumbai_card.count()
        print(f"Mumbai card count via filter: {cnt}")
        if cnt == 0:
            # Alternative: find by text
            mumbai_card = page.get_by_text("University Of Mumbai").first
            cnt = await mumbai_card.count()
            print(f"Via get_by_text count: {cnt}")
        
        if cnt > 0:
            # Find Edit button near this card
            # The card is a div containing Mumbai, BBA, Edit
            # Try to locate Edit within the same card's parent
            edit = mumbai_card.locator('..').get_by_text("Edit").first
            # Try alternative: find the closest div with both Mumbai and Edit
            # Use JS to find
            clicked = await page.evaluate("""() => {
                const all = [...document.querySelectorAll('div')];
                for(const div of all){
                    if(div.innerText.includes('University Of Mumbai') && div.innerText.includes('BBA') && div.innerText.includes('Edit')){
                        // Find Edit button inside
                        const edit = [...div.querySelectorAll('button, a')].find(b => b.innerText.trim() === 'Edit');
                        if(edit){
                            edit.click();
                            return 'found and clicked';
                        }
                    }
                }
                return 'not found';
            }""")
            print(f"JS click result: {clicked}")
            await page.wait_for_timeout(2500)
            await page.screenshot(path="precise_mumbai_edit.png", full_page=True)
            # Now click Remove education for this Mumbai entry
            # The edit form should be open for Mumbai now, with Remove education
            remove = page.get_by_text("Remove education").first
            if await remove.count() and await remove.is_visible():
                await remove.scroll_into_view_if_needed()
                await remove.click()
                print("Clicked Remove education for Mumbai")
                await page.wait_for_timeout(2000)
                await page.screenshot(path="precise_mumbai_after_remove.png", full_page=True)
            else:
                print("Remove not found after Mumbai edit")
                # Try JS
                await page.evaluate("() => { const b=[...document.querySelectorAll('button, a')].find(x=>x.innerText.trim()==='Remove education'); if(b) b.click(); }")
                await page.wait_for_timeout(2000)

        # Verify
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        has_mumbai = await page.evaluate("() => document.body.innerText.includes('University Of Mumbai')")
        has_nfsu = await page.evaluate("() => document.body.innerText.includes('National Forensic')")
        print(f"After - Mumbai: {has_mumbai}, NFSU: {has_nfsu}")
        body = await page.evaluate("() => document.body.innerText.slice(0,1200)")
        print(body[:600])
        await page.screenshot(path="precise_final.png", full_page=True)

        # Now fix NFSU degree if still MA
        # Check if NFSU entry shows MA
        has_ma = await page.evaluate("() => document.body.innerText.includes('Master of Arts')")
        print(f"Has MA: {has_ma}")
        if has_ma:
            print("Fixing NFSU MA to M.Tech...")
            # Click Edit on the NFSU MA card
            clicked2 = await page.evaluate("""() => {
                const divs = [...document.querySelectorAll('div')].filter(d => d.innerText.includes('National Forensic') && d.innerText.includes('Master of Arts'));
                for(const d of divs){
                    const edit = [...d.querySelectorAll('button, a')].find(b => b.innerText.trim()==='Edit');
                    if(edit){edit.click(); return 'clicked MA edit';}
                    // Check parent
                    let p=d;
                    for(let i=0;i<5;i++){
                        if(!p) break;
                        const e = [...p.querySelectorAll('button, a')].find(b=>b.innerText.trim()==='Edit');
                        if(e){e.click(); return 'clicked parent edit '+i;}
                        p=p.parentElement;
                    }
                }
                return 'not found';
            }""")
            print(f"MA Edit click: {clicked2}")
            await page.wait_for_timeout(2500)
            await page.screenshot(path="precise_ma_edit.png", full_page=True)
            # Now change Degree Type from MA to M.Tech or Master
            # Click the Degree Type dropdown (currently shows Master of Arts)
            try:
                # Find the select with MA
                await page.evaluate("""() => {
                    const labels = [...document.querySelectorAll('label')].find(l=>l.innerText.includes('Degree'));
                    if(labels){
                        const ctrl = labels.parentElement.querySelector('div.select__control') || document.querySelector('div.select__control');
                        if(ctrl) ctrl.click();
                    }
                }""")
                await page.wait_for_timeout(800)
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
                await page.keyboard.type("M.Tech", delay=30)
                await page.wait_for_timeout(1000)
                opts = page.locator('[role="option"]')
                cnt_o = await opts.count()
                print(f"M.Tech options: {cnt_o}")
                for i in range(min(cnt_o,6)):
                    txt = await opts.nth(i).inner_text()
                    print(f" opt {i}: {txt}")
                t = page.get_by_role("option").filter(has_text="M.Tech").first
                if await t.count():
                    await t.click()
                    print("Selected M.Tech")
                else:
                    t2 = page.get_by_role("option").filter(has_text="Master of Technology").first
                    if await t2.count():
                        await t2.click()
                        print("Selected Master of Technology")
                    else:
                        if cnt_o>0:
                            await opts.first.click()
                            print(f"Selected first: {await opts.first.inner_text()}")
                await page.wait_for_timeout(800)
                # Save
                save = page.locator('button:has-text("Save")').first
                saves = page.locator('button:has-text("Save")')
                c = await saves.count()
                print(f"Save buttons: {c}")
                for i in range(c):
                    b = saves.nth(i)
                    if await b.is_visible():
                        box = await b.bounding_box()
                        if box and box['y']>300:
                            await b.click()
                            print(f"Clicked Save {i}")
                            await page.wait_for_timeout(3000)
                            break
            except Exception as e:
                print(f"MA fix error: {e}")

        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        final_mumbai = await page.evaluate("() => document.body.innerText.includes('University Of Mumbai')")
        final_nfsu = await page.evaluate("() => document.body.innerText.includes('National Forensic')")
        final_has_ma = await page.evaluate("() => document.body.innerText.includes('Master of Arts')")
        print(f"Final Mumbai: {final_mumbai}, NFSU: {final_nfsu}, Has MA: {final_has_ma}")
        await page.screenshot(path="precise_final2.png", full_page=True)
        print("Keeping open 10 sec...")
        await page.wait_for_timeout(10000)
    finally:
        await context.close()
        await playwright.stop()
        print("Done")

if __name__ == "__main__":
    asyncio.run(main())
