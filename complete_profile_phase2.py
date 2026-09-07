"""Phase 2: Fill work experience, education, skills, location."""
import asyncio, pathlib
from wellfound_agent.browser.session import create_browser_context

async def fill_location2(page):
    print("\n[FIX] Location...")
    try:
        # Scroll to Where are you based?
        loc_label = page.locator('label:has-text("Where are you based")').first
        await loc_label.scroll_into_view_if_needed()
        await page.wait_for_timeout(800)
        inp = page.locator('input[placeholder="e.g. San Francisco"]').first
        if await inp.count() == 0:
            inp = page.locator('input[id^="downshift-"]').first
        await inp.click()
        await page.wait_for_timeout(500)
        # Clear and type
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await inp.type("India", delay=40)
        await page.wait_for_timeout(1800)
        # Select option
        opts = page.locator('[role="option"]')
        cnt = await opts.count()
        print(f"  location options: {cnt}")
        if cnt > 0:
            # Try India
            for i in range(min(cnt,5)):
                txt = await opts.nth(i).inner_text()
                print(f"   opt {i}: {txt}")
                if "India" in txt:
                    await opts.nth(i).click()
                    print(f"  -> clicked {txt}")
                    break
            else:
                await opts.first.click()
        else:
            # Try typing more specific
            await inp.fill("Dharwad, Karnataka, India")
            await page.wait_for_timeout(1500)
            opts2 = page.locator('[role="option"]')
            if await opts2.count()>0:
                await opts2.first.click()
            else:
                await page.keyboard.press("Enter")
        await page.wait_for_timeout(1000)
        # Check value
        val = await inp.input_value()
        print(f"  location value now: '{val}'")
        return True
    except Exception as e:
        print(f"  location2 failed: {e}")
        return False

async def fill_work_experience(page):
    print("\n[FIX] Work experience...")
    try:
        # Scroll to work experience
        exp_section = page.locator('text=Your work experience').first
        await exp_section.scroll_into_view_if_needed()
        await page.wait_for_timeout(500)
        # Company
        company = page.locator('input[placeholder="Type to search"]').first
        if await company.count()==0:
            # Try other selector
            company = page.locator('label:has-text("Company")').locator('..').locator('input').first
        await company.scroll_into_view_if_needed()
        await company.click()
        await page.wait_for_timeout(500)
        await company.fill("")
        await company.type("EmergeSmart Health", delay=30)
        await page.wait_for_timeout(1500)
        # Check for dropdown options for company
        opts = page.locator('[role="option"]')
        cnt = await opts.count()
        print(f"  company options: {cnt}")
        if cnt>0:
            # Try to select first
            txt = await opts.first.inner_text()
            print(f"   first opt: {txt}")
            # If option looks like company, click, else press Enter to create new
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(500)
        else:
            await page.keyboard.press("Enter")
        await page.wait_for_timeout(500)
        # Title
        title = page.locator('input[placeholder="Title"]').first
        await title.click()
        await title.fill("Cybersecurity & Tech Analyst Intern")
        print(f"  title filled")
        await page.wait_for_timeout(500)
        # Start date - try to click and type
        start = page.locator('input[placeholder="Start date"]').first
        if await start.count()>0:
            await start.scroll_into_view_if_needed()
            await start.click()
            await page.wait_for_timeout(500)
            # Try typing July 2025
            await start.fill("July 2025")
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(500)
            # Alternative: if date picker appears, select
            # Check if calendar
            # For now, try typing 07/2025
            val = await start.input_value()
            print(f"  start date value: '{val}'")
            if not val or "July" not in val:
                # Try different format
                await start.fill("")
                await start.type("07/2025", delay=30)
                await page.keyboard.press("Enter")
                print(f"  retried start date: '{await start.input_value()}'")
        # End date
        end = page.locator('input[placeholder="End date"]').first
        if await end.count()>0:
            await end.click()
            await end.fill("February 2026")
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(500)
        # Check I currently work here? Not needed
        # Description
        desc = page.locator('textarea[placeholder="Description"]').first
        if await desc.count()>0:
            await desc.click()
            await desc.fill("Built ZOHO CRM automated workflow, launched WordPress Webzine, OSINT across 50+ data points, HTTP flood resilience (5+ recommendations).")
            print("  description filled")
        # Save work experience if there's a Save button in that card
        # The card has Cancel and Save at bottom
        save = page.locator('button:has-text("Save")').last
        # There are multiple Saves, need the one near work experience
        # Let's find Save near work experience section
        try:
            # Scroll to bottom of work exp card and click Save
            await save.scroll_into_view_if_needed()
            # Check if visible and enabled
            if await save.is_visible() and await save.is_enabled():
                await save.click()
                print("  -> Clicked Save for work exp")
                await page.wait_for_timeout(3000)
            else:
                print("  Save not visible/enabled")
        except Exception as e:
            print(f"  Save work exp failed: {e}")
        return True
    except Exception as e:
        print(f"  work exp failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def fill_education(page):
    print("\n[FIX] Education...")
    try:
        edu_label = page.locator('text=Education*').first
        await edu_label.scroll_into_view_if_needed()
        await page.wait_for_timeout(500)
        edu_input = page.locator('input[placeholder="College / University"]').first
        if await edu_input.count()==0:
            edu_input = page.locator('input[placeholder*="College"]').first
        await edu_input.click()
        await edu_input.fill("National Forensic Sciences University")
        await page.wait_for_timeout(1500)
        opts = page.locator('[role="option"]')
        cnt = await opts.count()
        print(f"  edu options: {cnt}")
        if cnt>0:
            txt = await opts.first.inner_text()
            print(f"   {txt}")
            await opts.first.click()
            await page.wait_for_timeout(500)
        else:
            await page.keyboard.press("Enter")
        await page.wait_for_timeout(500)
        # Graduation - try to find year input
        # Look for inputs near Education
        # The graduation field placeholder "Graduation"
        grad = page.locator('input[placeholder="Graduation"]').first
        if await grad.count()>0:
            await grad.click()
            await grad.fill("2027")
            await page.keyboard.press("Enter")
            print(f"  grad filled: {await grad.input_value()}")
        # Degree Type dropdown
        try:
            degree_select = page.locator('text=Degree Type').locator('..').locator('div.select__control').first
            if await degree_select.count()==0:
                # Find by "Degree Type" label
                degree_select = page.locator('label:has-text("Degree")').locator('..').locator('div').first
            # Alternative: find all select controls and click the one for degree
            # degree is 4th select? Let's just try to click by placeholder
            # The degree dropdown shows "Degree Type"
            await page.get_by_text("Degree Type", exact=False).first.click(timeout=3000)
            await page.wait_for_timeout(800)
            await page.keyboard.type("Bachelor", delay=30)
            await page.wait_for_timeout(800)
            opt = page.get_by_role("option").filter(has_text="Bachelor").first
            if await opt.count():
                await opt.click()
                print("  -> Degree Bachelor")
            else:
                await page.keyboard.press("Enter")
        except Exception as e:
            print(f"  degree failed: {e}")
            await page.keyboard.press("Escape")
        # Major
        try:
            major = page.locator('input[placeholder="Major / Field of Study"]').first
            if await major.count()>0:
                await major.click()
                await major.fill("Computer Science (Cybersecurity)")
                await page.keyboard.press("Enter")
                print("  major filled")
        except Exception as e:
            print(f"  major failed: {e}")
        # GPA
        try:
            gpa = page.locator('input[placeholder="GPA"]').first
            if await gpa.count()>0:
                await gpa.click()
                await gpa.fill("8.8")
                print("  gpa filled")
            max_gpa = page.locator('input[placeholder="Max"]').first
            if await max_gpa.count()>0:
                await max_gpa.click()
                await max_gpa.fill("10")
                print("  max gpa filled")
        except Exception as e:
            print(f"  gpa failed: {e}")
        # Save education
        try:
            # Education card has Save at bottom
            save_edu = page.locator('button:has-text("Save")').last
            # Need to differentiate - but try clicking last Save visible
            saves = page.locator('button:has-text("Save")')
            cnt = await saves.count()
            print(f"  Save buttons: {cnt}")
            for i in range(cnt):
                btn = saves.nth(i)
                if await btn.is_visible():
                    txt = await btn.inner_text()
                    print(f"   save {i}: {txt} visible")
            # Try to click the one near education (second last?)
            if cnt>=2:
                await saves.nth(cnt-2).click()
                print("  -> Clicked Save for education")
                await page.wait_for_timeout(3000)
        except Exception as e:
            print(f"  save edu failed: {e}")
        return True
    except Exception as e:
        print(f"  education failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def fill_skills(page):
    print("\n[FIX] Skills...")
    try:
        skills_label = page.locator('text=Your Skills').first
        await skills_label.scroll_into_view_if_needed()
        await page.wait_for_timeout(500)
        skills_input = page.locator('input[placeholder="e.g. Python, React"]').first
        if await skills_input.count()==0:
            skills_input = page.locator('input[placeholder*="Python"]').first
        await skills_input.scroll_into_view_if_needed()
        await skills_input.click()
        await page.wait_for_timeout(300)
        skills = "Python, Java, Cybersecurity, Blockchain, Machine Learning, React, FastAPI, SQL, Docker, Azure"
        # Type skills one by one and press Enter
        for skill in skills.split(", "):
            await skills_input.type(skill, delay=20)
            await page.wait_for_timeout(500)
            # Try to select option or press Enter
            opts = page.locator('[role="option"]')
            cnt = await opts.count()
            if cnt>0:
                # click first
                await opts.first.click()
                await page.wait_for_timeout(300)
            else:
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(300)
        print(f"  skills added")
        await page.wait_for_timeout(1000)
        # Save skills? There is no explicit save for skills, maybe auto-saves
        # But check for Save button near skills
        return True
    except Exception as e:
        print(f"  skills failed: {e}")
        return False

async def main():
    playwright, context = await create_browser_context(headless=False)
    try:
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        await page.screenshot(path="phase2_before.png", full_page=True)
        print(f"Start URL {page.url}")

        await fill_location2(page)
        await page.wait_for_timeout(1000)
        await fill_work_experience(page)
        await page.wait_for_timeout(1500)
        await fill_education(page)
        await page.wait_for_timeout(1500)
        await fill_skills(page)
        await page.wait_for_timeout(1500)

        # Final screenshot and save
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        await page.screenshot(path="phase2_after.png", full_page=True)
        body = await page.evaluate("() => document.body.innerText.slice(0,1500)")
        print("\n=== After phase2 body snippet ===")
        print(body[:1200])
        # Check steps
        steps_text = await page.evaluate("() => { const m = document.body.innerText.match(/(\\d+) steps to complete/); return m ? m[0] : 'no steps found' }")
        print(f"\nSteps remaining: {steps_text}")
        print("Keeping open 25 sec...")
        await page.wait_for_timeout(25000)
    finally:
        await context.close()
        await playwright.stop()
        print("Phase2 done")

if __name__ == "__main__":
    asyncio.run(main())
