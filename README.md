# Droid Mirror 🪞

Open-source ADB/scrcpy Fleet Manager -- CLI nástroj pro správu Android zařízení.

**Žádný backdoor. Žádné phone-home. Pouze standardní ADB a scrcpy příkazy.**

Co nástroj dělá, je vidět v kódu a každý ADB/scrcpy příkaz je logován do konzole.

## Instalace

### Požadavky

- Python 3.11+
- ADB (platform-tools) -- [download](https://developer.android.com/studio/releases/platform-tools)
- scrcpy (volitelné, pro mirroring) -- [download](https://github.com/Genymobile/scrcpy)

*Na Windows se nástroj automaticky pokusí najít `adb` a `scrcpy` v PATH.
Pokud nejsou k dispozici, použije zabalenou verzi v `bin/`.*

### QR párování (volitelné)

Pro generování QR kódu (tool na PC, telefon skenuje) je potřeba:

```bash
pip install droid-mirror[qr]
```

Bez QR funguje manuální párování přes `adb pair <host>:<port> <code>`.

### Z repa

```bash
git clone https://github.com/<user>/droid-mirror.git
cd droid-mirror
pip install -e .
droid
```

Nebo:

```bash
python -m droid
```

## Použití

Spust `droid` v terminálu. Zobrazí se ASCII logo a číslované menu:

```
  1. Device Management    -- list, connect, disconnect, info, reboot, shell
  2. App Management       -- list packages, install, uninstall, clear, force-stop, launch
  3. File Operations      -- push, pull, ls, rm, mkdir
  4. System Monitoring    -- battery, memory, CPU, storage, processes
  5. Screen Mirroring     -- scrcpy mirror / record
  6. WiFi / Fleet         -- TCP/IP mode, batch connect
  7. Wireless Debugging   -- adb pair wrapper
  8. Exit
```

Každý příkaz je zalogovaný na stderr:

```
[ADB] adb devices -l
[ADB] adb connect 192.168.1.10:5555
```

## Menu struktura

| Kategorie | Příkazy |
|---|---|
| Device Management | `adb devices -l`, `adb connect`, `adb disconnect`, `adb shell getprop`, `adb reboot`, `adb shell` |
| App Management | `pm list packages`, `install -r`, `uninstall`, `pm clear`, `am force-stop`, `am start`, `backup` |
| File Operations | `adb push`, `adb pull`, `adb shell ls -la`, `adb shell rm`, `adb shell mkdir` |
| System Monitoring | `dumpsys battery`, `dumpsys meminfo`, `dumpsys cpuinfo`, `df -h`, `ps -A` |
| Screen Mirroring | `scrcpy`, `scrcpy --record` |
| WiFi / Fleet | `adb tcpip 5555`, `adb connect` (batch) |
| Pairing | QR generace (wifi:T:ADB formát) + `adb pair <host>:<port> <code>` |

## Bezpecnost

- Nástroj funguje JEN na zařízeních, kde má uživatel **vědomě zapnuté**
  USB debugging nebo Wireless debugging v Developer options.
- Není možné se vzdáleně připojit k zařízení bez fyzické interakce (spárování).
- Nástroj neodesílá žádná data (žádná telemetrie, žádný license check).
- Není rootkit -- využívá pouze veřejné ADB API.
- Každý příkaz je zalogovaný do konzole -- žádná "black box" akce.

## Licence

GPLv3 -- jakýkoliv closed-source fork je právně vyloučen.
