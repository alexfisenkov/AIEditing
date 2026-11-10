"""Install or check the complete local toolkit, with a restricted repair mode for chosen steps."""
from __future__ import annotations

from . import catalog
from .checks import current_os, status
from .installers import run_install
from .session import CliError


def selected_tools(steps=None, asr=None) -> list:
    rows = catalog.tools()
    if steps:
        chosen = [s.strip() for s in steps.split(",") if s.strip()]
        errors = catalog.check_steps(chosen)
        if errors:
            raise CliError("; ".join(errors))
        return catalog.needs(chosen, asr)["tools"]
    return [name for name, row in rows.items() if current_os() in row.get("install", {})]


def ensure_tools(ids: list[str], check_only: bool = False) -> str:
    """Repair every requested tool; collect errors and fail unless every post-install check is green."""
    rows = catalog.tools()
    unknown = [name for name in ids if name not in rows]
    if unknown:
        raise CliError("В каталоге нет: " + ", ".join(unknown))
    wanted = set(ids)
    pending = list(ids)
    while pending:
        need = rows[pending.pop()].get("needs") or []
        for name in ([need] if isinstance(need, str) else need):
            if name not in rows:
                raise CliError("В каталоге нет зависимости: " + name)
            if name not in wanted:
                wanted.add(name)
                pending.append(name)
    ids = [name for name in rows if name in wanted]
    lines, failures = [], []
    for name in dict.fromkeys(ids):
        row = rows[name]
        before = status(row)
        if before["ok"] is True:
            lines.append("{}: готово — {}".format(name, before["note"]))
            continue
        if check_only:
            failures.append("{}: {}".format(name, before["note"]))
            continue
        step = row.get("install", {}).get(current_os())
        if not step or step.get("kind") == "manual":
            failures.append("{}: нужна ручная установка — {}".format(name, step.get("url", "нет способа установки") if step else "нет способа установки"))
            continue
        try:
            run_install(row)
            after = status(row)
            if after["ok"] is not True:
                raise CliError("после установки: {}".format(after["note"]))
            lines.append("{}: установлено и проверено — {}".format(name, after["note"]))
        except (CliError, OSError, ValueError) as exc:
            failures.append("{}: {}".format(name, exc))
    if failures:
        raise CliError("\n".join(lines + ["Не готово:"] + failures))
    return "\n".join(lines) or "Для выбранных шагов ничего не требуется"


def cmd_setup(opt) -> str:
    return ensure_tools(selected_tools(opt.steps, opt.asr), check_only=opt.check)
