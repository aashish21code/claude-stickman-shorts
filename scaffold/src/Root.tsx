// Compositions. src/videos/bridge/ is a COPY of upstream templates/bridge/ made by setup.ps1 -- the
// originals are never edited. 1080x1920 at 30 fps; the final 2K render is --scale 1.3333 (1440x2560),
// stills are --scale 0.5.
import React from "react";
import { Composition } from "remotion";
import { BridgeShort, BRIDGE_FRAMES } from "./videos/bridge/Bridge";
import { FPS } from "./videos/bridge/story";

export const RemotionRoot: React.FC = () => (
  <>
    {/* the demo: upstream's "The Bridge That Fell for a Song" */}
    <Composition id="BridgeShort" component={BridgeShort} durationInFrames={BRIDGE_FRAMES} fps={FPS} width={1080} height={1920} />

    {/*
      A new short: copy src/videos/bridge/ to src/videos/<name>/, rename its component and frame-count
      exports, then register it here next to BridgeShort:

      import { MyShort, MY_FRAMES } from "./videos/my-short/Bridge";
      import { FPS as MY_FPS } from "./videos/my-short/story";

      <Composition id="MyShort" component={MyShort} durationInFrames={MY_FRAMES} fps={MY_FPS} width={1080} height={1920} />

      Render it:  npx remotion render src/index.ts MyShort out/my-short/video.mp4 --codec h264 --crf 16 --scale 1.3333
    */}
  </>
);
