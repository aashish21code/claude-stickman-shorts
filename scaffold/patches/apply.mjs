// usage: node patches/apply.mjs            (from scaffold/; setup.ps1 runs it after copying the templates)
//
// Fixes carried on top of the copied upstream templates. src/videos/bridge/ is a copy that setup.ps1
// regenerates and .gitignore excludes, so a fix made only in the copy never reaches git or anyone else,
// and upstream templates/bridge/ is never edited. Each edit is an exact old -> new string replacement:
//   new text already there -> skipped (idempotent)
//   old text there         -> replaced
//   neither                -> error: upstream changed under us, re-check the edit by hand
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

// TS2322 x6 (npx tsc --noEmit): @react-three/postprocessing 3.0.4 types EffectComposer's children as
// JSX.Element | JSX.Element[], so each optional pass written `cond ? <primitive/> : null` is Element | null.
// The component handles null children fine at runtime (it walks the r3f children of its group), so the fix is
// a type-only cast: identical JS after compilation, identical frames.
const opt = (cond, obj) => ({
  old: `      {${cond} ? <primitive object={${obj}} dispose={null} /> : null}\n`,
  new: `      {(${cond} ? <primitive object={${obj}} dispose={null} /> : null) as React.JSX.Element}\n`,
});
const EDITS = [
  { file: "src/videos/bridge/Bridge.tsx", why: "TS2322 optional post passes", edits: [
    opt("on.ink", "fx.ink"),
    opt("on.lens && on.pre", "fx.lens.pre"),
    opt("on.lens", "fx.lens.main"),
    opt("on.bloom", "fx.bloom"),
    opt("on.grade", "fx.grade"),
    opt("on.grain", "fx.grain"),
  ] },
];

let changed = 0, skipped = 0;
for (const { file, why, edits } of EDITS) {
  const p = path.join(root, file);
  let s = fs.readFileSync(p, "utf8");
  const eol = s.includes("\r\n") ? "\r\n" : "\n"; // a Windows checkout of upstream may carry CRLF
  for (const e of edits) {
    const o = e.old.replaceAll("\n", eol), n = e.new.replaceAll("\n", eol);
    if (s.includes(n)) { skipped++; continue; }
    if (!s.includes(o)) { console.error(`patch failed: ${file} (${why}): expected text not found:\n${e.old}`); process.exit(1); }
    s = s.replace(o, n); changed++;
  }
  fs.writeFileSync(p, s);
}
console.log(`  patches: ${changed} applied, ${skipped} already in place`);
