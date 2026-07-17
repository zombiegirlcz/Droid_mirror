# Plán: Výběr zařízení při více připojených (multi-device selector)

**Datum:** 2026-07-17
**Souvislost:** Po zabití duplicitních adb serverů uživatel hlásil, že `devices -l`
ukazuje zařízení, ale ostatní příkazy hlásily „no device". Cílem je, aby nástroj
**vždy pracoval s konkrétním zařízením přes `-s <serial>`** a uživatel si je mohl
vybrat, když jich je víc (nebo když žádné není, jasně to oznámit).

## Principy (závazné, dle existujícího designu)
- Žádné nové runtime závislosti (jen stdlib).
- Surový adb text beze změny, jen se orámovává.
- Bezpečnostní guardraily zachovány (logování příkazů).
- Barvy se vypnou při `NO_COLOR` / ne-TTY (existující logika v `style`).

## Změna A — `src/droid/core/adb_wrapper.py`
1. Přidat modul-rozsahový stav:
   ```python
   _DEVICE_SERIAL: str | None = None
   ```
2. Přidat funkce:
   - `parse_devices(raw: str) -> list[dict]` — parse `adb devices -l` výstupu
     do seznamu `{"serial", "state", "extra"}`. Přeskočí hlavičku a prázdné
     řádky; ignoruje `emulator-*` a `offline`? (NE — zahrň vše, uživatel rozhodne).
     Řádek formátu: `<serial>\t<state>\t<extra...>`.
   - `list_devices_parsed() -> list[dict]` — zavolá `adb_run(["devices","-l"])`
     a vrátí parseovaný seznam (odolné vůči chybě: při prázdném/neplatném
     výstupu vrátí `[]`).
   - `select_device(force=False) -> str | None` — viz logika níže.
   - `get_device_serial() -> str | None` a `set_device_serial(s)`.
   - `prompt_device_selection() -> str | None` — vytiskne číslovaný seznam
     zařízení a zeptá se; vrátí zvolený serial nebo `None` (zrušeno).
3. Úprava `adb_run(args)`:
   ```python
   if _DEVICE_SERIAL and args and args[0] not in ("devices", "connect",
       "disconnect", "pair", "tcpip", "kill-server", "start-server"):
       args = ["-s", _DEVICE_SERIAL] + args
   ```
   Tedy `-s` se přidá pro všechny příkazy, které cílí na konkrétní zařízení.
   `devices`/připojovací příkazy běží globálně (bez `-s`).

### Logika `select_device(force=False)`
```
devices = list_devices_parsed()
if not devices:
    print(varování "žádné zařízení — spusť devices / připoj")
    return None
if len(devices) == 1 and not force:
    return devices[0]["serial"]          # automatická volba
serial = prompt_device_selection()       # len>1 nebo force
set_device_serial(serial)
return serial
```

## Změna B — command moduly (volají `select_device()` před akcí)
Před každým příkazem, který cílí na zařízení, zavolat `select_device()` a pokud
vrátí `None`, akci přerušit (vrátit se do menu). Dotkne se:

| Soubor | Akce |
|---|---|
| `commands/device.py` | `device_info`, `reboot_menu` → `select_device()` (list/connect/disconnect/shell jsou globální/ruční) |
| `commands/apps.py` | všechny (list/install/uninstall/clear/force-stop/launch/backup) → `select_device()` |
| `commands/files.py` | `push/pull/ls/rm/mkdir` → `select_device()`; `interactive_shell` → `adb shell -s <serial>` |
| `commands/monitor.py` | `battery/memory/cpu/storage/processes` → `select_device()`; `logcat` → předat serial do streamu |
| `commands/mirror.py` | `mirror_screen`/`record_screen` → `select_device()` (serial → scrcpy `-s`) |
| `commands/wifi.py` | `enable_tcpip` → `select_device()` (vyžaduje USB); batch_connect je globální |

### `logcat` a serial
`adb_logcat_stream` dostane volitelný parametr `serial: str | None = None` a
přidá `-s <serial>` do `subprocess.Popen([_ADB_PATH, "logcat", *(["-s",serial] if serial else [])])`.

### `interactive_shell` / `shell` (device.py, files.py)
Místo `subprocess.run([adb_path, "shell"])` použít
`[adb_path, *(["-s", serial] if serial else []), "shell"]`.

## Změna C — `app.py` (globální volba zařízení)
Přidat do hlavního menu položku `0. Vybrat zařízení (active: <serial|žádné>)`,
která zavolá `select_device(force=True)` z `droid.core.adb_wrapper`.
Zobrazovat aktuální serial v hlavičce menu.

## Změna D — testy `tests/test_adb_run.py`
Přidat:
- `test_parse_devices` — 0/1/více zařízení, ignorování hlavičky a prázdných řádků.
- `test_adb_run_injects_serial` — mock `subprocess.run`, ověřit že při
  `_DEVICE_SERIAL` se předřadí `-s <serial>` (a že `devices` ho NEMÁ).
- `test_list_devices_parsed_handles_error` — neplatný výstup → `[]`.

## Soubory k úpravě
- `src/droid/core/adb_wrapper.py` (nové funkce + úprava `adb_run`)
- `src/droid/commands/device.py`
- `src/droid/commands/apps.py`
- `src/droid/commands/files.py`
- `src/droid/commands/monitor.py`
- `src/droid/commands/mirror.py`
- `src/droid/commands/wifi.py`
- `src/droid/app.py`
- `tests/test_adb_run.py` (nové testy)

## Ověření
- `python -m unittest discover -s tests -v` (vše zelené).
- Ručně: `python -m droid` → připojit 0/1/více zařízení → v menu zkusit
  Battery / Logcat → ověřit, že se použije správný serial (a že bez zařízení
  je jasná hláška místo „no device").
