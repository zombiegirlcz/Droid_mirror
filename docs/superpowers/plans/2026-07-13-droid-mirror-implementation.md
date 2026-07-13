# Droid Mirror Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a functioning open-source ADB/scrcpy fleet manager CLI tool with numbered text menu.

**Architecture:** Pure Python 3.11+ pip package with entry point `droid`. Single module `core/adb_wrapper.py` wraps `subprocess` calls to `adb`/`scrcpy`. Numbered menu in `app.py` dispatches to command modules (`commands/*.py`). Zero third-party dependencies.

**Tech Stack:** Python 3.11+, `subprocess`, `argparse` (for `__main__.py` entry), GPLv3.

## Global Constraints

- Pure Python 3.11+ — zero third-party dependencies (no `rich`, `click`, `questionary`, etc.)
- Every `adb`/`scrcpy` command MUST be logged to stderr as `[ADB] <command>` before execution
- Binary resolution: check PATH first, fall back to bundled `bin/<name>.exe` on Windows, raise `FileNotFoundError` if neither found
- No phone-home, analytics, telemetry, or license check of any kind
- All user-facing text in Czech (menu labels, prompts, messages)
- Package name: `droid` (entry point), project name: `droid-mirror`

---
### Task 1: Project skeleton and pip package

**Files:**
- Create: `src/droid/__init__.py` (empty)
- Create: `src/droid/__main__.py` (entry for `python -m droid`)
- Create: `pyproject.toml` (build config)
- Create: `LICENSE` (GPLv3)
- Create: `src/droid/bin/.gitkeep`

**Interfaces:**
- Consumes: nothing
- Produces: `droid` entry point → calls `droid.app:main`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "droid-mirror"
version = "1.0.0"
description = "Open-source ADB/scrcpy Fleet Manager"
readme = "README.md"
license = { text = "GPLv3" }
requires-python = ">=3.11"

[project.scripts]
droid = "droid.app:main"
```

- [ ] **Step 2: Create `src/droid/__init__.py`**

Empty file.

- [ ] **Step 3: Create `src/droid/__main__.py`**

```python
from droid.app import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Create `LICENSE`**

Copy the full GPLv3 license text (standard template). Use the official GPLv3 text.

- [ ] **Step 5: Create `src/droid/bin/.gitkeep`**

Empty file.

- [ ] **Step 6: Verify skeleton**

```bash
cd /path/to/droid-screen
pip install -e .
python -m droid
```

Expected: runs `main()` from app.py (will fail with ImportError until Task 3).

---

### Task 2: core/adb_wrapper.py — subprocess wrapper

**Files:**
- Create: `src/droid/core/__init__.py` (empty)
- Create: `src/droid/core/adb_wrapper.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `adb_run(args: list[str]) -> str` — runs `adb <args>`, logs command to stderr, returns stdout
  - `scrcpy_run(args: list[str]) -> None` — runs `scrcpy <args>` as passthrough (stream)
  - `find_binary(name: str) -> str` — resolves PATH → bundled → error

- [ ] **Step 1: Create `src/droid/core/__init__.py`**

Empty file.

- [ ] **Step 2: Write `src/droid/core/adb_wrapper.py`**

```python
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
    On non-zero exit, prints error to stderr but does NOT raise —
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
    Does NOT wait for completion — useful for screen mirroring.
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
```

- [ ] **Step 3: Quick smoke test**

```python
python -c "from droid.core.adb_wrapper import adb_run; print(repr(adb_run(['--help'])[:200]))"
```

Expected: prints first 200 chars of `adb --help` output (or error if no adb found — OK for now).

---

### Task 3: app.py — ASCII logo + main menu + submenu skeleton

**Files:**
- Create: `src/droid/app.py`
- Modify: `src/droid/__main__.py` (already done in Task 1)

**Interfaces:**
- Consumes: `droid.core.adb_wrapper.adb_run()`, `droid.commands.device.*`, etc.
- Produces: `main()` — entry point that renders menu and dispatches

- [ ] **Step 1: Write `src/droid/app.py`**

```python
"""
Droid Mirror — hlavní menu loop s ASCII logem.
Číslované menu, žádné externí závislosti.
"""

import sys

LOGO = """
██████╗ ██████╗  ██████╗ ██╗██████╗     ███╗   ███╗██╗██████╗ ██████╗  ██████╗ ██████╗
██╔══██╗██╔══██╗██╔═══██╗██║██╔══██╗    ████╗ ████║██║██╔══██╗██╔══██╗██╔═══██╗██╔══██╗
██║  ██║██████╔╝██║   ██║██║██║  ██║    ██╔████╔██║██║██████╔╝██████╔╝██║   ██║██████╔╝
██║  ██║██╔══██╗██║   ██║██║██║  ██║    ██║╚██╔╝██║██║██╔══██╗██╔══██╗██║   ██║██╔══██╗
██████╔╝██║  ██║╚██████╔╝██║██████╔╝    ██║ ╚═╝ ██║██║██║  ██║██║  ██║╚██████╔╝██║  ██║
╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝╚═════╝     ╚═╝     ╚═╝╚═╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝

          Open-source ADB Fleet Manager  |  GPLv3
"""


def print_header():
    """Clear screen (ANSI) and print logo + header."""
    print("\033[2J\033[H", end="")  # clear screen
    print(LOGO)
    print()


def print_menu(title: str, options: list[tuple[str, str]]) -> str | None:
    """
    Zobrazí číslované menu a vrátí vybranou klíč nebo None pro návrat.

    options: list of (key, label) — klíč "0" je vždy vyhrazen pro návrat.
    """
    print(f"── {title} ──\n")
    for key, label in options:
        print(f"  {key}. {label}")
    print()
    choice = input("Vyber možnost: ").strip()
    return choice


def main():
    """Hlavní vstupní bod — zobrazí logo a main menu."""
    while True:
        print_header()
        print_menu("HLAVNÍ MENU", [
            ("1", "Device Management"),
            ("2", "App Management"),
            ("3", "File Operations"),
            ("4", "System Monitoring"),
            ("5", "Screen Mirroring"),
            ("6", "WiFi / Fleet"),
            ("7", "Wireless Debugging Pairing"),
            ("8", "Exit"),
        ])
        choice = input("Vyber možnost (1-8): ").strip()

        match choice:
            case "1":
                from droid.commands.device import menu as m
                m()
            case "2":
                from droid.commands.apps import menu as m
                m()
            case "3":
                from droid.commands.files import menu as m
                m()
            case "4":
                from droid.commands.monitor import menu as m
                m()
            case "5":
                from droid.commands.mirror import menu as m
                m()
            case "6":
                from droid.commands.wifi import menu as m
                m()
            case "7":
                from droid.commands.pairing import menu as m
                m()
            case "8":
                print("\nDíky za použití Droid Mirror. Nashle!")
                break
            case _:
                print("\nNeplatná volba, zkus znovu.")
                input("Stiskni Enter pro pokračování...")
```

- [ ] **Step 2: Test basic menu**

```bash
cd /path/to/droid-screen
pip install -e .
python -m droid
```

Expected: Logo shows, menu shows, "8" exits, invalid choices show error and loop.

---

### Task 4: commands/device.py — Device Management

**Files:**
- Create: `src/droid/commands/__init__.py` (empty)
- Create: `src/droid/commands/device.py`

**Interfaces:**
- Consumes: `adb_run(args: list[str]) -> str` from `droid.core.adb_wrapper`
- Produces: `menu()` — device management submenu

- [ ] **Step 1: Create `src/droid/commands/__init__.py`**

Empty file.

- [ ] **Step 2: Write `src/droid/commands/device.py`**

```python
"""Device Management — list, connect, disconnect, info, reboot, shell."""

import subprocess
import sys

from droid.core.adb_wrapper import adb_run, find_binary


def list_devices():
    print(adb_run(["devices", "-l"]))


def connect_wifi():
    host = input("IP adresa: ").strip()
    port = input("Port (výchozí 5555): ").strip() or "5555"
    print(adb_run(["connect", f"{host}:{port}"]))


def disconnect():
    target = input("IP:Port k odpojení (nebo Enter = vše): ").strip()
    if target:
        print(adb_run(["disconnect", target]))
    else:
        print(adb_run(["disconnect"]))


def device_info():
    print(adb_run(["shell", "getprop"]))


def reboot_menu():
    print("\n── Reboot ──")
    print("  1. Normal (system)")
    print("  2. Bootloader")
    print("  3. Recovery")
    print("  4. Zpět")
    choice = input("Vyber možnost (1-4): ").strip()
    match choice:
        case "1": print(adb_run(["reboot"]))
        case "2": print(adb_run(["reboot", "bootloader"]))
        case "3": print(adb_run(["reboot", "recovery"]))
        case _: return


def shell():
    """Interactive adb shell passthrough."""
    try:
        adb_path = find_binary("adb")
        print("[*] Spouštím adb shell. Pro ukončení zadej 'exit' nebo Ctrl+D.")
        subprocess.run([adb_path, "shell"], check=False)
    except FileNotFoundError as e:
        print(f"[CHYBA] {e}", file=sys.stderr)


def menu():
    input_handler = input  # local ref for submenu reuse

    while True:
        print("\n── Device Management ──\n")
        print("  1. List devices          (adb devices -l)")
        print("  2. Connect (WiFi)        (adb connect <ip>:<port>)")
        print("  3. Disconnect            (adb disconnect)")
        print("  4. Device info           (adb shell getprop)")
        print("  5. Reboot                (normal / bootloader / recovery)")
        print("  6. Shell                 (interaktivní adb shell)")
        print("  7. Zpět\n")
        choice = input("Vyber možnost (1-7): ").strip()

        match choice:
            case "1": list_devices()
            case "2": connect_wifi()
            case "3": disconnect()
            case "4": device_info()
            case "5": reboot_menu()
            case "6": shell()
            case "7": break
            case _: print("\nNeplatná volba.")

        if choice != "7":
            input("\nStiskni Enter pro pokračování...")
```

- [ ] **Step 3: Quick test**

```bash
python -m droid
# → Device Management → 1 (should list devices or show "no devices")
```

---

### Task 5: commands/apps.py — App Management

**Files:**
- Create: `src/droid/commands/apps.py`

**Interfaces:**
- Consumes: `adb_run(args: list[str]) -> str`
- Produces: `menu()` — app management submenu

- [ ] **Step 1: Write `src/droid/commands/apps.py`**

```python
"""App Management — list, install, uninstall, clear, force-stop, launch, backup."""

from droid.core.adb_wrapper import adb_run


def list_packages():
    print("  Filtrovat: 1 = vše | 2 = third-party (-3) | 3 = system (-s)")
    choice = input("Vyber (1-3): ").strip()
    match choice:
        case "2": print(adb_run(["shell", "pm", "list", "packages", "-3"]))
        case "3": print(adb_run(["shell", "pm", "list", "packages", "-s"]))
        case _: print(adb_run(["shell", "pm", "list", "packages"]))


def install_apk():
    path = input("Cesta k APK souboru: ").strip()
    if path:
        print(adb_run(["install", "-r", path]))


def uninstall():
    pkg = input("Package name (např. com.example.app): ").strip()
    if pkg:
        print(adb_run(["uninstall", pkg]))


def clear_data():
    pkg = input("Package name: ").strip()
    if pkg:
        print(adb_run(["shell", "pm", "clear", pkg]))


def force_stop():
    pkg = input("Package name: ").strip()
    if pkg:
        print(adb_run(["shell", "am", "force-stop", pkg]))


def launch_app():
    pkg = input("Package name: ").strip()
    activity = input("Activity name: ").strip()
    if pkg and activity:
        print(adb_run(["shell", "am", "start", "-n", f"{pkg}/{activity}"]))


def backup_app():
    pkg = input("Package name: ").strip()
    out = input("Výstupní soubor (výchozí backup.ab): ").strip() or "backup.ab"
    if pkg:
        print(adb_run(["backup", "-f", out, pkg]))


def menu():
    while True:
        print("\n── App Management ──\n")
        print("  1. List packages")
        print("  2. Install APK")
        print("  3. Uninstall")
        print("  4. Clear data")
        print("  5. Force stop")
        print("  6. Launch app")
        print("  7. Backup app")
        print("  8. Zpět\n")
        choice = input("Vyber možnost (1-8): ").strip()

        match choice:
            case "1": list_packages()
            case "2": install_apk()
            case "3": uninstall()
            case "4": clear_data()
            case "5": force_stop()
            case "6": launch_app()
            case "7": backup_app()
            case "8": break
            case _: print("\nNeplatná volba.")

        if choice != "8":
            input("\nStiskni Enter pro pokračování...")
```

---

### Task 6: commands/files.py — File Operations

**Files:**
- Create: `src/droid/commands/files.py`

**Interfaces:**
- Consumes: `adb_run(args: list[str]) -> str`
- Produces: `menu()` — file operations submenu

- [ ] **Step 1: Write `src/droid/commands/files.py`**

```python
"""File Operations — push, pull, ls, rm, mkdir."""

from droid.core.adb_wrapper import adb_run


def push_file():
    local = input("Lokální cesta: ").strip()
    remote = input("Vzdálená cesta: ").strip()
    if local and remote:
        print(adb_run(["push", local, remote]))


def pull_file():
    remote = input("Vzdálená cesta: ").strip()
    local = input("Lokální cíl (výchozí .): ").strip() or "."
    if remote:
        print(adb_run(["pull", remote, local]))


def list_dir():
    path = input("Cesta (výchozí /sdcard): ").strip() or "/sdcard"
    print(adb_run(["shell", "ls", "-la", path]))


def delete_file():
    path = input("Cesta k souboru: ").strip()
    if path:
        print(adb_run(["shell", "rm", path]))


def mkdir():
    path = input("Cesta k adresáři: ").strip()
    if path:
        print(adb_run(["shell", "mkdir", "-p", path]))


def menu():
    while True:
        print("\n── File Operations ──\n")
        print("  1. Push file   (adb push <local> <remote>)")
        print("  2. Pull file   (adb pull <remote> <local>)")
        print("  3. List dir    (adb shell ls -la)")
        print("  4. Delete file (adb shell rm)")
        print("  5. Mkdir       (adb shell mkdir)")
        print("  6. Zpět\n")
        choice = input("Vyber možnost (1-6): ").strip()

        match choice:
            case "1": push_file()
            case "2": pull_file()
            case "3": list_dir()
            case "4": delete_file()
            case "5": mkdir()
            case "6": break
            case _: print("\nNeplatná volba.")

        if choice != "6":
            input("\nStiskni Enter pro pokračování...")
```

---

### Task 7: commands/monitor.py — System Monitoring

**Files:**
- Create: `src/droid/commands/monitor.py`

**Interfaces:**
- Consumes: `adb_run(args: list[str]) -> str`
- Produces: `menu()` — monitoring submenu

- [ ] **Step 1: Write `src/droid/commands/monitor.py`**

```python
"""System Monitoring — battery, memory, CPU, storage, processes."""

from droid.core.adb_wrapper import adb_run


def battery():
    print(adb_run(["shell", "dumpsys", "battery"]))


def memory():
    print(adb_run(["shell", "dumpsys", "meminfo"]))


def cpu():
    print(adb_run(["shell", "dumpsys", "cpuinfo"]))


def storage():
    print(adb_run(["shell", "df", "-h"]))


def processes():
    print(adb_run(["shell", "ps", "-A"]))


def menu():
    while True:
        print("\n── System Monitoring ──\n")
        print("  1. Battery   (dumpsys battery)")
        print("  2. Memory    (dumpsys meminfo)")
        print("  3. CPU       (dumpsys cpuinfo)")
        print("  4. Storage   (df -h)")
        print("  5. Processes (ps -A)")
        print("  6. Zpět\n")
        choice = input("Vyber možnost (1-6): ").strip()

        match choice:
            case "1": battery()
            case "2": memory()
            case "3": cpu()
            case "4": storage()
            case "5": processes()
            case "6": break
            case _: print("\nNeplatná volba.")

        if choice != "6":
            input("\nStiskni Enter pro pokračování...")
```

---

### Task 8: commands/mirror.py — Screen Mirroring

**Files:**
- Create: `src/droid/commands/mirror.py`

**Interfaces:**
- Consumes: `scrcpy_run(args: list[str]) -> None` from `droid.core.adb_wrapper`
- Produces: `menu()` — mirroring submenu

- [ ] **Step 1: Write `src/droid/commands/mirror.py`**

```python
"""Screen Mirroring — scrcpy passthrough."""

from droid.core.adb_wrapper import scrcpy_run


def mirror_screen():
    print("[*] Spouštím scrcpy — pro ukončení zavři okno scrcpy.")
    scrcpy_run([])


def record_screen():
    path = input("Cílová cesta (např. record.mp4): ").strip() or "record.mp4"
    print(f"[*] Nahrávám obrazovku do {path} — Ctrl+C pro ukončení.")
    scrcpy_run(["--record", path])


def menu():
    while True:
        print("\n── Screen Mirroring ──\n")
        print("  1. Mirror screen      (scrcpy)")
        print("  2. Record screen      (scrcpy --record)")
        print("  3. Zpět\n")
        choice = input("Vyber možnost (1-3): ").strip()

        match choice:
            case "1": mirror_screen()
            case "2": record_screen()
            case "3": break
            case _: print("\nNeplatná volba.")

        if choice != "3":
            input("\nStiskni Enter pro pokračování...")
```

---

### Task 9: commands/wifi.py + commands/pairing.py — WiFi/Fleet + Pairing

**Files:**
- Create: `src/droid/commands/wifi.py`
- Create: `src/droid/commands/pairing.py`

**Interfaces:**
- Consumes: `adb_run(args: list[str]) -> str`
- Produces: `menu()` for each

- [ ] **Step 1: Write `src/droid/commands/wifi.py`**

```python
"""WiFi / Fleet — enable TCP/IP mode + batch connect."""

from droid.core.adb_wrapper import adb_run


def enable_tcpip():
    port = input("Port (výchozí 5555): ").strip() or "5555"
    print("[*] Nastavuji TCP/IP mód (vyžaduje aktivní USB spojení).")
    print(adb_run(["tcpip", port]))


def batch_connect():
    print("Zadej IP adresy zařízení (oddělené mezerou nebo čárkou).")
    print("Příklad: 192.168.1.10 192.168.1.11 192.168.1.12")
    ips = input("IP adresy: ").strip().replace(",", " ").split()
    port = input("Port (výchozí 5555): ").strip() or "5555"

    if not ips:
        print("[!] Nezadána žádná IP adresa.")
        return

    for ip in ips:
        ip = ip.strip()
        if ip:
            print(f"[*] Připojuji {ip}:{port}...")
            print(adb_run(["connect", f"{ip}:{port}"]))


def menu():
    while True:
        print("\n── WiFi / Fleet ──\n")
        print("  1. Enable TCP/IP mode    (adb tcpip 5555)")
        print("  2. Batch connect         (adb connect přes seznam IP)")
        print("  3. Zpět\n")
        choice = input("Vyber možnost (1-3): ").strip()

        match choice:
            case "1": enable_tcpip()
            case "2": batch_connect()
            case "3": break
            case _: print("\nNeplatná volba.")

        if choice != "3":
            input("\nStiskni Enter pro pokračování...")
```

- [ ] **Step 2: Write `src/droid/commands/pairing.py`**

```python
"""Wireless Debugging Pairing — wrapper over 'adb pair'."""

from droid.core.adb_wrapper import adb_run


def pair_device():
    print("\n── Wireless Debugging Pairing ──")
    print("Na telefonu otevři: Vývojářské možnosti → Bezdrátové ladění →")
    print("Spárovat zařízení pomocí párovacího kódu")
    print("A zadej údaje níže.\n")
    host = input("IP adresa a port (např. 192.168.1.10:42345): ").strip()
    code = input("Párovací kód (např. 123456): ").strip()

    if host and code:
        print(f"[*] Páruji s {host}...")
        print(adb_run(["pair", host, code]))
    else:
        print("[!] Musíš zadat IP:port i párovací kód.")


def menu():
    while True:
        print("\n── Wireless Debugging Pairing ──\n")
        print("  1. Pair device   (adb pair <host>:<port> <code>)")
        print("  2. Zpět\n")
        choice = input("Vyber možnost (1-2): ").strip()

        match choice:
            case "1": pair_device()
            case "2": break
            case _: print("\nNeplatná volba.")

        if choice != "2":
            input("\nStiskni Enter pro pokračování...")
```

---

### Task 10: README + git init + final integration check

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`**

```markdown
# Droid Mirror 🪞

Open-source ADB/scrcpy Fleet Manager — CLI nástroj pro správu Android zařízení.

**Žádný backdoor. Žádné phone-home. Pouze standardní ADB a scrcpy příkazy.**

Co nástroj dělá, je vidět v kódu a každý ADB/scrcpy příkaz je logován do konzole.

## Instalace

### Požadavky

- Python 3.11+
- ADB (platform-tools) — [download](https://developer.android.com/studio/releases/platform-tools)
- scrcpy (volitelné, pro mirroring) — [download](https://github.com/Genymobile/scrcpy)

*Na Windows stačí stáhnout a rozbalit — droid-mirror automaticky použije
zabalené binárky, pokud nejsou v PATH.*

### Pip instalace

```bash
pip install droid-mirror
droid
```

### Nebo z repa

```bash
git clone https://github.com/<user>/droid-mirror.git
cd droid-mirror
pip install -e .
droid
```

## Použití

Spusť `droid` v terminálu. Zobrazí se číslované menu:

```
  1. Device Management    — list, connect, disconnect, info, reboot, shell
  2. App Management       — list packages, install, uninstall, clear, force-stop, launch
  3. File Operations      — push, pull, ls, rm, mkdir
  4. System Monitoring    — battery, memory, CPU, storage, processes
  5. Screen Mirroring     — scrcpy mirror / record
  6. WiFi / Fleet         — TCP/IP mode, batch connect
  7. Wireless Debugging   — adb pair wrapper
  8. Exit
```

Každý příkaz je zalogovaný:
```
[ADB] adb devices -l
[ADB] adb connect 192.168.1.10:5555
```

## Bezpečnost

- Nástroj funguje JEN na zařízeních, kde má uživatel vědomě zapnuté
  **USB debugging** nebo **Wireless debugging** v Developer options.
- Není možné se vzdáleně připojit k zařízení bez fyzické interakce.
- Nástroj neodesílá žádná data (žádná telemetrie, žádný license check).
- Nástroj není root kit — využívá pouze veřejné ADB API.

## Licence

GPLv3 — jakýkoliv closed-source fork je právně vyloučen.
```

- [ ] **Step 2: Git init + initial commit**

```bash
cd /path/to/droid-screen
git init
git add .
git commit -m "feat: initial Droid Mirror v1.0

- Project skeleton with pip packaging
- core/adb_wrapper.py — subprocess wrapper with binary resolution
- app.py — ASCII logo and numbered menu system
- commands/ — device, apps, files, monitor, mirror, wifi, pairing
- GPLv3 license
- README with security guarantees"
```

- [ ] **Step 3: Final integration test**

```bash
pip install -e .
python -m droid
```

Verify:
- Logo shows correctly
- All menu items navigate correctly
- "Exit" returns cleanly
- Invalid menu choices handled gracefully
- `python -m droid` and `droid` both work
