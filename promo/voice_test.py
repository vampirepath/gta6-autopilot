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
for name, dt, p in res:
    with open(p, "rb") as f:
        requests.post(f"https://api.telegram.org/bot{tok}/sendAudio", data={"chat_id": chat, "caption": f"Free voice test: {name} ({dt:.0f}s to make)"}, files={"audio": (p.name, f)}, timeout=120)
