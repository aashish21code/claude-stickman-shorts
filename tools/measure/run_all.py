# Step 7: a folder of reference videos -> every measurement, per video, plus
#   measurements/summary.json         one row per video
#   measurements/STYLE_BIBLE_DRAFT.md a skeleton style bible with the measured numbers filled in,
#                                     in the section order of upstream references/STYLE_BIBLE.md
# Re-running skips frame extraction for videos that have not changed.
#
# Usage: python run_all.py --videos <folder> [--language en] [--model small] [--no-asr] [--no-sheets]
import argparse, glob, json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import measurements_dir, probe, stem
from extract_frames import extract
from contact_sheets import sheets
from camera_track import track
from cut_detect import detect
from color_stats import stats
from script_analyze import analyze

VIDEO_EXT = (".mp4", ".webm", ".mkv", ".mov")


def med(rows, *path):
    v = []
    for r in rows:
        x = r
        for k in path:
            x = (x or {}).get(k) if isinstance(x, dict) else None
        if isinstance(x, (int, float)):
            v.append(x)
    return (round(float(np.median(v)), 3), round(float(min(v)), 3), round(float(max(v)), 3)) if v else (None, None, None)


def fmt(t, unit=""):
    m, lo, hi = t
    return "n/a" if m is None else f"{m}{unit} (range {lo}-{hi}{unit})"


def draft(rows, path, src):
    n = len(rows)
    first = [r["script"].get("first_sentence") for r in rows if r["script"].get("first_sentence")]
    pivots = sum(1 for r in rows if (r["script"].get("pivot_count") or 0) > 0)
    low_cut = sum(1 for r in rows if r["cuts"]["hard_cuts"] <= 1)
    L = []
    L += [f"# Style bible draft -- {n} videos measured ({time.strftime('%Y-%m-%d')})",
          f"Measured by tools/measure/run_all.py from `{src}`. Numbers only; read the contact sheets before writing the",
          "adjectives. Private study material: never upload, publish or send the videos, never copy their scripts or characters.", "",
          "## Format",
          f"- Vertical {fmt(med(rows, 'probe', 'w'))} x {fmt(med(rows, 'probe', 'h'))}, {fmt(med(rows, 'probe', 'fps'))} fps, "
          f"duration {fmt(med(rows, 'probe', 'duration'), ' s')}.",
          f"- Voice starts at {fmt(med(rows, 'script', 'voice_starts_s'), ' s')}.",
          f"- Pace: {fmt(med(rows, 'script', 'words_per_sec'), ' words/s')} (target 3.5-4.1).",
          f"- Dead air (word gaps > 0.25 s, total per video): {fmt(med(rows, 'script', 'dead_air_s'), ' s')}; "
          f"from silence alone: {fmt(med(rows, 'script', 'dead_air_from_silence_s'), ' s')} (target < 1 s).",
          "- Loudness / captions: measure the finished file with templates/scripts/short_qa.py; read captions off the sheets.", "",
          "## Script formula",
          f"- Sentences per video {fmt(med(rows, 'script', 'sentences'))}, median sentence {fmt(med(rows, 'script', 'median_sentence_words'), ' words')}.",
          f"- Pivot phrase present in {pivots}/{n} videos.",
          "- Hook candidates (first sentence of each video -- study the shape, never reuse the words):"]
    L += [f"  - {s}" for s in first[:20]] or ["  - (no transcripts: run without --no-asr once a whisper model is available)"]
    L += ["", "## Picture",
          f"- Luma mean {fmt(med(rows, 'color', 'median', 'luma_mean'))} (target 0.43-0.54), "
          f"std {fmt(med(rows, 'color', 'median', 'luma_std'))} (0.21-0.29).",
          f"- p2 {fmt(med(rows, 'color', 'median', 'p2'))} (0.03-0.11), p98 {fmt(med(rows, 'color', 'median', 'p98'))} (0.9-1.0).",
          f"- Saturation mean {fmt(med(rows, 'color', 'median', 'sat_mean'))} (0.38-0.65).", "",
          "## Camera / editing (measured)",
          f"- Hard cuts per video {fmt(med(rows, 'cuts', 'hard_cuts'))}; {low_cut}/{n} videos have 0-1 hard cuts. "
          f"Flashes per video {fmt(med(rows, 'cuts', 'flashes'))}.",
          f"- Camera still {fmt(med(rows, 'camera', 'pct_still'), ' %')}, slow drift {fmt(med(rows, 'camera', 'pct_slow_drift'), ' %')}, "
          f"moving {fmt(med(rows, 'camera', 'pct_moving'), ' %')} of frames "
          f"(moving incl. drift {fmt(med(rows, 'camera', 'pct_moving_incl_drift'), ' %')}).",
          f"- Median glide {fmt(med(rows, 'camera', 'median_glide_frames'), ' frames')}; "
          f"peak speed {fmt(med(rows, 'camera', 'peak_px_per_frame'), ' px/frame')} at the frames' width.", "",
          "## Effects", "- Not measurable by these scripts: list them from the contact sheets.", "",
          "## Per video", "| video | dur s | words/s | dead air s | cuts | flashes | still % | moving % | luma | sat |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        sc, c, cam, col = r["script"], r["cuts"], r["camera"], r["color"]["median"]
        L.append(f"| {r['video']} | {r['probe']['duration']:.1f} | {sc.get('words_per_sec') or 'n/a'} | "
                 f"{sc.get('dead_air_s') if sc.get('dead_air_s') is not None else sc.get('dead_air_from_silence_s')} | "
                 f"{c['hard_cuts']} | {c['flashes']} | {cam['pct_still']} | {cam['pct_moving']} | {col['luma_mean']} | {col['sat_mean']} |")
    open(path, "w", encoding="utf-8").write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser(description="Run every measurement on a folder of videos.")
    ap.add_argument("--videos", required=True, help="folder of reference videos")
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--width", type=int, default=720)
    ap.add_argument("--language", default="en")
    ap.add_argument("--model", default="small")
    ap.add_argument("--model-dir")
    ap.add_argument("--no-asr", action="store_true")
    ap.add_argument("--no-sheets", action="store_true", help="skip contact sheets (they are the slowest step)")
    a = ap.parse_args()
    vids = sorted(p for p in glob.glob(os.path.join(a.videos, "*")) if p.lower().endswith(VIDEO_EXT))
    if not vids:
        raise SystemExit(f"no videos ({', '.join(VIDEO_EXT)}) in {a.videos}")
    root = measurements_dir(a.videos)
    rows = []
    for i, v in enumerate(vids, 1):
        print(f"[{i}/{len(vids)}] {os.path.basename(v)}", flush=True)
        d = os.path.join(root, stem(v))
        fr = extract(v, os.path.join(d, "frames"), a.fps, a.width)
        if not a.no_sheets:
            sheets(fr, os.path.join(d, "sheets"))
        rows.append({"video": os.path.basename(v), "probe": probe(v),
                     "camera": track(fr, out=d), "cuts": detect(fr, out=d), "color": stats(fr, out=d),
                     "script": analyze(v, d, a.language, a.model, not a.no_asr, download_root=a.model_dir)})
        json.dump(rows, open(os.path.join(root, "summary.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=True)
    draft(rows, os.path.join(root, "STYLE_BIBLE_DRAFT.md"), a.videos)
    print(f"done: {len(rows)} videos -> {os.path.join(root, 'summary.json')} + STYLE_BIBLE_DRAFT.md")


if __name__ == "__main__":
    main()
