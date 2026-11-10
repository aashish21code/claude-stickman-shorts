# Shared helpers for tools/measure: frame listing, loading, timecodes, ffprobe.
# Plain Python + numpy + Pillow (cv2 only where phase correlation needs it), ffmpeg on PATH.
import glob, json, os, re, subprocess
import numpy as np
from PIL import Image

LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)   # Rec.709 on sRGB values, same as short_qa.py


def frames_in(d):
    """Sorted frame paths in a dir written by extract_frames.py (f000001.jpg ...)."""
    fs = sorted(glob.glob(os.path.join(d, "f*.jpg")) + glob.glob(os.path.join(d, "f*.png")))
    if not fs:
        raise SystemExit(f"no frames in {d} (expected f000001.jpg ... from extract_frames.py)")
    return fs


def frame_fps(d, default=30.0):
    """The fps extract_frames.py recorded next to the frames, else `default`."""
    p = os.path.join(d, "frames.json")
    return float(json.load(open(p)).get("fps", default)) if os.path.exists(p) else default


def load(path, width=None, gray=False):
    """Frame as float32 0..1, optionally downscaled to `width` (area filter)."""
    im = Image.open(path).convert("L" if gray else "RGB")
    if width and im.width != width:
        im = im.resize((width, round(im.height * width / im.width)), Image.BOX)
    return np.asarray(im, np.float32) / 255.0


def tc(i, fps):
    """Frame index -> m:ss.ff timecode."""
    s = i / fps
    return f"{int(s // 60)}:{s % 60:05.2f}"


def probe(video):
    """{w, h, fps, duration, audio} from ffprobe."""
    pr = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate:format=duration",
         "-of", "json", video], capture_output=True, text=True).stdout or "{}")
    v = next((s for s in pr.get("streams", []) if s.get("codec_type") == "video"), {})
    num, den = (v.get("r_frame_rate") or "30/1").split("/")
    return {"w": v.get("width"), "h": v.get("height"), "fps": float(num) / float(den or 1),
            "duration": float(pr.get("format", {}).get("duration") or 0),
            "audio": any(s.get("codec_type") == "audio" for s in pr.get("streams", []))}


def stem(path):
    return re.sub(r"[^\w.-]+", "_", os.path.splitext(os.path.basename(path))[0])


def measurements_dir(near):
    """measurements/ next to the input (a video file or a folder of videos)."""
    base = near if os.path.isdir(near) else os.path.dirname(os.path.abspath(near))
    d = os.path.join(base, "measurements")
    os.makedirs(d, exist_ok=True)
    return d
