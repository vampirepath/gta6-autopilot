@echo off
cd /d "%~dp0"
python -m pip install --quiet google-auth-oauthlib
python auth_youtube.py
