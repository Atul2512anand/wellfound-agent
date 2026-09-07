"""Applied-job tracking and eligibility filtering."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from wellfound_agent.config import APPLIED_JOBS_PATH, DATA_DIR

JOB_URL_PATTERN = re.compile(r"wellfound\.com/jobs/(\d+)-")


def extract_job_id(url: str) -> str | None:
    match = JOB_URL_PATTERN.search(url)
    return match.group(1) if match else None


def load_applied_jobs(path: Path = APPLIED_JOBS_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def save_applied_jobs(jobs: list[dict[str, Any]], path: Path = APPLIED_JOBS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)


def is_job_applied(job_id: str, applied_jobs: list[dict[str, Any]]) -> bool:
    return any(entry.get("job_id") == job_id for entry in applied_jobs)


def load_applied_job_ids() -> set[str]:
    return {e["job_id"] for e in load_applied_jobs() if e.get("job_id")}


def parse_posted_age_days(posted_label: str) -> int | None:
    """Parse Wellfound posted text into approximate age in days."""
    if not posted_label:
        return None
    text = posted_label.upper().strip()
    if "TODAY" in text:
        return 0
    if "YESTERDAY" in text:
        return 1
    match = re.search(r"POSTED\s+(\d+)\s+DAY", text)
    if match:
        return int(match.group(1))
    match = re.search(r"POSTED\s+(\d+)\s+WEEK", text)
    if match:
        return int(match.group(1)) * 7
    match = re.search(r"POSTED\s+(\d+)\s+MONTH", text)
    if match:
        return int(match.group(1)) * 30
    return None


def is_job_recent(job: dict[str, Any], max_days: int) -> bool:
    """True if job was posted within max_days (uses timestamp or POSTED label)."""
    live_start = job.get("live_start_at")
    if live_start:
        try:
            posted = datetime.fromtimestamp(int(live_start), tz=timezone.utc)
            age = (datetime.now(timezone.utc) - posted).days
            return age <= max_days
        except (TypeError, ValueError, OSError):
            pass

    age = parse_posted_age_days(job.get("posted_label", ""))
    if age is not None:
        return age <= max_days

    return True


def filter_eligible_jobs(
    jobs: list[dict[str, Any]],
    applied_ids: set[str],
    max_age_days: int,
) -> list[dict[str, Any]]:
    """Keep jobs that are recent, not already applied, and have a valid id."""
    eligible = []
    skipped_applied = skipped_old = 0

    for job in jobs:
        job_id = job.get("job_id") or extract_job_id(job.get("url", ""))
        if not job_id:
            continue
        job["job_id"] = job_id

        if job_id in applied_ids:
            skipped_applied += 1
            continue

        if not is_job_recent(job, max_age_days):
            skipped_old += 1
            continue

        eligible.append(job)

    if skipped_applied:
        print(f"  Skipped {skipped_applied} already applied")
    if skipped_old:
        print(f"  Skipped {skipped_old} older than {max_age_days} days")

    return eligible


def log_applied_job(
    job: dict[str, Any],
    match_score: float,
    applied_jobs: list[dict[str, Any]],
) -> None:
    job_id = job.get("job_id") or extract_job_id(job.get("url", ""))
    if not job_id:
        return
    applied_jobs.append(
        {
            "job_id": job_id,
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "url": job.get("url", ""),
            "match_score": match_score,
            "applied_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    save_applied_jobs(applied_jobs)


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
