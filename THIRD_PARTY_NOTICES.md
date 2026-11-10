# Third-party notices

| what | where | license |
|---|---|---|
| **Stickman Video Director** skill | `.claude/skills/directing-stickman-videos/` (included unchanged) | MIT, Copyright (c) 2026 Stickman Video Director contributors -- full text in that folder's `LICENSE` |
| **claude-animated-shorts** by Mr omi | not included; cloned by you into `upstream/` (`scaffold/setup.ps1` copies its `templates/` into the gitignored `scaffold/src/videos/bridge/` and `scaffold/scripts/`). `scaffold/engine/looks.ts` uses its types and extends its light and grade presets; `scaffold/patches/apply.mjs` edits the copy | MIT, Copyright (c) 2026 Mr omi -- https://github.com/mromidev/claude-animated-shorts |
| **Kenney** Nature Kit and Fantasy Town Kit | not included; downloaded by `scaffold/fetch-kenney.ps1` from https://kenney.nl | CC0 |
| Remotion, three.js, React and the other npm packages | installed by `npm install` from `scaffold/package.json` | each package's own license; note that Remotion has its own license terms for companies -- https://www.remotion.dev/license |
