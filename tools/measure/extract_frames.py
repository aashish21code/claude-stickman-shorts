# Step 1: video -> every frame as a JPG (f000001.jpg ...), plus frames.json with the fps and source.
# Usage: python extract_frames.py --input clip.mp4 [--outdir measurements/<clip>/frames] [--fps 30] [--width 720]
# 720 wide is the default because the reference study measured 720p downloads; pixel speeds in
# camera_track.py are reported at that width, so keep it unless you also rescale those targets.
import argparse, json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import measurements_dir, probe, stem


def extract(video, outdir=None, fps=30.0, width=720, quality=3):
    outdir = outdir or os.path.join(measurements_dir(video), stem(video), "frames")
    os.makedirs(outdir, exist_ok=True)
    info = probe(video)
    meta = os.path.join(outdir, "frames.json")
    done = os.path.exists(meta) and json.load(open(meta)).get("source_mtime") == os.path.getmtime(video)
    if done:
        print(f"  frames: up to date in {outdir}")
        return outdir
    for f in os.listdir(outdir):
        if f.startswith("f") and f.endswith((".jpg", ".png")):
            os.remove(os.path.join(outdir, f))
    vf = f"fps={fps},scale={width}:-2:flags=area" if width else f"fps={fps}"
    print(f"  frames: {os.path.basename(video)} {info['w']}x{info['h']} {info['fps']:.2f} fps "
          f"{info['duration']:.1f} s -> {fps:g} fps, {width or info['w']} wide", flush=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vf", vf, "-q:v", str(quality),
                    os.path.join(outdir, "f%06d.jpg")], check=True)
    n = len([f for f in os.listdir(outdir) if f.startswith("f") and f.endswith(".jpg")])
    json.dump({"source": os.path.abspath(video), "source_mtime": os.path.getmtime(video), "fps": fps,
               "width": width, "frames": n, "probe": info}, open(meta, "w"), indent=1)
    print(f"  frames: {n} written to {outdir}")
    return outdir


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Extract every frame of a video as JPGs for measurement.")
    ap.add_argument("--input", required=True, help="video file")
    ap.add_argument("--outdir", help="default: measurements/<video name>/frames next to the video")
    ap.add_argument("--fps", type=float, default=30.0, help="frames per second to extract (default 30)")
    ap.add_argument("--width", type=int, default=720, help="scale to this width, 0 = native (default 720)")
    a = ap.parse_args()
    extract(a.input, a.outdir, a.fps, a.width or None)
