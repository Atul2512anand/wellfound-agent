# Wellfound Job Agent

A local automation agent that finds recent jobs on [Wellfound](https://wellfound.com), scores them against your resume using a **local LLM** (Ollama + Llama 3.1, with keyword fallback), and applies to good matches. No cloud AI API keys required. Data stays on your machine.

> **Privacy note:** this repo is sanitized — personal details (name, email, phone, resume) are placeholders. Copy `resume.example.txt` → `resume.txt`, set `WELLFOUND_NAME` / `WELLFOUND_EMAIL` / `WELLFOUND_PHONE` env vars (or edit `config.py` locally), and never commit your real resume (it's gitignored).

## What it does

On each run, the agent:

1. **Finds** recent job listings (India + Remote + Worldwide, sorted **Most recent**)
2. **Filters** to technical roles only (software, AI/ML, backend, cybersecurity, blockchain, data)
3. **Scores** each job against your resume (Ollama 0–10, or keyword fallback)
4. **Applies** to jobs at/above threshold (max 5 per run) via your saved Wellfound profile
5. **Notifies** via Telegram (optional)
6. **Remembers** applied jobs in `data/applied_jobs.json` so it never applies twice

```text
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────┐
│   scrape    │ ──▶ │    match     │ ──▶ │    apply    │ ──▶ │  notify  │
│ (Playwright)│     │   (Ollama)   │     │ (Playwright)│     │(Telegram)│
└─────────────┘     └──────────────┘     └─────────────┘     └──────────┘
                           ▲
                       resume.txt
```

## Project structure

```text
wellfound-agent/
├── src/wellfound_agent/       # Main package
│   ├── cli.py                 # CLI entry (run, scrape, match, apply)
│   ├── pipeline.py            # Full scrape → match → apply flow
│   ├── config.py              # Settings (locations, thresholds, applicant)
│   ├── run_log.py             # Per-run logging
│   ├── browser/session.py     # Playwright + Edge/Chrome session mgmt
│   ├── scrape/service.py      # Wellfound job scraping
│   ├── match/filter.py        # Technical-role title filter
│   ├── match/matcher.py       # Ollama scoring + keyword fallback
│   ├── apply/service.py       # Auto-submit applications + cover note
│   ├── notify/service.py      # Telegram notifications
│   └── storage/               # jobs.py (applied/scraped), resume.py
├── scripts/
│   ├── run.sh                 # macOS/Linux runner
│   ├── setup_scheduler.sh     # Hourly cron setup (macOS/Linux)
│   └── get_telegram_chat_id.py
├── data/                      # Runtime JSON (gitignored, .gitkeep kept)
├── resume.example.txt         # Template — copy to resume.txt and fill in
├── AGENT.md                   # Windows + Edge quick guide
├── run_windows.ps1 / run.bat / run.sh   # Windows runners
├── login_only.py              # One-off manual login (saves session)
├── complete_profile*.py       # One-off Wellfound profile completion
├── fill_work_exp.py           # One-off work-experience filler
├── fix_*.py / remove_*.py     # One-off profile/location fix helpers
├── diag_*.py                  # Diagnostics (selectors, jobs, modals)
├── test_apply_*.py / verify_manual.py / check_jobs_access.py
├── pyproject.toml / requirements.txt / .env.example
```

Root-level `diag_*`, `fix_*`, `complete_*`, `test_*` scripts are one-off helpers/diagnostics — the daily flow is just `run`.

## Requirements

- **Python 3.10+**
- **Microsoft Edge** (Windows) or **Google Chrome** (macOS) — Wellfound blocks Playwright's bundled Chromium
- **Ollama** (optional, better matching) — https://ollama.com/download , then `ollama pull llama3.1`
- A **Wellfound account** (log in once; session saved in `.wellfound_browser_msedge/`, gitignored)

## Quick start (Windows)

```powershell
cd wellfound-agent
pip install -r requirements.txt
Copy-Item resume.example.txt resume.txt   # then edit resume.txt with YOUR resume
# optionally set your details without editing code:
$env:WELLFOUND_NAME="Your Name"; $env:WELLFOUND_EMAIL="you@example.com"; $env:WELLFOUND_PHONE="0000000000"
.\run_windows.ps1 run      # full pipeline: scrape -> match -> apply
```

Or directly:

```powershell
python -X utf8 -m wellfound_agent run     # full pipeline (default)
python -X utf8 -m wellfound_agent scrape  # jobs only -> data/scraped_jobs.json
python -X utf8 -m wellfound_agent match   # score scraped jobs, no browser
python -X utf8 -m wellfound_agent apply   # match scraped jobs + apply (no fresh scrape)
```

First run opens Edge — log in to Wellfound, solve any CAPTCHA, press **Enter** (120s window, session is saved).

### macOS/Linux

```bash
pip install -r requirements.txt
cp resume.example.txt resume.txt   # fill in your resume
./run.sh                            # or: PYTHONPATH=src python3 -m wellfound_agent run
./scripts/setup_scheduler.sh        # hourly cron
```

## Configuration

`src/wellfound_agent/config.py` (or env vars):

| Setting | Default | Description |
|---------|---------|-------------|
| `SEARCH_LOCATIONS` | India, Remote, Worldwide | Locations in Wellfound UI |
| `SORT_ORDER` | Most recent | Jobs page sort |
| `MAX_JOB_AGE_DAYS` | 2 | Only jobs posted within N days (`run`); `apply` matches all scraped |
| `MATCH_THRESHOLD` | 5 | Min Ollama score (0–10) to apply |
| `OLLAMA_MODEL` | llama3.1 | Local model |
| `MAX_JOBS_PER_LOCATION` | 25 | Cap per location |
| `BROWSER_CHANNEL` | msedge | `msedge` or `chrome` |

`.env` (optional, copy from `.env.example`):

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | Notifications |
| `WELLFOUND_HEADLESS=1` | Headless mode (after first login) |
| `WELLFOUND_NAME` / `WELLFOUND_EMAIL` / `WELLFOUND_PHONE` | Your details, no code edit needed |

## Practical tips

- `run` only considers jobs ≤ `MAX_JOB_AGE_DAYS` old; use `apply` to match everything already scraped.
- Weak fits applied while Ollama is off = keyword fallback — start Ollama or raise threshold to 6.
- `Apply button not found` = deleted/404 or external-apply (skipped by design).
- Never delete the browser profile dir unless login is broken; don't run two instances at once.

## Troubleshooting

- **0 jobs scraped:** complete CAPTCHA interactively; reset session (`Remove-Item -Recurse .wellfound_browser_msedge`, rerun `scrape`).
- **Ollama errors:** start Ollama service, `ollama pull llama3.1`.
- **Cron silent:** log in interactively first; check `logs/`.

## Safety

Automated applying may violate Wellfound's terms. Review `match` scores before `apply`, keep ~5/run, confirm in Wellfound → Applied.

## License

Personal project — use and modify as you like.
