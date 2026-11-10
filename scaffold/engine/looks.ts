// Extra looks for the bridge engine: an indoor day, a lamp-lit interior and moonlit night.
//
// Upstream ships two lights, "day" and "golden", both tuned for an open-air town. Indoor scenes and night
// scenes need their own: under the open-air day an interior's walls go purple in the shade, and a plain
// darkened day reads as a black frame on a phone. These presets were tuned on rendered interiors and
// checked with tools/measure (preview luma and saturation against the reference range).
//
// Copy this file next to lights.ts and grade.ts in your video folder (src/videos/<name>/), then register
// the looks you want -- see "Adding a look" in ../README.md. Shapes are upstream's own types, so a typo in
// a field name is a compile error, not a silently wrong frame.
import type { LightPreset, WorldLook } from "./lights";
import type { GradeParams } from "./grade";

export type ExtraLight = "interior" | "lamp" | "night";

export const EXTRA_LIGHTS: Record<ExtraLight, LightPreset> = {
  // indoors under a skylight: upstream's warm key and violet-blue shade, but a lower lift and flat character
  // cards -- real card shadows read as violet stains on doors and floors indoors
  interior: {
    az: 75, el: 48,
    lit: [1.58, 1.5, 1.33], shade: [0.3, 0.29, 0.36], lift: [0.04, 0.035, 0.05], lambert: 0.35, sideK: 0.84, term: 0.2,
    charTint: [1.0, 1.0, 1.0], charShade: 0.9, charGrad: 0.0, bodyGrad: 0.08, sideTint: [1.0, 1.0, 1.0],
    blob: [0.62, 0.58, 0.58], actorShadow: false,
    top: "#3e7fd2", hor: "#b8d0ec", skyCurve: [0.0, 0.5, 0.6], fog: "#b8d0ec", fogNear: 25, fogFar: 300, sunDisc: "#000000",
    sunCol: "#fff3e0", sunI: 2.8, sky: "#dcecff", ground: "#b49a78", hemiI: 0.55,
    bias: -0.00025, normalBias: 0.015,
  },
  // a room lit by an oil or electric lamp: the golden palette, but the light comes from front-left and well
  // above, so faces are lit instead of backlit
  lamp: {
    az: 125, el: 38,
    lit: [1.5, 0.68, 0.24], shade: [0.15, 0.15, 0.3], lift: [0.04, 0.06, 0.17], lambert: 0.35, sideK: 0.82, term: 0.07,
    charTint: [1.0, 0.78, 0.56], charShade: 0.88, charGrad: 0.1, bodyGrad: 0.25, sideTint: [0.85, 0.80, 0.95],
    blob: [0.75, 0.74, 0.9], actorShadow: true,
    top: "#6a4f8c", hor: "#ffd08a", skyCurve: [0.05, 0.6, 1.0], fog: "#efb489", fogNear: 50, fogFar: 380, sunDisc: "#ffcf9e",
    sunCol: "#ffab5e", sunI: 5.5, sky: "#d8b0b8", ground: "#8a6a60", hemiI: 0.5,
    bias: -0.0006, normalBias: 0.03,
  },
  // cool moonlight through a window: deep blue-violet shade that never goes black, faces still readable
  night: {
    az: 110, el: 30,
    lit: [0.62, 0.72, 1.12], shade: [0.13, 0.14, 0.27], lift: [0.05, 0.06, 0.14], lambert: 0.35, sideK: 0.84, term: 0.15,
    charTint: [0.8, 0.86, 1.0], charShade: 0.8, charGrad: 0.1, bodyGrad: 0.25, sideTint: [0.78, 0.8, 0.95],
    blob: [0.6, 0.6, 0.75], actorShadow: false,
    top: "#101a3a", hor: "#2b3a6a", skyCurve: [0.0, 0.5, 0.6], fog: "#1c2547", fogNear: 40, fogFar: 400, sunDisc: "#000000",
    sunCol: "#bcd0ff", sunI: 2.0, sky: "#4a5a8a", ground: "#202436", hemiI: 0.4,
    bias: -0.0004, normalBias: 0.02,
  },
};

export const EXTRA_LOOK: Record<ExtraLight, WorldLook> = {
  interior: {
    sky: { c: ["#b8d0ec", "#9cbfea", "#6a9fe0", "#4f8cdb", "#3373cc"], e: [0, 3, 8, 16, 40] },
    water: { near: "#22a7b6", mid: "#167fb2", far: "#1a5596", crest: "#7ddfe8", trough: "#0e4a80", glint: "#ffffff", shade: [0.5, 0.56, 0.72] },
    cloud: { lit: "#fbf8f1", mid: "#e1e5f3", shade: "#c3cbe9" },
    bounce: [0, 0, 0],
    sat: 1.12,
  },
  lamp: {
    sky: { c: ["#ffc47c", "#f7ae78", "#e8967c", "#c4848e", "#8a6f8a"], e: [0, 4, 10, 20, 40] },
    water: { near: "#1e3a6e", mid: "#355f96", far: "#d4a48e", crest: "#d9a088", trough: "#16294f", glint: "#ffe2b0", shade: [0.42, 0.46, 0.72] },
    cloud: { lit: "#ffd2a8", mid: "#f2a08f", shade: "#a98fc4" },
    bounce: [0.04, 0.02, 0.0],
    sat: 0.85,
  },
  night: {
    sky: { c: ["#2b3a6a", "#24315c", "#1b2650", "#141d42", "#0c1433"], e: [0, 4, 10, 20, 40] },
    water: { near: "#1e3a6e", mid: "#1e3a6e", far: "#1e3a6e", crest: "#3a5a8e", trough: "#16294f", glint: "#9fb8ff", shade: [0.42, 0.46, 0.72] },
    cloud: { lit: "#6a7aa8", mid: "#4a5a8a", shade: "#2a3560" },
    bounce: [0, 0, 0.02],
    sat: 0.9,
  },
};

// Grades: gentle S-curves. Interior lifts the mids (an indoor preview measured luma .39 against a reference
// range of .39-.57) and trims saturation (red walls pushed it to .66 against .40-.48); night keeps a lifted
// toe so blacks never crush.
export const EXTRA_GRADES: Record<ExtraLight, GradeParams> = {
  interior: {
    ky: [0, 0.12, 0.33, 0.68, 0.88, 0.96, 1],
    sat: [0.92, 0.9, 0.9],
    tintS: [0.01, 0.002], tintM: [0, 0], tintH: [0.006, 0],
    vig: [0.12, 0.45],
  },
  lamp: {
    ky: [0, 0.1, 0.27, 0.58, 0.82, 0.94, 1],
    sat: [0.95, 0.95, 1.0],
    tintS: [0.02, 0.002], tintM: [0, 0], tintH: [-0.012, 0.006],
    vig: [0.2, 0.4],
  },
  night: {
    ky: [0.02, 0.11, 0.27, 0.56, 0.82, 0.94, 1],
    sat: [0.95, 1.05, 1.05],
    tintS: [0.03, -0.004], tintM: [0.012, 0], tintH: [-0.006, 0.004],
    vig: [0.24, 0.38],
  },
};
