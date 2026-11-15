#!/bin/bash
# Downloads official Rockstar videos, cuts them into clips, AI-tags each clip. Takes 20-60 min the first time.
cd "$(dirname "$0")" && .venv/bin/python -m autopilot.library "$@"
