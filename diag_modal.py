import asyncio
from wellfound_agent.browser.session import create_browser_context

async def main():
    p,c = await create_browser_context(headless=False)
    try:
        page = c.pages[0] if c.pages else await c.new_page()
        await page.goto("https://wellfound.com/jobs/4658727-senior-ai-ml-engineer-lead-clone", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        await page.get_by_role("button", name="Apply").first.click()
        await page.wait_for_timeout(3000)
        # Get modal HTML
        html = await page.evaluate("""() => {
            const modal = document.querySelector('[role="dialog"]') || document.querySelector('div[class*="modal"]') || document.body;
            // Find the Send button's parent form
            const sendBtn = [...document.querySelectorAll('button')].find(b=>b.innerText.includes('Send application'));
            const form = sendBtn ? sendBtn.closest('form') || sendBtn.closest('div') : null;
            return {
                body: document.body.innerText.slice(0,2000),
                modal: (form ? form.innerText.slice(0,2000) : (document.querySelector('[role="dialog"]')?.innerText.slice(0,2000) || 'no dialog')),
                html: (form ? form.outerHTML.slice(0,4000) : 'no form'),
                sendOuter: sendBtn ? sendBtn.outerHTML.slice(0,800) : 'no send',
                sendDisabled: sendBtn ? sendBtn.disabled : 'no btn',
                sendParent: sendBtn ? sendBtn.parentElement.outerHTML.slice(0,1000) : 'no parent'
            }
        }""")
        import json
        print(json.dumps(html, indent=2)[:8000])
        await page.screenshot(path="diag_modal.png", full_page=True)
        print("Screenshot diag_modal.png")
        await page.wait_for_timeout(15000)
    finally:
        await c.close()
        await p.stop()
asyncio.run(main())
