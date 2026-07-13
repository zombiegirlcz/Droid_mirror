# Droid Mirror — Open-source ADB/scrcpy Fleet Manager

**Datum:** 2026-07-13
**Status:** Design schválen, ready k implementaci

---

## 1. Cíl

Free, open-source CLI nástroj nad standardním **ADB** a **scrcpy**. Žádná skrytá funkcionalita, žádný backdoor, žádný "phone home" k autorovi. Vše, co nástroj dělá, musí být viditelné v kódu a ověřitelné (`adb shell <cmd>` 1:1).

## 2. Explicitní NE

- ŽÁDNÉ nastavení vzdáleného přístupu na zařízení, které uživatel fyzicky nedrží a vědomě nespáruje přes Developer options.
- ŽÁDNÉ ukládání/odesílání přístupových tokenů, párovacích kódů nebo dat zařízení na externí server.
- ŽÁDNÝ silent/headless mód, který by skryl činnost na telefonu.
- QR kód = pouze vizualizace párovacích údajů (`adb pair`), které Android sám generuje. Nikdy QR generovaný nástrojem.

## 3. Tech stack (finální rozhodnutí)

| Vrstva | Volba |
|---|---|
| Jazyk | Python 3.11+ (pure, bez dependencies) |
| CLI framework | Žádný — číslované textové menu s `input()` |
| Formátování | Raw textový výstup `adb` příkazů |
| ADB/scrcpy | Hybrid — zkusí PATH, fallback na bundled bin/ |
| Balení | pip package s entry pointem `droid` + `python -m droid` |
| Licence | GPLv3 |

## 4. Architektura

### Adresářová struktura

```
droid-screen/
├── pyproject.toml               # build config + entry point "droid"
├── README.md
├── LICENSE (GPLv3)
├── src/
│   └── droid/
│       ├── __init__.py
│       ├── __main__.py          # enables `python -m droid`
│       ├── app.py               # hlavní menu loop + logo
│       ├── core/
│       │   ├── __init__.py
│       │   └── adb_wrapper.py   # run(adb_args) subprocess wrapper
│       ├── commands/
│       │   ├── __init__.py
│       │   ├── device.py        # Device Management
│       │   ├── apps.py          # App Management
│       │   ├── files.py         # File Operations
│       │   ├── monitor.py       # System Monitoring
│       │   ├── mirror.py        # Screen Mirroring (scrcpy)
│       │   ├── wifi.py          # WiFi / Fleet
│       │   └── pairing.py       # Wireless Debugging Pairing
│       └── bin/                 # bundled ADB + scrcpy (Windows)
│           └── .gitkeep
```

### Hlavní menu flow

```
┌─────────────────────────────────────────┐
│          DROID MIRROR v1.0              │
│     Open-source ADB Fleet Manager       │
├─────────────────────────────────────────┤
│  1. Device Management                   │
│  2. App Management                      │
│  3. File Operations                     │
│  4. System Monitoring                   │
│  5. Screen Mirroring                    │
│  6. WiFi / Fleet                        │
│  7. Wireless Debugging Pairing          │
│  8. Exit                                │
└─────────────────────────────────────────┘
```

Každá položka → submenu → volá `adb_wrapper.run()`.

## 5. Core — adb_wrapper.py

```python
def adb_run(args: list[str]) -> str:
    """Spustí 'adb <args>', zaloguje, vrátí stdout."""

def scrcpy_run(args: list[str]) -> None:
    """Spustí 'scrcpy <args>' jako passthrough (stream)."""

def find_binary(name: str) -> str:
    """PATH → bundled → FileNotFoundError."""
```

- Každý příkaz logován na stderr: `[ADB] adb devices -l`
- Non-zero exit: zobrazí chybu, vrátí se do menu

## 6. Command moduly

### device.py
- list_devices, connect_wifi, disconnect, device_info, reboot_menu, shell (passthrough)

### apps.py
- list_packages (s výběrem -3/-s/all), install_apk, uninstall, clear_data, force_stop, launch_app, backup_app

### files.py
- push_file, pull_file, list_dir, delete_file, mkdir

### monitor.py
- battery, memory, cpu, storage, processes — vše `adb shell dumpsys` / `df` / `ps`

### mirror.py
- mirror_screen (scrcpy), record_screen (scrcpy --record)

### wifi.py
- enable_tcpip, batch_connect (interaktivní seznam IP, session-only)

### pairing.py
- pair_device (ruční zadání host:port + kód z Android UI)

## 7. Startovní ASCII logo

```
██████╗ ██████╗  ██████╗ ██╗██████╗     ███╗   ███╗██╗██████╗ ██████╗  ██████╗ ██████╗
██╔══██╗██╔══██╗██╔═══██╗██║██╔══██╗    ████╗ ████║██║██╔══██╗██╔══██╗██╔═══██╗██╔══██╗
██║  ██║██████╔╝██║   ██║██║██║  ██║    ██╔████╔██║██║██████╔╝██████╔╝██║   ██║██████╔╝
██║  ██║██╔══██╗██║   ██║██║██║  ██║    ██║╚██╔╝██║██║██╔══██╗██╔══██╗██║   ██║██╔══██╗
██████╔╝██║  ██║╚██████╔╝██║██████╔╝    ██║ ╚═╝ ██║██║██║  ██║██║  ██║╚██████╔╝██║  ██║
╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝╚═════╝     ╚═╝     ╚═╝╚═╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝

          Open-source ADB Fleet Manager  |  GPLv3
```

## 8. Bezpečnostní guardraily

1. Každý spuštěný `adb`/`scrcpy` příkaz logován na stderr
2. Žádné volání domů (analytics, license check, telemetrie)
3. README varuje: vyžaduje vědomě zapnuté USB/Wireless debugging

## 9. Pořadí implementace

1. `pyproject.toml` + `__main__.py` — skeleton balíčku
2. `core/adb_wrapper.py` — subprocess wrapper + logging + find binary
3. `app.py` — logo + hlavní menu loop
4. `commands/device.py` — první command modul
5. `commands/apps.py`
6. `commands/files.py`
7. `commands/monitor.py`
8. `commands/mirror.py`
9. `commands/wifi.py`
10. `commands/pairing.py`
11. `README.md` + `LICENSE`
12. Otestovat na reálném zařízení / emulátoru
