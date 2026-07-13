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
    print(f"[ADB] {' '.join(cmd)}", file=sys.stderr)

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
    Run 'scrcpy <args>' as a passthrough subprocess (inherits stdin/stdout).
    Does NOT wait for completion -- useful for screen mirroring.
    """
    global _SCRCPY_PATH
    if _SCRCPY_PATH is None:
        _SCRCPY_PATH = find_binary("scrcpy")

    cmd = [_SCRCPY_PATH] + args
    print(f"[SCRCPY] {' '.join(cmd)}", file=sys.stderr)

    try:
        subprocess.run(cmd, check=False)
    except FileNotFoundError:
        print(f"[CHYBA] scrcpy binary nenalezen: {_SCRCPY_PATH}", file=sys.stderr)
    except Exception as e:
        print(f"[CHYBA] scrcpy selhal: {e}", file=sys.stderr)
