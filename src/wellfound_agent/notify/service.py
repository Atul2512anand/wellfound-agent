"""Telegram and macOS notifications."""

import json
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from wellfound_agent.config import NAME, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


@dataclass
class RunSummary:
    status: str = "success"
    scraped: int = 0
    new_jobs: int = 0
    matched: int = 0
    applied: int = 0
    matched_jobs: list[dict[str, Any]] = field(default_factory=list)
    applied_jobs: list[dict[str, Any]] = field(default_factory=list)
    failed_jobs: list[dict[str, Any]] = field(default_factory=list)
    error: str = ""
    started_at: str = ""

    def title(self) -> str:
        if self.status == "error":
            return "Wellfound Agent — Error"
        if self.applied > 0:
            return f"Applied to {self.applied} job{'s' if self.applied != 1 else ''}"
        if self.status == "no_new_jobs":
            return "Wellfound — No new jobs found"
        if self.status == "no_matches":
            return f"Wellfound — {self.new_jobs} jobs, none matched"
        return "Wellfound Agent — Done"

    def short_message(self) -> str:
        if self.status == "error":
            return (self.error or "Run failed")[:180]

        if self.applied > 0:
            lines = [f"Applied to {self.applied} of {self.matched} matched jobs."]
            for job in self.applied_jobs[:3]:
                lines.append(f"✓ {job.get('title', '?')} @ {job.get('company', '?')}")
            if len(self.applied_jobs) > 3:
                lines.append(f"+ {len(self.applied_jobs) - 3} more")
            return "\n".join(lines)

        if self.status == "no_new_jobs":
            return f"Checked {self.scraped} listings — nothing new to apply to."

        if self.status == "no_matches":
            return f"Found {self.new_jobs} recent jobs — none matched (threshold 5+)."

        return f"Scraped {self.scraped}, matched {self.matched}, applied {self.applied}."

    def body(self) -> str:
        lines = [
            "🤖 Wellfound Job Agent Report",
            f"🕐 {self.started_at or datetime.now(timezone.utc).isoformat()}",
            "",
            "📊 Summary",
            f"  Scraped:  {self.scraped}",
            f"  New:      {self.new_jobs}",
            f"  Matched:  {self.matched}",
            f"  Applied:  {self.applied}",
            f"  Failed:   {len(self.failed_jobs)}",
            "",
        ]

        if self.matched_jobs:
            lines.append("🎯 Identified (matched your resume)")
            for job in self.matched_jobs:
                score = job.get("match_score", "?")
                applied = any(j.get("job_id") == job.get("job_id") for j in self.applied_jobs)
                failed = any(j.get("job_id") == job.get("job_id") for j in self.failed_jobs)
                mark = "✅ APPLIED" if applied else ("❌ FAILED" if failed else "—")
                lines.append(
                    f"  [{score}/10] {job.get('title', '?')} @ {job.get('company', '?')} → {mark}"
                )
                if job.get("url"):
                    lines.append(f"  {job['url']}")
            lines.append("")

        if self.failed_jobs:
            lines.append("⚠️ Could not apply")
            for job in self.failed_jobs:
                reason = job.get("fail_reason", "")
                extra = f" — {reason}" if reason else ""
                lines.append(f"  ✗ {job.get('title', '?')} @ {job.get('company', '?')}{extra}")
            lines.append("")

        if self.error:
            lines.extend(["❌ Error", self.error[:500], ""])

        lines.append(f"— {NAME}")
        return "\n".join(lines)


def _send_macos_notification(title: str, message: str) -> bool:
    if sys.platform != "darwin":
        return False

    safe_title = title.replace('"', '\\"')
    safe_message = message.replace('"', '\\"').replace("\n", " ")
    script = (
        f'display notification "{safe_message}" '
        f'with title "{safe_title}" sound name "Glass"'
    )
    try:
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _send_telegram(text: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": text[:4096]}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            if not result.get("ok"):
                print(f"  Telegram API error: {result.get('description', result)}")
                return False
        return True
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        print(f"  Telegram HTTP {exc.code}: {body[:200]}")
        return False
    except Exception as exc:
        print(f"  Telegram failed: {exc}")
        return False


def notify_job_applied(job: dict[str, Any]) -> None:
    score = job.get("match_score", "?")
    title = job.get("title", "Job")
    company = job.get("company", "")
    label = f"{title} @ {company}" if company else title
    url = job.get("url", "")

    text = f"✅ Applied!\n\n[{score}/10] {label}"
    if job.get("remote"):
        text += " (Remote)"
    if url:
        text += f"\n{url}"

    _send_telegram(text)
    _send_macos_notification("Wellfound — Applied!", f"{label} [{score}/10]")


def send_run_summary(summary: RunSummary) -> None:
    print("\n── Sending notification ──")
    title = summary.title()
    body = summary.body()

    if _send_telegram(f"{title}\n\n{summary.short_message()}\n\n{body}"):
        print("  ✓ Telegram message sent")
    elif not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("  · Telegram skipped (set TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID in .env)")
    else:
        print("  · Telegram failed — check token and chat ID")

    if _send_macos_notification(title, summary.short_message()):
        print("  ✓ macOS notification sent")

    print("\n" + body)
