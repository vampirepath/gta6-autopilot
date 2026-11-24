"""One-off test: VoiceStudio (OmniVoice) voices for the promo reels -> samples sent to the promo Telegram bot."""
import os, time, requests
from pathlib import Path
B = "http://127.0.0.1:3900"
H = {"Authorization": f"Bearer {os.environ['OMNIVOICE_API_KEY']}"}
OUT = Path("output/voice_test"); OUT.mkdir(parents=True, exist_ok=True)
for i in range(120):
    try:
        if requests.get(f"{B}/v1/models", headers=H, timeout=5).status_code < 500: break
    except Exception: pass
    time.sleep(5)
ROMAN = "Bhai, kisi bhi live stream ko seedha mobile se clip karna hai? Bas link paste karo, start dabao, aur clips ready."
DEVA = "भाई, किसी भी लाइव स्ट्रीम को सीधा मोबाइल से क्लिप करना है? बस लिंक पेस्ट करो, स्टार्ट दबाओ, और क्लिप्स रेडी।"
VOICE = "male, young adult, moderate pitch, indian accent"
tests = [("A_roman_design", {"text": ROMAN, "instruct": VOICE}),
         ("B_deva_hindi_design", {"text": DEVA, "instruct": VOICE, "language": "hi"}),
         ("C_roman_hindi_design", {"text": ROMAN, "instruct": VOICE, "language": "hi"})]
res = []
for name, form in tests:
    form = {**form, "seed": "7", "effect_preset": "broadcast"}
    t0 = time.time()
    r = requests.post(f"{B}/generate", headers=H, data=form, timeout=1500)
    dt = time.time() - t0
    print(name, r.status_code, round(dt), r.headers.get("content-type"), r.text[:300] if r.status_code != 200 else "")
    if r.status_code == 200:
        (OUT / f"{name}.wav").write_bytes(r.content); res.append((name, dt))
tok = os.environ.get("PROMO_TELEGRAM_BOT_TOKEN") or os.environ["TELEGRAM_BOT_TOKEN"]
chat = os.environ.get("PROMO_TELEGRAM_CHAT_ID") or os.environ["TELEGRAM_CHAT_ID"]
for name, dt in res:
    with open(OUT / f"{name}.wav", "rb") as f:
        requests.post(f"https://api.telegram.org/bot{tok}/sendAudio", data={"chat_id": chat, "caption": f"VoiceStudio test {name} ({dt:.0f}s to make)"}, files={"audio": (f"{name}.wav", f)}, timeout=120)
