#!/bin/bash
crontab -l 2>/dev/null | grep -v gta6-autopilot | crontab -
echo "AUTOPILOT OFF."
