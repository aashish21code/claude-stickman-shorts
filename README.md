# claude-stickman-shorts

Claude Code skills and tools for making short vertical videos with stick figures and cartoon characters:

- **Stickman Video Director** (`.claude/skills/directing-stickman-videos/`) -- turns a piece of copy into
  a director's proposal and a set of ~10 s clip prompts for a video model, with styles, a storyboard
  template and voice continuity.
- **Cartoon-3D Shorts** (`.claude/skills/cartoon-3d-shorts/`) -- 55-70 s animated story Shorts with 2D
  bean-head characters in a colourful 3D world, rendered with three.js inside Remotion on your own PC,
  no AI video generator. Built on [mromidev/claude-animated-shorts](https://github.com/mromidev/claude-animated-shorts);
  this repo adds the pieces it does not ship.

## What is in here

| path | what |
|---|---|
| `.claude/skills/` | the two skills; Claude Code picks them up when you open this folder |
| `tools/measure/` | measure reference Shorts instead of eyeballing them: frames, contact sheets, subpixel camera tracking, cut and flash detection, colour stats, pace and dead air, and a style-bible draft with the numbers filled in |
| `tools/voice/` | script -> `voice.wav` (Cartesia, or offline Piper) -> word timings `words.json` -> a timing QA report |
| `scaffold/` | a runnable Remotion + three.js project with pinned versions, a Windows setup script that ends in a rendered smoke-test still, the Kenney model fetcher, patches for the upstream template, and extra looks (interior, lamp, night) |

## Quick start (Windows)

You need Node 18+, Python 3, ffmpeg and Google Chrome.

```powershell
git clone https://github.com/aashish21code/claude-stickman-shorts
cd claude-stickman-shorts
git clone --depth 1 https://github.com/mromidev/claude-animated-shorts upstream
pip install -r tools/measure/requirements.txt
cd scaffold
.\setup.ps1 -RepoPath ..\upstream -TempDrive D:\remotion-tmp
```

`setup.ps1` ends with `SMOKE TEST OK` and a still of the upstream demo short. Then open the folder in
Claude Code and ask for a short: *"Use the cartoon-3d-shorts skill and make a short about ..."*.

For the voice tools, set `CARTESIA_API_KEY` (or use `--engine piper`). See `tools/voice/README.md`.

## Ground rules

- Story, characters and voice are always your own. Reference videos are for measuring the look only:
  keep them in `refs/` (gitignored), never upload or redistribute them, never copy their scripts or shots.
- Media and build output are gitignored; this repo is code and docs only.

## License

MIT for the code and docs in this repo (`LICENSE`). Third-party parts and their licenses:
`THIRD_PARTY_NOTICES.md`.
