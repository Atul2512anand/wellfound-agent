import asyncio
from wellfound_agent.browser.session import create_browser_context

async def main():
    playwright, context = await create_browser_context(headless=False)
    try:
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3500)
        # If in edit mode (Remove education visible), cancel first
        remove_visible = await page.get_by_text("Remove education").count()
        print(f"Remove visible at start: {remove_visible}")
        if remove_visible > 0:
            cancel = page.get_by_text("Cancel").first
            if await cancel.count():
                await cancel.click()
                print("Clicked Cancel to exit edit mode")
                await page.wait_for_timeout(2000)

        # Now find Mumbai card's Edit and delete it
        print("\nFinding Mumbai card...")
        # Use JS to click Edit for Mumbai
        clicked = await page.evaluate("""() => {
            const cards = [...document.querySelectorAll('div')].filter(d => d.innerText.includes('University Of Mumbai') && d.innerText.includes('BBA'));
            console.log('cards', cards.length);
            for(const card of cards){
                // Find Edit button within card's parent
                let parent = card;
                for(let i=0;i<5;i++){
                    if(!parent) break;
                    const edit = [...parent.querySelectorAll('button, a')].find(b => b.innerText.trim() === 'Edit');
                    if(edit){
                        edit.click();
                        return `clicked Edit for Mumbai card at level ${i}`;
                    }
                    parent = parent.parentElement;
                }
            }
            // Alternative: find all Edit buttons and check nearby text
            const edits = [...document.querySelectorAll('button, a')].filter(b => b.innerText.trim() === 'Edit');
            for(const btn of edits){
                const container = btn.closest('div');
                if(container && container.innerText.includes('University Of Mumbai')){
                    btn.click();
                    return 'clicked via container check';
                }
            }
            return 'not found';
        }""")
        print(f"JS click result: {clicked}")
        await page.wait_for_timeout(2500)
        await page.screenshot(path="fix_mumbai_delete_edit.png", full_page=True)
        # Now click Remove education for Mumbai
        remove = page.get_by_text("Remove education").first
        cnt = await remove.count()
        print(f"Remove education count after edit: {cnt}")
        if cnt > 0 and await remove.is_visible():
            await remove.scroll_into_view_if_needed()
            await remove.click()
            print("Clicked Remove education for Mumbai")
            await page.wait_for_timeout(1500)
            # Check if confirmation needed? Usually it just removes
            await page.screenshot(path="fix_mumbai_delete_after.png", full_page=True)
        else:
            print("Remove not found after clicking Edit for Mumbai")
            # Try alternative: look for Remove in page
            has_remove = await page.evaluate("() => document.body.innerText.includes('Remove education')")
            print(f"Has Remove text: {has_remove}")

        await page.wait_for_timeout(2000)
        # Verify
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        has_mumbai = await page.evaluate("() => document.body.innerText.includes('University Of Mumbai')")
        has_nfsu = await page.evaluate("() => document.body.innerText.includes('National Forensic')")
        print(f"After delete - Has Mumbai: {has_mumbai}, Has NFSU: {has_nfsu}")
        body = await page.evaluate("() => document.body.innerText.slice(0,1200)")
        print(body[:800])
        await page.screenshot(path="fix_mumbai_delete_final.png", full_page=True)

        # Now fix NFSU degree to M.Tech if needed
        # Check current NFSU entry degree
        # The remaining NFSU entry shows MA - need to change to M.Tech
        if has_nfsu:
            print("\nFixing NFSU degree to M.Tech...")
            # Click Edit on NFSU
            clicked2 = await page.evaluate("""() => {
                const cards = [...document.querySelectorAll('div')].filter(d => d.innerText.includes('National Forensic Sciences University'));
                for(const card of cards){
                    let parent = card;
                    for(let i=0;i<5;i++){
                        if(!parent) break;
                        const edit = [...parent.querySelectorAll('button, a')].find(b => b.innerText.trim() === 'Edit');
                        if(edit && parent.innerText.includes('National Forensic')){
                            edit.click();
                            return 'clicked NFSU Edit';
                        }
                        parent = parent.parentElement;
                    }
                }
                const edits = [...document.querySelectorAll('button, a')].filter(b => b.innerText.trim() === 'Edit');
                for(const btn of edits){
                    if(btn.closest('div')?.innerText.includes('National Forensic')){
                        btn.click();
                        return 'clicked via fallback';
                    }
                }
                return 'not found NFSU';
            }""")
            print(f"NFSU Edit click: {clicked2}")
            await page.wait_for_timeout(2500)
            await page.screenshot(path="fix_nfsu_edit.png", full_page=True)
            # Now Degree Type dropdown
            # Find the Degree Type select
            try:
                # Click the Degree Type control
                # The control shows "Degree Type" placeholder or current value MA
                deg_control = page.locator('div.select__control').filter(has_text="Degree Type").first
                if await deg_control.count() == 0:
                    # Try finding by text MA or BBA
                    deg_control = page.locator('div.select__control').filter(has_text="MA").first
                    if await deg_control.count()==0:
                        deg_control = page.locator('div.select__control').first
                        # But we need the one for Degree & Major
                # Alternative: click the dropdown that contains "Master" or "MA"
                # Find label Degree & Major
                await page.evaluate("""() => {
                    const label = [...document.querySelectorAll('label')].find(l => l.innerText.includes('Degree'));
                    if(label){
                        const control = label.parentElement.querySelector('div.select__control') || document.querySelector('div.select__control');
                        if(control) control.click();
                    }
                }""")
                await page.wait_for_timeout(800)
                # Type M.Tech
                await page.keyboard.type("M.Tech", delay=30)
                await page.wait_for_timeout(1000)
                # Check options
                opts = page.locator('[role="option"]')
                cnt2 = await opts.count()
                print(f"Degree options for M.Tech: {cnt2}")
                for i in range(min(cnt2,8)):
                    txt = await opts.nth(i).inner_text()
                    print(f" deg {i}: {txt}")
                # Try to select M.Tech
                target = page.get_by_role("option").filter(has_text="M.Tech").first
                if await target.count():
                    await target.click()
                    print(" -> Selected M.Tech")
                else:
                    target2 = page.get_by_role("option").filter(has_text="Master").first
                    if await target2.count():
                        await target2.click()
                        print(" -> Selected Master")
                    else:
                        if cnt2>0:
                            await opts.first.click()
                            print(f" -> Selected first: {await opts.first.inner_text()}")
                        else:
                            await page.keyboard.press("Enter")
                await page.wait_for_timeout(800)
                # Save
                save = page.locator('button:has-text("Save")').first
                # Find Save near education form
                saves = page.locator('button:has-text("Save")')
                cnt_s = await saves.count()
                print(f"Save buttons: {cnt_s}")
                # Click the Save in the edit form (first Save visible)
                for i in range(cnt_s):
                    btn = saves.nth(i)
                    if await btn.is_visible():
                        box = await btn.bounding_box()
                        if box and box['y'] > 300:
                            await btn.click()
                            print(f" -> Clicked Save {i}")
                            break
                await page.wait_for_timeout(3000)
                await page.screenshot(path="fix_nfsu_after_save.png", full_page=True)
            except Exception as e:
                print(f"Degree fix failed: {e}")
                import traceback
                traceback.print_exc()

        # Final verification
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        final_has_mumbai = await page.evaluate("() => document.body.innerText.includes('University Of Mumbai')")
        final_has_nfsu = await page.evaluate("() => document.body.innerText.includes('National Forensic')")
        final_body = await page.evaluate("() => document.body.innerText.slice(0,1200)")
        print(f"\nFinal Has Mumbai: {final_has_mumbai}, Has NFSU: {final_has_nfsu}")
        print(final_body[:800])
        await page.screenshot(path="fix_final_check.png", full_page=True)
        print("Keeping open 15 sec...")
        await page.wait_for_timeout(15000)
    finally:
        await context.close()
        await playwright.stop()
        print("Done")

if __name__ == "__main__":
    asyncio.run(main())
