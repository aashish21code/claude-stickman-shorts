# Step 3a: script text (one sentence per line) -> voice.wav (48 kHz mono) + takes.json.
#
# One take per sentence, so a re-run after an edit only pays for the changed line: a take's file name
# carries a hash of its text and every voice parameter, and an existing file is reused. Takes are
# trimmed to their speech and butted together with --gap seconds, because the reference style has
# almost no pauses (word gaps > 0.25 s total < 1 s a video).
#
# Engines:
#   cartesia  Cartesia Sonic over its HTTP API; needs CARTESIA_API_KEY in the environment and a voice id
#   piper     offline and free (pip install piper-tts); the voice model downloads on first use
#
# Usage:
#   python tts.py --text script.txt --out voice/voice.wav --voice <cartesia-voice-uuid>
#   python tts.py --text script.txt --out voice/voice.wav --voice <uuid> --language en --speed 1.1 --emotion calm
#   python tts.py --text script.txt --out voice/voice.wav --engine piper --piper-voice en_US-ryan-high
import argparse, hashlib, io, json, os, re, subprocess, sys, tempfile, urllib.error, urllib.request, wave

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

CARTESIA_URL = "https://api.cartesia.ai/tts/bytes"
CARTESIA_VERSION = os.environ.get("CARTESIA_VERSION", "2026-08-14")   # a required header; override if it moves


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True).stdout.strip() or 0)


def speech_bounds(wav, db=-40):
    err = subprocess.run(["ffmpeg", "-i", wav, "-af", f"silencedetect=n={db}dB:d=0.08", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", err)]
    en = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", err)]
    total = dur(wav)
    a = en[0] if st and st[0] < 0.02 and en else 0.0
    b = st[-1] if st and (len(en) < len(st) or en[-1] >= total - 0.02) else total
    return max(0.0, a - 0.03), min(total, b + 0.08)


def cartesia_take(text, out, a):
    key = os.environ.get("CARTESIA_API_KEY")
    if not key:
        raise SystemExit("CARTESIA_API_KEY is not set (export it, or use --engine piper)")
    if not a.voice:
        raise SystemExit("--voice <cartesia voice id> is required for --engine cartesia")
    body = {"model_id": a.model, "transcript": text, "voice": {"id": a.voice}, "language": a.language,
            "output_format": {"container": "wav", "encoding": "pcm_s16le", "sample_rate": 44100}}
    gen = {k: v for k, v in {"speed": a.speed, "emotion": a.emotion}.items() if v not in (None, "")}
    if gen:
        body["generation_config"] = gen
    req = urllib.request.Request(CARTESIA_URL, data=json.dumps(body).encode(), method="POST", headers={
        "Authorization": f"Bearer {key}", "Cartesia-Version": CARTESIA_VERSION, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        detail = e.read()[:400].decode(errors="replace")
        # 402 is a billing state, not a rate limit: retrying never helps
        hint = " (out of credits -- retrying will not help)" if e.code == 402 else ""
        raise SystemExit(f"cartesia: HTTP {e.code}{hint}\n  {detail}")
    # check it is a readable WAV now: a truncated file shows up much later as a mis-timed cut
    with wave.open(io.BytesIO(raw)) as w:
        if w.getnframes() == 0:
            raise SystemExit(f"cartesia: empty audio for: {text[:60]}")
    open(out, "wb").write(raw)


def piper_take(text, out, a):
    try:
        import piper  # noqa: F401
    except ImportError:
        raise SystemExit("piper not installed: pip install piper-tts (voices: https://huggingface.co/rhasspy/piper-voices)")
    subprocess.run([sys.executable, "-m", "piper", "-m", a.piper_voice, "--data-dir", a.piper_dir,
                    "--download-dir", a.piper_dir, "-f", out, "--length-scale", str(round(1 / (a.speed or 1.0), 3))],
                   input=text, text=True, check=True)


def main():
    ap = argparse.ArgumentParser(description="Script text -> voice.wav, one take per sentence.")
    ap.add_argument("--text", required=True, help="text file, one sentence per line (blank and # lines ignored)")
    ap.add_argument("--out", required=True, help="voice.wav path; takes go in <out dir>/takes/")
    ap.add_argument("--engine", choices=["cartesia", "piper"], default="cartesia")
    ap.add_argument("--voice", default=os.environ.get("CARTESIA_VOICE"), help="Cartesia voice id (or CARTESIA_VOICE)")
    ap.add_argument("--model", default="sonic-3.6", help="Cartesia model id")
    ap.add_argument("--language", default="en")
    ap.add_argument("--speed", type=float, default=1.0, help="1.0 natural; the reference pace is ~3.5-3.7 words/s")
    ap.add_argument("--emotion", default=None, help="Cartesia emotion word, e.g. calm")
    ap.add_argument("--gap", type=float, default=0.08, help="seconds between sentences (default 0.08)")
    ap.add_argument("--piper-voice", default="en_US-ryan-high")
    ap.add_argument("--piper-dir", default=os.path.join(ROOT, "models", "piper"))
    a = ap.parse_args()

    lines = [l.strip() for l in open(a.text, encoding="utf-8") if l.strip() and not l.lstrip().startswith("#")]
    out_dir = os.path.dirname(os.path.abspath(a.out)); takes_dir = os.path.join(out_dir, "takes")
    os.makedirs(takes_dir, exist_ok=True)
    take = cartesia_take if a.engine == "cartesia" else piper_take
    takes = []
    for i, line in enumerate(lines, 1):
        # the hash covers every parameter: a take path that ignored them would hand back the old take
        # after a --speed or --voice change
        key = hashlib.sha1(json.dumps([a.engine, a.model, a.voice, a.language, a.speed, a.emotion,
                                       a.piper_voice if a.engine == "piper" else None, line]).encode()).hexdigest()[:8]
        p = os.path.join(takes_dir, f"t{i:02d}_{key}.wav")
        cached = os.path.exists(p)
        if not cached:
            take(line, p, a)
        s, e = speech_bounds(p)
        takes.append({"n": i, "text": line, "file": os.path.relpath(p, out_dir), "trim": [round(s, 3), round(e, 3)]})
        print(f"  t{i:02d} {e - s:5.2f}s {len(line.split()):3d} words{'  (cached)' if cached else ''}", flush=True)

    # trim each take to its speech, butt them together with a fixed gap, 48 kHz mono
    with tempfile.TemporaryDirectory(dir=out_dir) as td:
        parts, gap = [], os.path.join(td, "gap.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", str(a.gap), gap], check=True)
        for t in takes:
            q = os.path.join(td, f"{t['n']:02d}.wav")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(out_dir, t["file"]), "-af",
                            f"atrim={t['trim'][0]}:{t['trim'][1]},asetpts=PTS-STARTPTS,afade=t=in:d=0.01,afade=t=out:st={t['trim'][1] - t['trim'][0] - 0.02:.3f}:d=0.02",
                            "-ar", "48000", "-ac", "1", q], check=True)
            parts += [q, gap]
        lst = os.path.join(td, "list.txt")
        open(lst, "w").write("".join(f"file '{p.replace(os.sep, '/')}'\n" for p in parts[:-1]))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-ar", "48000", "-ac", "1",
                        "-c:a", "pcm_s16le", a.out], check=True)
    words = sum(len(t["text"].split()) for t in takes)
    d = dur(a.out)
    json.dump({"engine": a.engine, "model": a.model, "voice": a.voice, "language": a.language, "speed": a.speed,
               "emotion": a.emotion, "gap": a.gap, "takes": takes, "duration": round(d, 2)},
              open(os.path.join(out_dir, "takes.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=True)
    print(f"-> {a.out}: {d:.2f} s, {words} words, ~{words / d:.2f} words/s (reference 3.5-4.1)")


if __name__ == "__main__":
    main()
