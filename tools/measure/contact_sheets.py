# Step 2: frames dir -> one contact sheet per 2 s of video (60 frames at 30 fps, 10 cols x 6 rows),
# each cell labelled with its frame number and timecode. This is the "549 sheets" step: a person or
# an agent reads motion, cuts and flashes off a sheet far faster than off the video.
# Usage: python contact_sheets.py --frames <frames dir> [--out <dir>] [--per 60] [--cols 10] [--cell 108]
import argparse, os, sys
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import frame_fps, frames_in, tc


def sheets(frames_dir, out=None, per=60, cols=10, cell_w=108):
    fs = frames_in(frames_dir)
    fps = frame_fps(frames_dir)
    out = out or os.path.join(os.path.dirname(os.path.abspath(frames_dir)), "sheets")
    os.makedirs(out, exist_ok=True)
    w0, h0 = Image.open(fs[0]).size
    cw, ch = cell_w, round(cell_w * h0 / w0)
    rows = -(-per // cols)
    written = []
    for k in range(0, len(fs), per):
        S = Image.new("RGB", (cw * cols, ch * rows), "black")
        d = ImageDraw.Draw(S)
        for j, p in enumerate(fs[k:k + per]):
            x, y = (j % cols) * cw, (j // cols) * ch
            S.paste(Image.open(p).convert("RGB").resize((cw, ch), Image.BOX), (x, y))
            label = f"{k + j} {tc(k + j, fps)}"
            d.rectangle([x, y, x + 6 * len(label) + 4, y + 12], fill="black")
            d.text((x + 2, y + 1), label, fill="yellow")
        p = os.path.join(out, f"s{k // per + 1:03d}_{tc(k, fps).replace(':', 'm')}.jpg")
        S.save(p, quality=85)
        written.append(p)
    print(f"  sheets: {len(written)} x {per} frames -> {out}")
    return written


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Contact sheets, one per 2 s of video, labelled with timecodes.")
    ap.add_argument("--frames", required=True, help="frames dir from extract_frames.py")
    ap.add_argument("--out", help="default: sheets/ beside the frames dir")
    ap.add_argument("--per", type=int, default=60, help="frames per sheet (default 60 = 2 s at 30 fps)")
    ap.add_argument("--cols", type=int, default=10)
    ap.add_argument("--cell", type=int, default=108, help="cell width in px (default 108)")
    a = ap.parse_args()
    sheets(a.frames, a.out, a.per, a.cols, a.cell)
