import asyncio
from wellfound_agent.browser.session import create_browser_context

async def delete_all_educations(page):
    print("\nDeleting all existing educations to start fresh...")
    # Find all Edit buttons in Education section
    # Education section has Edit links
    for attempt in range(5):
        # Locate education cards - they contain "University" text
        has_edu = await page.evaluate("() => document.body.innerText.includes('University')")
        if not has_edu:
            print("  No more education entries found")
            break
        # Try to find Delete after clicking Edit
        # Find the first education card's Edit
        try:
            # Click Edit on first education card
            # The card has title University and an Edit button at right
            edit_btn = page.locator('button:has-text("Edit"), a:has-text("Edit")').first
            # Need to find the one near University text - use JS
            clicked = await page.evaluate("""() => {
                const edits = [...document.querySelectorAll('button, a')].filter(e => e.innerText.trim() === 'Edit');
                // Find the one closest to University text
                for(const btn of edits){
                    const card = btn.closest('div');
                    if(card && card.innerText.includes('University')){
                        btn.click();
                        return true;
                    }
                }
                // Fallback: click first Edit
                if(edits.length>0){edits[0].click(); return true;}
                return false;
            }""")
            if not clicked:
                # Try direct locator
                E = page.get_by_text("Edit").first
                if await E.count():
                    await E.click()
            print(f"  Clicked Edit attempt {attempt+1}")
            await page.wait_for_timeout(2000)
            await page.screenshot(path=f"fix_correct_edit_{attempt}.png", full_page=True)
            # Look for Delete button in edit mode
            del_btn = page.locator('button:has-text("Delete"), a:has-text("Delete")').first
            if await del_btn.count() > 0 and await del_btn.is_visible():
                await del_btn.click()
                print("  -> Clicked Delete")
                await page.wait_for_timeout(1000)
                # Confirm delete if modal
                confirm = page.locator('button:has-text("Delete")').last
                if await confirm.count() > 0:
                    # Check if its a confirm dialog
                    try:
                        await confirm.click(timeout=2000)
                        print("  -> Confirmed Delete")
                    except:
                        pass
                await page.wait_for_timeout(2000)
                # After delete, check if still has University
                await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(3000)
            else:
                print("  No Delete found after Edit, trying Cancel and next")
                cancel = page.get_by_text("Cancel").first
                if await cancel.count():
                    await cancel.click()
                    await page.wait_for_timeout(1000)
                break
        except Exception as e:
            print(f"  Delete attempt {attempt} failed: {e}")
            break

async def add_correct_education(page):
    print("\nAdding correct NFSU education...")
    try:
        add_btn = page.get_by_text("+ Add education").first
        if await add_btn.count() == 0:
            add_btn = page.locator('text=Add education').first
        await add_btn.scroll_into_view_if_needed()
        await add_btn.click()
        print("  -> Clicked + Add education")
        await page.wait_for_timeout(2000)
        await page.screenshot(path="fix_correct_add_form.png", full_page=True)

        # College - handle custom NFSU
        edu_input = page.locator('input[placeholder="College / University"]').first
        await edu_input.scroll_into_view_if_needed()
        await edu_input.click()
        await page.wait_for_timeout(300)
        await edu_input.fill("")
        await edu_input.type("National Forensic Sciences University", delay=25)
        await page.wait_for_timeout(2000)
        # Check options
        opts = page.locator('[role="option"]')
        cnt = await opts.count()
        print(f"  College options: {cnt}")
        selected = False
        for i in range(min(cnt,8)):
            txt = await opts.nth(i).inner_text()
            print(f"   opt {i}: {txt[:70]}")
            if "Forensic" in txt:
                await opts.nth(i).click()
                print(f"  -> Selected {txt[:50]}")
                selected = True
                break
        if not selected:
            print("  No Forensic found, creating custom via Enter")
            # Try Create option
            create = page.locator('[role="option"]:has-text("Create")').first
            if await create.count()>0:
                await create.click()
                print("  -> Clicked Create")
            else:
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(500)
                # If still open, Escape
                if await opts.count()>0:
                    await page.keyboard.press("Escape")
        await page.wait_for_timeout(800)

        # Graduation - use 2028 (5-year integrated from 2023)
        grad = page.locator('input[placeholder="Graduation"]').first
        await grad.click()
        await grad.fill("")
        await grad.type("2028", delay=30)
        await page.keyboard.press("Enter")
        print(f"  Graduation 2028")
        await page.wait_for_timeout(500)

        # Degree Type - need to handle react-select correctly
        # Find the control for Degree Type
        # Approach: click the placeholder "Degree Type"
        try:
            # The Degree Type control is a select with placeholder Degree Type
            deg_control = page.locator('div').filter(has_text="Degree Type").first
            # Find the select control below
            # Alternative: locate by the hidden input's id pattern
            # Try clicking the control that contains Degree Type text
            # Look for the select wrapper
            # Use JS to find and click
            clicked = await page.evaluate("""() => {
                const labels = [...document.querySelectorAll('label')].find(l => l.innerText.includes('Degree'));
                if(labels){
                    const control = labels.parentElement.querySelector('div.select__control') || labels.nextElementSibling?.querySelector('div.select__control') || document.querySelector('div.select__control');
                    if(control){control.click(); return true;}
                }
                // Fallback: click any select control that is near Degree Type
                const all = [...document.querySelectorAll('div.select__control')];
                if(all.length>=3){
                    all[2].click(); return true; // try 3rd control (after location, primary role, years)
                }
                return false;
            }""")
            print(f"  Degree control clicked via JS: {clicked}")
            await page.wait_for_timeout(800)
            # Now type
            await page.keyboard.type("Master", delay=30)
            await page.wait_for_timeout(1000)
            deg_opts = page.locator('[role="option"]')
            cnt2 = await deg_opts.count()
            print(f"  Degree options for Master: {cnt2}")
            for i in range(min(cnt2,10)):
                txt = await deg_opts.nth(i).inner_text()
                print(f"   deg {i}: {txt}")
            # Try Master of Technology or M.Tech or Master
            target = None
            for name in ["M.Tech", "Master of Technology", "Master's", "Master", "M Tech"]:
                t = page.get_by_role("option").filter(has_text=name).first
                if await t.count():
                    target = t
                    print(f"  Found target {name}")
                    break
            if target and await target.count():
                await target.click()
                print(f"  -> Selected degree target")
            else:
                if cnt2>0:
                    txt = await deg_opts.first.inner_text()
                    await deg_opts.first.click()
                    print(f"  -> Selected first degree: {txt}")
                else:
                    await page.keyboard.press("Enter")
            await page.wait_for_timeout(800)
        except Exception as e:
            print(f"  Degree failed: {e}")
            await page.keyboard.press("Escape")

        # Major
        major = page.locator('input[placeholder="Major / Field of Study"]').first
        await major.scroll_into_view_if_needed()
        await major.click()
        await major.fill("")
        await major.type("Computer Science (Cybersecurity)", delay=20)
        await page.wait_for_timeout(500)
        # Check for option
        m_opts = page.locator('[role="option"]')
        if await m_opts.count()>0:
            # If dropdown appears, select or press Enter
            await page.keyboard.press("Enter")
        await page.wait_for_timeout(500)
        print("  Major filled")

        # GPA
        gpa = page.locator('input[placeholder="GPA"]').first
        await gpa.click()
        await gpa.fill("")
        await gpa.type("8.8", delay=20)
        print("  GPA 8.8")
        max_gpa = page.locator('input[placeholder="Max"]').first
        await max_gpa.click()
        await max_gpa.fill("")
        await max_gpa.type("10", delay=20)
        print("  Max 10")
        await page.wait_for_timeout(500)

        # Save
        save_btns = page.locator('button:has-text("Save")')
        cnt = await save_btns.count()
        print(f"  Save buttons: {cnt}")
        # Find the Save in education card (near bottom, likely last visible)
        for i in range(cnt-1, -1, -1):
            btn = save_btns.nth(i)
            if await btn.is_visible():
                box = await btn.bounding_box()
                if box and box['y'] > 400:
                    print(f"  Clicking Save {i} at y={box['y']}")
                    await btn.click()
                    await page.wait_for_timeout(3500)
                    break
        await page.screenshot(path="fix_correct_after_save.png", full_page=True)
        print("  Education added")
        return True
    except Exception as e:
        print(f"  Add correct failed: {e}")
        import traceback
        traceback.print_exc()
        await page.screenshot(path="fix_correct_error.png", full_page=True)
        return False

async def main():
    playwright, context = await create_browser_context(headless=False)
    try:
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        await page.screenshot(path="fix_correct_start.png", full_page=True)
        print(f"Start URL {page.url}")

        # First, try to delete wrong entries if any, or just add correct and then delete old
        # Check current educations
        body = await page.evaluate("() => document.body.innerText")
        print("Current has Mumbai:", "University Of Mumbai" in body)
        print("Current has NFSU:", "Forensic" in body)

        # If has Mumbai, try to delete it via the more direct JS approach
        if "University Of Mumbai" in body:
            print("Attempting to remove Mumbai entry...")
            # Try JS deletion
            # Click Edit on Mumbai card then Delete
            try:
                await page.evaluate("""() => {
                    const cards = [...document.querySelectorAll('div')].filter(d => d.innerText.includes('University Of Mumbai') && d.innerText.includes('BBA'));
                    if(cards.length>0){
                        const card = cards[0];
                        const edit = [...card.querySelectorAll('button, a')].find(b => b.innerText.trim() === 'Edit');
                        if(edit) edit.click();
                    }
                }""")
                await page.wait_for_timeout(2000)
                await page.screenshot(path="fix_correct_mumbai_edit.png", full_page=True)
                del_btn = page.locator('button:has-text("Delete")').first
                if await del_btn.count() and await del_btn.is_visible():
                    await del_btn.click()
                    print("  -> Clicked Delete for Mumbai")
                    await page.wait_for_timeout(1000)
                    confirm = page.locator('button:has-text("Delete")').last
                    if await confirm.count():
                        await confirm.click()
                        print("  -> Confirmed")
                        await page.wait_for_timeout(2000)
            except Exception as e:
                print(f"  Mumbai delete failed: {e}")

        # Also check if we have New NFSU entry with wrong degree (BBA) - delete it too if degree is BBA
        # For now, just delete all educations to be clean
        # Let's check again after attempt
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        # Count education cards
        edu_count = await page.evaluate("() => [...document.querySelectorAll('*')].filter(e => (e.innerText||'').includes('University') && (e.innerText||'').includes('2027')).length")
        print(f"Education cards count: {edu_count}")

        # If still has any, delete all via loop
        for _ in range(3):
            has_any = await page.evaluate("() => document.body.innerText.includes('University Of Mumbai') || document.body.innerText.includes('Forensic Sciences')")
            if not has_any:
                break
            print("  Deleting an education entry...")
            try:
                await page.evaluate("""() => {
                    const edit = [...document.querySelectorAll('button, a')].find(b => b.innerText.trim() === 'Edit' && b.closest('div')?.innerText.includes('University'));
                    if(edit) edit.click();
                }""")
                await page.wait_for_timeout(2000)
                db = page.locator('button:has-text("Delete")').first
                if await db.count() and await db.is_visible():
                    await db.click()
                    await page.wait_for_timeout(1000)
                    conf = page.locator('button:has-text("Delete")').last
                    if await conf.count():
                        await conf.click()
                    await page.wait_for_timeout(2000)
                    print("   deleted one")
                    await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
                    await page.wait_for_timeout(3000)
                else:
                    print("   no delete, cancel")
                    cancel = page.get_by_text("Cancel").first
                    if await cancel.count():
                        await cancel.click()
                        await page.wait_for_timeout(1000)
                    break
            except Exception as e:
                print(f"   delete loop error: {e}")
                break

        # Now add correct one
        await add_correct_education(page)

        # Final check
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        await page.screenshot(path="fix_correct_final.png", full_page=True)
        body2 = await page.evaluate("() => document.body.innerText.slice(0,1500)")
        print("\n=== Final body snippet ===")
        print(body2[:1200])
        steps = await page.evaluate("() => { const m=document.body.innerText.match(/(\\d+) steps to complete/); return m?m[0]:'no steps'; }")
        print(f"\nSteps: {steps}")
        has_nfsu = await page.evaluate("() => document.body.innerText.includes('National Forensic') || document.body.innerText.includes('Forensic Sciences')")
        has_mumbai = await page.evaluate("() => document.body.innerText.includes('University Of Mumbai')")
        print(f"Has NFSU: {has_nfsu}, Has Mumbai: {has_mumbai}")
        print("Keeping open 20 sec...")
        await page.wait_for_timeout(20000)
    finally:
        await context.close()
        await playwright.stop()
        print("Fix correct done")

if __name__ == "__main__":
    asyncio.run(main())
