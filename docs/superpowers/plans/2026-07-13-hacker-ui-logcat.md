# Hacker UI + logcat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Přidat terminálový „hacker" vzhled (zelené Android logo, čistý `[ADB]` log, orámované výstupy) a použitelný živý, filtrovatelný logcat — bez nových závislostí.

**Architecture:** Nový modul `src/droid/ui/style.py` poskytuje čisté ANSI truecolor helpery (žádná knihovna). `adb_wrapper.py` zkracuje log řádky a přidává streamovaný `adb logcat` s klientským filtrováním (čistá pure funkce pro testovatelnost). Command moduly obalí surový adb text do `style.box(...)`. Vše zůstává „co vidíš = co adb dělá".

**Tech Stack:** Python 3.11+, stdlib `subprocess`/`unittest` (žádné nové runtime závislosti). Testy přes `unittest` (žádný pytest potřeba).

## Global Constraints

- Žádné nové runtime závislosti (pouze ANSI escape kódy). [spec §Principy]
- Surový adb text se nemění, jen se orámovává (režim A, bez parsování). [spec §4]
- Zachovat bezpečnostní guardraily (logování příkazů, žádné volání domů). [spec §Principy]
- Android zelená `#3DDC84` = `"\x1b[38;2;61;220;132m"`. [spec §1]
- Barvy se vypnou, pokud je `NO_COLOR` nastaveno nebo `sys.stdout` není TTY. [spec §1]
- `scrcpy_run` spouští scrcpy **na pozadí (neblokující)** — po spuštění se okamžitě vrátí do menu, zrcadlení běží dál a lze používat další adb příkazy. [požadavek uživatele]

---

### Task 1: Modul `src/droid/ui/style.py` + testy

**Files:**
- Create: `src/droid/ui/__init__.py` (prázdný)
- Create: `src/droid/ui/style.py`
- Create: `tests/test_style.py`
- Create: `tests/__init__.py` (prázdný, pro import path)

**Interfaces:**
- Consumes: nic
- Produces: `style.ANDROID_GREEN`, `style.RESET`, `style.green(t)`, `style.red(t)`, `style.yellow(t)`, `style.dim(t)`, `style.bold(t)`, `style.box(title, body) -> str`, `style.logcat_color(level, line) -> str`

- [ ] **Step 1: Write the failing test**

`tests/test_style.py`:
```python
import os
import sys
import io
import unittest

# zajistí import droid i bez editable install
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import droid.ui.style as style


class _TTY(io.StringIO):
    def isatty(self):
        return True


class StyleTest(unittest.TestCase):
    def setUp(self):
        os.environ.pop("NO_COLOR", None)
        self._old = sys.stdout
        sys.stdout = _TTY()

    def tearDown(self):
        sys.stdout = self._old

    def test_colors_enabled_contain_ansi(self):
        out = style.green("hi")
        self.assertIn("\x1b[", out)
        self.assertIn("hi", out)
        self.assertIn(style.RESET, out)

    def test_no_color_env_returns_plain(self):
        os.environ["NO_COLOR"] = "1"
        self.assertEqual(style.green("hi"), "hi")
        self.assertEqual(style.red("x"), "x")
        del os.environ["NO_COLOR"]

    def test_no_tty_returns_plain(self):
        sys.stdout = io.StringIO()  # isatty() -> False
        self.assertEqual(style.green("hi"), "hi")

    def test_android_green_is_correct_rgb(self):
        self.assertEqual(style.ANDROID_GREEN, "\x1b[38;2;61;220;132m")

    def test_box_contains_title_and_body(self):
        out = style.box("devices -l", "abc\ndef")
        self.assertIn("devices -l", out)
        self.assertIn("abc", out)
        self.assertIn("def", out)

    def test_box_empty_body_shows_placeholder(self):
        out = style.box("x", "")
        self.assertIn("žádný výstup", out)

    def test_logcat_color_priority_codes(self):
        e = style.logcat_color("E", "boom")
        self.assertIn("\x1b[", e)
        self.assertIn("boom", e)
        # neznámá priorita -> plain (obsahuje RESET jen pokud obarveno)
        self.assertIn("weird", style.logcat_color("Z", "weird"))

    def test_logcat_color_no_tty_plain(self):
        sys.stdout = io.StringIO()
        self.assertEqual(style.logcat_color("E", "boom"), "boom")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "C:/Users/admin/droid screen" && python -m unittest tests.test_style -v`
Expected: FAIL (ModuleNotFoundError: No module named 'droid.ui.style')

- [ ] **Step 3: Write minimal implementation**

`src/droid/ui/__init__.py` (prázdný soubor).

`src/droid/ui/style.py`:
```python
"""
Droid Mirror -- ANSI barvy a formátování (žádné externí závislosti).

Truecolor ANSI escape kódy. Pokud je NO_COLOR nastaveno nebo stdout není
TTY, barvy se vypnou (plain text).
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
    out.append(green("└" + "─" * (T - 1) + "┘"))
    return "\n".join(out)


def logcat_color(level: str, line: str) -> str:
    """Obarví jeden logcat řádek podle priority (E/W/I/D/V)."""
    level = (level or "?").upper()
    cmap = {"E": RED, "W": YELLOW, "I": GREEN, "D": DIM, "V": DIM}
    color = cmap.get(level)
    if not _colors_enabled() or not color:
        return line
    return f"{color}{line}{RESET}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "C:/Users/admin/droid screen" && python -m unittest tests.test_style -v`
Expected: all PASS (Ran 8 tests)

- [ ] **Step 5: Commit**

```bash
git add src/droid/ui/__init__.py src/droid/ui/style.py tests/__init__.py tests/test_style.py
git commit -m "feat: add ANSI style module (green logo, box, logcat colors)"
```

---

### Task 2: Čistý `[ADB]`/`[SCRCPY]` log + streamovaný logcat

**Files:**
- Modify: `src/droid/core/adb_wrapper.py`
- Create: `tests/test_adb_wrapper_filter.py`

**Interfaces:**
- Consumes: `droid.ui.style` (green, dim, red, logcat_color)
- Produces: `adb_run(args)` nyní loguje `f"[ADB] <args>"` (bez cesty k binárce); `scrcpy_run(args)` loguje `f"[SCRCPY] <args>"`; `extract_logcat_priority(line) -> str|None`; `filter_logcat_line(line, filters) -> bool`; `adb_logcat_stream(filters) -> None`

- [ ] **Step 1: Write the failing test**

`tests/test_adb_wrapper_filter.py`:
```python
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from droid.core.adb_wrapper import extract_logcat_priority, filter_logcat_line


SAMPLE = "07-13 19:14:01.234  1234  1234 E TagName: something broke"
SAMPLE_I = "07-13 19:14:02.000  1234  1234 I OtherTag: info message here"


class FilterTest(unittest.TestCase):
    def test_extract_priority(self):
        self.assertEqual(extract_logcat_priority(SAMPLE), "E")
        self.assertEqual(extract_logcat_priority(SAMPLE_I), "I")
        self.assertIsNone(extract_logcat_priority("malformed line"))

    def test_filter_by_priority_keeps_higher(self):
        self.assertTrue(filter_logcat_line(SAMPLE, {"priority": "W"}))
        self.assertFalse(filter_logcat_line(SAMPLE_I, {"priority": "W"}))
        # V pustí vše
        self.assertTrue(filter_logcat_line(SAMPLE_I, {"priority": "V"}))

    def test_filter_by_tag(self):
        self.assertTrue(filter_logcat_line(SAMPLE, {"tag": "tagname"}))
        self.assertFalse(filter_logcat_line(SAMPLE, {"tag": "nomatch"}))

    def test_filter_by_keyword(self):
        self.assertTrue(filter_logcat_line(SAMPLE, {"keyword": "broke"}))
        self.assertFalse(filter_logcat_line(SAMPLE, {"keyword": "zzz"}))

    def test_combined_filters(self):
        f = {"priority": "W", "tag": "tagname", "keyword": "broke"}
        self.assertTrue(filter_logcat_line(SAMPLE, f))
        f2 = {"priority": "W", "tag": "tagname", "keyword": "zzz"}
        self.assertFalse(filter_logcat_line(SAMPLE, f2))

    def test_empty_filters_keep_everything(self):
        self.assertTrue(filter_logcat_line(SAMPLE, {}))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "C:/Users/admin/droid screen" && python -m unittest tests.test_adb_wrapper_filter -v`
Expected: FAIL (ImportError: cannot import name 'extract_logcat_priority')

- [ ] **Step 3: Write minimal implementation**

V `src/droid/core/adb_wrapper.py`:
1. Přidat na začátek (pod existující importy) import stylu:
```python
from droid.ui import style
```
2. V `adb_run` změnit log řádek (cesta se schová — tiskneme jen args):
```python
    cmd = [_ADB_PATH] + args
    print(f"{style.dim('[ADB]')} {' '.join(args)}", file=sys.stderr)
```
3. V `scrcpy_run` **nahradit celou funkci neblokující verzí** (spustí scrcpy na pozadí a vrátí se do menu; opravuje rozpor mezi docstringem „non-blocking" a původním `subprocess.run`, který blokoval):
```python
import platform  # již importováno v hlavičce souboru

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
```
4. Přidat na konec souboru (před případné existující kód) tyto funkce:
```python
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
    if min_level and prio and prio in _LOGGCAT_LEVELS:
        if _LOGGCAT_LEVELS[prio] < _LOGGCAT_LEVELS.get(min_level.upper(), 1):
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "C:/Users/admin/droid screen" && python -m unittest tests.test_adb_wrapper_filter -v`
Expected: all PASS (Ran 6 tests)

- [ ] **Step 5: Commit**

```bash
git add src/droid/core/adb_wrapper.py tests/test_adb_wrapper_filter.py
git commit -m "feat: clean [ADB] log + streamed/filterable logcat"
```

---

### Task 3: Zelené logo v `app.py`

**Files:**
- Modify: `src/droid/app.py`

**Interfaces:**
- Consumes: `droid.ui.style.green`, `droid.ui.style.bold`
- Produces: `print_header()` tiskne zelené logo

- [ ] **Step 1: Upravit `print_header` a import**

V `src/droid/app.py` přidat import a obalit logo:
```python
from droid.ui import style
```
Změnit `print_header`:
```python
def print_header():
    """Clear screen (ANSI) and print logo + header."""
    print("\033[2J\033[H", end="")  # clear screen
    print(style.green(LOGO))
    print(style.dim("  Open-source ADB Fleet Manager  |  GPLv3"))
    print()
```
Změnit také hlavičku menu v `main()` pro konzistentní vzhled (volitelné, lehké):
```python
        print(style.green("  ── HLAVNÍ MENU ──\n"))
```
(původní `print("  ── HLAVNÍ MENU ──\n")` nahradit výše)

- [ ] **Step 2: Ověřit ručně (bez zařízení)**

Run: `cd "C:/Users/admin/droid screen" && python -m droid`
Expected: logo a hlavička jsou zelené (v TTY terminálu); v ne-TTY (např. piped) plain.
Pro ověření bez TTY: `python -m droid | head -5` → plain text, bez ANSI, bez chyb.

- [ ] **Step 3: Commit**

```bash
git add src/droid/app.py
git commit -m "feat: green Android logo + header"
```

---

### Task 4: Orámování výstupů v command modulech

**Files:**
- Modify: `src/droid/commands/device.py`
- Modify: `src/droid/commands/apps.py`
- Modify: `src/droid/commands/files.py`
- Modify: `src/droid/commands/wifi.py`
- Modify: `src/droid/commands/mirror.py`
- Modify: `src/droid/commands/pairing.py`

**Interfaces:**
- Consumes: `droid.ui.style.box(title, body)`
- Produces: každý `print(adb_run([...]))` nahrazen `print(style.box("<popis>", adb_run([...])))`

- [ ] **Step 1: Přidat import a orámovat v `device.py`**

Na začátek `device.py` přidat:
```python
from droid.ui import style
```
Nahradit volání (použít `style.box`):
```python
def list_devices():
    print(style.box("devices -l", adb_run(["devices", "-l"])))

def connect_wifi():
    host = input("IP adresa: ").strip()
    port = input("Port (vychozí 5555): ").strip() or "5555"
    print(style.box(f"connect {host}:{port}", adb_run(["connect", f"{host}:{port}"])))

def disconnect():
    target = input("IP:Port k odpojení (nebo Enter = vse): ").strip()
    if target:
        print(style.box(f"disconnect {target}", adb_run(["disconnect", target])))
    else:
        print(style.box("disconnect (vse)", adb_run(["disconnect"])))

def device_info():
    print(style.box("getprop", adb_run(["shell", "getprop"])))

def reboot_menu():
    ...
        case "1": print(style.box("reboot", adb_run(["reboot"])))
        case "2": print(style.box("reboot bootloader", adb_run(["reboot", "bootloader"])))
        case "3": print(style.box("reboot recovery", adb_run(["reboot", "recovery"])))
```
(`shell()` zůstává interaktivní passthrough, neobalovat.)

- [ ] **Step 2: Orámovat v `apps.py`**

Import `+` a nahradit:
```python
def list_packages():
    ...
        case "2": print(style.box("pm list packages -3", adb_run(["shell", "pm", "list", "packages", "-3"])))
        case "3": print(style.box("pm list packages -s", adb_run(["shell", "pm", "list", "packages", "-s"])))
        case _: print(style.box("pm list packages", adb_run(["shell", "pm", "list", "packages"])))

def install_apk():
    ...
        print(style.box(f"install -r {path}", adb_run(["install", "-r", path])))

def uninstall():
    ...
        print(style.box(f"uninstall {pkg}", adb_run(["uninstall", pkg])))

def clear_data():
    ...
        print(style.box(f"pm clear {pkg}", adb_run(["shell", "pm", "clear", pkg])))

def force_stop():
    ...
        print(style.box(f"am force-stop {pkg}", adb_run(["shell", "am", "force-stop", pkg])))

def launch_app():
    ...
        print(style.box(f"am start {pkg}/{activity}", adb_run(["shell", "am", "start", "-n", f"{pkg}/{activity}"])))

def backup_app():
    ...
        print(style.box(f"backup -f {out} {pkg}", adb_run(["backup", "-f", out, pkg])))
```

- [ ] **Step 3: Orámovat v `files.py`**

Import `+` a nahradit:
```python
def push_file():
    ...
        print(style.box(f"push {local} -> {remote}", adb_run(["push", local, remote])))

def pull_file():
    ...
        print(style.box(f"pull {remote} -> {local}", adb_run(["pull", remote, local])))

def list_dir():
    path = input("Cesta (vychozí /sdcard): ").strip() or "/sdcard"
    print(style.box(f"ls -la {path}", adb_run(["shell", "ls", "-la", path])))

def delete_file():
    ...
        print(style.box(f"rm {path}", adb_run(["shell", "rm", path])))

def mkdir():
    ...
        print(style.box(f"mkdir -p {path}", adb_run(["shell", "mkdir", "-p", path])))
```

- [ ] **Step 4: Orámovat v `wifi.py`**

Import `+` a nahradit:
```python
def enable_tcpip():
    port = input("Port (vychozí 5555): ").strip() or "5555"
    print(style.box(f"tcpip {port}", adb_run(["tcpip", port])))

def batch_connect():
    ...
            print(style.box(f"connect {ip}:{port}", adb_run(["connect", f"{ip}:{port}"])))
```

- [ ] **Step 5: Orámovat v `mirror.py`**

Import `+`. `mirror_screen`/`record_screen` volají `scrcpy_run`, které je nyní neblokující — po spuštění se vrátí do menu (zrcadlení běží na pozadí):
```python
def mirror_screen():
    print(style.box("scrcpy", "Spuštěno na pozadí — zavři okno scrcpy pro ukončení.\nmůžeš používat další adb příkazy v menu."))
    scrcpy_run([])

def record_screen():
    path = input("Cílová cesta (napr. record.mp4): ").strip() or "record.mp4"
    print(style.box(f"scrcpy --record {path}", f"Nahrávám na pozadí do {path} — zavři okno scrcpy pro ukončení."))
    scrcpy_run(["--record", path])
```

- [ ] **Step 6: Orámovat v `pairing.py`**

Import `+`. V `pair_manual` obalit výstup:
```python
    if host and code:
        print(style.box(f"pair {host}", adb_run(["pair", host, code])))
```
(QR párování má vlastní výstup v `core/pairing/server.py`, zde neměnit.)

- [ ] **Step 7: Smoke test (bez zařízení)**

Run: `cd "C:/Users/admin/droid screen" && python -m droid` → v menu zvol `1` → `1` (list devices).
Expected: box s titulkem `devices -l`, uvnitř surový adb výstup (nebo `(žádný výstup)`). Žádná vyjímka.
Run s `NO_COLOR=1 python -m droid` → plain text, bez ANSI.

- [ ] **Step 8: Commit**

```bash
git add src/droid/commands/device.py src/droid/commands/apps.py src/droid/commands/files.py src/droid/commands/wifi.py src/droid/commands/mirror.py src/droid/commands/pairing.py
git commit -m "feat: wrap command outputs in colored boxes"
```

---

### Task 5: logcat položka v *System Monitoring*

**Files:**
- Modify: `src/droid/commands/monitor.py`

**Interfaces:**
- Consumes: `droid.core.adb_wrapper.adb_logcat_stream(filters)`, `droid.ui.style`
- Produces: nová položka `6. Logcat` v menu; `Zpet` posunuto na `7`

- [ ] **Step 1: Přidat `logcat()` a orámovat existující**

V `src/droid/commands/monitor.py` upravit:
```python
"""System Monitoring -- battery, memory, CPU, storage, processes, logcat."""

from droid.core.adb_wrapper import adb_run, adb_logcat_stream
from droid.ui import style


def battery():
    print(style.box("dumpsys battery", adb_run(["shell", "dumpsys", "battery"])))

def memory():
    print(style.box("dumpsys meminfo", adb_run(["shell", "dumpsys", "meminfo"])))

def cpu():
    print(style.box("dumpsys cpuinfo", adb_run(["shell", "dumpsys", "cpuinfo"])))

def storage():
    print(style.box("df -h", adb_run(["shell", "df", "-h"])))

def processes():
    print(style.box("ps -A", adb_run(["shell", "ps", "-A"])))

def logcat():
    """Živý, filtrovatelný logcat stream."""
    print("\n── Logcat (živý stream) ──")
    print("  Minimální priorita: V / D / I / W / E / F (výchozí V)")
    prio = input("  Priorita: ").strip().upper() or "V"
    if prio not in ("V", "D", "I", "W", "E", "F"):
        prio = "V"
    tag = input("  Tag (prázdné = bez filtru): ").strip()
    kw = input("  Klíčové slovo (prázdné = bez filtru): ").strip()
    filters = {"priority": prio, "tag": tag, "keyword": kw}
    adb_logcat_stream(filters)


def menu():
    while True:
        print("\n── System Monitoring ──\n")
        print("  1. Battery   (dumpsys battery)")
        print("  2. Memory    (dumpsys meminfo)")
        print("  3. CPU       (dumpsys cpuinfo)")
        print("  4. Storage   (df -h)")
        print("  5. Processes (ps -A)")
        print("  6. Logcat    (živý stream, filtry)")
        print("  7. Zpet\n")
        choice = input("Vyber možnost (1-7): ").strip()

        match choice:
            case "1": battery()
            case "2": memory()
            case "3": cpu()
            case "4": storage()
            case "5": processes()
            case "6": logcat()
            case "7": break
            case _: print("\nNeplatná volba.")

        if choice != "7":
            input("\nStiskni Enter pro pokracování...")
```

- [ ] **Step 2: Ověřit ručně (vyžaduje připojené zařízení)**

Run: `python -m droid` → `4` (System Monitoring) → `6` (Logcat).
Expected: vytiskne `[LOGCAT] stream spuštěn — filtry: {...}` na stderr, pak barevné řádky (E červeně, W žlutě, I zeleně). Ctrl+C vrátí do menu.

- [ ] **Step 3: Commit**

```bash
git add src/droid/commands/monitor.py
git commit -m "feat: add live filterable logcat to System Monitoring"
```

---

### Task 6: Finální smoke test + README poznámka

**Files:**
- Modify: `README.md` (přidat odstavec o barvách / NO_COLOR)

**Interfaces:**
- Consumes: nic nového

- [ ] **Step 1: Spustit celou testovací sadu**

Run: `cd "C:/Users/admin/droid screen" && python -m unittest discover -s tests -v`
Expected: vše PASS (14 tests celkem).

- [ ] **Step 2: Ruční kontrola v TTY i plain režimu**

Run: `python -m droid` (TERM s barvami) → ověřit zelené logo + boxy.
Run: `NO_COLOR=1 python -m droid` → ověřit čistý plain text, žádné ANSI, žádné chyby.

- [ ] **Step 3: Doplnit README**

Do `README.md` přidat sekci (za "Menu struktura" nebo do "Bezpecnost"):
```markdown
## Barvy a terminál

Nástroj používá ANSI truecolor pro „hacker" vzhled (zelené logo, orámované
výstupy, barevný logcat). Barvy se **automaticky vypnou**, pokud:
- je nastavena proměnná prostředí `NO_COLOR`, nebo
- výstup není terminál (např. přesměrování do souboru / pipu).

Pro vynucení plain textu: `NO_COLOR=1 droid`
```

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: note about ANSI colors and NO_COLOR"
```

---

## Self-Review (provedeno při psaní)

1. **Spec coverage:** §1 style.py → Task 1. §2 zelené logo → Task 3. §3 čistý log → Task 2. §4 orámování → Task 4. §5 logcat → Task 2 (stream+filter) + Task 5 (menu). §6 mimo rozsah → dodrženo (žádné nové deps, žádné parsování). ✔️
2. **Placeholder scan:** žádné TBD/TODO; každý krok má kód nebo konkrétní příkaz. ✔️
3. **Type consistency:** `extract_logcat_priority(line) -> str|None` a `filter_logcat_line(line, filters) -> bool` a `adb_logcat_stream(filters)` použity konzistentně v Task 2 i Task 5. `style.box/green/dim/red/logcat_color` definovány v Task 1, použity v 2–5. ✔️
