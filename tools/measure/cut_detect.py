# Step 4: frames dir -> cuts.csv, every hard cut (frame index + timestamp), by frame-difference thresholding.
#
# A frame is a cut when its mean absolute difference from the previous frame is both large in
# absolute terms (--thresh) and a spike against its neighbourhood (--k x the local median), so a
# fast whip pan does not read as a run of cuts. Flashes are separated out: the reference shorts use
# 4-frame white/colour flashes that a naive detector counts as two cuts each (STYLE_BIBLE: "most
# 'cuts' detected are 4-frame flash effects"). A spike whose frame returns to within --flash-match of
# the pre-spike frame inside --flash-len frames is a flash, not a cut. Dissolves are left alone:
# they are gradual and do not cross the spike test.
#
# Usage: python cut_detect.py --frames <frames dir> [--thresh 0.12] [--k 4] [--width 180]
import argparse, csv, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import frame_fps, frames_in, load, tc


def detect(frames_dir, thresh=0.12, k=4.0, width=180, flash_len=8, flash_match=0.06, out=None):
    fs = frames_in(frames_dir)
    fps = frame_fps(frames_dir)
    out = out or os.path.dirname(os.path.abspath(frames_dir))
    F = np.stack([load(p, width) for p in fs])
    # Normalise each frame to the same mean brightness before differencing: a cut made through a
    # dip (both sides faded to 35 %) otherwise differs by only a third as much and slips under the
    # threshold -- on a test short with faded cuts, a plain threshold found 1 of its 8.
    mean = F.mean(axis=(1, 2, 3), keepdims=True)
    N = np.clip(F * (0.45 / np.maximum(mean, 0.04)), 0, 1)
    diff = np.abs(np.diff(N, axis=0)).mean(axis=(1, 2, 3))      # diff[i] = frame i+1 vs frame i
    med = np.array([np.median(diff[max(0, i - 12):i + 13]) for i in range(len(diff))])
    spike = [i + 1 for i in range(len(diff)) if diff[i] > thresh and diff[i] > k * med[i] + 0.01]
    cuts, flashes, skip = [], [], set()
    for f in spike:
        if f in skip:
            continue
        back = next((j for j in range(f + 1, min(len(F), f + flash_len + 1))
                     if np.abs(F[j] - F[f - 1]).mean() < flash_match), None)
        if back is not None:
            flashes.append((f, back)); skip.update(range(f, back + 1))
        else:
            cuts.append(f)
    path = os.path.join(out, "cuts.csv")
    with open(path, "w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["frame", "t", "timecode", "diff", "kind"])
        for f in cuts:
            wr.writerow([f, round(f / fps, 3), tc(f, fps), round(float(diff[f - 1]), 4), "cut"])
        for a, b in flashes:
            wr.writerow([a, round(a / fps, 3), tc(a, fps), round(float(diff[a - 1]), 4), f"flash {b - a} f"])
    s = {"frames": len(fs), "fps": fps, "hard_cuts": len(cuts), "flashes": len(flashes),
         "cuts_per_min": round(len(cuts) / (len(fs) / fps / 60), 2),
         "mean_shot_s": round((len(fs) / fps) / (len(cuts) + 1), 2),
         "cut_frames": cuts, "flash_frames": [a for a, _ in flashes]}
    json.dump(s, open(os.path.join(out, "cuts_summary.json"), "w"), indent=1)
    print(f"  cuts: {len(cuts)} hard cuts, {len(flashes)} flashes -> {path}")
    return s


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Hard-cut detection by frame difference, with flashes separated out.")
    ap.add_argument("--frames", required=True, help="frames dir from extract_frames.py")
    ap.add_argument("--thresh", type=float, default=0.12, help="min mean abs RGB diff (0..1) for a cut (default 0.12)")
    ap.add_argument("--k", type=float, default=4.0, help="cut must also exceed k x local median diff (default 4)")
    ap.add_argument("--width", type=int, default=180, help="analysis width (default 180)")
    ap.add_argument("--flash-len", type=int, default=8, help="a spike that returns within this many frames is a flash")
    ap.add_argument("--flash-match", type=float, default=0.06, help="how close the return frame must be (mean abs diff)")
    ap.add_argument("--out", help="default: the folder holding the frames dir")
    a = ap.parse_args()
    detect(a.frames, a.thresh, a.k, a.width, a.flash_len, a.flash_match, a.out)
