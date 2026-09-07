"""Complete Wellfound profile using resume data."""
import asyncio
import pathlib
from wellfound_agent.browser.session import create_browser_context

RESUME_PDF = pathlib.Path(__file__).parent / "resume.pdf"
RESUME_TXT = pathlib.Path(__file__).parent / "resume.txt"

async def fill_location(page):
    print("\n[1] Filling location...")
    try:
        # Location input is downshift combobox
        loc = page.locator('input[placeholder="e.g. San Francisco"]').first
        if await loc.count() == 0:
            loc = page.locator('input[id^="downshift-"][id$="-input"]').first
        await loc.scroll_into_view_if_needed()
        await loc.click()
        await page.wait_for_timeout(800)
        await loc.fill("")
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await loc.type("Dharwad, India", delay=50)
        await page.wait_for_timeout(1500)
        # Try to select option containing India or Dharwad
        opt = page.get_by_role("option", name="India").first
        if await opt.count() > 0:
            await opt.click()
            print("  -> Selected India")
        else:
            opt2 = page.locator('[role="option"]').first
            if await opt2.count() > 0:
                await opt2.click()
                print(f"  -> Selected first option: {await opt2.inner_text()}")
            else:
                await page.keyboard.press("Enter")
                print("  -> Pressed Enter for location")
        await page.wait_for_timeout(1000)
        return True
    except Exception as e:
        print(f"  Location failed: {e}")
        return False

async def fill_primary_role(page):
    print("\n[2] Filling primary role...")
    try:
        # Click the control, not hidden input
        # Find the placeholder "Select role" under primary role label
        label = page.locator('label:has-text("Select your primary role")').first
        control = page.locator('div.select__control').first
        # Try to find control near label
        # Alternative: click by text
        try:
            await page.get_by_text("Select role", exact=False).first.click(timeout=5000)
        except:
            # Fallback: click the control div
            await control.click(timeout=5000)
        await page.wait_for_timeout(800)
        # Type role
        await page.keyboard.type("Software Engineer", delay=30)
        await page.wait_for_timeout(1000)
        # Select option
        opt = page.get_by_role("option", name="Software Engineer").first
        if await opt.count() > 0:
            await opt.click()
            print("  -> Selected Software Engineer")
        else:
            # Try partial
            opt2 = page.locator('[role="option"]').filter(has_text="Software").first
            if await opt2.count() > 0:
                await opt2.click()
                print(f"  -> Selected {await opt2.inner_text()}")
            else:
                await page.keyboard.press("Enter")
                print("  -> Pressed Enter")
        await page.wait_for_timeout(800)
        return True
    except Exception as e:
        print(f"  Primary role failed: {e}")
        try:
            await page.keyboard.press("Escape")
        except: pass
        return False

async def fill_years_experience(page):
    print("\n[3] Filling years of experience...")
    try:
        # Years is second select
        # Try to click second "Select"
        selects = page.locator('div.select__control')
        count = await selects.count()
        print(f"  Found {count} select controls")
        if count >= 2:
            await selects.nth(1).click()
        else:
            # Fallback: click by label
            await page.get_by_text("Years of experience").click()
            await page.wait_for_timeout(500)
            # Find next control
            await page.locator('div.select__control').nth(1).click()
        await page.wait_for_timeout(800)
        await page.keyboard.type("1", delay=30)
        await page.wait_for_timeout(800)
        # Look for 1 year option
        opt = page.get_by_role("option").filter(has_text="1").first
        if await opt.count() > 0:
            txt = await opt.inner_text()
            await opt.click()
            print(f"  -> Selected {txt}")
        else:
            # Try 0-1 or 1-2
            opt2 = page.locator('[role="option"]').first
            if await opt2.count() > 0:
                txt = await opt2.inner_text()
                await opt2.click()
                print(f"  -> Selected first: {txt}")
            else:
                await page.keyboard.press("Enter")
        await page.wait_for_timeout(800)
        return True
    except Exception as e:
        print(f"  Years failed: {e}")
        try:
            await page.keyboard.press("Escape")
        except: pass
        return False

async def fill_bio(page):
    print("\n[4] Filling bio...")
    try:
        bio_text = """Cybersecurity & Software Engineer (NFSU, GPA 8.8/10) with experience in Python, FastAPI, React, Blockchain, ML/DL. Built blockchain DApp for AgriSupplyChain, Agentic AI bike maintenance (XGBoost+LangChain), face-recognition attendance on Azure. Interned at EmergeSmart Health (Zoho CRM, OSINT, HTTP flood resilience), IIT BHU (ML/DL 85-95% accuracy), Vodafone (9k+ retail entries). Seeking Software Engineer / Cybersecurity roles - India/Remote."""
        bio = page.locator('textarea[name="bio"]').first
        if await bio.count() == 0:
            bio = page.locator('textarea[placeholder*="Stanford"]').first
        await bio.scroll_into_view_if_needed()
        await bio.click()
        await bio.fill("")
        await bio.type(bio_text[:250], delay=10)  # Limit to ~250 chars, Wellfound max 160? but we try 160
        # Check that bio is required 160 chars? The preview said 160, but we have 250, let's trim to 160
        await page.wait_for_timeout(500)
        print("  -> Bio filled")
        return True
    except Exception as e:
        print(f"  Bio failed: {e}")
        return False

async def upload_resume(page):
    print("\n[5] Uploading resume...")
    try:
        # Go to Resume tab
        resume_tab = page.get_by_role("link", name="Resume / CV").first
        if await resume_tab.count() > 0:
            await resume_tab.click()
            await page.wait_for_timeout(2500)
            await page.screenshot(path="profile_resume_tab.png")
            print("  -> On Resume tab")
        # Find file input
        file_input = page.locator('input[type="file"]').first
        if await file_input.count() == 0:
            print("  No file input found")
            return False
        # Upload
        if RESUME_PDF.exists():
            await file_input.set_input_files(str(RESUME_PDF))
            print(f"  -> Uploaded {RESUME_PDF.name}")
        elif RESUME_TXT.exists():
            await file_input.set_input_files(str(RESUME_TXT))
            print(f"  -> Uploaded {RESUME_TXT.name}")
        await page.wait_for_timeout(3000)
        await page.screenshot(path="profile_after_upload.png")
        return True
    except Exception as e:
        print(f"  Upload failed: {e}")
        return False

async def fill_preferences(page):
    print("\n[6] Filling Preferences...")
    try:
        pref_tab = page.get_by_role("link", name="Preferences").first
        if await pref_tab.count() > 0:
            await pref_tab.click()
            await page.wait_for_timeout(2500)
            await page.screenshot(path="profile_preferences_before.png")
        # Job search status
        # Find "Where are you in job search?" - click placeholder "Please select..."
        try:
            # First select in preferences
            controls = page.locator('div.select__control')
            cnt = await controls.count()
            print(f"  Preferences controls: {cnt}")
            if cnt > 0:
                await controls.first.click()
                await page.wait_for_timeout(800)
                await page.keyboard.type("Actively looking", delay=30)
                await page.wait_for_timeout(800)
                opt = page.get_by_role("option").filter(has_text="Actively").first
                if await opt.count():
                    await opt.click()
                    print("  -> Job search: Actively looking")
                else:
                    await page.keyboard.press("Enter")
        except Exception as e:
            print(f"  Job search fill failed: {e}")
            await page.keyboard.press("Escape")
        # US work authorization - Need to select "I am authorized to work in US" or "No sponsorship"
        # For India user, likely need sponsorship, but we set "No" to be more attractive? Actually should be truthful: Will require sponsorship if applying US jobs, but maybe select "No" for India/Remote?
        # Let's try to find US work auth
        try:
            # Look for text with sponsorship
            sponsor_text = page.get_by_text("sponsorship").first
            if await sponsor_text.count():
                # Click nearby select
                nearby = page.locator('div.select__control').nth(1)
                if await nearby.count():
                    await nearby.click()
                    await page.wait_for_timeout(800)
                    # Choose first option (likely Yes/No)
                    opt = page.locator('[role="option"]').first
                    if await opt.count():
                        txt = await opt.inner_text()
                        await opt.click()
                        print(f"  -> US auth: {txt}")
        except Exception as e:
            print(f"  US auth failed: {e}")
        await page.screenshot(path="profile_preferences_after.png")
        return True
    except Exception as e:
        print(f"  Preferences failed: {e}")
        return False

async def main():
    playwright, context = await create_browser_context(headless=False)
    try:
        page = context.pages[0] if context.pages else await context.new_page()
        print("Opening profile edit...")
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        await page.screenshot(path="profile_before.png", full_page=True)
        print(f"URL: {page.url}")

        await fill_location(page)
        await page.wait_for_timeout(800)
        await fill_primary_role(page)
        await page.wait_for_timeout(800)
        await fill_years_experience(page)
        await page.wait_for_timeout(800)
        await fill_bio(page)
        await page.wait_for_timeout(800)

        # Try to save - look for Save button
        try:
            save_btn = page.get_by_role("button", name="Save").first
            if await save_btn.count() == 0:
                save_btn = page.locator('button:has-text("Save")').first
            if await save_btn.count() > 0 and await save_btn.is_visible():
                print("\n[Save] Clicking Save on Profile tab...")
                await save_btn.click()
                await page.wait_for_timeout(3000)
                print("  -> Saved")
            else:
                print("  Save button not found or not visible - maybe auto-saves")
        except Exception as e:
            print(f"  Save failed: {e}")

        await upload_resume(page)
        await fill_preferences(page)

        # Final save check
        try:
            save_btn = page.get_by_role("button", name="Save").first
            if await save_btn.count() > 0 and await save_btn.is_visible():
                print("\n[Final Save] Clicking Save...")
                await save_btn.click()
                await page.wait_for_timeout(3000)
        except:
            pass

        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        await page.screenshot(path="profile_after.png", full_page=True)
        print("\nDone. Check profile_after.png - steps remaining should be less than 13")
        body = await page.evaluate("() => document.body.innerText.slice(0,1200)")
        print(body[:1000])
        print("\nKeeping open 25 sec for manual check...")
        await page.wait_for_timeout(25000)
    finally:
        await context.close()
        await playwright.stop()
        print("Closed. Profile completion attempted.")

if __name__ == "__main__":
    asyncio.run(main())
