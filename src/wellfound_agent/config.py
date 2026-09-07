"""Application configuration and path resolution."""

import os
from pathlib import Path

# Project root: wellfound-agent/ (two levels above this package)
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv() -> None:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

# Applicant details - fill in your own (kept out of git; see resume.example.txt)
NAME = os.environ.get("WELLFOUND_NAME", "Your Name")
EMAIL = os.environ.get("WELLFOUND_EMAIL", "you@example.com")
PHONE = os.environ.get("WELLFOUND_PHONE", "0000000000")

# Default applicant location used in the Wellfound apply modal.
# When a job has a specific city (e.g. Ahmedabad), the applier prefers the
# job's city (willing to relocate) and only falls back to this.
DEFAULT_APPLICANT_LOCATION = os.environ.get("WELLFOUND_APPLICANT_LOCATION", "Bengaluru, India")

# Search — locations + Most recent sort (no role/keyword filter) - user open to any location India or abroad
SEARCH_LOCATIONS = ["India", "Remote", "Worldwide"]
SORT_ORDER = "Most recent"

# Only consider jobs posted within this many days
MAX_JOB_AGE_DAYS = 2

# Matching — technical roles only; lenient on experience, strict on domain
MATCH_THRESHOLD = 5
OLLAMA_MODEL = "llama3.1"

# Scraper limits (per location search)
MAX_JOBS_PER_LOCATION = 25
PAGE_LOAD_DELAY_SEC = 3

# Browser: use system Edge (DataDome blocks bundled Chromium). Change via WELLFOUND_BROWSER_CHANNEL env var.
HEADLESS = os.environ.get("WELLFOUND_HEADLESS", "0") == "1"
BROWSER_CHANNEL = os.environ.get("WELLFOUND_BROWSER_CHANNEL", "msedge")  # msedge = Edge, chrome = Chrome
# Backward compat flags
USE_CHROME_CHANNEL = BROWSER_CHANNEL == "chrome"
USE_EDGE_CHANNEL = BROWSER_CHANNEL == "msedge"

# Telegram notifications
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# Paths
DATA_DIR = PROJECT_ROOT / "data"
RESUME_PATH = PROJECT_ROOT / "resume.txt"
# Separate profile per browser so Edge/Chrome don't conflict
BROWSER_DATA_DIR = PROJECT_ROOT / f".wellfound_browser_{BROWSER_CHANNEL}" if BROWSER_CHANNEL else PROJECT_ROOT / ".wellfound_browser"
APPLIED_JOBS_PATH = DATA_DIR / "applied_jobs.json"
SCRAPED_JOBS_PATH = DATA_DIR / "scraped_jobs.json"
LOGS_DIR = PROJECT_ROOT / "logs"
