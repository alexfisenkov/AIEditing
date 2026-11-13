"""Where the picture under the face track changes, and smoothing that never goes through such a change.

A scene change or a hard cut shows as the face jumping between two adjacent frames; a head that moves fast does not jump.
Pure arithmetic over detections: no OpenCV here, so the rules are tested without a video. A face is (cx, cy, h) in shares
of the frame. A track smoothed through a cut glides from the old face to the new one for seconds, and the speaker's frame
cuts the face all that time.
"""
from __future__ import annotations

import math
from typing import Callable, List, Optional, Sequence, Tuple

Face = Tuple[float, float, float]
Look = Callable[[int, Face], Optional[Face]]  # the face in a frame; the one that continues the given face when there is one

ASPECT = 16 / 9  # `prepare` accepts only this frame
JUMP = 0.3       # two samples this far apart are looked at frame by frame
SHARE = 0.6      # a cut puts this share of the whole jump between two adjacent frames
BLIP = 2         # samples: a face that is elsewhere for a second and back is a misdetection, as the median took it before
KEEP = 1.3       # the face followed stays until another is this many times larger: two faces of one size do not take turns
BLUR = 2         # frames looked at to the left when the frame before a jump shows no face (a blurred head is not a cut)
SMOOTH = 8       # points each side: +-4 s, so the frame glides instead of jerking after the head


def gap(a: Sequence[float], b: Sequence[float]) -> float:
    """How far apart two faces are: the move of the centre in face heights, or the change of size, whichever is larger."""
    big, small = max(a[2], b[2]), max(min(a[2], b[2]), 1e-6)
    return max(math.hypot((a[0] - b[0]) * ASPECT, a[1] - b[1]) / big, big / small - 1)


def pick(faces: Sequence[Face], last: Optional[Face]) -> Optional[Face]:
    """The largest face, as before; the one that continues `last` is kept only against a face of about its own size.

    A clearly larger face always wins, so the track comes back to the speaker after a frame where only a small face on a
    shared screen was found; it cannot stay on that small face.
    """
    if not faces:
        return None
    big = max(faces, key=lambda f: f[2])
    if last is not None:
        near = min(faces, key=lambda f: gap(f, last))
        if gap(near, last) < JUMP and near[2] * KEEP >= big[2]:
            return near
    return big


def drop_blips(points: List[list]) -> None:
    """A face that leaves for up to BLIP samples and comes back never left: those samples hold the previous value."""
    i = 1
    while i < len(points):
        prev = points[i - 1]
        if gap(prev[1:4], points[i][1:4]) >= JUMP:
            back = next((j for j in range(i + 1, min(len(points), i + BLIP + 1)) if gap(prev[1:4], points[j][1:4]) < JUMP), None)
            if back is not None:
                for k in range(i, back):
                    points[k][1:4] = prev[1:4]
                i = back
                continue
        i += 1


def locate(left: Face, right: Face, lo: int, hi: int, look: Look) -> Optional[int]:
    """The first frame of the new face between two samples, or None when the head simply moved."""
    start, before, after = lo, None, right
    while hi - lo > 1:
        mid = (lo + hi) // 2
        seen = look(mid, left)
        if seen is not None and gap(seen, right) < gap(seen, left):
            hi, after = mid, seen
        else:
            lo, before = mid, seen
    if lo == start:
        before = look(lo, left)
    for back in range(1, BLUR + 1):  # no face right before the jump: a blurred frame of a fast head, or a real change
        if before is not None or lo - back < start:
            break
        before = look(lo - back, left)
    if before is None or gap(before, after) >= SHARE * gap(left, right):
        return hi
    return None


def find_cuts(points: Sequence[list], step: int, look: Look) -> List[int]:
    """Frames at which a new piece of the picture starts. `points` are filled [t, cx, cy, h]; sample k is frame k * step."""
    cuts = []
    for i in range(1, len(points)):
        left, right = tuple(points[i - 1][1:4]), tuple(points[i][1:4])
        if gap(left, right) < JUMP:
            continue
        frame = locate(left, right, (i - 1) * step, i * step, look)
        if frame is not None:
            cuts.append(frame)
    return cuts


def pieces(count: int, step: int, seconds_per_frame: float, cuts: Sequence[int]) -> List[float]:
    """For every sample, the second at which its piece of the picture began (0 for the first piece)."""
    out, at, since = [], 0, 0.0
    ordered = sorted(cuts)
    for k in range(count):
        while at < len(ordered) and ordered[at] <= k * step:
            since = round(ordered[at] * seconds_per_frame, 4)
            at += 1
        out.append(since)
    return out


def smooth(points: Sequence[list], since: Sequence[float]) -> List[list]:
    """[t, cx, cy, h, since]: a moving average that takes only the samples of the same piece."""
    out = []
    for i, p in enumerate(points):
        window = [points[j] for j in range(max(0, i - SMOOTH), min(len(points), i + SMOOTH + 1)) if since[j] == since[i]]
        out.append([round(p[0], 2)] + [round(sum(q[k] for q in window) / len(window), 4) for k in (1, 2, 3)] + [since[i]])
    return out
