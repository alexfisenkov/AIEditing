"""Do the answers of a profile fit together? A parameter has one owner, and a decision a method depends on is not left open.

`catalog/params.json` names, for each parameter that more than one step could touch, the one place that applies it. A step, a
method file or a kit file that applies it too is a defect: the video comes out with it applied twice, and nothing fails.
"""
from __future__ import annotations

from typing import List

WAYS = ("takes", "trim", "whole")


def problems(profile: dict) -> List[str]:
    """What must be answered or changed before the format is built, in the person's language."""
    params, steps, found = profile.get("params") or {}, profile.get("steps") or [], []
    if "behind_head" in steps and not {"plate", "overlay_png", "animations"}.intersection(steps):
        found.append("behind_head нужен источник графики: plate, overlay_png или animations. "
                     "Без наложений нечего помещать за человеком.")
    way = params.get("recording")
    if way is not None and way not in WAYS:
        found.append("params.recording — одно из: takes, trim, whole; сейчас: {}".format(way))
    if params.get("clean_speech") and way not in ("takes", "trim"):
        found.append("Формат собирает чистую речь, но не решено, что делаем с записью: params.recording = takes (режем: дубли, паузы "
                     "вон) или trim (запись цельная, только края); если паузы режет шаг cut_spans или файл идёт как есть, уберите "
                     "params.clean_speech. Это первый вопрос интервью, phases/interview.md")
    if params.get("clean_speech") and "graphics" not in steps:
        found.append("Чистая речь идёт с комплектом наложений: у формата без graphics её инструментов нет. Либо добавьте шаг graphics, "
                     "либо режьте шагом cut_spans и уберите params.clean_speech и params.recording")
    verify = params.get("verify_asr") or {}
    if params.get("clean_speech") and (profile.get("asr") or {}).get("provider", "whispercpp") != "whispercpp" and not verify.get("model"):
        found.append("Чистая речь слышит запись локальным whisper, какой бы распознаватель ни писал .srt: нужна его модель в "
                     "params.verify_asr.model")
    if way in ("takes", "trim") and not params.get("clean_speech"):
        found.append("params.recording = {} делается чистой речью: нужен params.clean_speech = true".format(way))
    if way == "whole" and params.get("clean_speech"):
        found.append("params.recording = whole: запись идёт как есть, params.clean_speech тут не нужен")
    if way in ("trim", "whole") and "cut_spans" in steps:
        found.append("Запись решено не резать (params.recording = {}), а в шагах есть cut_spans: он вырежет паузы".format(way))
    if way == "takes" and "cut_spans" in steps:
        found.append("Паузы режутся дважды: чистая речь из дублей уже без них, cut_spans тут лишний")
    if "graphics" in steps and "loudnorm" in steps:
        found.append("Громкость ставится дважды: у формата с graphics её ставит overlay.py final (--lufs), шаг loudnorm лишний")
    return found
