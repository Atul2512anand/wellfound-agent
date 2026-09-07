import asyncio, json
from wellfound_agent.browser.session import create_browser_context

async def main():
    playwright, context = await create_browser_context(headless=False)
    try:
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://wellfound.com/profile/edit", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        await page.screenshot(path="diag_profile_edit_full.png", full_page=True)
        print("Saved full screenshot")
        # Evaluate required fields
        data = await page.evaluate("""() => {
            const required = [];
            // Find elements with red dot or * 
            document.querySelectorAll('*').forEach(el => {
                const text = el.innerText?.trim() || '';
                if (text.includes('*') && text.length < 100) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0) required.push({text: text.slice(0,120), tag: el.tagName, classes: el.className.slice(0,200)});
                }
            });
            // Find inputs
            const inputs = [...document.querySelectorAll('input, textarea, select')].map(i => ({
                type: i.type,
                placeholder: i.placeholder,
                name: i.name,
                id: i.id,
                value: i.value?.slice(0,100),
                label: i.closest('label')?.innerText?.slice(0,100) || i.parentElement?.innerText?.slice(0,100),
                outer: i.outerHTML.slice(0,400)
            }));
            // Find dropdowns / role selectors
            const selectors = [...document.querySelectorAll('[role="combobox"], [role="listbox"], .select__control, [data-test]')].slice(0,10).map(e => ({
                html: e.outerHTML.slice(0,500),
                text: e.innerText.slice(0,100)
            }));
            return {required: required.slice(0,30), inputs: inputs.slice(0,30), selectors, url: location.href, title: document.title};
        }""")
        print(json.dumps(data, indent=2)[:8000])
        # Try tabs
        for tab in ["Resume / CV", "Preferences", "Culture"]:
            try:
                el = page.get_by_role("link", name=tab).first
                if await el.count():
                    await el.click()
                    await page.wait_for_timeout(3000)
                    await page.screenshot(path=f"diag_tab_{tab.replace(' ','_')}.png", full_page=True)
                    print(f"Tab {tab} -> {page.url}")
                    # Count required again
                    req = await page.evaluate("() => document.body.innerText.slice(0,1500)")
                    print(f"{tab} preview: {req[:800]}")
            except Exception as e:
                print(f"Tab {tab} error: {e}")
        await page.wait_for_timeout(15000)
    finally:
        await context.close()
        await playwright.stop()

if __name__ == "__main__":
    asyncio.run(main())
