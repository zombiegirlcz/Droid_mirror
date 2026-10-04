"""
Droid Mirror -- ANSI barvy a formátování (žádné externí závislosti).

Truecolor ANSI escape kódy. Pokud je NO_COLOR nastaveno nebo stdout není
TTY, barvy se vypnou (plain text). Barvy se také vypnou, pokud je nastavena
proměnná prostředí DROID_PLAIN (užitečné pro logy/piping).
"""

import os
import sys

# Android brand zelená #3DDC84
ANDROID_GREEN = "\x1b[38;2;61;220;132m"
RED = "\x1b[38;2;255;85;85m"
YELLOW = "\x1b[38;2;255;204;0m"
GREEN = "\x1b[38;2;80;200;120m"
DIM = "\x1b[2m"
BOLD = "\x1b[1m"
RESET = "\x1b[0m"


def _colors_enabled() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("DROID_PLAIN"):
        return False
    return sys.stdout.isatty()


def green(text: str) -> str:
    return f"{ANDROID_GREEN}{text}{RESET}" if _colors_enabled() else text


def red(text: str) -> str:
    return f"{RED}{text}{RESET}" if _colors_enabled() else text


def yellow(text: str) -> str:
    return f"{YELLOW}{text}{RESET}" if _colors_enabled() else text


def dim(text: str) -> str:
    return f"{DIM}{text}{RESET}" if _colors_enabled() else text


def bold(text: str) -> str:
    return f"{BOLD}{text}{RESET}" if _colors_enabled() else text


def box(title: str, body: str) -> str:
    """Obarvený rám kolem adb výstupu. Vrací string (volající vytiskne)."""
    if not body:
        body = "(žádný výstup)"
    lines = body.rstrip("\n").split("\n")
    inner = max(
        [len(title)] + [len(l) for l in lines] + [20]
    )
    T = max(inner + 4, len(title) + 6, 24)
    out = []
    top_inner = ("┌─ " + title + " ").ljust(T - 1, "─")
    out.append(green(top_inner + "┐"))
    for l in lines:
        row = ("│ " + l).ljust(T - 1) + "│"
        out.append(green(row[:2]) + row[2:-1] + green(row[-1]))
    out.append(green("└" + "─" * (T - 2) + "┘"))
    return "\n".join(out)


def logcat_color(level: str, line: str) -> str:
    """Obarví jeden logcat řádek podle priority (E/W/I/D/V)."""
    level = (level or "?").upper()
    cmap = {"E": RED, "W": YELLOW, "I": GREEN, "D": DIM, "V": DIM}
    color = cmap.get(level)
    if not _colors_enabled() or not color:
        return line
    return f"{color}{line}{RESET}"
