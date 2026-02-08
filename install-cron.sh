#!/bin/bash
# Install cron jobs for Future Outlook Agent
# Usage: bash install-cron.sh /path/to/potential-garbanzo /path/to/python

set -e

PROJECT_DIR="${1:-.}"
PYTHON="${2:-python3}"

# Resolve absolute paths
PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"

# Verify the project exists
if [ ! -f "$PROJECT_DIR/outlook/cli.py" ]; then
    echo "Error: $PROJECT_DIR does not look like the outlook project"
    exit 1
fi

# Build cron entries
CRON_AM="0 7 * * * cd $PROJECT_DIR && $PYTHON -m outlook scan --time AM >> $PROJECT_DIR/data/cron.log 2>&1"
CRON_PM="0 17 * * * cd $PROJECT_DIR && $PYTHON -m outlook scan --time PM >> $PROJECT_DIR/data/cron.log 2>&1"

# Add to crontab (preserving existing entries)
(crontab -l 2>/dev/null | grep -v "outlook scan"; echo "$CRON_AM"; echo "$CRON_PM") | crontab -

echo "Installed cron jobs:"
echo "  7:00 AM (server time): $CRON_AM"
echo "  5:00 PM (server time): $CRON_PM"
echo ""
echo "Note: cron uses server timezone. If your server is UTC, adjust the hours."
echo "  For EST: use 12 and 22 instead of 7 and 17"
echo ""
echo "View with: crontab -l"
echo "Logs at: $PROJECT_DIR/data/cron.log"
