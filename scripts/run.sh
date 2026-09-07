#!/bin/bash
# Run the Wellfound agent from the project root.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
if [[ -x "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3" ]]; then
    PYTHON="/Library/Frameworks/Python.framework/Versions/3.13/bin/python3"
fi

export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
exec "$PYTHON" -m wellfound_agent "$@"
