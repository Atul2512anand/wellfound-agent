"""Match scraped jobs against resume using local Ollama."""

import json
import re
from typing import Any

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    ollama = None  # type: ignore
    OLLAMA_AVAILABLE = False

from wellfound_agent.config import MATCH_THRESHOLD, OLLAMA_MODEL, SCRAPED_JOBS_PATH
from wellfound_agent.match.filter import filter_technical_jobs
from wellfound_agent.storage.resume import load_resume


def _fallback_score(job: dict[str, Any]) -> tuple[float, str]:
    """Resume-aware keyword fallback when Ollama is not running."""
    title = job.get("title", "").lower()
    desc = job.get("description", "").lower()
    text = title + " " + desc

    # Resume-specific keywords grouped by domain (customize to your background)
    resume_keywords = {
        "cybersecurity": ["cybersecurity", "cyber security", "security analyst", "soc analyst", "ot security", "it security", "scada", "plc", "osint", "penetration", "vulnerability", "siem"],
        "blockchain": ["blockchain", "solidity", "ethereum", "web3", "dapp", "smart contract", "ethers.js"],
        "ai_ml": ["machine learning", "artificial intelligence", "ai", "ml", "deep learning", "xgboost", "scikit-learn", "pytorch", "tensorflow", "langchain", "agentic ai", "rag", "llm", "computer vision", "opencv", "nlp"],
        "data": ["data analyst", "data scientist", "data engineer", "pandas", "numpy", "sql", "postgresql", "data cleaning", "eda", "analytics"],
        "software": ["python", "java", "c++", "javascript", "fastapi", "flask", "react", "node", "backend", "frontend", "full stack", "azure", "docker", "git"],
    }
    # Flatten and score
    all_keywords = [kw for group in resume_keywords.values() for kw in group]
    matches = [kw for kw in all_keywords if kw in text]
    # Count distinct domains matched
    domains_matched = sum(1 for group_kws in resume_keywords.values() if any(kw in text for kw in group_kws))
    # Experience level handling
    is_senior = bool(re.search(r"\bsenior\b|\blead\b|\bstaff\b|\bprincipal\b|\bmanager\b|\bhead\b|5\+|8\+|10\+ years", title, re.I))
    is_junior = bool(re.search(r"\bintern\b|\bjunior\b|\bentry\b|\bassociate\b|\btrainee\b|0-1|0-2|1-2 years|fresher", title, re.I))
    # Base score by matches
    if domains_matched >= 2 and len(matches) >= 4:
        base = 8.0
    elif domains_matched >= 1 and len(matches) >= 3:
        base = 7.0
    elif len(matches) >= 2:
        base = 6.0
    elif len(matches) >= 1:
        base = 5.5
    else:
        base = 5.0

    # Adjust for seniority: student (<1 year), so senior roles get penalty, junior gets bonus
    if is_senior and not is_junior:
        base -= 1.5  # Penalty for senior 5+ years roles
        reason_suffix = " - senior role penalty (you're <1yr)"
    elif is_junior:
        base += 0.5
        reason_suffix = " + junior friendly"
    else:
        reason_suffix = ""

    # Clamp
    base = max(0, min(10, base))
    # Build reason
    if matches:
        reason = f"Fallback ({domains_matched} domains, {len(matches)} keywords: {', '.join(matches[:4])}){reason_suffix}"
    else:
        reason = f"Fallback technical role{reason_suffix}"

    return round(base, 1), reason

SCORE_PATTERN = re.compile(r"(?:score|rating)[:\s]*(\d+(?:\.\d+)?)", re.IGNORECASE)
JSON_SCORE_PATTERN = re.compile(r'"score"\s*:\s*(\d+(?:\.\d+)?)')


def _build_prompt(resume: str, job: dict[str, Any]) -> str:
    description = job.get("description", "")[:6000]
    return f"""You are a job matching assistant for THE CANDIDATE - Computer Science student (Cybersecurity), India.

Candidate profile:
- Cybersecurity: OSINT, OT/IT/SCADA/PLC concepts, SOC workflows
- Blockchain: DApps (Solidity, Ethereum, Ethers.js)
- AI/ML: ML/DL, XGBoost, LangChain, RAG/LLM apps, computer vision (OpenCV)
- Data: Pandas, SQL, EDA, analytics
- Software: Python, Java, C/C++, SQL, JavaScript, Flask, FastAPI, React, Docker, Git
- Experience: <1 year (student, internships), seeking Junior/Entry-level, Intern, Associate roles - NOT Senior 5+ years
- Location: Open to any (India/Remote/Worldwide)

Score jobs favourably only if they match this resume's domains and junior level.

Scoring guide:
- 0-3: Wrong domain (sales, writing, finance, HR, or Senior 8+ years with no junior path)
- 4-5: Partial fit - some skill overlap but senior or not ideal (e.g., Senior 5+ years requires more exp)
- 6-7: Good fit - junior/mid in Cybersecurity/Blockchain/AI/Data/Software with Python etc.
- 8-10: Strong fit - Intern/Junior/Associate in Cybersecurity, Blockchain, AI/ML, Data, or Software with clear skill match

Be STRICT on seniority: If job says Senior/Lead/Staff/5+ years and candidate is <1yr, cap at 5.5 unless it's clearly junior-friendly.
Be STRICT on domain: Do NOT score 6+ for non-tech or unrelated.
Favour: Cybersecurity, Blockchain, AI/ML, Data Analytics, Software Engineer (Junior/Intern).

Respond with ONLY valid JSON:
{{"score": <number 0-10>, "reason": "<one sentence>"}}

RESUME:
{resume}

JOB TITLE: {job.get('title', 'Unknown')}
COMPANY: {job.get('company', 'Unknown')}
LOCATION: {job.get('location', 'Unknown')}

JOB DESCRIPTION:
{description}
"""


def _parse_score(response_text: str) -> tuple[float, str]:
    text = response_text.strip()

    try:
        data = json.loads(text)
        score = float(data.get("score", 0))
        reason = str(data.get("reason", ""))
        return min(max(score, 0), 10), reason
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    json_match = JSON_SCORE_PATTERN.search(text)
    if json_match:
        return float(json_match.group(1)), text[:200]

    score_match = SCORE_PATTERN.search(text)
    if score_match:
        return float(score_match.group(1)), text[:200]

    number_match = re.search(r"\b(\d+(?:\.\d+)?)\s*/\s*10\b", text)
    if number_match:
        return float(number_match.group(1)), text[:200]

    lone_number = re.search(r"\b([0-9]|10)(?:\.\d+)?\b", text)
    if lone_number:
        return float(lone_number.group(0)), text[:200]

    return 0.0, "Could not parse score from model response"


def score_job(resume: str, job: dict[str, Any]) -> dict[str, Any]:
    prompt = _build_prompt(resume, job)

    # Try Ollama if available
    if OLLAMA_AVAILABLE:
        try:
            response = ollama.chat(
                model=OLLAMA_MODEL,
                messages=[{"role": "user", "content": prompt}],
            )
            content = response["message"]["content"]
            score, reason = _parse_score(content)
            return {**job, "match_score": score, "match_reason": reason}
        except Exception as exc:
            print(f"  Ollama not running for {job.get('title')}: {exc} — using fallback")
            fb_score, fb_reason = _fallback_score(job)
            return {**job, "match_score": fb_score, "match_reason": fb_reason}
    else:
        fb_score, fb_reason = _fallback_score(job)
        return {**job, "match_score": fb_score, "match_reason": fb_reason}


def match_jobs(
    jobs: list[dict[str, Any]] | None = None,
    resume: str | None = None,
    threshold: float = MATCH_THRESHOLD,
) -> list[dict[str, Any]]:
    """Filter to technical roles, score against resume, return matches above threshold."""
    if jobs is None:
        if not SCRAPED_JOBS_PATH.exists():
            raise FileNotFoundError(
                f"No scraped jobs found at {SCRAPED_JOBS_PATH}. Run scrape first."
            )
        with SCRAPED_JOBS_PATH.open(encoding="utf-8") as f:
            jobs = json.load(f)

    print("\nFiltering to technical roles only...")
    jobs = filter_technical_jobs(jobs)

    if not jobs:
        print("  No technical roles to match.")
        return []

    resume = resume or load_resume()
    matched: list[dict[str, Any]] = []

    print(f"\nMatching {len(jobs)} technical jobs (threshold: {threshold}/10)...")

    for i, job in enumerate(jobs, 1):
        print(f"  [{i}/{len(jobs)}] {job.get('title', 'Unknown')} @ {job.get('company', '')}")
        scored = score_job(resume, job)
        score = scored["match_score"]
        reason = scored.get("match_reason", "")
        print(f"    Score: {score}/10 — {reason}")

        if score >= threshold:
            matched.append(scored)

    matched.sort(key=lambda j: j["match_score"], reverse=True)
    print(f"\n{len(matched)} jobs scored {threshold}+ out of {len(jobs)}")
    return matched
