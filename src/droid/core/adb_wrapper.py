"""
ADB/scrcpy subprocess wrapper with command logging and binary resolution.
Zero third-party dependencies.
"""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from droid.ui import style

_ADB_PATH: str | None = None
_SCRCPY_PATH: str | None = None


def _bundled_dir() -> Path:
    """Return path to the bundled bin/ directory adjacent to this package."""
    return Path(__file__).resolve().parent.parent / "bin"


def find_binary(name: str) -> str:
    """
    Resolve path to a binary (adb or scrcpy).

    1. Check PATH via shutil.which()
    2. Fall back to bundled bin/<name>.exe on Windows
    3. Raise FileNotFoundError with install instructions
    """
    path = shutil.which(name)
    if path:
        return path

    if platform.system() == "Windows":
        bundled = _bundled_dir() / f"{name}.exe"
        if bundled.exists():
            print(
                f"[!] {name} nebyl v PATH, používám zabalenou verzi: {bundled}",
                file=sys.stderr,
            )
            return str(bundled)

    if name == "adb":
        install_hint = "Stáhni ADB z https://developer.android.com/studio/releases/platform-tools"
    elif name == "scrcpy":
        install_hint = "Stáhni scrcpy z https://github.com/Genymobile/scrcpy"
    else:
        install_hint = f"Nainstaluj {name} a přidej ho do PATH"

    raise FileNotFoundError(
        f"{name} nebyl nalezen v PATH ani v bundled bin/.\n{install_hint}"
    )


def adb_run(args: list[str]) -> str:
    """
    Run 'adb <args>' as a subprocess.

    Logs the full command to stderr, returns stdout as str.
    On non-zero exit, prints error to stderr but does NOT raise --
    returns stdout (which often contains the error message).
    """
    global _ADB_PATH
    if _ADB_PATH is None:
        _ADB_PATH = find_binary("adb")

    cmd = [_ADB_PATH] + args
    print(f"{style.dim('[ADB]')} {' '.join(args)}", file=sys.stderr)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            print(
                f"[CHYBA] adb vrátil kód {result.returncode}: {result.stderr.strip()}",
                file=sys.stderr,
            )
        return result.stdout
    except FileNotFoundError:
        print(f"[CHYBA] adb binary nenalezen: {_ADB_PATH}", file=sys.stderr)
        return ""
    except Exception as e:
        print(f"[CHYBA] adb selhal: {e}", file=sys.stderr)
        return ""


def scrcpy_run(args: list[str]) -> None:
    """
    Spustí 'scrcpy <args>' na pozadí (NEPOČKÁ na dokončení).

    Uživatel se okamžitě vrátí do menu, zrcadlení běží dál a droid
    mezitím přijímá další adb příkazy. Okno scrcpy zavře pro ukončení.
    """
    global _SCRCPY_PATH
    if _SCRCPY_PATH is None:
        _SCRCPY_PATH = find_binary("scrcpy")

    cmd = [_SCRCPY_PATH] + args
    print(f"{style.dim('[SCRCPY]')} {' '.join(args)}", file=sys.stderr)

    try:
        if platform.system() == "Windows":
            subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            subprocess.Popen(cmd, start_new_session=True)
        print(
            style.dim("  scrcpy spuštěno na pozadí — zavři okno pro ukončení."),
            file=sys.stderr,
        )
    except FileNotFoundError:
        print(style.red(f"[CHYBA] scrcpy binary nenalezen: {_SCRCPY_PATH}"), file=sys.stderr)
    except Exception as e:
        print(style.red(f"[CHYBA] scrcpy selhal: {e}"), file=sys.stderr)


# ---- logcat streaming + filtrování ----

_LOGCAT_LEVELS = {"V": 1, "D": 2, "I": 3, "W": 4, "E": 5, "F": 6}


def extract_logcat_priority(line: str) -> str | None:
    """
    Vratí prioritní písmeno (E/W/I/D/V/F) z radku logcat, nebo None.
    Format: 'MM-DD HH:MM:SS.mmm  PID  TID  P  TAG: zprava'
    """
    parts = line.split(None, 5)
    if len(parts) >= 6:
        return parts[4].upper()
    return None


def filter_logcat_line(line: str, filters: dict) -> bool:
    """Vratí True, pokud radek projde vsemi zadanymi filtry."""
    prio = extract_logcat_priority(line)
    min_level = filters.get("priority")
    if min_level and prio and prio in _LOGCAT_LEVELS:
        if _LOGCAT_LEVELS[prio] < _LOGCAT_LEVELS.get(min_level.upper(), 1):
            return False

    if filters.get("tag"):
        tag = (line.split(None, 5)[5].split(":", 1)[0] if len(line.split(None, 5)) >= 6 else "")
        if filters["tag"].lower() not in tag.lower():
            return False

    if filters.get("keyword"):
        msg = line.split(":", 1)[1] if ":" in line else line
        if filters["keyword"].lower() not in msg.lower():
            return False

    return True


def adb_logcat_stream(filters: dict) -> None:
    """Spustí `adb logcat` jako živý stream, filtruje + obarví klientky."""
    global _ADB_PATH
    if _ADB_PATH is None:
        _ADB_PATH = find_binary("adb")

    print(
        f"{style.dim('[LOGCAT]')} stream spuštěn — filtry: {filters} "
        f"(Ctrl+C pro zastavení)",
        file=sys.stderr,
    )
    try:
        proc = subprocess.Popen(
            [_ADB_PATH, "logcat"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        for line in proc.stdout:
            if not filter_logcat_line(line, filters):
                continue
            print(style.logcat_color(extract_logcat_priority(line) or "", line.rstrip("\n")))
    except KeyboardInterrupt:
        proc.terminate()
        print(style.dim("\n[LOGCAT] zastaveno."), file=sys.stderr)
    except FileNotFoundError:
        print(style.red("[CHYBA] adb binary nenalezen"), file=sys.stderr)
