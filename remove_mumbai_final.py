import asyncio
from wellfound_agent.browser.session import create_browser_context

async def main():
    playwright, context = await create_browser_context(headless=False)
    try:
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3500)
        # If in edit mode, cancel
        remove_cnt = await page.get_by_text("Remove education").count()
        print(f"Initial Remove count: {remove_cnt}")
        if remove_cnt > 0:
            cancel = page.get_by_text("Cancel").first
            if await cancel.count() and await cancel.is_visible():
                await cancel.click()
                print("Clicked Cancel to close edit")
                await page.wait_for_timeout(1500)

        # Now find and delete Mumbai - target last Edit
        edits = page.get_by_text("Edit")
        cnt = await edits.count()
        print(f"Edit buttons: {cnt}")
        for i in range(cnt):
            txt = await edits.nth(i).inner_text()
            # Get nearby card text
            card_text = await page.evaluate(f"""() => {{
                const btn = [...document.querySelectorAll('button, a')].filter(b => b.innerText.trim()==='Edit')[{i}];
                if(!btn) return 'no btn';
                let p = btn.parentElement;
                for(let k=0;k<6;k++){{
                    if(!p) break;
                    if(p.innerText.includes('University')) return p.innerText.slice(0,150);
                    p = p.parentElement;
                }}
                return btn.closest('div')?.innerText.slice(0,150) || 'unknown';
            }}""")
            print(f" Edit {i}: {card_text[:80]}")

        # Click last Edit (should be Mumbai BBA)
        if cnt > 0:
            last_edit = edits.last
            await last_edit.scroll_into_view_if_needed()
            await last_edit.click()
            print(f"Clicked last Edit (Mumbai expected)")
            await page.wait_for_timeout(2500)
            await page.screenshot(path="remove_final_edit.png", full_page=True)
            # Now click Remove education for this Mumbai entry
            remove = page.get_by_text("Remove education").first
            if await remove.count() and await remove.is_visible():
                await remove.scroll_into_view_if_needed()
                await remove.click()
                print("Clicked Remove education for Mumbai")
                await page.wait_for_timeout(2000)
                # Check if need confirm - sometimes it asks to confirm
                # Look for any dialog with Delete/Confirm
                await page.screenshot(path="remove_final_after_remove.png", full_page=True)
            else:
                print("Remove not found after clicking last Edit")
                # Try JS
                await page.evaluate("""() => {
                    const btn = [...document.querySelectorAll('button, a')].find(b => b.innerText.trim()==='Remove education');
                    if(btn) btn.click();
                }""")
                await page.wait_for_timeout(2000)

        # Verify Mumbai gone
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        has_mumbai = await page.evaluate("() => document.body.innerText.includes('University Of Mumbai')")
        has_nfsu = await page.evaluate("() => document.body.innerText.includes('National Forensic')")
        print(f"After Mumbai delete - Has Mumbai: {has_mumbai}, Has NFSU: {has_nfsu}")
        await page.screenshot(path="remove_final_verify.png", full_page=True)

        # Now fix NFSU degree - find NFSU entry and edit it to set M.Tech
        if has_nfsu:
            print("\nFixing NFSU degree to M.Tech/B.Tech...")
            # Find NFSU card's Edit (now should be only one NFSU left, but there were two: one with MA and one with 2028 and no degree)
            # After Mumbai delete, there should be 2 NFSU entries: one MA and one 01/2028 with no degree (the top form's entry)
            # Let's edit the one with 01/2028 (the top form was for that, but we cancelled)
            # Now click Edit on the NFSU entry that has no degree or MA
            # Find the NFSU card with MA or 01/2028 and click its Edit
            edits2 = page.get_by_text("Edit")
            cnt2 = await edits2.count()
            print(f"Edits after Mumbai delete: {cnt2}")
            # Try to find NFSU with 01/2028
            for i in range(cnt2):
                card = await page.evaluate(f"""() => {{
                    const btn = [...document.querySelectorAll('button, a')].filter(b => b.innerText.trim()==='Edit')[{i}];
                    if(!btn) return '';
                    let p = btn.closest('div');
                    for(let k=0;k<6;k++){{
                        if(!p) break;
                        if(p.innerText.includes('National Forensic')) return p.innerText.slice(0,200);
                        p = p.parentElement;
                    }}
                    return '';
                }}""")
                print(f" NFSU card {i}: {card[:100]}")
                if "National Forensic" in card:
                    # Click this Edit
                    await edits2.nth(i).click()
                    print(f"Clicked Edit for NFSU card {i}")
                    await page.wait_for_timeout(2500)
                    await page.screenshot(path=f"fix_nfsu_degree_edit_{i}.png", full_page=True)
                    # Now handle Degree Type
                    # The Degree Type control is empty or shows Degree Type
                    try:
                        # Click the Degree Type dropdown
                        # Find the select with placeholder Degree Type
                        await page.evaluate("""() => {
                            const labels = [...document.querySelectorAll('label')].find(l => l.innerText.includes('Degree'));
                            if(labels){
                                const ctrl = labels.closest('div').querySelector('div.select__control') || document.querySelector('div.select__control');
                                if(ctrl) ctrl.click();
                            }
                        }""")
                        await page.wait_for_timeout(800)
                        await page.keyboard.type("M.Tech", delay=30)
                        await page.wait_for_timeout(1000)
                        opts = page.locator('[role="option"]')
                        cnt_o = await opts.count()
                        print(f"  Degree options: {cnt_o}")
                        for k in range(min(cnt_o,6)):
                            txt = await opts.nth(k).inner_text()
                            print(f"   opt {k}: {txt}")
                        # Try M.Tech
                        t = page.get_by_role("option").filter(has_text="M.Tech").first
                        if await t.count():
                            await t.click()
                            print("  -> Selected M.Tech")
                        else:
                            t2 = page.get_by_role("option").filter(has_text="Master").first
                            if await t2.count():
                                await t2.click()
                                print("  -> Selected Master")
                            else:
                                if cnt_o>0:
                                    await opts.first.click()
                                    print(f"  -> First: {await opts.first.inner_text()}")
                                else:
                                    await page.keyboard.press("Enter")
                        await page.wait_for_timeout(800)
                        # Save
                        save = page.locator('button:has-text("Save")').first
                        # Find the Save in this form
                        saves = page.locator('button:has-text("Save")')
                        c = await saves.count()
                        print(f"  Save buttons: {c}")
                        for j in range(c):
                            b = saves.nth(j)
                            if await b.is_visible():
                                box = await b.bounding_box()
                                if box and box['y'] > 300:
                                    await b.click()
                                    print(f"  -> Clicked Save {j}")
                                    await page.wait_for_timeout(3000)
                                    break
                    except Exception as e:
                        print(f"  Degree fix error: {e}")
                        await page.keyboard.press("Escape")
                    break

        # Final verification
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        final_mumbai = await page.evaluate("() => document.body.innerText.includes('University Of Mumbai')")
        final_nfsu = await page.evaluate("() => document.body.innerText.includes('National Forensic')")
        body = await page.evaluate("() => document.body.innerText.slice(0,1200)")
        print(f"\nFinal - Mumbai: {final_mumbai}, NFSU: {final_nfsu}")
        print(body[:600])
        await page.screenshot(path="remove_final_final.png", full_page=True)
        print("Keeping open 15 sec...")
        await page.wait_for_timeout(15000)
    finally:
        await context.close()
        await playwright.stop()
        print("Done")

if __name__ == "__main__":
    asyncio.run(main())
