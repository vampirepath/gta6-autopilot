#!/bin/bash
# One-command installer for Ubuntu VPS.   Run:  bash install.sh
set -e
cd "$(dirname "$0")"
echo "==> Installing system packages"
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-venv python3-pip ffmpeg fonts-dejavu-core curl
echo "==> Creating Python environment"
python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt
echo "==> Downloading caption font (Anton)"
mkdir -p assets/fonts
curl -sSLf -o assets/fonts/Anton-Regular.ttf https://github.com/google/fonts/raw/main/ofl/anton/Anton-Regular.ttf || echo "   (font download failed - captions will use DejaVu Sans)"
[ -f .env ] || cp .env.example .env
mkdir -p secrets music logs
chmod +x *.sh
echo
echo "INSTALL DONE. Next: fill in .env  (nano .env)  then run  ./build_library.sh"
