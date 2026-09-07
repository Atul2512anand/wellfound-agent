import asyncio
from wellfound_agent.browser.session import create_browser_context

async def fix_bio(page):
    print("\n--- Bio ---")
    try:
        bio = page.locator('textarea[name="bio"]').first
        if await bio.count()==0:
            bio = page.locator('textarea[placeholder*="Stanford"]').first
        await bio.scroll_into_view_if_needed()
        await bio.click()
        await page.wait_for_timeout(300)
        # Clear
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        bio_text = "Cybersecurity & Software Engineer (NFSU, GPA 8.8/10) with Python, FastAPI, React, Blockchain, ML/DL. Built AgriSupplyChain DApp, Agentic AI bike maintenance (XGBoost+LangChain), face-recognition on Azure. Interned at EmergeSmart, IIT BHU, Vodafone. Seeking SDE/Cybersecurity roles."
        # Wellfound bio max 160
        bio_text = bio_text[:160]
        await bio.type(bio_text, delay=10)
        await page.wait_for_timeout(500)
        print(f"  Bio filled len {len(bio_text)}")
        # Save near About
        # Find Save button near top (y < 500)
        saves = page.locator('button:has-text("Save")')
        cnt = await saves.count()
        for i in range(cnt):
            b = saves.nth(i)
            if await b.is_visible():
                box = await b.bounding_box()
                if box and box['y'] < 600:
                    await b.scroll_into_view_if_needed()
                    await b.click()
                    print(f"  Clicked Save bio {i} y={box['y']}")
                    await page.wait_for_timeout(2500)
                    break
        return True
    except Exception as e:
        print(f" Bio failed: {e}")
        return False

async def fix_work_exp(page):
    print("\n--- Work Experience ---")
    try:
        # Scroll to work exp
        await page.locator('text=Your work experience').first.scroll_into_view_if_needed()
        await page.wait_for_timeout(500)
        # Company
        company = page.locator('input[placeholder="Type to search"]').first
        await company.scroll_into_view_if_needed()
        await company.click()
        await page.wait_for_timeout(400)
        await company.fill("")
        await company.type("EmergeSmart Health", delay=25)
        await page.wait_for_timeout(1800)
        # Look for Create option specifically for EmergeSmart Health
        opts = page.locator('[role="option"]')
        cnt = await opts.count()
        print(f"  Company opts: {cnt}")
        # Print first few
        for i in range(min(cnt,5)):
            txt = await opts.nth(i).inner_text()
            print(f"   {i}: {txt[:70]}")
        # Try to find Create EmergeSmart
        create = page.locator('[role="option"]').filter(has_text="Create").first
        # More precise: option containing EmergeSmart
        create_emerge = page.locator('[role="option"]').filter(has_text="EmergeSmart").first
        if await create_emerge.count():
            txt = await create_emerge.inner_text()
            print(f"  Found EmergeSmart option: {txt[:80]}")
            await create_emerge.click()
            print("  Clicked EmergeSmart Create")
        elif await create.count():
            await create.click()
            print("  Clicked Create")
        else:
            # If no create, press Enter to create custom
            await page.keyboard.press("Enter")
            print("  Pressed Enter for company")
        await page.wait_for_timeout(800)

        # Title
        title = page.locator('input[placeholder="Title"]').first
        await title.click()
        await title.fill("")
        await title.type("Cybersecurity & Tech Analyst Intern", delay=15)
        print("  Title filled")
        await page.wait_for_timeout(400)

        # Start date
        start = page.locator('input[placeholder="Start date"]').first
        await start.scroll_into_view_if_needed()
        await start.click()
        await page.wait_for_timeout(300)
        await start.fill("")
        await start.type("July 2025", delay=20)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(500)
        print(f"  Start: {await start.input_value()}")

        # End date
        end = page.locator('input[placeholder="End date"]').first
        await end.click()
        await end.fill("")
        await end.type("February 2026", delay=20)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(500)
        print(f"  End: {await end.input_value()}")

        # Description
        desc = page.locator('textarea[placeholder="Description"]').first
        if await desc.count()==0:
            # Find textarea near work exp
            desc = page.locator('div:has-text("Your work experience")').locator('..').locator('textarea').first
        await desc.scroll_into_view_if_needed()
        await desc.click()
        await desc.fill("")
        await desc.type("Built ZOHO CRM workflow, launched WordPress Webzine, OSINT 50+ data points, HTTP flood resilience 5+ recs.", delay=8)
        print("  Desc filled")
        await page.wait_for_timeout(400)

        # This position is a... - scroll and click
        # Find the dropdown
        pos_dropdown = page.locator('text=This position is a').first
        await pos_dropdown.scroll_into_view_if_needed()
        await page.wait_for_timeout(300)
        # Click the control below it
        # The control is a div.select__control near it
        # Use JS to click
        clicked = await page.evaluate("""() => {
            const label = [...document.querySelectorAll('*')].find(e => e.innerText.includes('This position is a'));
            if(!label) return false;
            let el = label;
            for(let i=0;i<4;i++){
                const ctrl = el.parentElement.querySelector('div.select__control');
                if(ctrl){ctrl.click(); return true;}
                el = el.parentElement;
                if(!el) break;
            }
            // Fallback: click any select control near bottom
            const ctrls = [...document.querySelectorAll('div.select__control')];
            if(ctrls.length>0){ctrls[ctrls.length-2].click(); return true;}
            return false;
        }""")
        print(f"  Position dropdown clicked: {clicked}")
        await page.wait_for_timeout(800)
        await page.keyboard.type("Internship", delay=20)
        await page.wait_for_timeout(1000)
        opt = page.get_by_role("option").filter(has_text="Internship").first
        if await opt.count():
            await opt.click()
            print("  Selected Internship")
        else:
            # First option
            o2 = page.locator('[role="option"]').first
            if await o2.count():
                await o2.click()
                print(f"  Selected first position: {await o2.inner_text()}")
            else:
                await page.keyboard.press("Enter")
        await page.wait_for_timeout(500)

        # Save work exp - find Save near work exp (y 600-900)
        saves = page.locator('button:has-text("Save")')
        cnt_s = await saves.count()
        print(f"  Save buttons: {cnt_s}")
        for i in range(cnt_s-1, -1, -1):
            b = saves.nth(i)
            if await b.is_visible():
                box = await b.bounding_box()
                if box and 500 < box['y'] < 1100:
                    print(f"  Clicking Save {i} y={box['y']}")
                    await b.scroll_into_view_if_needed()
                    await b.click()
                    await page.wait_for_timeout(3500)
                    # Check for error
                    err = await page.evaluate("() => document.body.innerText.includes('required') ? document.body.innerText.slice(0,500) : ''")
                    if err:
                        print(f"  Save error hint: {err[:200]}")
                    break
        print("  Work exp save done")
        return True
    except Exception as e:
        print(f"  Work exp failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def fix_degree(page):
    print("\n--- Degree fix for NFSU (if empty) ---")
    try:
        # Check current NFSU entry degree
        # The NFSU 2028 entry currently has Degree Type empty (shows placeholder)
        # Find the NFSU card with 2028 and click Edit
        # Locate the card with National Forensic and 2028
        # Use JS to find and click Edit
        clicked = await page.evaluate("""() => {
            const cards = [...document.querySelectorAll('div')].filter(d => d.innerText.includes('National Forensic') && d.innerText.includes('2028'));
            for(const card of cards){
                let p=card;
                for(let i=0;i<6;i++){
                    if(!p) break;
                    const edit = [...p.querySelectorAll('button, a')].find(b=>b.innerText.trim()==='Edit');
                    if(edit && p.innerText.includes('National Forensic')){
                        edit.click();
                        return 'clicked';
                    }
                    p=p.parentElement;
                }
            }
            // Fallback: find any Edit near NFSU
            const edits = [...document.querySelectorAll('button, a')].filter(b=>b.innerText.trim()==='Edit');
            for(const btn of edits){
                let p=btn.closest('div');
                for(let i=0;i<6;i++){
                    if(!p) break;
                    if(p.innerText.includes('National Forensic') && p.innerText.includes('2028')){
                        btn.click();
                        return 'clicked fallback';
                    }
                    p=p.parentElement;
                }
            }
            return 'not found';
        }""")
        print(f"  NFSU Edit click: {clicked}")
        if "clicked" not in clicked:
            print("  No NFSU 2028 edit found, skipping degree fix")
            return False
        await page.wait_for_timeout(2500)
        await page.screenshot(path="fix_degree_edit.png", full_page=True)
        # Now fix Degree Type
        # The Degree Type field is empty (placeholder Degree Type)
        # Click its control
        await page.evaluate("""() => {
            const label = [...document.querySelectorAll('label')].find(l=>l.innerText.includes('Degree'));
            if(label){
                const ctrl = label.closest('div').querySelector('div.select__control') || document.querySelector('div.select__control');
                if(ctrl) ctrl.click();
            }
        }""")
        await page.wait_for_timeout(800)
        await page.keyboard.type("Master", delay=25)
        await page.wait_for_timeout(1000)
        opts = page.locator('[role="option"]')
        cnt = await opts.count()
        print(f"  Degree opts for Master: {cnt}")
        for i in range(min(cnt,6)):
            txt = await opts.nth(i).inner_text()
            print(f"   {i}: {txt}")
        # Try M.Tech
        t = page.get_by_role("option").filter(has_text="M.Tech").first
        if await t.count():
            await t.click()
            print("  Selected M.Tech")
        else:
            t2 = page.get_by_role("option").filter(has_text="Master of Technology").first
            if await t2.count():
                await t2.click()
                print("  Selected Master of Technology")
            else:
                t3 = page.get_by_role("option").filter(has_text="Master").first
                if await t3.count():
                    await t3.click()
                    print("  Selected Master")
                else:
                    if cnt>0:
                        await opts.first.click()
                        print(f"  First: {await opts.first.inner_text()}")
                    else:
                        await page.keyboard.press("Enter")
        await page.wait_for_timeout(800)
        # Save
        saves = page.locator('button:has-text("Save")')
        # Find Save in this form (near degree)
        for i in range(await saves.count()-1, -1, -1):
            b = saves.nth(i)
            if await b.is_visible():
                box = await b.bounding_box()
                if box and box['y']>400 and box['y']<900:
                    await b.click()
                    print(f"  Clicked Save for degree {i}")
                    await page.wait_for_timeout(3000)
                    break
        return True
    except Exception as e:
        print(f"  Degree fix failed: {e}")
        return False

async def main():
    p,c = await create_browser_context(headless=False)
    try:
        page = c.pages[0] if c.pages else await c.new_page()
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        await page.screenshot(path="fix_all_start.png", full_page=True)
        print("Start fixes...")

        await fix_bio(page)
        await page.wait_for_timeout(1000)
        await fix_work_exp(page)
        await page.wait_for_timeout(1000)
        await fix_degree(page)
        await page.wait_for_timeout(1000)

        # Final verification
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        steps = await page.evaluate("() => { const m=document.body.innerText.match(/(\\d+) steps to complete/); return m?m[0]:'no steps'; }")
        has_work = await page.evaluate("() => document.body.innerText.includes('EmergeSmart')")
        bio_len = await page.evaluate("() => { const ta=document.querySelector('textarea[name=\"bio\"]'); return ta?ta.value.length:0; }")
        has_mumbai = await page.evaluate("() => document.body.innerText.includes('University Of Mumbai')")
        print(f"\nFinal - Steps: {steps}, Has EmergeSmart: {has_work}, Bio len: {bio_len}, Has Mumbai: {has_mumbai}")
        await page.screenshot(path="fix_all_final.png", full_page=True)
        print("Keeping open 15 sec...")
        await page.wait_for_timeout(15000)
    finally:
        await c.close()
        await p.stop()
        print("Fix all done")

if __name__ == "__main__":
    asyncio.run(main())
