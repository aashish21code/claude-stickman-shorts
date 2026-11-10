# tools/measure -- "make it measure, don't eyeball it"

The upstream skill ([mromidev/claude-animated-shorts](https://github.com/mromidev/claude-animated-shorts))
ships the *results* of its reference study (`references/STYLE_BIBLE.md`, `references/reports/*.md`,
the contact sheets) but not the tool that produced them. These scripts are that tool, rebuilt so it
runs on any folder of Shorts you want to study, and writes numbers instead of adjectives.

Python 3 + ffmpeg/ffprobe on PATH:

```bash
pip install -r tools/measure/requirements.txt
```

| script | in -> out | what it answers |
|---|---|---|
| `extract_frames.py` | video -> `frames/f000001.jpg ...` + `frames.json` | every frame at 30 fps, 720 wide (the width the reference study used) |
| `contact_sheets.py` | frames -> `sheets/sNNN_*.jpg` | one sheet per 2 s (60 frames, 10 x 6), frame number + timecode on each cell |
| `camera_track.py` | frames -> `camera_track.csv`, `camera_summary.json` | per-frame dx/dy by **subpixel** phase correlation plus a log-polar zoom estimate; % still / slow drift / moving, median glide length |
| `cut_detect.py` | frames -> `cuts.csv`, `cuts_summary.json` | hard cuts by frame difference, with 4-frame flashes separated out (they are not cuts) |
| `color_stats.py` | frames -> `color_stats.json` | per-video medians of luma mean / std / p2 / p98 and saturation, caption band masked; same definitions as upstream `templates/scripts/short_qa.py` |
| `script_analyze.py` | video -> `script_stats.json`, `words.json` | words/s, dead air (gaps > 0.25 s), first sentence (hook), pivot count, sentence stats -- faster-whisper word timestamps |
| `run_all.py` | folder -> `measurements/summary.json`, `measurements/STYLE_BIBLE_DRAFT.md` | all of the above for every video, and a style-bible skeleton with the numbers filled in |

Everything is written under `measurements/` next to the input (gitignored -- frames and sheets are media).

## One command

```bash
python tools/measure/run_all.py --videos refs/my-study --language en
```

Per script, on one video:

```bash
python tools/measure/extract_frames.py  --input  refs/my-study/01.mp4
python tools/measure/contact_sheets.py  --frames refs/my-study/measurements/01/frames
python tools/measure/camera_track.py    --frames refs/my-study/measurements/01/frames
python tools/measure/cut_detect.py      --frames refs/my-study/measurements/01/frames
python tools/measure/color_stats.py     --frames refs/my-study/measurements/01/frames
python tools/measure/script_analyze.py  --input  refs/my-study/01.mp4 --language en
```

## Choices worth knowing

- **Slow drift is not "still".** Thresholding small shifts away reports the camera holding ~80 % of
  frames; measured properly, it moves in ~65 %, pushing in at 0.15-0.35 %/frame. `camera_track.py`
  keeps every subpixel shift and reports three classes: still, slow drift, moving. A pure push-in has
  near-zero translation, so the zoom is measured separately (`zoom_pct`).
- **Flashes are not cuts.** A spike that comes back to the pre-spike frame within 8 frames is a flash.
- **No invented numbers.** If whisper cannot run (no model, no network), `script_analyze.py` still
  reports dead air from the audio's silences and leaves `words_per_sec` null with the reason in `asr`.
- **Captions are masked** (60-74 % of the height) before colour statistics, because a white word with a
  black outline would otherwise skew p98 and saturation.

## Reference videos

Study material only: keep them in `refs/` (gitignored). Never upload, publish or redistribute
someone else's videos, and never copy their scripts, characters or shots -- measure the look, make
your own story.
