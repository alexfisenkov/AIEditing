# Background, alpha and foreground layers

Read for a request to remove or replace a background, make a transparent layer, or put graphics
behind a person. Choose the method from the source, then prove it on a representative stretch.
AIEditing processes locally; the requested edit authorizes its local dependencies. It does not
authorize media upload, paid inference or publication.

## Select the source-specific method

| Source and result | Method in this version | Boundary |
|---|---|---|
| Moving person against an ordinary room; transparent or replaced background | `ae.py background --mode remove|solid|image|video|blur` uses the pinned RVM MobileNetV3 ONNX model | A human matte, not general object video segmentation. CPU execution also works on an Apple Silicon M1; inspect speed and edge quality on this machine. |
| Evenly lit green or blue screen; transparent video | `ae.py background --mode chromakey` uses FFmpeg's local chroma key | Tune key colour, similarity and blend on a short preview. A keyed edge may retain green spill or erase similarly coloured clothing. |
| Person in front of a graphic layer | A format with `behind_head` and a chosen overlay step composites its RVM foreground over the graphic | The graphic must cover the same frame size and duration. A title placed behind the face still needs readable space elsewhere. |
| Still image of a person or object; transparent PNG | `ae.py image-cutout` uses local rembg with the explicitly pinned BiRefNet General Lite model | It is a single-image method. Running it on separate frames does not establish temporal continuity or object tracking. |

RVM is a recurrent video model: each frame's states feed the next. Its official
[inference guide](https://github.com/PeterL1n/RobustVideoMatting/blob/master/documentation/inference.md)
explains the ONNX inputs, alpha/foreground outputs and the downsample ratio. AIEditing's
stream keeps those states across the input, including hard cuts; inspect the first frames
after each change of shot for a stale silhouette. A higher ratio can help small or full-body
subjects but is not automatically better. The default is selected from frame size; change
`--downsample-ratio` only after comparing previews.

## Run an isolated sample, then the requested duration

Use a separate **new, unused** output path for every probe/render. The existing background
CLI can replace a previous non-source output, so select a fresh versioned name or preserve
the previous file before an intentionally authorized replacement. The commands below are
alternatives, not a sequence to run against the same filenames. `ae.py background` checks and repairs its selected dependencies
before processing. `--mode` is required. Remove and chroma key write transparent ProRes 4444
`.mov`; replacement and blur modes write H.264 `.mp4`. These exact flags were checked
against the local CLI help.

```bash
python3 "<skillDir>/tools/ae.py" capabilities --json
ffmpeg -ss 00:00:10 -i recording.mp4 -t 4 -c:v libx264 -c:a aac sample.mp4
python3 "<skillDir>/tools/ae.py" background sample.mp4 subject.mov --mode remove
python3 "<skillDir>/tools/ae.py" background sample.mp4 solid.mp4 --mode solid --value "#202123"
python3 "<skillDir>/tools/ae.py" background sample.mp4 backdrop.mp4 --mode image --value backdrop.png
python3 "<skillDir>/tools/ae.py" background sample.mp4 moving.mp4 --mode video --value background-video.mp4
python3 "<skillDir>/tools/ae.py" background sample.mp4 soft.mp4 --mode blur
python3 "<skillDir>/tools/ae.py" background green.mp4 keyed.mov --mode chromakey --key-color "#00ff00" --similarity 0.12 --blend 0.08
python3 "<skillDir>/tools/ae.py" image-cutout product.png product-alpha.png
```

Use the person's actual local file in place of each example. Create the short sample from the
same source when the full recording is long; preserve the original and audio. For `image` or
`video` replacement, `--value` is an existing file. A replacement video loops to cover the
source duration. For `solid`, it is a `#RRGGBB` colour. A custom `--model` path is possible
for RVM, but its provenance and compatibility must be checked before use.

The chroma key defaults in the example are starting values, not universal settings. Change
one at a time on a representative frame with hair, hands and clothing near the key colour.
The `chromakey` route does not need RVM. For naturally filmed footage, a key colour chosen
from the room is usually the wrong method: use the temporal human matte first.

## Inspect picture and sound

1. View the foreground on both a dark and a light temporary background. Check hair,
   fingers, glasses, motion blur, translucent objects and the gap between arms and torso.
   A white fringe can hide against white and become obvious against graphite.
2. Play several consecutive seconds, not only stills. Look for flicker, holes, doubled
   contours and the first second after each edit. If a hard cut causes a temporal artifact,
   segment the source at that cut and recheck each segment before assembly; do not silently
   hand over a single bad stream.
3. For chroma, inspect green/blue spill on skin and hair plus holes in clothes. For image or
   video replacement, compare background scale, horizon, light direction and motion; a
   technically correct mask can still look pasted on.
4. Confirm output codec, pixel format, dimensions, duration and audio streams with `ffprobe`.
   Listen to the beginning, the change of shot and the end. AIEditing checks presence and
   duration; it cannot judge whether an edge looks convincing.

```bash
ffprobe -v error -show_entries stream=codec_name,pix_fmt,width,height -show_entries format=duration -of json subject.mov
```

Transparent ProRes 4444 is an editing intermediate. A delivery MP4 made from that MOV will
usually be opaque unless it is deliberately composited over a background. Remotion's
[transparency guide](https://www.remotion.dev/docs/transparent-videos) independently documents
the alpha-capable ProRes profile and pixel format.

The rembg package and model have separate licences. The [rembg model list and licence note](https://github.com/danielgatis/rembg/blob/main/README.md)
distinguish its models; AIEditing explicitly selects BiRefNet General Lite rather than
the package's default BRIA model. The [BiRefNet maintainer confirmed MIT for code and
weights](https://github.com/ZhengPeng7/BiRefNet/issues/316). RVM's model is the project's
GPL-3.0 release; do not replace it with an unreviewed download or assume that the still
image route grants an arbitrary-object video capability.
