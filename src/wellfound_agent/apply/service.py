"""Auto-fill and submit Wellfound job applications."""

import asyncio
from typing import Any, Callable

from playwright.async_api import Page

from wellfound_agent.browser.session import (
    create_browser_context,
    ensure_logged_in,
    navigate_wellfound,
)
from wellfound_agent.config import DEFAULT_APPLICANT_LOCATION
from wellfound_agent.notify.service import notify_job_applied
from wellfound_agent.storage.jobs import (
    extract_job_id,
    is_job_applied,
    load_applied_jobs,
    log_applied_job,
)

COVER_NOTE = (
    "Hi — I'm a Computer Science student (Cybersecurity) with experience in "
    "Cybersecurity, Blockchain (Solidity/Ethereum DApps), and AI/ML. "
    "Excited about this role and keen to contribute!"
)


async def _is_external_apply_only(page: Page) -> bool:
    return await page.evaluate(
        """() => {
            const t = document.body.innerText.toLowerCase();
            return t.includes("company's website")
                || t.includes("apply on company")
                || t.includes("apply on the company");
        }"""
    )


async def _is_already_applied(page: Page) -> bool:
    return await page.evaluate(
        """() => {
            const applyButtons = [...document.querySelectorAll('button.styles_applyButton__7gnpI')];
            for (const btn of applyButtons) {
                const text = btn.innerText.trim().toLowerCase();
                if (text.includes('applied') || text.includes('✓')) return true;
            }
            const header = document.querySelector('h1, h2, [class*="jobTitle"]');
            const section = header?.closest('div')?.parentElement || document.body;
            const sectionText = section.innerText || '';
            if (/✓\\s*applied/i.test(sectionText)) return true;
            if (/you applied/i.test(sectionText.toLowerCase())) return true;
            return false;
        }"""
    )


async def _click_apply_button(page: Page) -> bool:
    locators = [
        page.locator("button.styles_applyButton__7gnpI").filter(has_text="Apply").first,
        page.get_by_role("button", name="Apply", exact=True).first,
    ]
    for loc in locators:
        try:
            if await loc.count() > 0 and await loc.is_visible():
                text = (await loc.inner_text()).lower()
                if "applied" in text:
                    return False
                await loc.click()
                return True
        except Exception:
            continue
    return False


async def _fill_cover_note(page: Page) -> None:
    try:
        note = page.locator('textarea[name="userNote"]').first
        if await note.count() > 0 and await note.is_visible():
            await note.fill(COVER_NOTE)
    except Exception:
        pass

    # Also handle Wellfound's custom question "What interests you about working for this company?" if present
    try:
        custom = page.locator('textarea[name*="customQuestionAnswers"]').first
        if await custom.count() > 0:
            # It may be disabled initially due to location error, wait a bit
            await page.wait_for_timeout(500)
            if await custom.is_visible() and await custom.is_enabled():
                await custom.fill("I'm excited about this role because it aligns with my skills in Python, Cybersecurity, and Blockchain, and I admire your product. I'd love to contribute and learn.")
            elif await custom.count() > 0:
                # Try to fill even if seems disabled after location fix
                try:
                    await custom.fill("Excited about this role and eager to contribute with my Python/ML/Blockchain background.", timeout=2000)
                except:
                    pass
    except Exception:
        pass


def _normalize_target_location(raw: str) -> str:
    """Normalize a city/region into 'City, India' form for the Wellfound modal."""
    text = (raw or "").strip().split("\n")[0].strip(" -•|,")
    if not text:
        return DEFAULT_APPLICANT_LOCATION
    low = text.lower()
    # Too broad / non-specific values fall back to the default.
    if low in ("india", "remote", "remote only", "worldwide", "in office", "hybrid", "onsite"):
        return DEFAULT_APPLICANT_LOCATION
    if "," in text:
        return text
    # Assume Indian city when no country is given (search scope is India/Remote).
    if "india" not in low:
        return f"{text}, India"
    return text


def _city_from_title(title: str) -> str:
    """Extract a trailing ' - City' from titles like 'Sales Associate - Chennai'."""
    if not title or "-" not in title:
        return ""
    tail = title.rsplit("-", 1)[-1].strip()
    # Only accept short alphabetic tails (avoid 'Full-time - ...' noise).
    if 2 <= len(tail) <= 30 and all(c.isalpha() or c.isspace() or c in "._-" for c in tail):
        return tail
    return ""


async def _get_job_target_location(page: Page, job: dict[str, Any] | None) -> str:
    """Pick the location to put in the apply modal.

    Preference: specific job city (willing to relocate) -> default location.
    Falls back to DEFAULT_APPLICANT_LOCATION when nothing specific is found.
    """
    job = job or {}
    candidates: list[str] = []

    job_loc = (job.get("location") or "").strip()
    if job_loc:
        # location may be "Ahmedabad, IN" or comma-separated list; take first specific part
        first = job_loc.split(",")[0].strip() if "," not in job_loc.lower().replace(", in", "") else job_loc
        # If it looks like a list ("Mumbai, Delhi"), prefer the first city-like token
        candidates.append(first)

    title_city = _city_from_title(job.get("title", ""))

    # Extract the Location field from the live job page (most reliable).
    page_city = ""
    try:
        page_city = await page.evaluate(
            """() => {
                const t = document.body.innerText || '';
                // Wellfound job page shows e.g. "Location\\nAhmedabad\\nRemote work policy"
                let m = t.match(/Location\\s*\\n\\s*([A-Za-z][A-Za-z\\s\\.\\-]*)/);
                if (m) return (m[1] || '').split('\\n')[0].trim();
                return '';
            }"""
        )
        if page_city:
            candidates.append(page_city.strip())
    except Exception:
        pass

    # Title city is last resort (clone titles like "- Chennai" can be stale).
    if title_city:
        candidates.append(title_city)

    for cand in candidates:
        normalized = _normalize_target_location(cand)
        # Accept it only if it is specific (not the generic fallback from broad input),
        # unless every candidate is broad.
        if normalized != DEFAULT_APPLICANT_LOCATION:
            return normalized

    return DEFAULT_APPLICANT_LOCATION


async def _fix_modal_location_if_needed(page: Page, job: dict[str, Any] | None = None) -> bool:
    """Fix 'Your primary location is too broad' error in apply modal.

    Uses the job's city (willing to relocate) when available, else the default.
    """
    try:
        has_error = await page.evaluate("() => document.body.innerText.includes('Your primary location is too broad')")
        if not has_error:
            return False
        target = await _get_job_target_location(page, job)
        city_only = target.split(",")[0].strip()
        print(f"  -> Detected 'location too broad' in apply modal, fixing to {target} (job: {(job or {}).get('title', '?')})...")
        # Modal's location input is downshift-0-input or placeholder e.g. San Francisco
        loc = page.locator('#downshift-0-input').first
        if await loc.count() == 0:
            loc = page.locator('input[placeholder="e.g. San Francisco"]').first
        if await loc.count() == 0:
            loc = page.locator('input[id^="downshift-"]').first
        if await loc.count() == 0:
            print("  No location input found in modal")
            return False
        await loc.scroll_into_view_if_needed()
        await loc.click()
        await page.wait_for_timeout(400)
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await loc.type(target, delay=30)
        await page.wait_for_timeout(1500)
        # Select the job city option (handle Bengaluru/Bangalore alias)
        opt = page.get_by_role("option").filter(has_text=city_only).first
        if await opt.count() == 0 and city_only.lower() in ("bengaluru", "bangalore"):
            opt = page.get_by_role("option").filter(has_text="Bengaluru").first
            if await opt.count() == 0:
                opt = page.get_by_role("option").filter(has_text="Bangalore").first
        if await opt.count():
            await opt.click()
            print(f"  -> Selected {await opt.inner_text() if await opt.count() else city_only} in modal")
        else:
            # Fallback: first option that looks like a city
            first = page.locator('[role="option"]').first
            if await first.count():
                txt = await first.inner_text()
                if "," in txt or city_only.lower() in txt.lower():
                    await first.click()
                    print(f"  -> Selected first city: {txt}")
                else:
                    await page.keyboard.press("Enter")
            else:
                await page.keyboard.press("Enter")
        await page.wait_for_timeout(1200)
        # After fixing location, the textarea may become enabled and Send may become enabled
        return True
    except Exception as e:
        print(f"  Modal location fix failed: {e}")
        return False


async def _submit_application(page: Page, job: dict[str, Any] | None = None) -> bool:
    await page.wait_for_timeout(2000)
    # Fix location too broad if present before trying to fill note/Send
    await _fix_modal_location_if_needed(page, job)
    await page.wait_for_timeout(800)
    await _fill_cover_note(page)
    await page.wait_for_timeout(500)
    # Re-check location after fill (sometimes Send stays disabled until location is fixed)
    await _fix_modal_location_if_needed(page, job)

    locators = [
        page.get_by_role("button", name="Send application", exact=False),
        page.locator('button:has-text("Send application")'),
        page.get_by_role("button", name="Apply now", exact=False),
    ]
    for loc in locators:
        try:
            if await loc.count() > 0 and await loc.first.is_visible():
                # Check if disabled - if disabled, try location fix again
                try:
                    is_enabled = await loc.first.is_enabled()
                    if not is_enabled:
                        print("  Send button disabled, retrying location fix...")
                        await _fix_modal_location_if_needed(page, job)
                        await page.wait_for_timeout(1000)
                        is_enabled = await loc.first.is_enabled()
                        print(f"  Send enabled after fix: {is_enabled}")
                        if not is_enabled:
                            # Try to fill any required textarea that may be blocking
                            await _fill_cover_note(page)
                            await page.wait_for_timeout(500)
                except:
                    pass
                await loc.first.click()
                await page.wait_for_timeout(3000)
                return True
        except Exception:
            continue
    return False


async def apply_to_job(page: Page, job: dict[str, Any], applied_jobs_log: list) -> tuple[bool, str]:
    url = job.get("url", "")
    if not url:
        return False, "no URL"

    print(f"\n  Applying: {job.get('title')} @ {job.get('company')}")

    try:
        await navigate_wellfound(page, url)

        if await _is_external_apply_only(page):
            return False, "external apply only (company website)"

        if await _is_already_applied(page):
            log_applied_job(job, job.get("match_score", 0), applied_jobs_log)
            return True, "already applied"

        if not await _click_apply_button(page):
            return False, "Apply button not found"

        if not await _submit_application(page, job):
            return False, "Send application button not found"

        if await _is_already_applied(page):
            return True, "submitted"

        return False, "could not confirm submission"

    except Exception as exc:
        return False, str(exc)


async def apply_to_jobs(
    jobs: list[dict[str, Any]],
    skip_applied: bool = True,
    on_applied: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    applied_jobs_log = load_applied_jobs()
    successful: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []

    jobs_to_apply = []
    for job in jobs:
        job_id = job.get("job_id") or extract_job_id(job.get("url", ""))
        if not job_id:
            continue
        job["job_id"] = job_id
        if skip_applied and is_job_applied(job_id, applied_jobs_log):
            print(f"  Skip (already in log): {job.get('title')}")
            continue
        jobs_to_apply.append(job)

    if not jobs_to_apply:
        print("  No new jobs to apply to.")
        return successful, failed

    playwright, context = await create_browser_context(headless=False)
    try:
        page = context.pages[0] if context.pages else await context.new_page()
        await ensure_logged_in(page)

        for job in jobs_to_apply:
            success, reason = await apply_to_job(page, job, applied_jobs_log)
            if success:
                if not is_job_applied(job["job_id"], applied_jobs_log):
                    log_applied_job(job, job.get("match_score", 0), applied_jobs_log)
                successful.append(job)
                print(f"    ✓ {reason}")
                (on_applied or notify_job_applied)(job)
            else:
                job["fail_reason"] = reason
                failed.append(job)
                print(f"    ✗ {reason}")
            await asyncio.sleep(2)

    finally:
        await context.close()
        await playwright.stop()

    print(f"\n  Applied: {len(successful)}/{len(jobs_to_apply)}")
    return successful, failed
