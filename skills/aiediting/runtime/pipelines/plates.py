"""The `plate` step: chapter plates, cards and (for 9:16) burned-in captions, as the profile's params say."""
from __future__ import annotations


def plan_plates(ctx) -> None:
    from .cards import plan_cards
    from .chapters import plan_chapters

    plan_chapters(ctx)
    plan_cards(ctx)
    if ctx.p("captions") == "burned" and not ctx.has("vertical"):
        ctx.note("Вшитые субтитры заданы для горизонтального ролика — вшиваю, хотя рядом можно класть .srt")
