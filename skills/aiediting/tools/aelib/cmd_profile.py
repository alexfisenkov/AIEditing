"""Formats and draft profiles in the workshop folder: `<work>/<skill>/profile.json` + `design/`."""
from __future__ import annotations

import shutil
from pathlib import Path

import state as st

from . import coherence, formats, handmade, intro, profiles, proofs, session, variants
from .assemble import KIT_MARK, OWN
from .install import find_installed
from .paths import DESIGN_DIR, PRESETS_DIR
from .session import CliError


def draft(skill: str) -> Path:
    return session.work() / skill / "profile.json"


def _remember(data: dict, fmt: dict, path: Path) -> None:
    rows = [f for f in data.setdefault("formats", []) if f["skill"] != fmt["skill"]]
    rows.append(dict(fmt, profile=st.rel(session.work(), path)))
    data["formats"] = rows


def cmd_formats(opt) -> str:
    chosen = formats.parse_answer(opt.answer)
    if opt.preset and not (PRESETS_DIR / (opt.preset + ".json")).is_file():
        raise CliError("Такой заготовки нет: {}".format(opt.preset))
    like = variants.catalog_format(opt.like) if opt.like else None
    if opt.like and like is None:
        raise CliError("В каталоге нет формата «{}»: --like берёт формат из списка".format(opt.like))
    lines = []
    for fmt in chosen:
        laid = []
        if like:  # the person's word, narrowed from a format of the catalog: its start and its paths
            fmt = dict(fmt, preset=like["preset"], **({"variants": like["variants"]} if like.get("variants") else {}))
        fmt = dict(fmt, preset=opt.preset or fmt["preset"])
        path = draft(fmt["skill"])
        if (opt.preset or like) and path.is_file():
            raise CliError("Черновик {} уже есть, заготовка к нему не применится: задайте шаги через ae.py profile set".format(path))
        if not path.is_file():
            profile = profiles.new_profile(fmt, language=opt.language)
            if like:
                profile["like"] = like["word"]
            named = variants.named_by_preset(fmt, opt.preset)
            profiles.write(dict(profile, variant=named) if named else profile, path)
            laid = intro.to_new_draft(fmt["skill"])
        session.touch(lambda d, f=fmt, p=path: _remember(d, f, p))
        lines.append("{} — {}{}: {}".format(fmt["skill"], fmt["title"], " (свой)" if fmt["custom"] else "", path))
        lines += ["  путь {}: {} — {}".format(r["id"], r["title"], r["hint"]) for r in fmt.get("variants", [])]
        lines += ["  из знакомства — " + line for line in laid]
    return "\n".join(lines)


def cmd_variant(opt) -> str:
    """The paths of a format: without an id, the list and the choice so far; with one, the draft goes onto that path."""
    path = draft(opt.skill)
    if not path.is_file():
        raise CliError("Черновика {} нет: сначала ae.py formats или ae.py profile open".format(path))
    profile = profiles.read(path)
    rows = variants.of_profile(profile)
    if not opt.id and not opt.own:
        listed = ["{}: {} — {}".format(r["id"], r["title"], r["hint"]) for r in rows] or ["у этого формата один путь"]
        return "\n".join(listed + ["выбран: {}".format(profile.get("variant") or "ещё ничего")])
    if opt.own:
        chosen = variants.OWN + formats.format_word(opt.own)
    else:
        row = variants.by_id(profile, opt.id)
        chosen = row["id"]
        profile = profile if opt.keep else variants.switched(profile, row)  # --keep: it already is on that path
    profile["variant"] = chosen
    profiles.write(profile, path)

    def change(d):
        st.log(d, "variant", skill=opt.skill, note=chosen)
        for row in d.get("trials", []):
            if row["skill"] == opt.skill and row.get("probe"):
                row["chosen"] = row.get("variant") == chosen

    session.touch(change)
    return "{}: путь {}, шаги: {}".format(opt.skill, chosen, ", ".join(profile["steps"]))


def cmd_kit(opt) -> str:
    """The person's choice about a kit changed after its build: it becomes the format's own, or goes and comes back new."""
    kit = session.work() / opt.skill / "design" / "overlay-kit"
    if not kit.is_dir():
        raise CliError("В черновике {} нет design/overlay-kit".format(opt.skill))
    if opt.choice == "own":
        (kit / KIT_MARK).unlink(missing_ok=True)
        return "design/overlay-kit теперь свой: сборка его не обновляет, поправки из мастерской доходят до него вручную"
    shutil.rmtree(str(kit))
    return "design/overlay-kit убран из черновика: следующая сборка положит новый; прежний остался в резерве установленной версии"


def cmd_profile(opt) -> str:
    if opt.action == "open":
        return _open(opt.skill, opt.fresh)
    path = draft(opt.skill)
    if not path.is_file():
        raise CliError("Черновика {} нет: сначала ae.py formats или ae.py profile open".format(path))
    profile = profiles.read(path)
    if opt.action == "set":
        profiles.set_values(profile, opt.values)
    elif opt.action == "taste":
        if opt.replace:
            profiles.replace_taste(profile, opt.replace, " ".join(opt.values), video=opt.video or "")
        else:
            profiles.add_taste(profile, " ".join(opt.values), video=opt.video or "")
        session.touch(lambda d: st.log(d, "taste", skill=opt.skill, note=" ".join(opt.values)))
    from runtime.profile import check_profile

    errors = check_profile(profile) + coherence.problems(profile)
    if opt.action != "check":
        profiles.write(profile, path)
    return "{}: {}{}".format(path, "в порядке" if not errors else "есть замечания:\n- " + "\n- ".join(errors),
                             proofs.said(proofs.unproved(profile, path.parent)))


def _open(skill: str, fresh: bool) -> str:
    """Refinement starts from the installed skill: its profile and design come into the workshop."""
    source = find_installed(skill)
    written = handmade.found(skill) if source is None else None
    if source is None and written is None:
        raise CliError("Скилл {} не найден среди установленных (ae.py list-skills)".format(skill))
    target = session.work() / skill
    if target.exists() and not fresh:
        raise CliError("Черновик {} уже есть — продолжайте его или откройте заново с --fresh".format(target))
    shutil.rmtree(str(target), ignore_errors=True)
    target.mkdir(parents=True)
    if written is not None:
        copy = handmade.open_copy(written, target)
        return ("Открыт для доработки: {} (из {}). Профиля у него нет, это скилл без сборки: правьте его файлы в этой копии вместе "
                "с человеком, ничего не отбрасывая; поставить обратно: ae.py install-skill {}".format(copy, written, copy))
    shutil.copy2(str(source / "profile.json"), str(target / "profile.json"))
    if (source / "design").is_dir():
        shutil.copytree(str(source / "design"), str(target / "design"))
    extra = handmade.own_parts(source, target / OWN)
    profile = profiles.read(target / "profile.json")
    fmt = {"id": "installed", "word": profile["format"], "title": profile["format"], "preset": "custom",
           "skill": skill, "custom": False}
    session.touch(lambda d: _remember(d, fmt, target / "profile.json"))
    return "\n".join(["Открыт для доработки: {} (из {})".format(target, source)] + extra)


def cmd_design_example(opt) -> str:
    """The bundled example design system (Chrome & Graphite) as the start of this skill's design."""
    found = sorted(p.parent for p in DESIGN_DIR.rglob("tokens.json"))
    if not found:
        raise CliError("В этой версии AIEditing нет примера дизайн-системы — собираем свой стиль")
    target = session.work() / opt.skill / "design"
    for item in found[0].iterdir():
        dst = target / item.name
        if item.is_dir():
            shutil.copytree(str(item), str(dst), dirs_exist_ok=True)
        else:
            target.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(item), str(dst))
    session.touch(lambda d: d["design"].update(example=found[0].name))
    return "Пример {} положен в {}".format(found[0].name, target)
