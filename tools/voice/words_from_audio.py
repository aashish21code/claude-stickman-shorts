# Step 3b: voice.wav -> words.json in the exact schema upstream templates/audio/mix.py reads:
#   [{"s": start_seconds, "e": end_seconds, "w": "word"}, ...]
# (mix.py speech_spans() reads float(w["s"]) and float(w["e"]); "w" is for people and story.ts.)
#
# faster-whisper with word_timestamps=True. If --text is given, whisper's words are snapped to the
# script's own words (Needleman-Wunsch, `align()` below) so words.json carries the script's
# spelling, not whisper's guesses. If whisper cannot run and --text is given, words are timed from
# the audio's pauses instead (snapped to punctuation, spread by length) -- good enough for cuts and
# captions when the whisper model will not download.
#
# Then it checks the pace against STYLE_BIBLE (3.5-4.1 words/s, dead air < 1 s) and warns.
#
# Usage: python words_from_audio.py --audio voice/voice.wav [--text script.txt] [--language en] [--model small]
import argparse, difflib, json, os, re, subprocess, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
from timing_qa import qa, report

PUNCT = (",", ".", "...", "?", "!", ";", ":", "।")


def pcm16k(path):
    # faster-whisper 1.2.1 decodes through PyAV with av.open(..., metadata_errors=...), an argument
    # PyAV 18 removed (TypeError). ffmpeg decodes the same 16 kHz mono
    # float32 whisper wants, whatever the av version.
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def whisper_words(audio, language, model, model_dir, prompt=None):
    from faster_whisper import WhisperModel
    m = WhisperModel(model, device="cpu", compute_type="int8", download_root=model_dir)
    segs, _ = m.transcribe(pcm16k(audio), language=language, word_timestamps=True, initial_prompt=prompt)
    return [{"w": w.word.strip(), "s": float(w.start), "e": float(w.end)} for s in segs for w in s.words if w.word.strip()]


def norm(w):
    """lower-case letters and digits only, so "Bridge," and "bridge" compare equal"""
    return "".join(c for c in unicodedata.normalize("NFC", w).lower() if c.isalnum())


def align(script, asr, gap=-0.55, floor=0.42):
    """Needleman-Wunsch over two word lists -> {script index: asr index}.

    Similarity is difflib's ratio minus `floor`, so a weak resemblance scores negative and the alignment
    prefers a gap over a bad pairing: one misheard name cannot drag a whole paragraph out of place.
    """
    n, m = len(script), len(asr)
    if not n or not m:
        return {}
    sim = lambda a, b: (1.0 if a == b else difflib.SequenceMatcher(None, a, b).ratio()) - floor
    S = [[0.0] * (m + 1) for _ in range(n + 1)]
    B = [[0] * (m + 1) for _ in range(n + 1)]  # 0 = pair, 1 = skip a script word, 2 = skip an asr word
    for i in range(1, n + 1):
        S[i][0], B[i][0] = gap * i, 1
    for j in range(1, m + 1):
        S[0][j], B[0][j] = gap * j, 2
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            opts = (S[i - 1][j - 1] + sim(script[i - 1], asr[j - 1]), S[i - 1][j] + gap, S[i][j - 1] + gap)
            k = max(range(3), key=opts.__getitem__)
            S[i][j], B[i][j] = opts[k], k
    pair, i, j = {}, n, m
    while i > 0 and j > 0:
        if B[i][j] == 0:
            if sim(script[i - 1], asr[j - 1]) > 0:
                pair[i - 1] = j - 1
            i, j = i - 1, j - 1
        elif B[i][j] == 1:
            i -= 1
        else:
            j -= 1
    return pair


def snap_to_script(asr, script_words):
    pair = align([norm(w) for w in script_words], [norm(a["w"]) for a in asr])
    s = [asr[pair[i]]["s"] if i in pair else None for i in range(len(script_words))]
    e = [asr[pair[i]]["e"] if i in pair else None for i in range(len(script_words))]
    t0, t1 = asr[0]["s"], asr[-1]["e"]
    known = [(-1, t0)] + [(i, x) for i, x in enumerate(s) if x is not None] + [(len(script_words), t1)]
    for (ia, ta), (ib, tb) in zip(known, known[1:]):
        for k in range(ia + 1, ib):
            s[k] = ta + (tb - ta) * (k - ia) / (ib - ia)
    out = []
    for i, w in enumerate(script_words):
        nxt = s[i + 1] if i + 1 < len(script_words) else t1
        end = e[i] if e[i] is not None and e[i] <= nxt else nxt
        out.append({"s": round(s[i], 3), "e": round(max(end, s[i] + 0.06), 3), "w": w})
    return out, len(pair)


def pause_words(audio, script_words, db=-38):
    err = subprocess.run(["ffmpeg", "-i", audio, "-af", f"silencedetect=n={db}dB:d=0.12", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", err)]
    en = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", err)]
    m = re.search(r"Duration: (\d+):(\d+):([0-9.]+)", err)
    total = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    sil = list(zip(st, en + [total] * (len(st) - len(en))))
    on = sil[0][1] if sil and sil[0][0] < 0.05 else 0.0
    off = sil[-1][0] if sil and sil[-1][1] >= total - 0.05 else total
    inner = [(a, b) for a, b in sil if a > on + 0.05 and b < off - 0.05]
    wt = [len(re.sub(r"[^\w]", "", w)) + 1.5 for w in script_words]
    cum = [sum(wt[:i]) / sum(wt) for i in range(len(wt) + 1)]
    bounds = [i + 1 for i, w in enumerate(script_words[:-1]) if w.endswith(PUNCT)]
    speech = (off - on) - sum(b - a for a, b in inner)
    anchors, last = {0: (None, on), len(script_words): (off, None)}, 0
    for a, b in inner:                       # pauses in time order...
        frac = ((a - on) - sum(y - x for x, y in inner if y <= a)) / speech
        # ...may only take a boundary AFTER the previous pause's: without this a later pause can land
        # on an earlier comma and the words between run backwards in time (seen on the first test)
        best = min((k for k in bounds if k > last), key=lambda k: abs(cum[k] - frac), default=None)
        if best is not None and abs(cum[best] - frac) < 0.18:
            anchors[best] = (a, b); last = best
    s = [0.0] * len(script_words)
    keys = sorted(anchors)
    for ka, kb in zip(keys, keys[1:]):
        x0, x1, span = anchors[ka][1], anchors[kb][0], sum(wt[ka:kb])
        for i in range(ka, kb):
            s[i] = x0; x0 += (x1 - anchors[ka][1]) * wt[i] / span
    out = []
    for i, w in enumerate(script_words):
        nxt = anchors.get(i + 1)
        end = nxt[0] if nxt and nxt[0] is not None else (s[i + 1] if i + 1 < len(s) else off)
        out.append({"s": round(s[i], 3), "e": round(end, 3), "w": w})
    return out


def main():
    ap = argparse.ArgumentParser(description="voice.wav -> words.json ([{s, e, w}]) + a pace check.")
    ap.add_argument("--audio", required=True)
    ap.add_argument("--text", help="the script; when given, words.json uses its spelling, and enables the no-whisper fallback")
    ap.add_argument("--out", help="default: words.json next to the audio")
    ap.add_argument("--language", default="en")
    ap.add_argument("--model", default="small", help="faster-whisper model (default small)")
    ap.add_argument("--model-dir", default=os.path.join(ROOT, "models", "faster-whisper"))
    ap.add_argument("--no-whisper", action="store_true", help="use the pause-based fallback (needs --text)")
    a = ap.parse_args()
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.audio)), "words.json")
    script = None
    if a.text:
        script = " ".join(l.strip() for l in open(a.text, encoding="utf-8") if l.strip() and not l.lstrip().startswith("#")).split()
    words, how = None, None
    if not a.no_whisper:
        try:
            asr = whisper_words(a.audio, a.language, a.model, a.model_dir, " ".join(script) if script else None)
            if script:
                words, n = snap_to_script(asr, script); how = f"whisper {a.model}, snapped to script ({n}/{len(script)} matched)"
            else:
                words = [{"s": round(w["s"], 3), "e": round(w["e"], 3), "w": w["w"]} for w in asr]; how = f"whisper {a.model}"
        except Exception as e:
            print(f"  whisper unavailable ({type(e).__name__}: {str(e)[:120]})")
    if words is None:
        if not script:
            raise SystemExit("no whisper and no --text: nothing to time. Pass --text script.txt for the pause-based fallback.")
        words = pause_words(a.audio, script); how = "pause-based fallback (no whisper): hand-check with timing_qa.py"
    json.dump(words, open(out, "w", encoding="utf-8"), indent=0, ensure_ascii=False)
    print(f"-> {out}: {len(words)} words ({how})")
    print(report(qa(words)))


if __name__ == "__main__":
    main()
