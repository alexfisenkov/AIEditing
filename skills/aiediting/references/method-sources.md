# Method sources and coverage

Checked for this knowledge update on 2026-11-10. This is a route to the parts actually used, not a
copy of vendor manuals. API behaviour is checked against the installed catalog pins and executable
examples. A method can be detailed while its visual result on a future source still needs acceptance.

| Maintained tool/model | Method coverage | Primary source / relevant section |
|---|---|---|
| FFmpeg Full / ffprobe | Audio processing, ASS, colour, VidStab, Rubber Band, technical QC/VMAF | [Filters](https://ffmpeg.org/ffmpeg-filters.html), per-page filter anchors; local 9.0.2 help/feature inventory |
| PySceneDetect | Content/adaptive thresholds, minimum scene length, source-time boundaries | [Examples](https://www.scenedetect.com/docs/latest/examples.html), [detectors](https://www.scenedetect.com/docs/latest/api/detectors.html) |
| SoundFile | Bounded PCM read/write and sample-rate ownership | [read/blocks](https://python-soundfile.readthedocs.io/en/latest/index.html) |
| librosa / NumPy | Window RMS/onsets, time units, normalized correlation and drift checks | [RMS](https://librosa.org/doc/main/api/generated/librosa.feature.rms.html), [onsets](https://librosa.org/doc/1.0.0/auto_tutorials/01-intro/05-onsets.html), [NumPy dtype](https://numpy.org/doc/stable/reference/arrays.dtypes.html) |
| pysubs2 | Local SRT/ASS/VTT, shift/FPS correction, style retention/loss | [API](https://pysubs2.readthedocs.io/en/latest/api-reference.html), pinned 1.9.1 installed API |
| whisper.cpp / large-v3 | Local recognizer, word timing limits and seam listening | [Word-timestamp documentation](https://github.com/ggml-org/whisper.cpp#word-level-timestamp-experimental), local 1.9.5 CLI/provider contract |
| OpenCV / YuNet | Face result columns, input size, coordinate transforms and tracking limits | [OpenCV 5 FaceDetectorYN](https://docs.opencv.org/5.0/main_modules/objdetect_dnn_face.html), local look APIs |
| Tesseract | Language inventory, crop/PSM choice, TSV boxes and verification | [CLI](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html), [quality](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html) |
| Pillow | RGBA layers, actual font files, measured text and clipping | [ImageDraw](https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html) |
| ONNX Runtime / RVM | Local human video matte, recurrent state and compositing | [RVM inference](https://github.com/PeterL1n/RobustVideoMatting/blob/master/documentation/inference.md), local background runtime |
| rembg / BiRefNet Lite | Explicit still-image model and alpha inspection | [Model list](https://github.com/danielgatis/rembg/blob/main/README.md), pinned 2.0.87 wrapper/model contract |
| Node.js / HyperFrames | Runtime versus renderer, short designed inserts, alpha intermediate | [v0.9.28 rendering guide](https://github.com/heygen-com/hyperframes/blob/v0.9.28/docs/guides/rendering.mdx), local renderer wrapper |
| Remotion | Sequence/frame timing, staged motion, native scene/layout kit and output checks | [Sequence](https://www.remotion.dev/docs/sequence), [interpolate](https://www.remotion.dev/docs/interpolate), [still](https://www.remotion.dev/docs/cli/still), [alpha](https://www.remotion.dev/docs/transparent-videos) |

## Supplied skills: adapted methods

The owner supplied a motion-studio brief and a local corpus of editing skills. The current material
registry contains 20 clones plus separately installed skills; a dated historical note about eight
clones is not used to guess which eight existed then. Every current clone's relevant SKILL/README
was inspected and recorded in the local engineering ledger, with an adopted topic or an explicit
exclusion. App code, media packs, cloud commands and licence-unclear code were not imported.

| Supplied source and inspected pin | Adapted principle | Where it is used |
|---|---|---|
| Owner-supplied motion-studio brief | One focal idea per scene, visual action bound to words, draft/still/final review | Graphics and editorial methods |
| [browser-use/video-use](https://github.com/browser-use/video-use), `SKILL.md`, `43cfc566` | Inspectable edit plan and original/final time ownership | Editorial planning and technical QC |
| [Barty-Bart/motion-graphics](https://github.com/Barty-Bart/motion-graphics), motion-broll, `3d83d987` | A motivated word-bound insert rather than unrelated decoration | Graphics and B-roll |
| [charlie947/motion-graphics-skills](https://github.com/charlie947/motion-graphics-skills), animated-chart/reference-to-motion, `229022eb` | Exact supplied chart values; separate movement and visual-style references | Graphics planning and numeric checks |
| [LottieFiles/motion-design-skill](https://github.com/LottieFiles/motion-design-skill), motion-design, `f9a8a041` | Staging and readable states | Graphics and compositing |
| [whaleyxbt/claude-motion](https://github.com/whaleyxbt/claude-motion), review-loop, `e6279415` | Stills and draft review before final render | Graphics acceptance |
| [aaksa/facecammaxxing](https://github.com/aaksa/facecammaxxing), `SKILL.md`, `a9976a70` | Explicit foreground/layer order and edge review | Background and alpha |
| [brookejlacey/boring-tools](https://github.com/brookejlacey/boring-tools), `SKILL.md`, `fa775045` | Visible EDL and frame-grid inspection | Editorial plan and QA |
| Supplied Palmier UGC/multicam/colour/caption guides | Span-scoped B-roll, separate sync and camera choice, normalize/match before look, caption hierarchy | Audio sync, colour, subtitles and editorial methods |
| Supplied Remotion skill family and AIEditing's own kit | Deterministic frame-based motion and real local interfaces | Graphics and compositing |

These are adapted principles, not a claim that Palmier/Final Cut MCP is connected or that their
preset/API names exist in AIEditing. Personal sound/image assets and fixed taste settings stay
with their owner/format. Existing format skills are outside this update's write perimeter.
