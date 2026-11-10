# Human video background

Read when the person asks to remove, blur or replace a background behind a person in video, or asks
for graphics behind the head. This is local foreground matting with ONNX Runtime and RVM
MobileNetV3. It is intended for a person, including on a Mac M1. It does not upload the source,
use paid inference or promise a clean mask around every hair strand on every shot.
For a still image with a person or object, use `ae.py image-cutout <source>
<output.png>` instead: it uses a separately pinned MIT BiRefNet General Lite model
and does not track objects through video.

1. Locate this installed AIEditing skill and run `python3 "<skillDir>/tools/ae.py" setup
   --check`. If dependencies are missing, run `setup` or the targeted repair supported by
   the current CLI. State the combined heavy download size once; the requested local
   capability already authorizes its dependencies.
2. Inspect source duration, resolution, orientation and a few frames. Create a short preview
   from a representative stretch. Preserve the source file.
3. For transparent output: `python3 "<skillDir>/tools/ae.py" background "<video>"
   "<output.mov>" --mode remove`. The default output is alpha ProRes 4444 in a MOV container.
4. For replacement: use `--mode solid --value "<color>"`, `--mode image --value
   "<image path>"`, `--mode video --value "<video path>"` or `--mode blur`. Use an
   output path appropriate for the requested delivery and verify its codec and dimensions.
5. Watch the preview for hair, fingers, motion blur, occlusions, holes and flicker. Inspect
   the composited edge against the requested background; revise the source segment or
   treatment if visible artifacts matter. Then render the full duration and check a few
   frames throughout and audio continuity.

If the catalog lacks a requested variant, inspect the actual media and tool requirements,
choose a real local tool, install checked dependencies in an isolated environment, and
validate an output. For a recurring format feature, extend the catalog, runtime and tests.
Report concrete platform, disk, download or source failures if the viable route cannot run.
