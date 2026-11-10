# tools/voice -- script -> voice.wav -> words.json -> timing QA

Upstream SKILL.md step 3 says "record or generate `voice.wav`, then make its word timings
`words.json`, hand-fix them; everything is timed to words.json" -- and ships no tool for it. These are
that tool. `words.json` is the exact schema upstream `templates/audio/mix.py` reads
(`speech_spans()`: `float(w["s"])`, `float(w["e"])`), plus `"w"`, the word:

```json
[{"s": 0.0, "e": 0.135, "w": "A"}, {"s": 0.135, "e": 0.646, "w": "bridge"}, ...]
```

It goes to `<project>/voice/words.json`, and `story.ts` times every shot to it.

## End to end

```bash
pip install faster-whisper numpy          # for words_from_audio.py
export CARTESIA_API_KEY=...               # or use --engine piper (offline, free)

# 1. text -> voice.wav, one take per line
python tools/voice/tts.py --text my-short/script.txt --out my-short/voice/voice.wav --voice <cartesia-voice-id>
# 2. voice.wav -> words.json, with a pace check
python tools/voice/words_from_audio.py --audio my-short/voice/voice.wav --text my-short/script.txt --language en
# 3. the hand-fix list
python tools/voice/timing_qa.py --words my-short/voice/words.json
```

`script.txt` is one sentence per line; lines starting with `#` are ignored.

## Choices

- **Two engines.** `cartesia` (default) calls Cartesia Sonic directly: `--voice` is a Cartesia voice
  id (or set `CARTESIA_VOICE`), `--speed`, `--emotion`, `--language` and `--model` pass through.
  `piper` is the offline route the upstream guide asked for: `pip install piper-tts`, the voice model
  downloads to `models/piper/` on first use (`--piper-voice en_US-ryan-high`, any name from
  https://huggingface.co/rhasspy/piper-voices).
- **One take per sentence**, trimmed to speech and butted with `--gap` (0.08 s): the reference style
  has almost no pauses. A take's file name carries a hash of its text and params, so an unchanged line
  is reused for free, and changing `--speed` or `--voice` makes a new take instead of silently reusing
  the old file.
- **No whisper? Still a words.json.** If faster-whisper or its model is missing, `--text` enables a
  fallback: pauses from silencedetect snapped to the script's punctuation, in order, words spread by
  length. Good enough for cuts and captions; check it with `timing_qa.py`.
- **Script spelling wins.** With `--text`, whisper's words are aligned to the script's
  (Needleman-Wunsch), so captions show your spelling, not whisper's guesses.

## Targets (upstream STYLE_BIBLE, re-measured by tools/measure)

| | target |
|---|---|
| pace | 3.2-3.7 words/s reads well; upstream says 3.5-4.1 |
| dead air (gaps > 0.25 s) | longest gap < 0.5 s |
| voice starts | frame 1-4 (< 0.14 s) |

Some voices barely respond to a speed parameter. To change the pace of the whole read, time-stretch the
joined voice.wav (`ffmpeg -i voice.wav -af atempo=1.15 voice_fast.wav`) and re-run step 2 -- but
past ~1.4x the voice starts to sound processed.
