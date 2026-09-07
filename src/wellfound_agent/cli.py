"""Command-line interface."""

import argparse
import asyncio
import sys
import traceback
from datetime import datetime, timezone

from wellfound_agent.apply.service import apply_to_jobs
from wellfound_agent.match.matcher import match_jobs
from wellfound_agent.notify.service import RunSummary, send_run_summary
from wellfound_agent.pipeline import run_pipeline
from wellfound_agent.run_log import setup_run_logging
from wellfound_agent.scrape.service import scrape_and_save


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wellfound-agent",
        description="Wellfound job automation - scrape, match, and apply locally.",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("run", help="Full pipeline: scrape -> match -> apply (default)")
    subparsers.add_parser("scrape", help="Scrape recent jobs only")
    subparsers.add_parser("match", help="Score scraped jobs against resume")

    subparsers.add_parser("apply", help="Match scraped jobs and apply")

    return parser


def _run_with_logging(coro_factory) -> int:
    log_file = setup_run_logging()
    print(f"Python: {sys.executable}")
    print(f"Log: {log_file}\n")

    summary = RunSummary(status="error", started_at=datetime.now(timezone.utc).isoformat())
    try:
        summary = asyncio.run(coro_factory())
        return 0
    except KeyboardInterrupt:
        summary.error = "Interrupted by user"
        print("\nInterrupted.")
        return 1
    except Exception:
        summary.error = traceback.format_exc()
        print(f"\nFatal error:\n{summary.error}")
        return 1
    finally:
        send_run_summary(summary)


async def _cmd_run() -> RunSummary:
    return await run_pipeline()


async def _cmd_scrape() -> RunSummary:
    started_at = datetime.now(timezone.utc).isoformat()
    jobs = await scrape_and_save()
    summary = RunSummary(status="success", started_at=started_at, scraped=len(jobs))
    if not jobs:
        summary.status = "no_new_jobs"
    return summary


async def _cmd_match() -> RunSummary:
    started_at = datetime.now(timezone.utc).isoformat()
    matched = match_jobs()
    summary = RunSummary(
        status="success" if matched else "no_matches",
        started_at=started_at,
        matched=len(matched),
        matched_jobs=matched,
    )
    return summary


async def _cmd_apply() -> RunSummary:
    started_at = datetime.now(timezone.utc).isoformat()
    matched = match_jobs()
    if not matched:
        return RunSummary(status="no_matches", started_at=started_at)

    applied, failed = await apply_to_jobs(matched)
    return RunSummary(
        status="success",
        started_at=started_at,
        matched=len(matched),
        matched_jobs=matched,
        applied=len(applied),
        applied_jobs=applied,
        failed_jobs=failed,
    )


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    command = args.command or "run"

    if command == "run":
        exit_code = _run_with_logging(_cmd_run)
    elif command == "scrape":
        exit_code = _run_with_logging(_cmd_scrape)
    elif command == "match":
        exit_code = _run_with_logging(_cmd_match)
    elif command == "apply":
        exit_code = _run_with_logging(_cmd_apply)
    else:
        parser.print_help()
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
