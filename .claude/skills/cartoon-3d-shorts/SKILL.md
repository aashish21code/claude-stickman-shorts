---
name: cartoon-3d-shorts
description: "Use when making a 55-70 s vertical animated story Short in the cartoon-3D look -- 2D bean-head characters in a colourful 3D world, ink outlines, painted town, lens blur, gliding camera -- rendered with three.js inside Remotion on your own PC, no AI video generator. Covers measuring reference Shorts, the script formula, voice and word timings, the shot plan, look checks and the final render."
---

# Cartoon-3D Shorts

Built on [mromidev/claude-animated-shorts](https://github.com/mromidev/claude-animated-shorts) (MIT).
That repo is the engine and the full pipeline (`upstream/SKILL.md`); this skill adds what it does not
ship: the measuring tool, the voice tools, a runnable Remotion project and extra looks. Clone it once
next to this repo's tools:

```bash
git clone --depth 1 https://github.com/mromidev/claude-animated-shorts upstream
```

Read `upstream/SKILL.md` before the first short. The steps below say where each one runs here.

## Pipeline

1. **Topic + facts** -> `<short>/SCRIPT.md`, sources at the top. One surprising true story with a
   physical cause and effect, plus an everyday analogy. Every claim sourced; no listicles.
2. **Script**, 55-70 s, the beat formula: hook = the absurd fact in one sentence, setting,
   escalation, snap, "Luckily / Unluckily", one "You see," + analogy, consequence, callback.
   The voice starts on frame 0; no pause longer than half a second.
3. **Voice** -> `tools/voice/`: `tts.py` (Cartesia or offline Piper) -> `words_from_audio.py`
   -> `timing_qa.py`. Fix what the QA lists, re-run.
4. **Shot plan** -> copy `scaffold/src/videos/bridge/` to `scaffold/src/videos/<name>/`, register it in
   `scaffold/src/Root.tsx`, and time every shot in `story.ts` to `words.json`.
5-7. **World, characters, post** -> the copied template files (`world.ts`, `cast.ts`, `toon.ts`,
   `lights.ts`, `grade.ts`, ...). Indoors or at night, add a look from `scaffold/engine/looks.ts`
   (`scaffold/README.md`, "Adding a look").
8. **Sound** -> `upstream/templates/audio/` (synthesized SFX + score, ducked mix, loudness).
9. **Look checks** -> stills (`scaffold/stills.mjs` or `scripts/bridge-stills.mjs`), side-by-sides
   against reference frames (`scripts/sbs_sheet.py`), and `tools/measure/` on your own render: the
   same numbers as the reference.
10. **Final** -> `npx remotion render ... --scale 1.3333`, mux the mix, `scripts/short_qa.py`.

## Measure, don't eyeball

Before a style decision, measure a handful of reference Shorts with `tools/measure/run_all.py`:
camera motion (still / drift / moving), hard cuts, colour, pace and dead air. Typical numbers for
this style: 60-65 s, the camera moving in 75-88 % of frames, 0-3 hard cuts, 3.4-3.7 words/s,
longest pause under 0.5 s, one-word captions in the lower middle. Measure your own stills the same
way and compare numbers, not impressions.

References are study material only: never upload, publish or cut someone else's video into yours,
and never copy their scripts, characters, shots or name. Story, characters and voice are always your own.

## What held up across several shorts

- **Keep the camera moving.** Glides and slow push-ins on every shot, small impact kicks on the
  beats, idle sway and blinks on characters. A version with locked-off shots and hard cuts every few
  seconds read as a slideshow of pictures, not a video.
- **Pace the read at about 3.2 words/s overall.** Faster than ~3.7 sounds rushed on a story Short.
  If a voice ignores its speed setting, time-stretch the joined voice.wav, but not past ~1.4x. To slow
  a finished cut, retime the picture inside Remotion (sample frame `f / k`), not with ffmpeg -- an
  ffmpeg retime of moving shots judders.
- **Money and signs stay small and fully inside the frame**, with a margin. A big number goes in the
  caption flow, not on a prop the camera might crop.
- **The thumbnail is a frame of the final video**, captions included (`ffmpeg -ss <t> -i final.mp4
  -frames:v 1 thumb.jpg`), picked for the most engaging moment -- not a separate clean render.
- **Whisper can drop the first sentence** of a read (all its words stacked at one timestamp). Check
  the first line in `words.json`; if it is wrong, time it from `ffmpeg silencedetect` instead.
- **Ground boxes stay inside their own set's x range.** Two sets' floors overlapping z-fight and
  flicker in a glide.
- **One look pass at a time, verified on stills** (composition, light, characters, text inside the
  frame) before a full render: a still costs seconds, a 4K render costs most of an hour.

## Traps

- **yt-dlp without a JS runtime gets 360x640 only.** Install `deno` for 720p; 360p is still fine for
  camera, cuts and colour, not for line widths.
- **`cv2.logPolar` is gone in OpenCV 4.x/5.x** -- use `cv2.warpPolar(..., WARP_POLAR_LOG)`.
- **Slow push-ins read ~40 % low frame to frame**; measure zoom over 4 frames.
- **Cuts through a fade are missed** unless frames are normalised for brightness before differencing.
- **faster-whisper 1.2.1 + PyAV 18** fail with `unexpected keyword argument 'metadata_errors'`; the
  tools here decode with ffmpeg and hand whisper an array. Set `HF_HUB_OFFLINE=1` when the models
  are already cached and the network is slow.
- **`world.ts` swallows every model 404**, so a missing Kenney kit renders an empty town and nothing
  fails. `scaffold/fetch-kenney.ps1` fills it; kenney.nl answers 403 to curl's default user agent and
  hands out a signed link per page visit.
- **Remotion bundles fill the temp drive** (every bundle copies `public/`); point `REMOTION_TMP` at a
  big drive.
