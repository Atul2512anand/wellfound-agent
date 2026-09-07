"""End-to-end scrape → match → apply pipeline."""

from datetime import datetime, timezone

from wellfound_agent.apply.service import apply_to_jobs
from wellfound_agent.config import MAX_JOB_AGE_DAYS, SEARCH_LOCATIONS
from wellfound_agent.match.matcher import match_jobs
from wellfound_agent.notify.service import RunSummary
from wellfound_agent.scrape.service import scrape_and_save
from wellfound_agent.storage.jobs import filter_eligible_jobs, load_applied_job_ids
from wellfound_agent.storage.resume import load_resume


async def run_pipeline() -> RunSummary:
    started_at = datetime.now(timezone.utc).isoformat()
    summary = RunSummary(status="success", started_at=started_at)

    print("=" * 60)
    print("  WELLFOUND JOB AGENT")
    print(f"  {started_at}")
    print("=" * 60)

    applied_ids = load_applied_job_ids()
    print(f"\nAlready applied to {len(applied_ids)} jobs (will skip these)")

    locations = " + ".join(SEARCH_LOCATIONS)
    print(f"\n[1/3] FIND — recent jobs ({locations}, ≤{MAX_JOB_AGE_DAYS} days old)...")
    scraped_jobs = await scrape_and_save()
    summary.scraped = len(scraped_jobs)

    eligible = filter_eligible_jobs(scraped_jobs, applied_ids, MAX_JOB_AGE_DAYS)
    summary.new_jobs = len(eligible)
    print(f"       {summary.new_jobs} eligible jobs to evaluate")

    if not eligible:
        summary.status = "no_new_jobs"
        return summary

    for job in eligible:
        posted = job.get("posted_label") or "recent"
        remote = " [remote]" if job.get("remote") else ""
        print(f"       • {job['title']} @ {job.get('company', '?')} ({posted}){remote}")

    print("\n[2/3] IDENTIFY — resume-aware matching (Cybersecurity/Blockchain/AI/Data/Software, junior-friendly)...")
    print(f"  Resume: {load_resume().splitlines()[0][:60]}... (NFSU Cybersecurity, Blockchain DApp, AI/ML, Data)")
    matched_jobs = match_jobs(jobs=eligible)
    # Sort by score and favour junior roles - already penalized senior, boost junior
    # For this resume, we want to apply to most favourable (highest scores), not just first 5
    # Keep limit of 5 per run as requested, but pick highest scoring
    if len(matched_jobs) > 5:
        print(f"  Found {len(matched_jobs)} favourable jobs (score >=5) - picking top 5 by resume match")
        matched_jobs = matched_jobs[:5]
    summary.matched = len(matched_jobs)
    summary.matched_jobs = matched_jobs

    if not matched_jobs:
        summary.status = "no_matches"
        print("  No favourable jobs found for your resume (Cybersecurity/Blockchain/AI/Data/Software junior). Try lowering threshold or broadening search.")
        return summary

    print(f"\n[3/3] APPLY — submitting {len(matched_jobs)} most favourable application(s)...")
    for job in matched_jobs:
        print(f"  -> {job['title']} @ {job.get('company','?')} [{job.get('match_score')}/10] - {job.get('match_reason','')}")
    applied, failed = await apply_to_jobs(matched_jobs)
    summary.applied = len(applied)
    summary.applied_jobs = applied
    summary.failed_jobs = failed
    summary.status = "success"

    print("\n" + "=" * 60)
    print(f"  DONE — applied to {summary.applied}/{summary.matched} matched jobs")
    print("=" * 60)

    return summary
