import asyncio
from wellfound_agent.browser.session import create_browser_context

async def get_options(page, input_id):
    # Click the react-select input to open dropdown
    await page.click(f"#{input_id}")
    await page.wait_for_timeout(1500)
    options = await page.evaluate("""() => {
        return [...document.querySelectorAll('[role="option"], [id*="react-select"][id*="option"] , .react-select__option, [class*="option"]')].map(e => e.innerText.trim()).filter(t => t.length>0 && t.length<60).slice(0,40)
    }""")
    # Also try alternative
    if not options:
        options = await page.evaluate("""() => {
            return [...document.querySelectorAll('div')].filter(d => d.textContent.length < 80 && ['Engineer','Designer','Manager','Scientist','Analyst'].some(k => d.textContent.includes(k))).slice(0,30).map(d => d.innerText.trim())
        }""")
    return options

async def main():
    playwright, context = await create_browser_context(headless=False)
    try:
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        # Primary role options
        print("Getting primary role options...")
        opts = await get_options(page, "react-select-form-input--primaryRole-input")
        print("PrimaryRole options:", opts[:20])
        # Need to close dropdown
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(1000)
        # Years experience options
        print("Getting years experience options...")
        opts2 = await get_options(page, "react-select-form-input--yearsExperienceInPrimaryRole-input")
        print("YearsExperience options:", opts2[:20])
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(1000)
        # Where are you based? type India and see dropdown
        print("Testing location...")
        loc_input = page.locator("#downshift-94-input")
        await loc_input.click()
        await page.wait_for_timeout(500)
        await loc_input.fill("India")
        await page.wait_for_timeout(2000)
        loc_opts = await page.evaluate("""() => {
            return [...document.querySelectorAll('[role="option"]')].map(e => e.innerText.trim()).slice(0,10)
        }""")
        print("Location options for 'India':", loc_opts)
        await page.screenshot(path="diag_role_location.png", full_page=False)
        print("Screenshot diag_role_location.png")
        await page.wait_for_timeout(15000)
    finally:
        await context.close()
        await playwright.stop()

if __name__ == "__main__":
    asyncio.run(main())
