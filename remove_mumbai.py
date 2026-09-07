import asyncio
from wellfound_agent.browser.session import create_browser_context

async def main():
    playwright, context = await create_browser_context(headless=False)
    try:
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        print("Opened profile")
        # Find Mumbai card and click Edit if not already in edit
        # Check if already in edit mode with Remove education visible
        remove = page.get_by_text("Remove education").first
        if await remove.count() == 0:
            print("Not in edit mode, clicking Edit for Mumbai...")
            # Click Edit near Mumbai
            await page.evaluate("""() => {
                const edits = [...document.querySelectorAll('button, a')].filter(e => e.innerText.trim() === 'Edit');
                for(const btn of edits){
                    const parent = btn.closest('div');
                    if(parent && parent.innerText.includes('University Of Mumbai')){
                        btn.click();
                        return;
                    }
                }
                // Fallback: find the education card with Mumbai and click its Edit
                const cards = [...document.querySelectorAll('div')].filter(d => d.innerText.includes('University Of Mumbai') && d.innerText.includes('Edit'));
                if(cards.length>0){
                    const edit = [...cards[0].querySelectorAll('button, a')].find(b => b.innerText.trim()==='Edit');
                    if(edit) edit.click();
                }
            }""")
            await page.wait_for_timeout(2500)
            await page.screenshot(path="remove_mumbai_edit.png", full_page=True)
            print("Clicked Edit")
        else:
            print("Already in edit mode")

        # Now click Remove education
        remove = page.get_by_text("Remove education").first
        if await remove.count() > 0:
            await remove.scroll_into_view_if_needed()
            await remove.click()
            print("Clicked Remove education")
            await page.wait_for_timeout(1500)
            # Confirm if needed? Might not need confirm
            # Check for confirmation dialog
            # Sometimes it directly removes, sometimes asks confirm
            await page.screenshot(path="remove_mumbai_after_remove.png", full_page=True)
            # Check if still has Mumbai
            has_mumbai = await page.evaluate("() => document.body.innerText.includes('University Of Mumbai')")
            print(f"Has Mumbai after remove click: {has_mumbai}")
            # If still there, maybe need to confirm or Save?
            # Look for Save or Confirm
            # After Remove, it should automatically remove without Save
            await page.wait_for_timeout(2000)
        else:
            print("Remove education not found")

        # Go back to profile edit to verify
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        body = await page.evaluate("() => document.body.innerText.slice(0,1200)")
        print(body[:1000])
        has_mumbai = await page.evaluate("() => document.body.innerText.includes('University Of Mumbai')")
        has_nfsu = await page.evaluate("() => document.body.innerText.includes('National Forensic')")
        print(f"Final Has Mumbai: {has_mumbai}, Has NFSU: {has_nfsu}")
        await page.screenshot(path="remove_mumbai_final.png", full_page=True)
        print("Keeping open 15 sec...")
        await page.wait_for_timeout(15000)
    finally:
        await context.close()
        await playwright.stop()
        print("Done")

if __name__ == "__main__":
    asyncio.run(main())
