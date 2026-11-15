"""ONE-TIME YouTube login. Run this on your Windows PC (not the VPS):
    1. Put client_secret.json (from Google Cloud) next to this file
    2. Double-click  auth_youtube.bat   (or run: python auth_youtube.py)
    3. Log in with the Google account that owns your GTA 6 channel
    4. A file youtube_token.json appears -> upload it to the VPS folder  secrets/
"""
from google_auth_oauthlib.flow import InstalledAppFlow

flow = InstalledAppFlow.from_client_secrets_file(
    "client_secret.json", ["https://www.googleapis.com/auth/youtube.upload"])
creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
open("youtube_token.json", "w").write(creds.to_json())
print("\nDONE! youtube_token.json created. Upload it to the VPS folder: gta6-autopilot/secrets/")
input("Press Enter to close...")
