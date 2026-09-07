# AGENT.md — Run the Wellfound Job Automation Yourself

Self-contained starter for the Wellfound job agent in this folder.
No AI model needed. Windows + Microsoft Edge.

## 1. What this does
- Scrapes recent Wellfound jobs (India + Remote + Worldwide, Most recent)
- Keeps technical roles only (software, backend, AI/ML, data, cybersecurity, blockchain)
- Scores each against `resume.txt` (Ollama if running, else keyword fallback)
- Applies to scores >= `MATCH_THRESHOLD` (max 5 per `run`), skips already-applied
- Remembers applied jobs in `data/applied_jobs.json` so it never applies twice

## 2. First-time setup (once)
```powershell
cd "C:\Users\HP\OneDrive\Documents\job automation\wellfound-agent"
python --version            # need Python 3.10+
pip install -r requirements.txt
```
- Install Microsoft Edge (already used via `BROWSER_CHANNEL=msedge`).
- Optional (better matching): install Ollama from https://ollama.com/download,
  then `ollama pull llama3.1` and keep the Ollama app running.
  Without it, the agent uses keyword fallback scoring.
- Optional (notifications): copy `.env.example` to `.env`, fill
  `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`.

## 3. Everyday use (Windows)
```powershell
cd "C:\Users\HP\OneDrive\Documents\job automation\wellfound-agent"
.\run_windows.ps1 run      # full pipeline: scrape -> match -> apply
```
Or directly:
```powershell
python -X utf8 -m wellfound_agent run     # full pipeline (default)
python -X utf8 -m wellfound_agent scrape  # jobs only -> data/scraped_jobs.json
python -X utf8 -m wellfound_agent match   # score scraped jobs, no browser
python -X utf8 -m wellfound_agent apply   # match scraped jobs + apply (no fresh scrape)
```
`run.bat` also works (double-click, then type `run` / `scrape` / `match` / `apply`).

First run opens Edge. If asked, log in to Wellfound with Google
(your account), solve any CAPTCHA, then press Enter in the
terminal (you get 120s; session is saved in `.wellfound_browser_msedge/`).

## 4. Key files
- `resume.txt` — your resume (matching source). Update it to change targeting.
- `src/wellfound_agent/config.py` — `SEARCH_LOCATIONS`, `MAX_JOB_AGE_DAYS` (2),
  `MATCH_THRESHOLD` (5), `MAX_JOBS_PER_LOCATION` (25),
  `DEFAULT_APPLICANT_LOCATION` (Bengaluru, India; override with
  `WELLFOUND_APPLICANT_LOCATION` env). Job-city relocation fix uses the job's
  city when the apply modal says "Your primary location is too broad".
- `data/scraped_jobs.json` — last scrape results.
- `data/applied_jobs.json` — applied log (skip list). Back it up before resets.
- `logs/run_*.log` — per-run logs + final report.

## 5. Practical tips
- `run` only considers jobs <= `MAX_JOB_AGE_DAYS` old. To also apply to older
  scraped jobs (e.g. Backend Engineer Python from weeks ago), use `apply`
  instead — it matches everything in `data/scraped_jobs.json`.
- If a run applies to weak fits (Marketing/Creative), that's fallback scoring
  (Ollama off). Start Ollama or raise `MATCH_THRESHOLD` to 6.
- Typical failures and meaning:
  - `Apply button not found` — job deleted (404) or external-apply only.
  - `Send application button not found` — Send stayed disabled (usually an
    unfilled required question like "What interests you...?" or location error).
  - `external apply only` — must apply on company site, skipped by design.
- Never delete `.wellfound_browser_msedge/` unless login is broken; deleting
  logs you out. To reset login: close Edge, `Remove-Item -Recurse .wellfound_browser_msedge`, rerun `scrape`.
- Do not run two instances at once (same Edge profile).

## 6. Safety
Automated applying may violate Wellfound's terms. Review `match` scores
before `apply`, keep to ~5/run, and confirm submissions in
Wellfound → Applied.
