"""One-off test: VoxCPM2 (the Apache-2.0, commercial-use engine inside VoiceStudio) on CPU -> samples to the promo Telegram bot."""
import os, time, requests, soundfile as sf
from pathlib import Path
from voxcpm import VoxCPM
OUT = Path("output/voice_test"); OUT.mkdir(parents=True, exist_ok=True)
t0 = time.time()
m = VoxCPM.from_pretrained("openbmb/VoxCPM2", load_denoiser=False, optimize=False, device="cpu")
sr = m.tts_model.sample_rate
print("load", round(time.time() - t0)); 
DESC = "(A young Indian man in his twenties, energetic and excited, clear upbeat social media narrator voice)"
ROMAN = "Bhai, kisi bhi live stream ko seedha mobile se clip karna hai? Bas link paste karo, start dabao, aur clips ready."
DEVA = "भाई, किसी भी लाइव स्ट्रीम को सीधा मोबाइल से क्लिप करना है? बस लिंक पेस्ट करो, स्टार्ट दबाओ, और क्लिप्स रेडी।"
res = []
def gen(name, **kw):
    t = time.time(); w = m.generate(inference_timesteps=10, cfg_value=2.0, **kw); dt = time.time() - t
    p = OUT / f"{name}.wav"; sf.write(p, w, sr); print(name, round(dt), "s for", round(len(w) / sr, 1), "s audio", flush=True); res.append((name, dt, p)); return p
ref = gen("1_design_hindi", text=DESC + DEVA)
gen("2_clone_hindi", text=DEVA, reference_wav_path=str(ref))
gen("3_clone_roman_hinglish", text=ROMAN, reference_wav_path=str(ref))
tok = os.environ.get("PROMO_TELEGRAM_BOT_TOKEN") or os.environ["TELEGRAM_BOT_TOKEN"]
chat = os.environ.get("PROMO_TELEGRAM_CHAT_ID") or os.environ["TELEGRAM_CHAT_ID"]
import subprocess
for name, dt, p in res:
    mp3 = p.with_suffix(".mp3"); ogg = p.with_suffix(".ogg")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(p), "-ar", "44100", "-b:a", "192k", str(mp3)], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(p), "-c:a", "libopus", "-b:a", "64k", str(ogg)], check=True)
    with open(ogg, "rb") as f:   # voice note: plays right inside the chat
        r = requests.post(f"https://api.telegram.org/bot{tok}/sendVoice", data={"chat_id": chat, "caption": f"Voice test {name}"}, files={"voice": (ogg.name, f, "audio/ogg")}, timeout=120)
    print("sendVoice", name, r.status_code, r.text[:200])
    with open(mp3, "rb") as f:
        r = requests.post(f"https://api.telegram.org/bot{tok}/sendAudio", data={"chat_id": chat, "title": name, "caption": f"{name} (mp3)"}, files={"audio": (mp3.name, f, "audio/mpeg")}, timeout=120)
    print("sendAudio", name, r.status_code, r.text[:200])
