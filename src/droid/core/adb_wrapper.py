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
    returns stdout (which often contains the error message). Pokud je
    stdout prázdný (napr. neúspěšný příkaz), vrací stderr, aby se chyba
    zobrazila uvnitř boxu místo "(žádný výstup)".
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
                f"{style.dim('[CHYBA]')} adb vrátil kód {result.returncode}",
                file=sys.stderr,
            )
        # Prázdný stdout (napr. neúspěšný příkaz) -> vrať stderr,
        # ať se chyba ukáže v boxu místo "(žádný výstup)".
        if result.stdout.strip():
            return result.stdout
        return result.stderr
    except FileNotFoundError:
        msg = f"adb binary nenalezen: {_ADB_PATH}"
        print(f"{style.red('[CHYBA]')} {msg}", file=sys.stderr)
        return msg
    except Exception as e:
        msg = f"adb selhal: {e}"
        print(f"{style.red('[CHYBA]')} {msg}", file=sys.stderr)
        return msg


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
    parts = line.split(None, 5)
    if len(parts) < 6:
        # Nejde o standardní logcat radek (napr. pokračování) — necháme projít,
        # abychom neztratili data.
        return True

    prio = parts[4].upper()
    rest = parts[5]
    # za oddelovacem "TAG: zprava" jsou tag i zprava
    if ":" in rest:
        tag, msg = rest.split(":", 1)
    else:
        tag, msg = rest, ""

    min_level = filters.get("priority")
    if min_level and prio in _LOGCAT_LEVELS:
        if _LOGCAT_LEVELS[prio] < _LOGCAT_LEVELS.get(min_level.upper(), 1):
            return False

    if filters.get("tag"):
        if filters["tag"].lower() not in tag.lower():
            return False

    if filters.get("keyword"):
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
    proc = None
    try:
        popen_kwargs = dict(
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        # Na Windows nestačí CREATE_NEW_CONSOLE: otevřelo by se navíc syrové
        # konzolové okno s neobarveným logcatem (výstup čteme přes PIPE a
        # obarvujeme sami). Stdout je přesměrován do roury, takže dítě běží
        # na pozadí a my se vrátíme do menu bez dalšího okna.
        if platform.system() != "Windows":
            popen_kwargs["start_new_session"] = True
        proc = subprocess.Popen([_ADB_PATH, "logcat"], **popen_kwargs)
        for line in proc.stdout:
            if not filter_logcat_line(line, filters):
                continue
            print(style.logcat_color(extract_logcat_priority(line) or "", line.rstrip("\n")))
    except KeyboardInterrupt:
        print(style.dim("\n[LOGCAT] zastaveno."), file=sys.stderr)
    except Exception as e:
        print(style.red(f"[CHYBA] logcat stream selhal: {e}"), file=sys.stderr)
    finally:
        if proc is not None:
            try:
                proc.terminate()
            except Exception:
                pass
            try:
                proc.wait(timeout=5)
            except Exception:
                pass
