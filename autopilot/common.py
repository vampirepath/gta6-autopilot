"""Shared helpers: paths, config, database, logging, alerts."""
import json
import logging
import os
import sqlite3
import time
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

LIB_DIR = ROOT / "library"
CLIPS_DIR = LIB_DIR / "clips"
LIB_INDEX = LIB_DIR / "index.json"
MUSIC_DIR = ROOT / "music"
OUT_DIR = ROOT / "output"
WORK_DIR = OUT_DIR / "work"
READY_DIR = OUT_DIR / "ready"
POSTED_DIR = OUT_DIR / "posted"
SECRETS_DIR = ROOT / "secrets"
FONT_DIR = ROOT / "assets" / "fonts"
for d in (CLIPS_DIR, MUSIC_DIR, WORK_DIR, READY_DIR, POSTED_DIR, SECRETS_DIR, ROOT / "logs"):
    d.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(ROOT / "logs" / "autopilot.log"), logging.StreamHandler()],
)
log = logging.getLogger("autopilot")


def config() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


# ---------------- database: remembers used stories & posted videos ----------
def db() -> sqlite3.Connection:
    con = sqlite3.connect(ROOT / "autopilot.db")
    con.execute("""CREATE TABLE IF NOT EXISTS stories(
        key TEXT PRIMARY KEY, title TEXT, url TEXT, used_at REAL)""")
    con.execute("""CREATE TABLE IF NOT EXISTS videos(
        id TEXT PRIMARY KEY, title TEXT, path TEXT, meta TEXT, created REAL,
        youtube TEXT, instagram TEXT, facebook TEXT)""")
    return con


def story_used(key: str) -> bool:
    with db() as con:
        return con.execute("SELECT 1 FROM stories WHERE key=?", (key,)).fetchone() is not None


def mark_story(key: str, title: str, url: str):
    with db() as con:
        con.execute("INSERT OR REPLACE INTO stories VALUES(?,?,?,?)", (key, title, url, time.time()))


def recent_titles(n: int = 30) -> list[str]:
    with db() as con:
        rows = con.execute("SELECT title FROM videos ORDER BY created DESC LIMIT ?", (n,)).fetchall()
    return [r[0] for r in rows]


def save_video(vid: str, title: str, path: str, meta: dict):
    with db() as con:
        con.execute("INSERT OR REPLACE INTO videos(id,title,path,meta,created) VALUES(?,?,?,?,?)",
                    (vid, title, path, json.dumps(meta), time.time()))


def set_platform(vid: str, platform: str, value: str):
    with db() as con:
        con.execute(f"UPDATE videos SET {platform}=? WHERE id=?", (value, vid))


def notify(text: str):
    """Optional Telegram alert."""
    tok, chat = env("TELEGRAM_BOT_TOKEN"), env("TELEGRAM_CHAT_ID")
    if not (tok and chat):
        return
    try:
        requests.post(f"https://api.telegram.org/bot{tok}/sendMessage",
                      data={"chat_id": chat, "text": text[:4000]}, timeout=15)
    except Exception as e:  # never let alerts break the pipeline
        log.warning("telegram failed: %s", e)
