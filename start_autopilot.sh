#!/bin/bash
# Turns on the schedule: videos at 8:30 AM, 1:30 PM and 7:30 PM India time,
# and checks your Telegram approve buttons every 2 minutes.
cd "$(dirname "$0")"
DIR=$(pwd)
sudo timedatectl set-timezone Asia/Kolkata 2>/dev/null || true
( crontab -l 2>/dev/null | grep -v gta6-autopilot ;
  echo "30 8,13,19 * * * cd $DIR && .venv/bin/python -m autopilot.run >> logs/cron.log 2>&1 # gta6-autopilot"
  echo "*/2 * * * * cd $DIR && .venv/bin/python -m autopilot.review >> logs/cron.log 2>&1 # gta6-autopilot"
) | crontab -
echo "AUTOPILOT ON. Schedule:"; crontab -l | grep gta6-autopilot
