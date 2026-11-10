# Step 5: frames dir -> color_stats.json, per-video medians of the per-frame luma mean / std / p2 / p98
# and saturation mean (targets in STYLE_BIBLE.md: luma mean 0.43-0.54, std 0.21-0.29, p2 0.03-0.11,
# p98 0.9-1.0, saturation 0.38-0.65). Same definitions as templates/scripts/short_qa.py, so your renders
# and the references are measured identically.
#
# Burned-in captions (one white bold word with a black outline at ~60-74 % of the height) would pull
# p98 up and saturation down, so that band is masked by default (--no-mask to keep it).
#
# Usage: python color_stats.py --frames <frames dir> [--every 3] [--no-mask]
import argparse, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import LUMA, frames_in, load

TARGETS = {"luma_mean": (0.43, 0.54), "luma_std": (0.21, 0.29), "p2": (0.03, 0.11), "p98": (0.90, 1.00),
           "sat_mean": (0.38, 0.65)}


def stats(frames_dir, every=3, width=270, mask=(0.60, 0.74), out=None):
    fs = frames_in(frames_dir)[::every]
    out = out or os.path.dirname(os.path.abspath(frames_dir))
    per = {k: [] for k in TARGETS}
    for p in fs:
        f = load(p, width)
        if mask:
            h = f.shape[0]
            f = np.concatenate([f[:int(h * mask[0])], f[int(h * mask[1]):]])
        px = f.reshape(-1, 3)
        L = px @ LUMA
        mx, mn = px.max(1), px.min(1)
        sat = np.where(mx > 0.06, (mx - mn) / np.maximum(mx, 1e-6), 0)
        per["luma_mean"].append(L.mean()); per["luma_std"].append(L.std())
        per["p2"].append(np.percentile(L, 2)); per["p98"].append(np.percentile(L, 98))
        per["sat_mean"].append(sat.mean())
    med = {k: round(float(np.median(v)), 3) for k, v in per.items()}
    s = {"frames_sampled": len(fs), "every": every, "caption_band_masked": list(mask) if mask else None,
         "median": med,
         "in_target": {k: TARGETS[k][0] <= med[k] <= TARGETS[k][1] for k in TARGETS},
         "targets": TARGETS}
    json.dump(s, open(os.path.join(out, "color_stats.json"), "w"), indent=1)
    print("  color: " + ", ".join(f"{k} {v}{'' if s['in_target'][k] else ' (off target)'}" for k, v in med.items()))
    return s


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Per-video median luma / contrast / saturation stats.")
    ap.add_argument("--frames", required=True, help="frames dir from extract_frames.py")
    ap.add_argument("--every", type=int, default=3, help="sample every Nth frame (default 3)")
    ap.add_argument("--no-mask", action="store_true", help="do not mask the caption band (60-74 %% height)")
    ap.add_argument("--out", help="default: the folder holding the frames dir")
    a = ap.parse_args()
    stats(a.frames, a.every, mask=None if a.no_mask else (0.60, 0.74), out=a.out)
