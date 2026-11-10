"""`ae.py doctor`: what of the catalog is here, what is missing — and installs one tool by its pin, only on «да»."""
from __future__ import annotations

from pathlib import Path
import sys

from . import catalog
from .checks import current_os, status
from .installers import pip_package, run_install
from .session import CliError


def _rows(opt):
    base = Path(opt.catalog) if opt.catalog else None
    rows = catalog.tools(base)
    if opt.steps:
        chosen = [s.strip() for s in opt.steps.split(",") if s.strip()]
        bad = catalog.check_steps(chosen, base)
        if bad:
            raise CliError("; ".join(bad))
        wanted = catalog.needs(chosen, opt.asr, base)["tools"]
        return [rows[t] for t in wanted]
    return list(rows.values())


def _line(row) -> str:
    s = status(row)
    mark = {True: "есть", False: "нет", None: "проверьте сами"}[s["ok"]]
    heavy = ", тяжёлое" + (" " + row["size"] if row.get("size") else "") if row.get("heavy") else ""
    warn = "\n    ! " + row["warning"] if row.get("warning") else ""
    pin = row["pin"] + (" [{}]".format(row["pin_note"]) if row.get("pin_note") else "")
    return "{:<14} {:<15} пин {} ({}){} — {}{}".format(row["id"], mark, pin, row["license"], heavy,
                                                      s["note"], warn)


def _npm_plan(step) -> str:
    from .npm import prefix_for

    package = step["package"].rsplit("@", 1)[0]
    if step.get("lock"):
        how = "npm ci --ignore-scripts --prefix {} по проверенному lock-файлу catalog/{} ({})".format(
            prefix_for(package), step["lock"], step["package"])
    else:
        how = "npm install --ignore-scripts --prefix {} {}".format(prefix_for(package), step["package"])
    browser_note = ("браузер рендера ляжет в ~/.cache/hyperframes/chrome (≈200 МБ) — он общий с другими "
                    "установками HyperFrames и не удаляется вместе с префиксом" if package == "hyperframes" else
                    "браузер рендера ляжет в node_modules/.remotion внутри префикса Remotion")
    after = (" и `{} {}`: {}".format(package, " ".join(step["after"]), browser_note)
             if step.get("after") else "")
    return how + " — не глобально" + after


def plan(row) -> str:
    step = row["install"].get(current_os())
    if not step:
        return "{}: на этой системе не ставится".format(row["id"])
    what = {"command": lambda: " ".join(step["argv"]), "pip": lambda: "pip install " + pip_package(step),
            "npm": lambda: _npm_plan(step),
            "download": lambda: "скачать " + step["url"] + " → " + step["save_to"],
            "zip": lambda: "скачать проверенный архив CPU x64/ARM64 → " + step["save_to"],
            "manual": lambda: "вручную: " + step["url"] + (" → " + step["save_to"] if step.get("save_to") else "")}
    return "{} {}: {}{}".format(row["id"], row["pin"], what[step["kind"]](),
                                " ({})".format(row["size"]) if row.get("size") else "")


def requirements(rows) -> str:
    """Pinned pip requirements of the rows for this Python and system, one per line (CI installs them)."""
    steps = []
    for row in rows:
        floor = row.get("min_python")
        if floor and sys.version_info[:2] < tuple(int(x) for x in floor.split(".")):
            continue
        steps.append(row["install"].get(current_os()))
    return "\n".join(pip_package(s) for s in steps if s and s.get("kind") == "pip")


def cmd_doctor(opt) -> str:
    rows = _rows(opt)
    if getattr(opt, "requirements", False):
        return requirements(rows)
    if not opt.install:
        return "\n".join(_line(r) for r in rows) or "Для выбранных шагов ничего не нужно"
    row = next((r for r in catalog.tools(Path(opt.catalog) if opt.catalog else None).values()
                if r["id"] == opt.install), None)
    if row is None:
        raise CliError("В каталоге нет {}".format(opt.install))
    head = "План установки — " + plan(row) + ("\n! " + row["warning"] if row.get("warning") else "")
    if not opt.yes:
        return head + "\nНичего не поставлено: нужно «да» человека, затем тот же вызов с --yes."
    result = run_install(row)
    if row["install"].get(current_os(), {}).get("kind") == "manual":
        return head + "\n" + result
    checked = status(row)
    if checked["ok"] is not True:
        raise CliError("{}: установка завершилась, но проверка не прошла: {}".format(row["id"], checked["note"]))
    return head + "\n" + result + "\nПроверено: " + checked["note"]
