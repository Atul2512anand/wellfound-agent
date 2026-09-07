"""Filter jobs to technical engineering/AI roles only."""

import re
from typing import Any

EXCLUDE_TITLE_PATTERNS = [
    r"content writer",
    r"creative writer",
    r"copywriter",
    r"copy writer",
    r"\bwriter\b",
    r"\bsales\b",
    r"account executive",
    r"outreach specialist",
    r"business owner",
    r"licensee",
    r"tax analyst",
    r"policy admin",
    r"\btutor\b",
    r"recruiting",
    r"\bhr\b",
    r"recruiter",
    r"digital marketing",
    r"seo specialist",
    r"customer support",
    r"virtual assistant",
    r"data entry",
    r"international sales",
    r"cx analytics",
    r"business development",
    r"marketing manager",
    r"product manager",
    r"designer",
    r"ux designer",
    r"ui designer",
]

INCLUDE_TITLE_PATTERNS = [
    # Core software
    r"software engineer",
    r"software developer",
    r"\bdeveloper\b",
    r"\bengineer\b",
    r"backend",
    r"frontend",
    r"front-end",
    r"full stack",
    r"fullstack",
    r"full-stack",
    r"\bsde\b",
    # AI/ML roles
    r"ai engineer",
    r"ml engineer",
    r"machine learning",
    r"data engineer",
    r"data scientist",
    r"data analyst",
    r"ai\b",
    r"\bml\b",
    r"artificial intelligence",
    # Cybersecurity roles
    r"cybersecurity",
    r"cyber security",
    r"security engineer",
    r"security analyst",
    r"soc analyst",
    r"ot security",
    r"it security",
    r"scada",
    r"plc",
    r"osint",
    r"penetration tester",
    r"pen tester",
    # Blockchain roles
    r"blockchain",
    r"solidity",
    r"ethereum",
    r"web3",
    r"dapp",
    # General tech that matches resume
    r"devops",
    r"platform engineer",
    r"infra",
    r"gen ai",
    r"genai",
    r"agentic",
    r"llm",
    r"python",
    r"java\b",
    r"react\b",
    r"fastapi",
    r"flask",
    # Junior-friendly - we include these but matcher will score them higher
    r"intern",
    r"junior",
    r"entry level",
    r"associate",
    r"trainee",
]


def is_technical_role(job: dict[str, Any]) -> bool:
    title = job.get("title", "").lower()

    for pattern in EXCLUDE_TITLE_PATTERNS:
        if re.search(pattern, title, re.IGNORECASE):
            return False

    for pattern in INCLUDE_TITLE_PATTERNS:
        if re.search(pattern, title, re.IGNORECASE):
            return True

    return False


def filter_technical_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    kept = []
    skipped = 0
    for job in jobs:
        if is_technical_role(job):
            kept.append(job)
        else:
            skipped += 1
            print(f"  Skip (non-technical): {job.get('title', '?')}")
    if skipped:
        print(f"  Filtered out {skipped} non-technical roles")
    return kept
