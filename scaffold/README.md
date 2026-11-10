# scaffold -- a working Remotion project for the cartoon-3D shorts (Windows first)

Upstream ([mromidev/claude-animated-shorts](https://github.com/mromidev/claude-animated-shorts)) ships
the bridge short's source (`templates/bridge/`) but no project to run it in. This is that project:
pinned packages, one composition, and a setup script that proves the toolchain by rendering a still.

```powershell
git clone --depth 1 https://github.com/mromidev/claude-animated-shorts upstream   # from the repo root, once
cd scaffold
.\setup.ps1 -RepoPath ..\upstream -TempDrive D:\remotion-tmp     # once; safe to re-run
```

It ends with `SMOKE TEST OK <path> <bytes>` -- a 540x960 still of the bridge short in about 10 s. The
run also fetches the Kenney models (step 5) and patches the copied template (step 4), so a still prints
no `404` lines; any `404` for `public/bridge/kenney/*.glb` means a model really is missing -- run
`.\fetch-kenney.ps1`.

## Which file is which

| file | what it is |
|---|---|
| `package.json` | the version set the bridge short rendered on (upstream `references/reports/CONTEXT.md`), each checked with `npm view`. `postprocessing@6.37.2` requires `three <0.176`, so three stays at 0.175 -- the latest three would break the post chain |
| `src/index.ts` | registers Root; a sandbox is a copy of this file with one import path changed |
| `src/Root.tsx` | `BridgeShort`, 1080x1920, 30 fps, length from `story.ts`; a commented block shows how to add your own short |
| `src/videos/bridge/` | a **copy** of `upstream/templates/bridge/` made by setup.ps1. Work on copies; the originals stay as they are |
| `scripts/` | a copy of `upstream/templates/scripts/` (stills, side-by-sides, merge, QA) |
| `public/bridge/kenney/` | the 26 Kenney CC0 `.glb` models `world.ts` loads, plus `Textures/colormap.png`. `world.ts` silently skips a missing one, so the town just looks empty |
| `fetch-kenney.ps1` | downloads Nature Kit + Fantasy Town Kit from kenney.nl into `../kenney/` (once), copies those models in; exits 1 naming any that are missing |
| `patches/apply.mjs` | fixes on top of the copied template, as exact old -> new edits (idempotent; errors if upstream moved). Today: the 6 TS2322 in `Bridge.tsx` -- type-only casts, same JS, same frames |
| `engine/looks.ts` | three extra looks (interior, lamp, night) -- see "Adding a look" below |
| `stills.mjs` | the still renderer with the composition as a parameter (`COMP=MyShort node stills.mjs out/x_ 100,400 0.5`) |
| `remotion.config.ts` | ANGLE GL, jpeg frames, one render at a time |
| `setup.ps1` | checks tools, installs, sets the temp folder, copies templates, renders the smoke still |

Topic, script and voice happen outside Remotion: `../tools/voice/` makes `voice.wav` and `words.json`.
Sound is `upstream/templates/audio/` (Python).

## Commands

```powershell
npm run studio                                                     # preview
node scripts/bridge-stills.mjs out/bridge/x_ 100,400 0.5           # look checks
npx remotion render src/index.ts BridgeShort out/bridge/video.mp4 --codec h264 --crf 16 --scale 1.3333
ffmpeg -i out/bridge/video.mp4 -i mix.wav -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac final.mp4   # Remotion writes a silent track
python scripts/short_qa.py final.mp4 out/bridge/qa shots.json      # frame-by-frame QA
```

## Adding a look

Upstream has two lights, `day` and `golden`, both for an open-air town. For a room or a night scene,
copy `engine/looks.ts` into your video folder and register the look in four places:

1. `story.ts` -- widen `export type Light = "day" | "golden"` with the look's name, and set `light:` on the shots.
2. `lights.ts` -- add `EXTRA_LIGHTS.<name>` to `LIGHTS` and `EXTRA_LOOK.<name>` to `LOOK` (and widen their `Record` keys).
3. `grade.ts` -- add `EXTRA_GRADES.<name>` to `GRADES` and a strength (start at 1) to `GRADE_STRENGTH`; widen `gradeFor`'s parameter.
4. `world.ts` -- `cloudMaps` is built per light; build one for the new name too (indoors, reuse the day maps).

Run `npm run typecheck` -- the compiler lists anything still keyed on `"day" | "golden"` -- then a still,
then `tools/measure/color_stats.py` on the stills against your reference range.

## Windows notes

- **Disk.** Every bundle copies `public/` into TEMP and never deletes it; a few dozen bundles fill 60+ GB.
  `setup.ps1` sets `TEMP`, `TMP` and `REMOTION_TMP` to a big-drive folder for the session; set them
  again in any new shell before rendering, and clear `remotion-webpack-bundle-*` and
  `puppeteer_dev_chrome_profile-*` there when a short is finished.
- **Forward slashes in JS strings**: `"D:/remotion-tmp"`, never `"D:\remotion-tmp"` (`\r` is a carriage return).
- **R3F clamps dpr to >= 1**, so `--scale 0.5` stills still render a 1080x1920 buffer; every pixel
  parameter in the templates scales with output height / 1920.
- `scripts/bridge-stills.mjs` and `stills.mjs` render through `C:/Program Files/Google/Chrome/Application/chrome.exe`.
- **Windows PowerShell 5.1 and native stderr.** With output redirected, 5.1 wraps every stderr line
  of a native command in an error record, and under `$ErrorActionPreference = "Stop"` the first
  `npm warn` (or a Chrome console 404) ends the script. `setup.ps1` runs `npm install` and the still
  under `"Continue"` and judges them by `$LASTEXITCODE`; do the same in any script you add.
- **npm EBUSY on `esbuild.exe`** is antivirus holding the new binary during esbuild's postinstall --
  re-run `setup.ps1 -Refresh`.
- **Stopping a render** can leave its Chrome children alive and holding the temp profile; kill them by
  command line (`*puppeteer_dev_chrome_profile*`), never all of Chrome.

Nothing setup.ps1 copies or installs is committed (`../.gitignore`).
