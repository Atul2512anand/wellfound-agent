#!/bin/bash
# Set up a cron job to run the Wellfound agent every hour.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
if [[ -x "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3" ]]; then
    PYTHON_BIN="/Library/Frameworks/Python.framework/Versions/3.13/bin/python3"
fi

LOG_DIR="$ROOT/logs"
CRON_LOG="$LOG_DIR/cron.log"
ENV_FILE="$ROOT/.env"

mkdir -p "$LOG_DIR"

ENV_PREFIX=""
if [[ -f "$ENV_FILE" ]]; then
    ENV_PREFIX="set -a && source $ENV_FILE && set +a && "
fi

CRON_LINE="0 * * * * ${ENV_PREFIX}cd $ROOT && PYTHONPATH=$ROOT/src WELLFOUND_HEADLESS=1 $PYTHON_BIN -m wellfound_agent run >> $CRON_LOG 2>&1"

echo "Wellfound Agent Scheduler Setup"
echo "================================"
echo ""
echo "This will add/update the following cron entry:"
echo "  $CRON_LINE"
echo ""
echo "The agent will run every hour (at :00 each hour)."
echo ""

read -p "Continue? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

EXISTING=$(crontab -l 2>/dev/null || true)
FILTERED=$(echo "$EXISTING" | grep -vF "wellfound_agent" | grep -v "Wellfound job automation" || true)

{
    echo "$FILTERED"
    echo ""
    echo "# Wellfound job automation agent — runs every hour"
    echo "$CRON_LINE"
} | crontab -

echo ""
echo "Cron job installed successfully!"
echo ""
echo "Setup Telegram: copy .env.example → .env, then run:"
echo "  python3 scripts/get_telegram_chat_id.py"
echo ""
echo "Useful commands:"
echo "  crontab -l"
echo "  tail -f $CRON_LOG"
echo "  ./scripts/run.sh"
