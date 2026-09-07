import asyncio
from wellfound_agent.browser.session import create_browser_context

async def main():
    playwright, context = await create_browser_context(headless=False)
    try:
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://wellfound.com/jobs", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        # Dump search area HTML
        html = await page.evaluate("""() => {
            // Find search inputs
            const inputs = [...document.querySelectorAll('input')].map(i => ({
                placeholder: i.placeholder,
                name: i.name,
                type: i.type,
                outer: i.outerHTML.slice(0,300),
                parentClasses: i.parentElement?.className?.slice(0,200)
            }));
            const divs = [...document.querySelectorAll('div')].filter(d => d.textContent.includes('Location') && d.textContent.length < 500).slice(0,5).map(d => ({
                text: d.innerText.slice(0,200),
                classes: d.className.slice(0,300),
                html: d.outerHTML.slice(0,500)
            }));
            return {inputs, divs, bodySnippet: document.documentElement.outerHTML.slice(0,5000)};
        }""")
        import json, pathlib
        pathlib.Path("diag_selectors.json").write_text(json.dumps(html, indent=2), encoding="utf-8")
        print(json.dumps(html, indent=2)[:8000])
        await page.screenshot(path="diag_selectors.png", full_page=True)
        print("Saved diag_selectors.json and diag_selectors.png")
        await page.wait_for_timeout(20000)
    finally:
        await context.close()
        await playwright.stop()

if __name__ == "__main__":
    asyncio.run(main())
