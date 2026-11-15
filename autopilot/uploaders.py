"""Step 5 – upload to YouTube Shorts, Instagram Reels and Facebook Reels (official APIs only)."""
import os
import time
from pathlib import Path

import requests

from .common import SECRETS_DIR, config, env, log

YT_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
YT_TOKEN = SECRETS_DIR / "youtube_token.json"


# ---------------- YouTube ---------------------------------------------------
def youtube(video: Path, title: str, description: str, tags: list[str]) -> str:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    if env("YT_REFRESH_TOKEN"):   # GitHub Actions: built from repository secrets
        creds = Credentials(None, refresh_token=env("YT_REFRESH_TOKEN"),
                            token_uri="https://oauth2.googleapis.com/token",
                            client_id=env("YT_CLIENT_ID"), client_secret=env("YT_CLIENT_SECRET"),
                            scopes=YT_SCOPES)
    else:
        creds = Credentials.from_authorized_user_file(str(YT_TOKEN), YT_SCOPES)
    if not creds.valid:
        creds.refresh(Request())
        if not env("YT_REFRESH_TOKEN"):
            YT_TOKEN.write_text(creds.to_json())
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
    cfg = config()
    body = {
        "snippet": {"title": title, "description": description, "tags": tags[:15],
                    "categoryId": cfg["youtube_category"], "defaultLanguage": "en"},
        "status": {"privacyStatus": cfg["youtube_privacy"], "selfDeclaredMadeForKids": False,
                   "containsSyntheticMedia": True},   # honest AI-voice disclosure
    }
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(video), chunksize=-1, resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    vid = resp["id"]
    log.info("YouTube: https://youtube.com/shorts/%s", vid)
    return vid


# ---------------- Meta (Instagram + Facebook) -------------------------------
def _graph() -> str:
    return f"https://graph.facebook.com/{env('META_GRAPH_VERSION', 'v23.0')}"


def _check(r: requests.Response) -> dict:
    data = r.json() if r.content else {}
    if r.status_code >= 400 or "error" in data:
        raise RuntimeError(f"Meta API error: {data.get('error', r.text)}")
    return data


def instagram(video: Path, caption: str) -> str:
    token, ig = env("META_PAGE_TOKEN"), env("META_IG_USER_ID")
    ver = env("META_GRAPH_VERSION", "v23.0")
    # 1. create a resumable REELS container
    c = _check(requests.post(f"{_graph()}/{ig}/media", data={
        "media_type": "REELS", "upload_type": "resumable", "caption": caption,
        "share_to_feed": "true", "access_token": token}))
    cid = c["id"]
    # 2. send the file bytes
    size = os.path.getsize(video)
    with open(video, "rb") as f:
        _check(requests.post(f"https://rupload.facebook.com/ig-api-upload/{ver}/{cid}", data=f, headers={
            "Authorization": f"OAuth {token}", "offset": "0", "file_size": str(size)}, timeout=600))
    # 3. wait for Instagram to process it
    for _ in range(60):
        st = _check(requests.get(f"{_graph()}/{cid}", params={
            "fields": "status_code,status", "access_token": token}))
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") == "ERROR":
            raise RuntimeError(f"Instagram processing error: {st}")
        time.sleep(10)
    else:
        raise RuntimeError("Instagram processing timed out")
    # 4. publish
    pub = _check(requests.post(f"{_graph()}/{ig}/media_publish", data={
        "creation_id": cid, "access_token": token}))
    log.info("Instagram: media %s", pub["id"])
    return pub["id"]


def facebook(video: Path, description: str) -> str:
    token, page = env("META_PAGE_TOKEN"), env("META_PAGE_ID")
    ver = env("META_GRAPH_VERSION", "v23.0")
    start = _check(requests.post(f"{_graph()}/{page}/video_reels", data={
        "upload_phase": "start", "access_token": token}))
    vid = start["video_id"]
    size = os.path.getsize(video)
    with open(video, "rb") as f:
        _check(requests.post(f"https://rupload.facebook.com/video-upload/{ver}/{vid}", data=f, headers={
            "Authorization": f"OAuth {token}", "offset": "0", "file_size": str(size)}, timeout=600))
    _check(requests.post(f"{_graph()}/{page}/video_reels", data={
        "upload_phase": "finish", "video_id": vid, "video_state": "PUBLISHED",
        "description": description, "access_token": token}))
    log.info("Facebook: reel %s", vid)
    return vid
