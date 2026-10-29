"""Editing mechanics on ffmpeg. Callers see functions and plain data, never ffmpeg commands."""
from .blur import blur_regions
from .codec import codec_chain
from .cut import cut_spans
from .drift import drift_ms
from .ffmpeg import MediaError
from .loudness import loudnorm
from .probe import probe
from .spans import speech_spans
from .srt import write_srt
from ..render.overlay import overlay_png  # media's face for the design layer (interfaces §2)

__all__ = ["MediaError", "blur_regions", "codec_chain", "cut_spans", "drift_ms", "loudnorm",
           "overlay_png", "probe", "speech_spans", "write_srt"]
