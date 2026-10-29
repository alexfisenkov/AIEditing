"""What each recogniser is good at — shown to the person when they choose one."""
from __future__ import annotations

from typing import List

_HELP = [
    {
        "provider": "whispercpp",
        "title": "Локальный whisper (whisper.cpp)",
        "cost": "бесплатно",
        "privacy": "запись не покидает компьютер",
        "word_timing": "границы слов хорошие, но короткие слова и «э-э» иногда теряются",
        "needs": "программа whisper-cli и файл модели (large-v3 — около 3 ГБ)",
        "best_for": "по умолчанию: приватно и без счетов; на маке с Apple Silicon быстро",
    },
    {
        "provider": "scribe",
        "title": "ElevenLabs Scribe",
        "cost": "платно, по минутам записи",
        "privacy": "запись уходит в облако ElevenLabs",
        "word_timing": "самые точные границы слов, слышит «э-э» и оговорки",
        "needs": "ключ ElevenLabs в файле окружения (переменная ELEVENLABS_API_KEY)",
        "best_for": "урок с вырезкой пауз и «э-э», где важна каждая граница слова",
    },
    {
        "provider": "openai_compat",
        "title": "Любой OpenAI-совместимый сервис (OpenAI, OpenRouter, свой сервер)",
        "cost": "зависит от сервиса; свой сервер — бесплатно",
        "privacy": "запись уходит по адресу, который вы указали",
        "word_timing": "зависит от модели; без пословных меток время слов оценивается по фразам",
        "needs": "адрес (base_url), модель и имя переменной с ключом (api_key_env)",
        "best_for": "если уже платите за такой сервис или держите свой",
    },
    {
        "provider": "command",
        "title": "Своя команда",
        "cost": "как у вашей программы",
        "privacy": "как у вашей программы",
        "word_timing": "как у вашей программы",
        "needs": "программа, которая печатает JSON со словами и их временем",
        "best_for": "любой другой распознаватель, которого нет в списке",
    },
]


def providers_help() -> List[dict]:
    """[{provider, title, cost, privacy, word_timing, needs, best_for}] — по-русски."""
    return [dict(item) for item in _HELP]
