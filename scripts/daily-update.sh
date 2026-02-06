#!/bin/bash
#
# Portfolio update script for cron
#
# Exit codes from main.py update:
#   0 = new data saved
#   1 = error (config, network, etc.)
#   2 = no new data (already have today's data)
#
# Usage in crontab (daily at 7 AM):
#   0 7 * * * /path/to/ibkr/scripts/daily-update.sh >> /path/to/ibkr/logs/cron.log 2>&1

# Change to project directory
cd "$(dirname "$0")/.."

echo "=================================================="
echo "Portfolio update: $(date)"
echo "=================================================="

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Try to update (capture exit code without failing)
python3 -m src.main update || UPDATE_EXIT_CODE=$?
UPDATE_EXIT_CODE=${UPDATE_EXIT_CODE:-0}

if [ $UPDATE_EXIT_CODE -eq 0 ]; then
    echo "New data received, regenerating site..."
    python3 -m src.main site

    echo "Committing and pushing changes..."
    git add docs/ data/portfolio_history.json
    git commit -m "Daily portfolio update $(date +%Y-%m-%d)"
    git push

    echo "Done!"
elif [ $UPDATE_EXIT_CODE -eq 2 ]; then
    echo "No new data available. Skipping site generation and commit."
else
    echo "Error updating portfolio (exit code: $UPDATE_EXIT_CODE)"
    exit 1
fi
