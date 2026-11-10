// Standard Remotion config for the cartoon-3D shorts.
// ANGLE is the GL backend the upstream stills script uses on Windows (three.js through Chrome's GPU path);
// jpeg frames keep the intermediate render small. Output size and fps live on the composition (src/Root.tsx).
import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setChromiumOpenGlRenderer("angle");
Config.setConcurrency(1); // one three.js context at a time: two at 2K exhaust GPU memory
Config.setOverwriteOutput(true);
