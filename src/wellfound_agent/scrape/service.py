"""Scrape recent Wellfound jobs sorted by Most recent."""

import asyncio
import json
import sys
from typing import Any

from playwright.async_api import Page

from wellfound_agent.browser.session import (
    create_browser_context,
    ensure_logged_in,
    navigate_wellfound,
)
from wellfound_agent.config import (
    MAX_JOBS_PER_LOCATION,
    PAGE_LOAD_DELAY_SEC,
    SCRAPED_JOBS_PATH,
    SEARCH_LOCATIONS,
    SORT_ORDER,
)
from wellfound_agent.storage.jobs import ensure_data_dir

JOBS_URL = "https://wellfound.com/jobs"
_SELECT_ALL = "Meta+A" if sys.platform == "darwin" else "Control+A"

EXTRACT_JOBS_JS = """
() => {
    const jobs = [];
    const seen = new Set();

    const cardForJob = (jobId) => {
        for (const link of document.querySelectorAll('a[href*="/jobs/"]')) {
            const match = link.href.match(/\\/jobs\\/(\\d+)-/);
            if (!match || match[1] !== jobId) continue;
            return link.closest('[class*="component"]') || link.closest('div.mb-6') || link.parentElement;
        }
        return null;
    };

    const enrichFromDom = (jobId) => {
        const card = cardForJob(jobId);
        if (!card) return null;
        let company = '';
        const companyLink = card.querySelector('a[href*="/company/"]');
        if (companyLink) company = companyLink.innerText.trim();
        const link = card.querySelector('a[href*="/jobs/"]');
        const title = link ? link.innerText.trim().split('\\n')[0] : '';
        const postedMatch = card.innerText.match(/POSTED [A-Z0-9 ]+/i);
        const cardText = card.innerText || '';
        const isRemote = /remote only|remote •|• remote|\\bremote\\b/i.test(cardText);
        const isExternalApply = /apply on (the )?company|company'?s website/i.test(cardText);
        return {
            title,
            company,
            url: link ? link.href.split('?')[0] : '',
            posted_label: postedMatch ? postedMatch[0].toUpperCase() : '',
            is_remote: isRemote,
            apply_on_wellfound: !isExternalApply,
        };
    };

    const el = document.getElementById('__NEXT_DATA__');
    if (el) {
        try {
            const apollo = JSON.parse(el.textContent).props.pageProps.apolloState.data;
            if (apollo) {
                const jobToCompany = {};
                for (const [key, val] of Object.entries(apollo)) {
                    if (!key.startsWith('StartupResult:') || !val.highlightedJobListings) continue;
                    for (const ref of val.highlightedJobListings) {
                        const refId = ref.id || ref.__ref || '';
                        const numericId = refId.split(':').pop();
                        if (numericId) jobToCompany[numericId] = val.name || '';
                    }
                }

                for (const [key, val] of Object.entries(apollo)) {
                    if (!key.startsWith('JobListingSearchResult:')) continue;
                    const jobId = String(val.id || key.split(':').pop());
                    if (!jobId || seen.has(jobId)) continue;
                    seen.add(jobId);

                    const slug = val.slug || 'job';
                    const title = val.title || '';
                    if (!title) continue;

                    let locations = val.locationNames;
                    if (locations && locations.json) locations = locations.json;
                    if (!Array.isArray(locations)) locations = [];

                    const dom = enrichFromDom(jobId);
                    jobs.push({
                        job_id: jobId,
                        title,
                        company: jobToCompany[jobId] || dom?.company || '',
                        url: `https://wellfound.com/jobs/${jobId}-${slug}`,
                        location: locations.join(', '),
                        description: val.description || '',
                        job_type: val.jobType || '',
                        compensation: val.compensation || '',
                        remote: !!val.remote || !!dom?.is_remote,
                        live_start_at: val.liveStartAt || null,
                        posted_label: dom?.posted_label || '',
                        apply_on_wellfound: dom?.apply_on_wellfound ?? true,
                    });
                }
            }
        } catch (e) { /* fall through */ }
    }

    if (jobs.length === 0) {
        for (const link of document.querySelectorAll('a[href*="/jobs/"]')) {
            const href = link.href;
            const match = href.match(/\\/jobs\\/(\\d+)-/);
            if (!match || seen.has(match[1])) continue;
            const title = link.innerText.trim().split('\\n')[0];
            if (!title || title.length < 3) continue;
            if (['Home', 'Applied', 'Messages', 'Jobs'].includes(title)) continue;
            seen.add(match[1]);
            const dom = enrichFromDom(match[1]);
            jobs.push({
                job_id: match[1],
                title: dom?.title || title,
                company: dom?.company || '',
                url: dom?.url || href.split('?')[0],
                location: '',
                description: '',
                job_type: '',
                compensation: '',
                remote: dom?.is_remote || false,
                live_start_at: null,
                posted_label: dom?.posted_label || '',
                apply_on_wellfound: dom?.apply_on_wellfound ?? true,
            });
        }
    }

    return jobs;
}
"""


async def _fill_location(page: Page, location: str) -> None:
    loc_selector = ".styles_roleAndLocation__TcRMj > div:nth-child(2)"
    if await page.locator(loc_selector).count() == 0:
        loc_selector = ".styles_roleAndLocation__TcRMj"
    # If still not found (new Wellfound UI), skip location change - jobs page already filtered
    if await page.locator(loc_selector).count() == 0:
        print(f"  Location filter not found for '{location}' (new UI) - skipping, using current search")
        return

    field = page.locator(loc_selector).first
    await field.click()
    await page.wait_for_timeout(300)
    await page.keyboard.press(_SELECT_ALL)
    await page.keyboard.press("Backspace")
    await page.keyboard.type(location, delay=30)
    await page.wait_for_timeout(1200)

    option = page.get_by_role("option", name=location).first
    if await option.count():
        await option.click()
    else:
        fallback = page.locator('[role="option"]').filter(has_text=location.split()[0]).first
        if await fallback.count():
            await fallback.click()
        else:
            await page.keyboard.press("Enter")

    await page.wait_for_timeout(1500)


async def _clear_role_filter(page: Page) -> None:
    role = page.locator(".styles_roleWrapper__e5l9z").first
    if await role.count() == 0:
        return
    await role.click()
    await page.wait_for_timeout(300)
    await page.keyboard.press(_SELECT_ALL)
    await page.keyboard.press("Backspace")
    await page.wait_for_timeout(300)
    await page.keyboard.press("Escape")
    await page.wait_for_timeout(500)


async def _set_sort_order(page: Page, sort_label: str) -> None:
    sort_btn = page.locator(".styles_sortOrder__3Qukq").first
    if await sort_btn.count() == 0:
        print(f"  Sort button not found (new UI) - skipping sort '{sort_label}'")
        return
    try:
        current = await sort_btn.inner_text()
        if sort_label.lower() in current.lower():
            print(f"  Sort: {sort_label}")
            return
    except:
        print(f"  Sort check failed, skipping")
        return

    print(f"  Setting sort: {sort_label}")
    try:
        await sort_btn.click()
        await page.wait_for_timeout(800)
        await page.locator("button.styles_component__7ZpRT").filter(has_text=sort_label).first.click()
        await page.wait_for_timeout(2500)
    except Exception as e:
        print(f"  Sort set failed (new UI): {e}")


async def _run_recent_jobs_search(page: Page, location: str) -> None:
    await navigate_wellfound(page, JOBS_URL)
    print(f"  Location: {location} | Sort: {SORT_ORDER} | No role filter")
    await _clear_role_filter(page)
    await _fill_location(page, location)
    await _set_sort_order(page, SORT_ORDER)
    await page.wait_for_timeout(PAGE_LOAD_DELAY_SEC * 1000)


async def _scrape_location(page: Page, location: str) -> list[dict[str, Any]]:
    print(f"\nFetching recent jobs — {location}...")
    await _run_recent_jobs_search(page, location)
    jobs = await page.evaluate(EXTRACT_JOBS_JS)

    result_count = await page.evaluate(
        """() => {
            const m = document.body.innerText.match(/(\\d+) results/);
            return m ? parseInt(m[1], 10) : null;
        }"""
    )
    print(f"  → {len(jobs)} listings ({result_count or '?'} total results)")

    for job in jobs:
        job["search_location"] = location
        if location.lower() == "remote":
            job["remote"] = True

    return jobs[:MAX_JOBS_PER_LOCATION]


def _filter_wellfound_apply(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    kept = []
    skipped = 0
    for job in jobs:
        if job.get("apply_on_wellfound", True):
            kept.append(job)
        else:
            skipped += 1
            print(f"  Skip (external apply): {job.get('title', '?')}")
    if skipped:
        print(f"  Filtered out {skipped} external-apply-only jobs")
    return kept


async def _fetch_job_description(page: Page, job: dict[str, Any]) -> str:
    if job.get("description") and len(job["description"]) > 100:
        return job["description"]

    try:
        await navigate_wellfound(page, job["url"])
        description = await page.evaluate(
            """() => {
                for (const sel of ['[data-test="JobDescription"]', '[class*="JobDescription"]', 'section[class*="description"]']) {
                    const el = document.querySelector(sel);
                    if (el && el.innerText.trim().length > 100) return el.innerText.trim();
                }
                const main = document.querySelector('main');
                return main ? main.innerText.trim().slice(0, 8000) : '';
            }"""
        )
        return description or job.get("description", "")
    except Exception as exc:
        print(f"  Warning: could not fetch description for {job['url']}: {exc}")
        return job.get("description", "")


async def scrape_wellfound_jobs(fetch_descriptions: bool = True) -> list[dict[str, Any]]:
    """Scrape recent jobs for each configured location (India + Remote)."""
    playwright, context = await create_browser_context(headless=False)
    all_jobs: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    try:
        page = context.pages[0] if context.pages else await context.new_page()
        await ensure_logged_in(page)

        for location in SEARCH_LOCATIONS:
            location_jobs = await _scrape_location(page, location)
            for job in location_jobs:
                if job["job_id"] not in seen_ids:
                    seen_ids.add(job["job_id"])
                    all_jobs.append(job)
            await asyncio.sleep(PAGE_LOAD_DELAY_SEC)

        all_jobs = _filter_wellfound_apply(all_jobs)

        if fetch_descriptions:
            for i, job in enumerate(all_jobs, 1):
                if len(job.get("description", "")) < 100:
                    remote_tag = " [remote]" if job.get("remote") else ""
                    print(f"  Fetching description {i}/{len(all_jobs)}: {job['title']}{remote_tag}")
                    job["description"] = await _fetch_job_description(page, job)
                    await asyncio.sleep(PAGE_LOAD_DELAY_SEC)

        if not all_jobs:
            print(
                "\nNo listings found. Tips:"
                "\n  • Log in to Wellfound when the browser opens"
                "\n  • Ensure Microsoft Edge is installed (now using Edge)"
                "\n  • Complete any CAPTCHA if shown"
            )

    finally:
        await context.close()
        await playwright.stop()

    return all_jobs


def save_scraped_jobs(jobs: list[dict[str, Any]], path=SCRAPED_JOBS_PATH) -> None:
    ensure_data_dir()
    with path.open("w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)


async def scrape_and_save() -> list[dict[str, Any]]:
    jobs = await scrape_wellfound_jobs()
    save_scraped_jobs(jobs)
    print(f"\nScraped {len(jobs)} jobs total. Saved to {SCRAPED_JOBS_PATH}")
    return jobs
