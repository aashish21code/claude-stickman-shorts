# Step 3c: words.json -> a short report: words/s, longest gap, every gap > 0.25 s with its timestamp
# (the spots SKILL.md step 3 says to hand-fix), total duration, and whether the pace is inside the
# STYLE_BIBLE targets (3.5-4.1 words/s, dead air < 1 s per video). This is the hand-fix helper:
# fix the listed gaps in the voice (re-take or tighten the cut), re-run words_from_audio.py, repeat.
#
# Usage: python timing_qa.py --words voice/words.json [--gap 0.25] [--out report.txt]
import argparse, json

WPS = (3.5, 4.1)
DEAD_AIR_MAX = 1.0


def qa(words, gap=0.25):
    words = sorted(words, key=lambda w: float(w["s"]))
    s0, e1 = float(words[0]["s"]), float(words[-1]["e"])
    gaps = [(float(a["e"]), float(b["s"]) - float(a["e"]), a.get("w", ""), b.get("w", ""))
            for a, b in zip(words, words[1:])]
    long = [g for g in gaps if g[1] > gap]
    span = e1 - s0
    return {"words": len(words), "starts_s": round(s0, 3), "ends_s": round(e1, 3), "span_s": round(span, 2),
            "words_per_sec": round(len(words) / span, 2) if span else None,
            "longest_gap_s": round(max((g[1] for g in gaps), default=0), 3),
            "dead_air_s": round(sum(g[1] for g in long), 3), "gap_threshold_s": gap,
            "gaps": [{"at_s": round(t, 3), "gap_s": round(d, 3), "between": f"{a} | {b}"} for t, d, a, b in long]}


def report(r):
    ok_w = r["words_per_sec"] is not None and WPS[0] <= r["words_per_sec"] <= WPS[1]
    ok_d = r["dead_air_s"] < DEAD_AIR_MAX
    L = [f"TIMING QA  {r['words']} words, {r['starts_s']:.2f}-{r['ends_s']:.2f} s ({r['span_s']} s)",
         f"  words/s     {r['words_per_sec']}  {'ok' if ok_w else f'OUT OF TARGET {WPS[0]}-{WPS[1]}'}",
         f"  dead air    {r['dead_air_s']} s in gaps > {r['gap_threshold_s']} s  {'ok' if ok_d else f'OVER {DEAD_AIR_MAX} s'}",
         f"  longest gap {r['longest_gap_s']} s",
         f"  voice starts at {r['starts_s']} s (reference: frame 1-4, i.e. < 0.14 s)"]
    if r["gaps"]:
        L.append("  gaps to hand-fix:")
        L += [f"    {g['at_s']:7.3f} s  +{g['gap_s']:.3f} s  ({g['between']})" for g in r["gaps"]]
    return "\n".join(L)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Pace and gap report for a words.json ([{s, e, w}]).")
    ap.add_argument("--words", required=True)
    ap.add_argument("--gap", type=float, default=0.25, help="a gap longer than this counts as dead air (default 0.25 s)")
    ap.add_argument("--out", help="also write the report here")
    a = ap.parse_args()
    text = report(qa(json.load(open(a.words, encoding="utf-8")), a.gap))
    print(text.encode("ascii", "replace").decode())
    if a.out:
        open(a.out, "w", encoding="utf-8").write(text + "\n")
