"""Run logging to stdout and timestamped log files."""

import sys
from datetime import datetime, timezone
from pathlib import Path

from wellfound_agent.config import LOGS_DIR


def setup_run_logging() -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.log"

    # Try to set stdout to utf-8 on Windows (cp1252 breaks on emojis/arrows)
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    class Tee:
        def __init__(self, *streams):
            self.streams = streams

        def write(self, data):
            for stream in self.streams:
                try:
                    stream.write(data)
                except UnicodeEncodeError:
                    # Fallback for Windows consoles that don't support emojis
                    stream.write(data.encode("utf-8", errors="replace").decode("utf-8", errors="replace").encode(stream.encoding or "utf-8", errors="replace").decode(stream.encoding or "utf-8", errors="replace"))
                try:
                    stream.flush()
                except Exception:
                    pass

        def flush(self):
            for stream in self.streams:
                try:
                    stream.flush()
                except Exception:
                    pass

    log_handle = log_file.open("a", encoding="utf-8")
    sys.stdout = Tee(sys.__stdout__, log_handle)
    sys.stderr = Tee(sys.__stderr__, log_handle)
    return log_file
