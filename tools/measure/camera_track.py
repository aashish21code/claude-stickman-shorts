# Step 3: frames dir -> camera_track.csv (per-frame dx, dy in px at the frames' width) + a summary.
# Subpixel phase correlation (cv2.phaseCorrelate with a Hanning window) between consecutive frames.
#
# Why subpixel and no dead-zone: the first reference study thresholded small shifts away and
# reported "camera holds ~80 % of frames"; the corrected finding was that the camera is moving in
# ~65 % of frames, pushing in slowly at 0.15-0.35 %/frame. A slow push-in is a fraction of a pixel a
# frame, so the tracker keeps every shift and the summary reports slow drift as its own class
# instead of calling it "still".
#
# Phase correlation measures translation only. A pure push-in (zoom) shows up as near-zero dx/dy
# with a falling response, so the scale change is estimated separately from the log-polar
# correlation of the two frames (zoom_pct column).
#
# Usage: python camera_track.py --frames <frames dir> [--still 0.5] [--width 360]
import argparse, csv, json, os, sys
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import frame_fps, frames_in, load


ZOOM_STRIDE = 4


def zoom_pct(a, b):
    """Scale change between two gray frames, % per frame (+ = pushing in), via log-polar phase correlation."""
    h, w = a.shape
    c = (w / 2, h / 2)
    r = min(w, h) / 2
    K = w / np.log(r)                      # warpPolar log mode: x = K * ln(radius)
    hw = np.outer(np.hanning(h), np.hanning(w))
    fa = np.log1p(np.abs(np.fft.fftshift(np.fft.fft2(a * hw)))).astype(np.float32)
    fb = np.log1p(np.abs(np.fft.fftshift(np.fft.fft2(b * hw)))).astype(np.float32)
    flags = cv2.INTER_LINEAR + cv2.WARP_FILL_OUTLIERS + cv2.WARP_POLAR_LOG   # cv2.logPolar is gone in 4.x
    la = cv2.warpPolar(fa, (w, h), c, r, flags)
    lb = cv2.warpPolar(fb, (w, h), c, r, flags)
    (sx, _), _ = cv2.phaseCorrelate(la, lb)
    # a zoom in the image is the inverse scale in its spectrum
    return (np.exp(-sx / K) - 1.0) * 100.0


def track(frames_dir, still=0.5, width=360, out=None):
    fs = frames_in(frames_dir)
    fps = frame_fps(frames_dir)
    full_w = load(fs[0]).shape[1]
    k = full_w / width                       # report shifts at the frames' own width
    out = out or os.path.dirname(os.path.abspath(frames_dir))
    prev = load(fs[0], width, gray=True)
    win = cv2.createHanningWindow(prev.shape[::-1], cv2.CV_32F)
    rows, hist = [], [prev]
    for i, p in enumerate(fs[1:], 1):
        cur = load(p, width, gray=True)
        (dx, dy), resp = cv2.phaseCorrelate(prev, cur, win)
        # Zoom over a ZOOM_STRIDE-frame span, divided back to per-frame: a 0.25 %/frame push-in is a
        # third of a pixel in log-polar space frame to frame and reads ~40 % low (synthetic test,
        # 4 Nov 2026); over 4 frames it reads within ~10 %.
        hist = (hist + [cur])[-(ZOOM_STRIDE + 1):]
        z = zoom_pct(hist[0], cur) / (len(hist) - 1) if resp > 0.05 else 0.0
        rows.append({"frame": i, "t": round(i / fps, 3), "dx": round(dx * k, 3), "dy": round(dy * k, 3),
                     "mag": round(float(np.hypot(dx, dy) * k), 3), "zoom_pct": round(float(z), 4),
                     "response": round(float(resp), 4)})
        prev = cur
        if i % 300 == 0:
            print(f"  track: {i}/{len(fs) - 1}", flush=True)
    path = os.path.join(out, "camera_track.csv")
    with open(path, "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]))
        wr.writeheader(); wr.writerows(rows)

    # Low response = the frames barely match (a cut, a flash, a whip): not camera motion.
    ok = [r for r in rows if r["response"] >= 0.1]
    mag = np.array([r["mag"] for r in ok]); zm = np.abs([r["zoom_pct"] for r in ok])
    moving = (mag >= still) | (zm >= 0.15)
    drift = (~moving) & ((mag >= 0.05) | (zm >= 0.05))
    runs, n = [], 0
    for m in moving:
        if m: n += 1
        elif n: runs.append(n); n = 0
    if n: runs.append(n)
    s = {"frames": len(rows), "tracked": len(ok), "width_px": full_w, "fps": fps,
         "still_threshold_px": still,
         "pct_still": round(100 * float((~moving & ~drift).mean()), 1) if len(ok) else None,
         "pct_slow_drift": round(100 * float(drift.mean()), 1) if len(ok) else None,
         "pct_moving": round(100 * float(moving.mean()), 1) if len(ok) else None,
         "pct_moving_incl_drift": round(100 * float((moving | drift).mean()), 1) if len(ok) else None,
         "median_glide_frames": float(np.median(runs)) if runs else 0,
         "glides": len(runs),
         "peak_px_per_frame": round(float(mag.max()), 2) if len(mag) else 0,
         "median_moving_px_per_frame": round(float(np.median(mag[moving])), 3) if moving.any() else 0}
    json.dump(s, open(os.path.join(out, "camera_summary.json"), "w"), indent=1)
    print(f"  track: still {s['pct_still']}%, slow drift {s['pct_slow_drift']}%, moving {s['pct_moving']}%, "
          f"median glide {s['median_glide_frames']} f -> {path}")
    return s


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Per-frame camera motion by subpixel phase correlation.")
    ap.add_argument("--frames", required=True, help="frames dir from extract_frames.py")
    ap.add_argument("--still", type=float, default=0.5, help="px/frame (at the frames' width) below which a frame is not 'moving' (default 0.5)")
    ap.add_argument("--width", type=int, default=360, help="analysis width; shifts are rescaled to the frames' width (default 360)")
    ap.add_argument("--out", help="default: the folder holding the frames dir")
    a = ap.parse_args()
    track(a.frames, a.still, a.width, a.out)
