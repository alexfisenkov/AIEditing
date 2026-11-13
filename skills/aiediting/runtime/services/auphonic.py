"""Auphonic cleans the voice by the person's own key: send the audio with a preset, wait, download the result.

The key is `AUPHONIC_API_KEY` (or the variable the profile names), read by `runtime/asr/secrets.py`, sent only in the
Authorization header and never printed. A preset is an Auphonic preset (its id or name) or the algorithms themselves
(`denoise`, `denoisemethod`, `denoiseamount`, `leveler`, `normloudness`, `loudnesstarget`, `filtering`, `filtermethod`).
Auphonic counts every production as at least 3 minutes of the person's credits.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List, Tuple, Union

from ..asr.contract import AsrError
from ..asr.secrets import config_dir, read_key
from .web import ServiceError, download, get_json, post_form

BASE = "https://auphonic.com"
KEY_ENV = "AUPHONIC_API_KEY"
WHAT = "Auphonic"
POLL = 10.0          # seconds between two looks at a production
MAX_WAIT = 2 * 3600  # a production that is not done by then is left to finish on the site
DONE, FAILED = 3, 2
RESERVED = {"input_file", "action", "title", "preset"}

__all__ = ["ServiceError", "process", "check_key", "KEY_ENV"]


def _key(key_env: str) -> str:
    try:
        return read_key(key_env)
    except AsrError:
        raise ServiceError(
            "Нет ключа Auphonic: переменная {0} не задана. Откройте auphonic.com → настройки аккаунта (Account Settings) → "
            "API Key, скопируйте ключ и впишите строку {0}=… в файл .env (в папке, где идёт работа, или в {1}) — "
            "в чат ключ не присылайте.".format(key_env, config_dir()))


def _headers(key: str) -> Dict[str, str]:
    return {"Authorization": "bearer " + key, "User-Agent": "aiediting"}


def _value(v) -> str:
    return ("true" if v else "false") if isinstance(v, bool) else str(v)


def fields_of(preset: Union[str, Dict], title: str) -> List[Tuple[str, str]]:
    fields = [("title", title), ("action", "start")]
    if isinstance(preset, dict):
        return fields + [(k, _value(v)) for k, v in preset.items() if k not in RESERVED and v is not None]
    return fields + [("preset", str(preset))]


def _wait(uuid: str, key: str) -> Dict:
    started = time.monotonic()
    while True:
        data = get_json("{}/api/production/{}.json".format(BASE, uuid), _headers(key), WHAT, key).get("data") or {}
        status = data.get("status")
        if status == DONE:
            return data
        if status == FAILED:
            raise ServiceError("Auphonic не обработал звук: {}".format(data.get("error_message") or data.get("status_string") or "ошибка"))
        if time.monotonic() - started > MAX_WAIT:
            raise ServiceError("Auphonic не закончил за {} мин; результат будет на сайте в списке обработок".format(MAX_WAIT // 60))
        time.sleep(POLL)


def _result_url(data: Dict) -> str:
    files = [f for f in data.get("output_files") or [] if f.get("download_url")]
    wav = [f for f in files if str(f.get("ending") or f.get("format") or "").lower() == "wav"]
    if not (wav or files):
        raise ServiceError("Auphonic закончил, но не отдал файла результата")
    return (wav or files)[0]["download_url"]


def process(audio: Path, preset: Union[str, Dict], out: Path, key_env: str = KEY_ENV) -> Path:
    """The cleaned voice of `audio` into `out` (WAV when Auphonic gives one); ServiceError says why it could not."""
    audio = Path(audio)
    if not audio.is_file():
        raise ServiceError("Нет звука для Auphonic: {}".format(audio))
    key = _key(key_env)
    reply = post_form(BASE + "/api/simple/productions.json", fields_of(preset, audio.stem), "input_file", audio,
                      _headers(key), WHAT, key)
    uuid = (reply.get("data") or {}).get("uuid")
    if not uuid:
        raise ServiceError("Auphonic не принял звук: {}".format(reply.get("error_message") or "нет номера обработки"))
    url = _result_url(_wait(uuid, key))
    headers = _headers(key) if url.startswith(BASE + "/") else {"User-Agent": "aiediting"}  # the key goes to Auphonic only
    return download(url, headers, Path(out), WHAT, key)


def check_key(key_env: str = KEY_ENV) -> str:
    """A trial request: the account answers or not. The key itself is never shown."""
    key = _key(key_env)
    data = get_json(BASE + "/api/user.json", _headers(key), WHAT, key).get("data") or {}
    left = data.get("credits")
    return "Ключ Auphonic принят: аккаунт отвечает{}.".format("; остаток кредитов: {}".format(left) if left is not None else "")
