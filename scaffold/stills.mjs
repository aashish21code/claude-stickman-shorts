// usage: COMP=BridgeShort node stills.mjs <outPrefix> <frame,frame,...> [scale]
// scripts/bridge-stills.mjs (a setup.ps1 copy of upstream, never edited) is hard-wired to BridgeShort; this is the same
// still renderer with the composition as a parameter. Bundles once, GPU via ANGLE, jpeg. Set REMOTION_TMP to a folder
// with room: every bundle copies public/ into the temp dir and never deletes it.
import fs from "node:fs";
if (process.env.REMOTION_TMP) { fs.mkdirSync(process.env.REMOTION_TMP, { recursive: true }); process.env.TEMP = process.env.TMP = process.env.REMOTION_TMP; }
import { bundle } from "@remotion/bundler";
import { renderStill, selectComposition } from "@remotion/renderer";
import path from "node:path";
const [prefix, frames, scale = "0.5"] = process.argv.slice(2);
const browserExecutable = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const chromiumOptions = { gl: "angle" };
const inputProps = process.env.PROPS ? JSON.parse(process.env.PROPS) : {};
fs.mkdirSync(path.dirname(path.resolve(prefix)), { recursive: true });
const serveUrl = await bundle({ entryPoint: path.resolve("src/index.ts"), publicDir: path.resolve("public") });
const composition = await selectComposition({ serveUrl, id: process.env.COMP || "BridgeShort", browserExecutable, chromiumOptions, inputProps });
const onBrowserLog = (l) => { if (l.type === "error" || l.type === "warning") console.log(`[${l.type}]`, l.text.slice(0, 300)); };
for (const f of frames.split(",").map(Number)) {
  const t0 = Date.now();
  await renderStill({ composition, serveUrl, frame: f, output: `${prefix}${String(f).padStart(4, "0")}.jpg`, imageFormat: "jpeg", jpegQuality: 88, scale: Number(scale),
    browserExecutable, chromiumOptions, timeoutInMilliseconds: 240000, onBrowserLog, inputProps });
  console.log("still", f, ((Date.now() - t0) / 1000).toFixed(1) + "s");
}
