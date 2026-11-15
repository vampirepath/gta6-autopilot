#!/bin/bash
# Make videos now.  ./make_video.sh                -> from the latest news
#                   ./make_video.sh --topic "GTA 6 map size compared to GTA 5"
cd "$(dirname "$0")" && .venv/bin/python -m autopilot.run "$@"
