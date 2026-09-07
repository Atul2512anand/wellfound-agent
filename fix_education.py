import asyncio
from wellfound_agent.browser.session import create_browser_context

async def main():
    playwright, context = await create_browser_context(headless=False)
    try:
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        print("Opened profile edit")
        await page.screenshot(path="fix_edu_start.png", full_page=True)
        # Step 1: Remove wrong University Of Mumbai entry
        print("\nStep 1: Handling existing wrong entry...")
        # Find Edit button near University Of Mumbai
        # The entry has text "University Of Mumbai" and an Edit link
        try:
            # Look for the card with University Of Mumbai
            mumbai_card = page.locator('text=University Of Mumbai').first
            if await mumbai_card.count() > 0:
                print("  Found Mumbai entry")
                # Find Edit button nearby
                # The card has an Edit on right
                edit_btn = page.locator('button:has-text("Edit"), a:has-text("Edit")').filter(has_text="Edit").first
                # More precise: find Edit near that card
                # Try to click the Edit in that education card
                # The structure: Education card has Edit at top right
                edit_in_edu = page.locator('text=University Of Mumbai').locator('..').locator('..').get_by_text("Edit").first
                if await edit_in_edu.count() == 0:
                    # Alternative: find all Edit and click the one for education (second Edit)
                    edits = page.get_by_text("Edit")
                    cnt = await edits.count()
                    print(f"  Edit buttons found: {cnt}")
                    # Education Edit is likely first or second
                    for i in range(cnt):
                        txt = await edits.nth(i).inner_text()
                        print(f"   Edit {i}: {txt}")
                    # Try clicking the education Edit (usually near 2027)
                    # Let's try to locate via the card
                    await page.evaluate("""() => {
                        const cards = [...document.querySelectorAll('*')].filter(e => e.innerText.includes('University Of Mumbai'));
                        console.log(cards.length);
                    }""")
                    # Simplest: click the Edit button that is near the 2027 text
                    target = page.locator('div:has-text("University Of Mumbai")').get_by_text("Edit").first
                    if await target.count() > 0:
                        await target.click()
                        print("  -> Clicked Edit via div:has-text")
                    else:
                        # Fallback: click first Edit after scrolling to education
                        await page.locator('text=University Of Mumbai').scroll_into_view_if_needed()
                        await page.wait_for_timeout(500)
                        # Try to find delete or edit via JS
                        await page.evaluate("""() => {
                            const el = [...document.querySelectorAll('button, a')].find(e => e.innerText.trim() === 'Edit' && e.closest('div')?.innerText.includes('University Of Mumbai'));
                            if(el) el.click();
                        }""")
                        print("  -> Tried JS click")
                else:
                    await edit_in_edu.click()
                    print("  -> Clicked Edit")
                await page.wait_for_timeout(2500)
                await page.screenshot(path="fix_edu_after_edit_click.png", full_page=True)
                # Now in edit mode, look for Delete option or Cancel and try to remove
                # Check for Delete button
                del_btn = page.get_by_text("Delete").first
                if await del_btn.count() > 0 and await del_btn.is_visible():
                    await del_btn.click()
                    print("  -> Clicked Delete")
                    await page.wait_for_timeout(1500)
                    # Confirm
                    confirm = page.get_by_role("button", name="Delete").first
                    if await confirm.count():
                        await confirm.click()
                        print("  -> Confirmed Delete")
                    await page.wait_for_timeout(2000)
                else:
                    print("  No Delete button, will overwrite or add new and delete later")
                    # If no delete, we can just close edit and add new
                    cancel = page.get_by_text("Cancel").first
                    if await cancel.count():
                        await cancel.click()
                        await page.wait_for_timeout(1000)
            else:
                print("  No Mumbai entry found - maybe already removed")
        except Exception as e:
            print(f"  Step1 error: {e}")
            import traceback
            traceback.print_exc()

        # Step 2: Add correct NFSU education
        print("\nStep 2: Adding correct NFSU education...")
        try:
            add_btn = page.get_by_text("+ Add education").first
            if await add_btn.count() == 0:
                add_btn = page.locator('text=Add education').first
            await add_btn.scroll_into_view_if_needed()
            await add_btn.click()
            print("  -> Clicked + Add education")
            await page.wait_for_timeout(2000)
            await page.screenshot(path="fix_edu_add_form.png", full_page=True)

            # Fill College - type NFSU and handle not found
            edu_input = page.locator('input[placeholder="College / University"]').first
            await edu_input.click()
            await edu_input.fill("")
            await edu_input.type("National Forensic Sciences University", delay=30)
            await page.wait_for_timeout(1800)
            # Check options
            opts = page.locator('[role="option"]')
            cnt = await opts.count()
            print(f"  College options: {cnt}")
            found_nfsu = False
            for i in range(min(cnt,6)):
                txt = await opts.nth(i).inner_text()
                print(f"   opt {i}: {txt[:80]}")
                if "Forensic" in txt or "National Forensic" in txt:
                    await opts.nth(i).click()
                    found_nfsu = True
                    print(f"  -> Selected {txt}")
                    break
            if not found_nfsu:
                print("  No NFSU found, pressing Enter to create custom")
                # Press Enter to create custom / or click Create
                # Look for "Create" option
                create_opt = page.locator('[role="option"]:has-text("Create")').first
                if await create_opt.count()>0:
                    await create_opt.click()
                    print("  -> Clicked Create")
                else:
                    await page.keyboard.press("Enter")
                    await page.wait_for_timeout(500)
                    # Check if still open, press again
                    if await opts.count()>0:
                        await page.keyboard.press("Escape")
            await page.wait_for_timeout(1000)

            # Graduation - try 2027
            grad = page.locator('input[placeholder="Graduation"]').first
            await grad.click()
            await grad.fill("2027")
            await page.keyboard.press("Enter")
            print(f"  Graduation filled: {await grad.input_value()}")
            await page.wait_for_timeout(500)

            # Degree Type - try Master of Technology or M.Tech
            # Find degree dropdown
            # The placeholder is "Degree Type"
            try:
                # Click the dropdown control for Degree Type
                # Find label Degree Type then nearby control
                degree_label = page.locator('text=Degree Type').first
                await degree_label.scroll_into_view_if_needed()
                # Click the control below
                degree_control = page.locator('div.select__control').nth(2)  # approximate index
                # More robust: find the select with placeholder Degree Type
                # Try to click by text
                await page.get_by_text("Degree Type").first.click()
                await page.wait_for_timeout(500)
                # Now find the input inside
                degree_input = page.locator('input[id*="react-select"][id*="Degree"]')
                # Alternative: just type
                await page.keyboard.type("Master", delay=30)
                await page.wait_for_timeout(1000)
                deg_opts = page.locator('[role="option"]')
                cnt2 = await deg_opts.count()
                print(f"  Degree options for Master: {cnt2}")
                for i in range(min(cnt2,8)):
                    txt = await deg_opts.nth(i).inner_text()
                    print(f"   deg {i}: {txt}")
                # Try to select Master or M.Tech
                target = page.get_by_role("option").filter(has_text="Master").first
                if await target.count():
                    await target.click()
                    print("  -> Selected Master")
                else:
                    target2 = page.locator('[role="option"]').filter(has_text="M.Tech").first
                    if await target2.count():
                        await target2.click()
                        print("  -> Selected M.Tech")
                    else:
                        # First option
                        if cnt2>0:
                            await deg_opts.first.click()
                            print(f"  -> Selected first degree: {await deg_opts.first.inner_text()}")
                        else:
                            await page.keyboard.press("Enter")
                await page.wait_for_timeout(800)
            except Exception as e:
                print(f"  Degree failed: {e}")
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(500)

            # Major
            major = page.locator('input[placeholder="Major / Field of Study"]').first
            await major.click()
            await major.fill("Computer Science (Cybersecurity)")
            await page.keyboard.press("Enter")
            print("  Major filled")
            await page.wait_for_timeout(500)

            # GPA
            gpa = page.locator('input[placeholder="GPA"]').first
            await gpa.click()
            await gpa.fill("8.8")
            print("  GPA 8.8")
            max_gpa = page.locator('input[placeholder="Max"]').first
            await max_gpa.click()
            await max_gpa.fill("10")
            print("  Max 10")
            await page.wait_for_timeout(500)

            # Save education
            save_btns = page.locator('button:has-text("Save")')
            cnt = await save_btns.count()
            print(f"  Save buttons: {cnt}")
            # The last Save is likely for education form
            # Try clicking the Save in the education card
            for i in range(cnt-1, -1, -1):
                btn = save_btns.nth(i)
                if await btn.is_visible():
                    box = await btn.bounding_box()
                    if box and box['y'] > 300:  # lower on page (education is mid)
                        print(f"  Trying Save {i} at y={box['y']}")
                        await btn.click()
                        print("  -> Clicked Save for education")
                        await page.wait_for_timeout(3000)
                        break
            await page.screenshot(path="fix_edu_after_save.png", full_page=True)
        except Exception as e:
            print(f"  Step2 error: {e}")
            import traceback
            traceback.print_exc()

        # Step 3: If still have Mumbai, try to delete it now via Edit
        print("\nStep 3: Check remaining entries...")
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        body = await page.evaluate("() => document.body.innerText.slice(0,1200)")
        print(body[:1000])
        await page.screenshot(path="fix_edu_final.png", full_page=True)
        # Check if NFSU present
        has_nfsu = await page.evaluate("() => document.body.innerText.includes('National Forensic') || document.body.innerText.includes('Forensic Sciences')")
        has_mumbai = await page.evaluate("() => document.body.innerText.includes('University Of Mumbai')")
        print(f"Has NFSU: {has_nfsu}, Has Mumbai: {has_mumbai}")
        # If Mumbai still there, try to remove via JS
        if has_mumbai:
            print("Mumbai still present - attempting to remove via Edit->Delete...")
            try:
                await page.evaluate("""() => {
                    const btn = [...document.querySelectorAll('button')].find(b => b.innerText.trim() === 'Edit' && document.body.innerText.includes('University Of Mumbai'));
                    if(btn) btn.click();
                }""")
                await page.wait_for_timeout(2000)
                # Look for Delete
                del2 = page.get_by_text("Delete").first
                if await del2.count():
                    await del2.click()
                    await page.wait_for_timeout(1000)
                    # Confirm
                    confirm = page.locator('button:has-text("Delete")').last
                    if await confirm.count():
                        await confirm.click()
                        await page.wait_for_timeout(2000)
                        print("  -> Deleted Mumbai")
            except Exception as e:
                print(f"  Delete Mumbai failed: {e}")
        print("Keeping open 15 sec...")
        await page.wait_for_timeout(15000)
    finally:
        await context.close()
        await playwright.stop()
        print("Fix education done")

if __name__ == "__main__":
    asyncio.run(main())
