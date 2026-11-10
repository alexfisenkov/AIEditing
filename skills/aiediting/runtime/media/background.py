"""Stream a human matte through RVM ONNX and compose it with a local background.

RVM is a portrait/person model, not a general object remover. No source is sent to a service.
The ONNX model is loaded as data by onnxruntime; no upstream Python code is executed.
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

from .ffmpeg import MediaError, ensure_file, run, tool
from .probe import probe

MODEL_ENV = "AIEDITING_RVM_MODEL"
MODEL_NAME = "rvm_mobilenetv3_fp32.onnx"
COLOUR = re.compile(r"^#[0-9a-fA-F]{6}$")
OUTPUTS = ["fgr", "pha", "r1o", "r2o", "r3o", "r4o"]


def default_model_path(system=None, localappdata=None) -> Path:
    """Match the catalog's model destination on macOS and Windows."""
    system = system or os.name
    if system == "nt":
        base = localappdata or os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / "AIEditing" / "models" / MODEL_NAME
    return Path.home() / ".aiediting" / "models" / MODEL_NAME


def model_file(path=None) -> Path:
    candidate = path or os.environ.get(MODEL_ENV) or default_model_path()
    candidate = Path(candidate).expanduser()
    if not candidate.is_file():
        raise MediaError("Нет модели RVM: {}. Установите проверенный rvm-model через ae.py doctor.".format(candidate))
    return candidate


def _session(path):
    try:
        import onnxruntime as ort
    except ImportError as exc:
        raise MediaError("Нет onnxruntime в Python-окружении AIEditing; установите его через ae.py doctor.") from exc
    try:
        return ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    except Exception as exc:
        raise MediaError("Не удалось открыть модель RVM: {}".format(path)) from exc


def _shape(info):
    w, h = info["width"], info["height"]
    if info["rotation"] in (90, 270):
        return h, w
    return w, h


def _read_frame(pipe, n):
    parts, size = [], 0
    while size < n:
        chunk = pipe.read(n - size)
        if not chunk:
            break
        parts.append(chunk)
        size += len(chunk)
    if size == 0:
        return None
    if size != n:
        raise MediaError("Последний кадр исходника прочитан не полностью")
    return b"".join(parts)


def _matte(src, matte, info, session, ratio):
    try:
        import numpy as np
    except ImportError as exc:
        raise MediaError("Для удаления фона нужен numpy в окружении AIEditing") from exc

    w, h = _shape(info)
    fps = info["fps"]
    frame_size = w * h * 3
    decode = [tool("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "error", "-i", str(src),
              "-vf", "fps={:.8f},format=rgb24".format(fps), "-an", "-f", "rawvideo",
              "-pix_fmt", "rgb24", "pipe:1"]
    encode = [tool("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo",
              "-pix_fmt", "rgba", "-s", "{}x{}".format(w, h), "-r", "{:.8f}".format(fps),
              "-i", "pipe:0", "-an", "-c:v", "prores_ks", "-profile:v", "4",
              "-pix_fmt", "yuva444p10le", str(matte)]
    states = [np.zeros((1, 1, 1, 1), dtype=np.float32) for _ in range(4)]
    downsample = np.asarray([ratio], dtype=np.float32)
    with tempfile.TemporaryFile() as decode_err, tempfile.TemporaryFile() as encode_err:
        decoder = subprocess.Popen(decode, stdout=subprocess.PIPE, stderr=decode_err)
        encoder = subprocess.Popen(encode, stdin=subprocess.PIPE, stderr=encode_err)
        frames = 0
        try:
            while True:
                raw = _read_frame(decoder.stdout, frame_size)
                if raw is None:
                    break
                src_rgb = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3)
                tensor = np.transpose(src_rgb, (2, 0, 1))[None].astype(np.float32) / 255.0
                feeds = dict(src=tensor, downsample_ratio=downsample)
                feeds.update({"r{}i".format(i): state for i, state in enumerate(states, 1)})
                try:
                    fgr, pha, *states = session.run(OUTPUTS, feeds)
                    if fgr.shape != (1, 3, h, w) or pha.shape != (1, 1, h, w) or len(states) != 4:
                        raise ValueError("RVM вернула неожиданную форму кадра или состояний")
                    if not np.isfinite(fgr).all() or not np.isfinite(pha).all():
                        raise ValueError("RVM вернула NaN или бесконечное значение")
                    rgb = np.transpose(np.clip(fgr[0], 0, 1), (1, 2, 0))
                    alpha = np.clip(pha[0, 0], 0, 1)
                    rgba = np.empty((h, w, 4), dtype=np.uint8)
                    rgba[:, :, :3] = np.rint(rgb * 255).astype(np.uint8)
                    rgba[:, :, 3] = np.rint(alpha * 255).astype(np.uint8)
                    encoder.stdin.write(rgba.tobytes())
                except Exception as exc:
                    raise MediaError("RVM не обработала кадр {}: {}".format(frames + 1, str(exc)[:400])) from exc
                frames += 1
            encoder.stdin.close()
            decode_rc = decoder.wait()
            encode_rc = encoder.wait()
            if decode_rc or encode_rc:
                decode_err.seek(0)
                encode_err.seek(0)
                detail = (decode_err.read() + encode_err.read()).decode("utf-8", "replace")[-1500:]
                raise MediaError("Не удалось прочесть или записать видеокадры: {}".format(detail))
            if frames == 0:
                raise MediaError("В исходнике нет видеокадров")
        finally:
            if decoder.poll() is None:
                decoder.kill()
            if encoder.poll() is None:
                encoder.kill()
            decoder.wait()
            encoder.wait()
            decoder.stdout.close()
            if encoder.stdin and not encoder.stdin.closed:
                encoder.stdin.close()


def _compose(src, matte, out, info, mode, background):
    w, h = _shape(info)
    fps = info["fps"]
    if mode == "remove":
        run(["-i", matte, "-i", src, "-map", "0:v:0", "-map", "1:a?", "-c:v", "copy",
             "-c:a", "aac", "-shortest", out])
        return

    args = ["-i", matte]
    if mode == "solid":
        args += ["-f", "lavfi", "-i", "color=c=0x{}:s={}x{}:r={:.8f}:d={:.8f}".format(
            background[1:], w, h, fps, info["duration"])]
        bg_filter = "[1:v]format=rgba[bg]"
    else:
        if mode == "image":
            args += ["-loop", "1", "-framerate", "{:.8f}".format(fps), "-i", background]
        elif mode == "video":
            args += ["-stream_loop", "-1", "-i", background]
        else:  # blur or foreground
            args += ["-i", src if mode == "blur" else background]
        prep = "fps={:.8f},scale={}:{}:force_original_aspect_ratio=increase,crop={}:{}".format(fps, w, h, w, h)
        if mode == "blur":
            prep += ",gblur=sigma=18"
        bg_filter = "[1:v]{}[bg]".format(prep)
    args += ["-i", src, "-filter_complex", bg_filter + ";[bg][0:v]overlay=shortest=1:format=auto,format=yuv420p[v]",
             "-map", "[v]", "-map", "2:a?", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
             "-c:a", "aac", "-shortest", out]
    run(args)


def edit_background(src, out, mode="remove", background=None, model_path=None, session=None, downsample_ratio=None) -> Path:
    """Remove a person's background to alpha MOV, or replace it in an MP4.

    `foreground` places the person from `src` over a same-size, same-time video in `background`.
    The caller may inject an ONNX-compatible session for tests; production loads local RVM ONNX.
    """
    src, out = ensure_file(src).resolve(), Path(out).expanduser().resolve()
    if src == out:
        raise MediaError("Исходник и результат должны быть разными файлами")
    if mode not in {"remove", "solid", "image", "video", "blur", "foreground"}:
        raise MediaError("Неизвестный режим фона: {}".format(mode))
    if mode == "remove" and out.suffix.lower() != ".mov":
        raise MediaError("Прозрачный результат требует .mov (ProRes 4444)")
    if mode != "remove" and out.suffix.lower() != ".mp4":
        raise MediaError("Результат с новым фоном требует .mp4")
    if mode == "solid" and (not isinstance(background, str) or not COLOUR.fullmatch(background)):
        raise MediaError("Однотонный фон задаётся цветом #RRGGBB")
    if mode in {"image", "video", "foreground"}:
        if background is None or background == "":
            raise MediaError("Нужен файл фона для режима {}".format(mode))
        background = ensure_file(background).resolve()
        if background == out:
            raise MediaError("Фон и результат должны быть разными файлами")
    info = probe(src)
    if not info["has_video"] or not info["fps"] or info["duration"] <= 0:
        raise MediaError("Нужен исходник с видео, длительностью и частотой кадров")
    if mode == "foreground":
        other = probe(background)
        if _shape(other) != _shape(info) or abs(other["duration"] - info["duration"]) > 0.1:
            raise MediaError("Графика за человеком должна совпадать с исходником по размеру и времени")
    if session is None:
        session = _session(model_file(model_path))
    ratio = float(downsample_ratio) if downsample_ratio is not None else min(1.0, 512 / max(_shape(info)))
    if not 0 < ratio <= 1:
        raise MediaError("downsample_ratio должен быть больше 0 и не больше 1")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".aiediting-background-", dir=str(out.parent)) as work:
        work = Path(work)
        matte = work / "matte.mov"
        staged = work / ("result" + out.suffix.lower())
        _matte(src, matte, info, session, ratio)
        _compose(src, matte, staged, info, mode, background)
        final_info = probe(staged)
        if not final_info["has_video"] or (info["has_audio"] and not final_info["has_audio"]):
            raise MediaError("Проверка результата: потеряно видео или аудио")
        if abs(final_info["duration"] - info["duration"]) > max(0.15, info["duration"] * 0.005):
            raise MediaError("Проверка результата: длительность отличается от исходника")
        os.replace(str(staged), str(out))
    return out


def main(argv=None) -> int:
    """One-off local edit without building a format skill."""
    import argparse

    parser = argparse.ArgumentParser(description="Удалить или заменить фон вокруг человека локальной RVM ONNX")
    parser.add_argument("source", help="исходное видео")
    parser.add_argument("output", help="выходной .mov для remove, .mp4 для остальных режимов")
    parser.add_argument("--mode", choices=("remove", "solid", "image", "video", "blur", "foreground"), default="remove")
    parser.add_argument("--value", help="цвет #RRGGBB или путь к фону")
    parser.add_argument("--model", help="путь к локальной ONNX-модели, если не установлен стандартный")
    parser.add_argument("--ratio", type=float, help="downsample_ratio модели, (0, 1]")
    args = parser.parse_args(argv)
    try:
        result = edit_background(args.source, args.output, mode=args.mode, background=args.value,
                                 model_path=args.model, downsample_ratio=args.ratio)
    except MediaError as exc:
        parser.exit(2, "{}\n".format(exc))
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
