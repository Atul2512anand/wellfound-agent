import asyncio
from wellfound_agent.browser.session import create_browser_context

async def main():
    p,c = await create_browser_context(headless=False)
    try:
        page = c.pages[0] if c.pages else await c.new_page()
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        print("Filling work experience...")
        # Scroll to work experience
        exp_label = page.locator('text=Your work experience').first
        await exp_label.scroll_into_view_if_needed()
        await page.wait_for_timeout(500)
        # Company
        company = page.locator('input[placeholder="Type to search"]').first
        await company.scroll_into_view_if_needed()
        await company.click()
        await page.wait_for_timeout(500)
        await company.fill("")
        await company.type("EmergeSmart Health", delay=30)
        await page.wait_for_timeout(1500)
        # Check for Create option
        opts = page.locator('[role="option"]')
        cnt = await opts.count()
        print(f"Company options: {cnt}")
        for i in range(min(cnt,3)):
            txt = await opts.nth(i).inner_text()
            print(f" opt {i}: {txt[:80]}")
        if cnt > 0:
            # Click Create EmergeSmart Health
            create = page.get_by_role("option").filter(has_text="Create").first
            if await create.count():
                await create.click()
                print("Clicked Create")
            else:
                await opts.first.click()
                print("Clicked first option")
        else:
            await page.keyboard.press("Enter")
            print("Pressed Enter for company")
        await page.wait_for_timeout(800)

        # Title
        title = page.locator('input[placeholder="Title"]').first
        await title.click()
        await title.fill("")
        await title.type("Cybersecurity & Tech Analyst Intern", delay=20)
        print("Title filled")
        await page.wait_for_timeout(500)

        # Start date - try 07/2025
        start = page.locator('input[placeholder="Start date"]').first
        await start.scroll_into_view_if_needed()
        await start.click()
        await page.wait_for_timeout(300)
        # Try typing
        await start.fill("")
        # Try format July 2025
        await start.type("July 2025", delay=20)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(500)
        val = await start.input_value()
        print(f"Start value: '{val}'")
        if not val or "2025" not in val:
            await start.fill("")
            await start.type("07/2025", delay=20)
            await page.keyboard.press("Enter")
            print(f"Retry start: '{await start.input_value()}'")
        await page.wait_for_timeout(500)

        # End date
        end = page.locator('input[placeholder="End date"]').first
        await end.click()
        await end.fill("")
        await end.type("February 2026", delay=20)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(500)
        print(f"End value: '{await end.input_value()}'")

        # Description
        desc = page.locator('textarea[placeholder="Description"]').first
        if await desc.count() == 0:
            desc = page.locator('textarea').filter(has_text="Description").first
            if await desc.count()==0:
                # Find textarea near work exp
                desc = page.locator('div:has-text("Your work experience")').locator('..').locator('textarea').first
        await desc.scroll_into_view_if_needed()
        await desc.click()
        await desc.fill("")
        await desc.type("Built ZOHO CRM automated workflow and launched WordPress Webzine. Conducted OSINT across 50+ data points, improved compliance visibility. Assessed HTTP flood resilience (5+ recommendations).", delay=10)
        print("Description filled")
        await page.wait_for_timeout(500)

        # This position is a... dropdown - select Internship or Full-time
        try:
            pos_label = page.locator('text=This position is a').first
            await pos_label.scroll_into_view_if_needed()
            # Find the select control near it
            # Click the placeholder
            await page.evaluate("""() => {
                const label = [...document.querySelectorAll('*')].find(e => e.innerText.includes('This position is a'));
                if(label){
                    const ctrl = label.parentElement.querySelector('div.select__control') || document.querySelector('div.select__control');
                    if(ctrl) ctrl.click();
                }
            }""")
            await page.wait_for_timeout(800)
            await page.keyboard.type("Internship", delay=20)
            await page.wait_for_timeout(800)
            opt = page.get_by_role("option").filter(has_text="Internship").first
            if await opt.count():
                await opt.click()
                print("Selected Internship")
            else:
                await page.keyboard.press("Enter")
        except Exception as e:
            print(f"Position type failed: {e}")

        # Save work experience
        saves = page.locator('button:has-text("Save")')
        cnt_s = await saves.count()
        print(f"Save buttons: {cnt_s}")
        # Find the Save near work experience (likely last visible)
        for i in range(cnt_s-1, -1, -1):
            btn = saves.nth(i)
            if await btn.is_visible():
                box = await btn.bounding_box()
                if box:
                    # Work exp Save is near middle (y ~ 800-900)
                    print(f" Save {i} at y={box['y']}")
                    if 600 < box['y'] < 1200:
                        await btn.scroll_into_view_if_needed()
                        await btn.click()
                        print(f"Clicked Save {i} for work exp")
                        break
        await page.wait_for_timeout(3500)
        await page.screenshot(path="work_exp_after_save.png", full_page=True)
        print("Work exp save attempted")

        # Also refill bio if empty (shows 0)
        bio_check = await page.evaluate("() => { const ta=document.querySelector('textarea[name=\"bio\"]'); return ta ? ta.value.length : -1; }")
        print(f"Bio length: {bio_check}")
        if bio_check == 0:
            print("Refilling bio...")
            bio = page.locator('textarea[name="bio"]').first
            if await bio.count()==0:
                bio = page.locator('textarea[placeholder*="Stanford"]').first
            await bio.scroll_into_view_if_needed()
            await bio.click()
            await bio.fill("")
            bio_text = "Cybersecurity & Software Engineer (NFSU, GPA 8.8/10) with Python, FastAPI, React, Blockchain, ML/DL. Built AgriSupplyChain DApp, Agentic AI bike maintenance (XGBoost+LangChain), face-recognition on Azure. Interned at EmergeSmart, IIT BHU, Vodafone."
            await bio.type(bio_text[:160], delay=10)
            print("Bio refilled")
            # Save bio - need to click Save near About?
            # The About Save is near top, but we can scroll and find Save
            await page.wait_for_timeout(500)
            # Try to find Save near About (first Save)
            saves2 = page.locator('button:has-text("Save")')
            for i in range(await saves2.count()):
                b = saves2.nth(i)
                if await b.is_visible():
                    box = await b.bounding_box()
                    if box and box['y'] < 400:
                        await b.click()
                        print(f"Clicked Save {i} for bio")
                        await page.wait_for_timeout(2000)
                        break

        # Final check
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        steps = await page.evaluate("() => { const m=document.body.innerText.match(/(\\d+) steps to complete/); return m?m[0]:'no steps'; }")
        print(f"\nSteps after work exp: {steps}")
        has_work = await page.evaluate("() => document.body.innerText.includes('EmergeSmart')")
        print(f"Has EmergeSmart: {has_work}")
        await page.screenshot(path="work_exp_final.png", full_page=True)
        print("Keeping open 15 sec...")
        await page.wait_for_timeout(15000)
    finally:
        await c.close()
        await p.stop()
        print("Done")

if __name__ == "__main__":
    asyncio.run(main())
