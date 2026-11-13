// The frames the face check looks at, rendered from the composition itself, and where the speaker's window is in each.
// `overlay.py face --check`, `draft`, `final`, `vertical-check` and `vertical-final` run it, each into a folder of its own run.
//   node tools-local/face-frames.mjs <bundle dir> <out dir> <composition> <frames, comma separated> [input props as JSON]
// <out dir>/f-<frame>.jpeg   the frames, the name carries the real frame number
// <out dir>/boxes.json       { frame: [x, y, w, h, corner radius, shown] } as the presenter reported it (src/kit/speakerBox.ts)
// Only these files of <out dir> are ever removed: a wrong <out dir> given by hand loses nothing else.
import { ensureBrowser, renderFrames, selectComposition } from "@remotion/renderer";
import { mkdirSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";

const [bundle, outDir, id, framesArg, propsArg = "{}"] = process.argv.slice(2);
if (!bundle || !outDir || !id || !framesArg) {
  console.error("usage: face-frames.mjs <bundle dir> <out dir> <composition> <frames> [props]");
  process.exit(2);
}
const browserExecutable = process.env.OVERLAY_BROWSER || null;
if (!browserExecutable) await ensureBrowser();
mkdirSync(outDir, { recursive: true });
for (const name of readdirSync(outDir)) {
  if (/^f-\d+\.jpe?g$/.test(name) || name === "boxes.json") rmSync(path.join(outDir, name));
}

const inputProps = { ...JSON.parse(propsArg), faceProbe: true };
const composition = await selectComposition({ serveUrl: bundle, id, inputProps, logLevel: "error", browserExecutable, timeoutInMilliseconds: 120000 });
const frames = [...new Set(framesArg.split(",").map(Number))].filter((f) => Number.isInteger(f) && f >= 0 && f < composition.durationInFrames);
const boxes = {};
if (frames.length) {
  await renderFrames({
    composition,
    serveUrl: bundle,
    inputProps,
    outputDir: outDir,
    imageFormat: "jpeg",
    jpegQuality: 90,
    frames,
    imageSequencePattern: "f-[frame].[ext]",
    concurrency: Math.max(1, Math.min(6, os.cpus().length - 1)),
    logLevel: "error",
    browserExecutable,
    timeoutInMilliseconds: 120000,
    onStart: () => {},
    onFrameUpdate: () => {},
    onBrowserLog: (log) => {
      if (!log.text.startsWith("FACEBOX ")) return;
      const [frame, ...values] = log.text.slice(8).split("|");
      boxes[frame] = values.map(Number);
    },
  });
}
writeFileSync(`${outDir}/boxes.json`, JSON.stringify({ id, fps: composition.fps, width: composition.width, height: composition.height, frames, boxes }, null, 1));
console.log(`${id}: frames ${frames.length}, boxes ${Object.keys(boxes).length}`);
