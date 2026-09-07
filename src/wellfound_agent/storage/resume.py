"""Resume loading."""

from wellfound_agent.config import RESUME_PATH


def load_resume() -> str:
    return RESUME_PATH.read_text(encoding="utf-8")
