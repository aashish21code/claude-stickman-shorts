# Step 6: video -> script_stats.json: words/sec, dead air (word gaps > 0.25 s), the first sentence
# (the hook candidate), count of the pivot phrase ("you see"), sentence count and median sentence
# length. Targets from STYLE_BIBLE.md: 3.5-4.1 words/s, dead air < 1 s per video.
#
# Transcription is faster-whisper with word timestamps. When it cannot run -- the package or the
# model is missing, or (as on 4 Nov 2026) the network is too slow to fetch a 1.6 GB model -- the
# script still reports what the audio alone can say: speech span and dead air from silencedetect.
# words_per_sec is then null and "asr" says why, so a summary never shows an invented number.
#
# Usage: python script_analyze.py --input clip.mp4 [--language en] [--model small] [--no-asr]
import argparse, json, os, re, subprocess, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import measurements_dir, stem

PIVOTS = {"en": ["you see"], "hi": ["dekho", "samjho", "asal mein", "darasal"]}


def silences(video, db=-35, d=0.25):
    err = subprocess.run(["ffmpeg", "-i", video, "-vn", "-af", f"silencedetect=n={db}dB:d={d}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", err)]
    en = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", err)]
    m = re.search(r"Duration: (\d+):(\d+):([0-9.]+)", err)
    total = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 0.0
    return list(zip(st, en + [total] * (len(st) - len(en)))), total


def pcm16k(path):
    # faster-whisper 1.2.1 decodes through PyAV with av.open(..., metadata_errors=...), an argument
    # PyAV 18 removed (TypeError on this machine, 5 Nov 2026). ffmpeg decodes the same 16 kHz mono
    # float32 whisper wants, whatever the av version.
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def transcribe(video, language, model_name, download_root):
    from faster_whisper import WhisperModel
    model = WhisperModel(model_name, device="cpu", compute_type="int8", download_root=download_root)
    segs, info = model.transcribe(pcm16k(video), language=language, word_timestamps=True, vad_filter=False)
    words = [{"w": w.word.strip(), "s": round(float(w.start), 3), "e": round(float(w.end), 3)} for s in segs for w in s.words]
    return [w for w in words if w["w"]], info.language


def analyze(video, out=None, language="en", model="small", asr=True, gap=0.25, download_root=None):
    out = out or os.path.join(measurements_dir(video), stem(video))
    os.makedirs(out, exist_ok=True)
    sil, total = silences(video)
    lead = sil[0][1] if sil and sil[0][0] < 0.05 else 0.0
    tail = sil[-1][0] if sil and sil[-1][1] >= total - 0.05 else total
    s = {"video": os.path.basename(video), "duration_s": round(total, 2), "voice_starts_s": round(lead, 2),
         "language": language, "asr": None, "words": None, "words_per_sec": None,
         "dead_air_s": None, "first_sentence": None, "pivot_count": None,
         "sentences": None, "median_sentence_words": None,
         "dead_air_from_silence_s": round(sum(b - a for a, b in sil if a > lead + 0.01 and b < tail - 0.01), 2)}
    words = None
    if asr:
        try:
            words, lang = transcribe(video, language, model, download_root)
            s["asr"] = f"faster-whisper {model} ({lang})"
        except Exception as e:      # missing package/model, no network: report it, never guess
            s["asr"] = f"unavailable: {type(e).__name__}: {str(e)[:160]}"
    else:
        s["asr"] = "skipped (--no-asr)"
    if words:
        json.dump(words, open(os.path.join(out, "words.json"), "w", encoding="utf-8"), indent=0, ensure_ascii=False)
        span = words[-1]["e"] - words[0]["s"]
        gaps = [b["s"] - a["e"] for a, b in zip(words, words[1:])]
        text = " ".join(w["w"] for w in words)
        sents = [x.strip() for x in re.split(r"(?<=[.!?।])\s+", text) if x.strip()]
        lens = [len(x.split()) for x in sents]
        low = text.lower()
        s.update({"words": len(words), "words_per_sec": round(len(words) / span, 2) if span else None,
                  "dead_air_s": round(sum(g for g in gaps if g > gap), 2),
                  "longest_gap_s": round(max(gaps), 2) if gaps else 0,
                  "voice_starts_s": words[0]["s"],
                  "first_sentence": sents[0] if sents else None,
                  "pivot_count": sum(low.count(p) for p in PIVOTS.get(language, PIVOTS["en"])),
                  "sentences": len(sents), "median_sentence_words": float(np.median(lens)) if lens else None,
                  "transcript": text})
    s["in_target"] = {"words_per_sec": s["words_per_sec"] is not None and 3.5 <= s["words_per_sec"] <= 4.1,
                      "dead_air": (s["dead_air_s"] if s["dead_air_s"] is not None else s["dead_air_from_silence_s"]) < 1.0}
    json.dump(s, open(os.path.join(out, "script_stats.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=True)
    wps = s["words_per_sec"] if s["words_per_sec"] is not None else "n/a"
    print(f"  script: {wps} words/s, dead air {s['dead_air_s'] if s['dead_air_s'] is not None else s['dead_air_from_silence_s']} s, "
          f"asr: {s['asr'][:60]}")
    return s


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Narration pace, dead air, hook and pivot from a video's audio.")
    ap.add_argument("--input", required=True, help="video file")
    ap.add_argument("--out", help="default: measurements/<video name>/ next to the video")
    ap.add_argument("--language", default="en", help="whisper language code (default en; hi for Hindi)")
    ap.add_argument("--model", default="small", help="faster-whisper model (default small; large-v3-turbo is better and 1.6 GB)")
    ap.add_argument("--model-dir", help="where models are cached (default: faster-whisper's own cache)")
    ap.add_argument("--no-asr", action="store_true", help="skip transcription; report silence-based dead air only")
    a = ap.parse_args()
    analyze(a.input, a.out, a.language, a.model, not a.no_asr, download_root=a.model_dir)
