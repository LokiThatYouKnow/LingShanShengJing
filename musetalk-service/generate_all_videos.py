"""
Generate opening + idle videos for ALL 3 engines.
Strategy:
  - Opening video: Real engine inference (lip-sync with TTS audio)
  - Idle videos (MuseTalk/Wav2Lip): ffmpeg static frame loop (no speech = no lip movement)
  - Idle videos (SadTalker): idlemode=True via SadTalker API
Total: 3 opening + 15 idle = 18 videos
"""
import os, sys, time, json, shutil, subprocess, tempfile, requests
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ENGINES = {
    "musetalk": {
        "api": "http://localhost:8003", "output": ROOT / "musetalk-service" / "output",
        "avatar": ROOT / "musetalk-service" / "avatars" / "avatar_female.png", "name": "MuseTalk",
    },
    "wav2lip": {
        "api": "http://localhost:8004", "output": ROOT / "wav2lip-service" / "output",
        "avatar": ROOT / "wav2lip-service" / "avatars" / "avatar_female.png", "name": "Wav2Lip",
    },
    "sadtalker": {
        "api": "http://localhost:8001", "output": ROOT / "sadtalker-service" / "output",
        "avatar": ROOT / "sadtalker-service" / "avatars" / "avatar_female.png", "name": "SadTalker",
    },
}

WELCOME_TEXT = "您好！欢迎来到灵山胜境，我是AI导览助手小灵，请问有什么可以帮您？"

SILENT_DIR = ROOT / "musetalk-service" / "uploads" / "silent"
SILENT_DIR.mkdir(parents=True, exist_ok=True)

IDLE_DURATIONS = [3, 5, 4, 3, 6]  # seconds per idle video

def cmd(args, **kw):
    return subprocess.run(args, capture_output=True, text=True, **kw)

def generate_silent_wav(dur, path):
    cmd(["ffmpeg", "-y", "-v", "warning", "-f", "lavfi", "-i", f"anullsrc=r=16000:cl=mono",
         "-t", str(dur), "-acodec", "pcm_s16le", path], check=True)
    return path

def generate_tts_wav(text, path):
    """TTS via backend → WAV."""
    r = requests.post("http://localhost:8000/api/chat/message-tts", json={
        "message": text, "session_id": f"tts_{int(time.time())}", "platform": "kiosk"
    }, timeout=120)
    if r.status_code != 200: raise RuntimeError(f"TTS failed: {r.status_code}")
    audio_url = r.json().get("audio_url")
    if not audio_url: raise RuntimeError("No audio_url")
    mp3 = path.replace(".wav", ".mp3")
    r2 = requests.get(f"http://localhost:8000{audio_url}", timeout=30)
    with open(mp3, "wb") as f: f.write(r2.content)
    cmd(["ffmpeg", "-y", "-v", "warning", "-i", mp3, "-ac", "1", "-ar", "16000", path], check=True)
    os.remove(mp3)
    import wave
    with wave.open(path, "rb") as wf: dur = wf.getnframes() / wf.getframerate()
    print(f"    TTS WAV: {os.path.getsize(path)} bytes, {dur:.1f}s")
    return path

def call_engine_generate(engine_key, audio_path, session_id):
    """Call engine /generate API, download video, return local path."""
    cfg = ENGINES[engine_key]
    files = {"audio": (os.path.basename(audio_path), open(audio_path, "rb"), "audio/wav")}
    if cfg["avatar"].exists():
        files["image"] = (cfg["avatar"].name, open(cfg["avatar"], "rb"), "image/png")
    data = {"session_id": session_id, "text": "auto", "emotion": "neutral"}
    try:
        r = requests.post(f"{cfg['api']}/generate", files=files, data=data, timeout=600)
    finally:
        for v in files.values():
            try: v[1].close()
            except: pass
    if r.status_code != 200:
        raise RuntimeError(f"API {r.status_code}: {r.text[:200]}")
    video_url = r.json().get("video_url", "")
    if not video_url: raise RuntimeError("No video_url")
    vr = requests.get(f"{cfg['api']}{video_url}", timeout=30)
    tmp = cfg["output"] / f"_tmp_{session_id}.mp4"
    with open(tmp, "wb") as f: f.write(vr.content)
    return str(tmp)

def ffmpeg_static_video(avatar_path, audio_path, output_path):
    """Create a video from static image + audio using ffmpeg."""
    cmd(["ffmpeg", "-y", "-v", "warning",
         "-loop", "1", "-i", str(avatar_path), "-i", str(audio_path),
         "-c:v", "libx264", "-preset", "fast", "-crf", "23",
         "-pix_fmt", "yuv420p", "-shortest", output_path], check=True)
    return output_path

def generate_opening(engine_key):
    """Generate opening video: TTS → engine inference."""
    cfg = ENGINES[engine_key]
    tts_wav = str(SILENT_DIR / f"opening_{engine_key}.wav")
    generate_tts_wav(WELCOME_TEXT, tts_wav)
    tmp = call_engine_generate(engine_key, tts_wav, f"opening_{engine_key}")
    target = cfg["output"] / "opening.mp4"
    if target.exists(): target.unlink()
    shutil.move(tmp, target)
    try: os.remove(tts_wav)
    except: pass
    print(f"  ✅ Opening: {target} ({os.path.getsize(target)} bytes)")
    return str(target)

def generate_idle_ffmpeg(engine_key, n, dur):
    """Generate idle video using ffmpeg (static frame + silent audio)."""
    cfg = ENGINES[engine_key]
    silent_wav = str(SILENT_DIR / f"silent_{dur}s_{engine_key}.wav")
    generate_silent_wav(dur, silent_wav)
    target = cfg["output"] / f"idle_{n:02d}.mp4"
    if target.exists(): target.unlink()
    ffmpeg_static_video(cfg["avatar"], silent_wav, str(target))
    try: os.remove(silent_wav)
    except: pass
    print(f"  ✅ Idle {n}/5: {target} ({os.path.getsize(target)} bytes)")
    return str(target)

def generate_idle_sadtalker(n, dur):
    """Generate idle video via SadTalker idlemode API."""
    cfg = ENGINES["sadtalker"]
    try:
        r = requests.get(f"{cfg['api']}/generate-idle",
                        params={"session_id": f"idle_{n:02d}", "length": dur}, timeout=600)
        if r.status_code == 200:
            data = r.json()
            vpath = data.get("video_path")
            if vpath and os.path.exists(vpath):
                target = cfg["output"] / f"idle_{n:02d}.mp4"
                if target.exists(): target.unlink()
                shutil.copy(vpath, target)
                return str(target)
        print(f"    SadTalker idle {n}/5: HTTP {r.status_code}")
    except Exception as e:
        print(f"    SadTalker idle {n}/5 error: {e}")
    return None

def main():
    print("=" * 60)
    print("🎬 MULTI-ENGINE VIDEO GENERATION")
    print("=" * 60)

    all_results = {}

    for engine_key in ["wav2lip", "musetalk", "sadtalker"]:
        cfg = ENGINES[engine_key]
        cfg["output"].mkdir(parents=True, exist_ok=True)

        # Check engine
        try:
            r = requests.get(f"{cfg['api']}/status", timeout=5)
            ready = r.json().get("ready", False) if r.status_code == 200 else False
        except:
            ready = False

        print(f"\n{'='*50}")
        print(f"{cfg['name']} ({engine_key}): {'✅ online' if ready else '⚠️ offline'}")
        print(f"{'='*50}")

        res = {"opening": None, "idle": []}

        # --- Opening Video ---
        if ready:
            print(f"  📢 Opening video...")
            try:
                res["opening"] = generate_opening(engine_key)
            except Exception as e:
                print(f"  ❌ Opening failed: {e}")
        else:
            print(f"  ⚠️ Skipping opening (engine offline)")

        # --- Idle Videos ---
        for i, dur in enumerate(IDLE_DURATIONS):
            n = i + 1

            if engine_key == "sadtalker" and ready:
                # SadTalker: use idlemode API for real idle movement
                idle_path = generate_idle_sadtalker(n, dur)
                if idle_path:
                    res["idle"].append(idle_path)
                else:
                    # Fallback to ffmpeg
                    print(f"    ⚠️ SadTalker fallback to ffmpeg for idle {n}")
                    res["idle"].append(generate_idle_ffmpeg(engine_key, n, dur))
            else:
                # MuseTalk/Wav2Lip: ffmpeg static frame (no speech = no lip move)
                # Also used as fallback if engine is offline
                try:
                    res["idle"].append(generate_idle_ffmpeg(engine_key, n, dur))
                except Exception as e:
                    print(f"  ❌ Idle {n}/5: {e}")
                    res["idle"].append(None)

        all_results[engine_key] = res

    # Summary
    print("\n\n" + "=" * 60)
    print("📊 GENERATION SUMMARY")
    print("=" * 60)
    for eng, res in all_results.items():
        ok = "✅" if res["opening"] else "❌"
        idle_ok = sum(1 for v in res["idle"] if v)
        print(f"  {ENGINES[eng]['name']:<12} Opening: {ok}  Idle: {idle_ok}/5")

    # Save
    out = ROOT / "musetalk-service" / "video_gen_results.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n✅ Saved to {out}")

if __name__ == "__main__":
    main()
