# Design: Hacker vzhled + logcat (Droid Mirror)

**Datum:** 2026-07-13
**Status:** Schváleno (návrh odsouhlasen uživatelem)

## Cíl
Přidat nástroji „hacker" terminálový vzhled a použitelný logcat:
- Zelené Android logo a barevné hlavičky (čisté ANSI, žádná nová závislost).
- Vyčištění `[ADB]`/`[SCRCPY]` log řádků (skrýt cestu k binárce).
- Čitelné orámování adb výstupů (režim A — bez parsování).
- Nová položka **logcat** v *System Monitoring*: živý, barevný stream s filtry.

## Principy (závazné)
- **Žádné nové runtime závislosti** — pouze ANSI escape kódy (truecolor).
- **Co vidíš = co adb dělá** — surový adb text se nemění, jen se orámovává.
- Zachovat bezpečnostní guardraily (logování příkazů, žádné volání domů).

---

## 1. Modul `src/droid/ui/style.py` (NOVÝ)
Centrální místo pro barvy a formátování. Žádné importy mimo stdlib.

### Konstanty / barvy
- `ANDROID_GREEN = "\x1b[38;2;61;220;132m"` (`#3DDC84`, oficiální Android brand zelená).
- `RED`, `YELLOW`, `GREEN`, `DIM`, `BOLD`, `RESET` jako ANSI řetězce.
- Helpery: `green(t)`, `red(t)`, `yellow(t)`, `dim(t)`, `bold(t)`.

### Detekce prostředí
- Pokud je nastavena env proměnná `NO_COLOR`, nebo `sys.stdout` není TTY,
  všechny helpery vrací vstup beze změny (plain text).

### Formátovací pomocníci
- `box(title: str, body: str) -> str`: obarvený rám (box-drawing znaky) se
  jménem příkazu jako titulkem; uvnitř je původní adb výstup. Vrací string
  (volající vytiskne), nebo přímo tiskne — rozhodnuto: **vrací string**.
- `logcat_color(level: str, line: str) -> str`: obarví jeden logcat řádek
  podle priority: `E`→červená, `W`→žlutá, `I`→zelená, `D`→šedá (DIM),
  `V`→DIM, ostatní→plain.

## 2. Logo v `app.py`
- `LOGO` se obalí do `style.green()` (případně `bold`). Hlavička
  ("Open-source ADB Fleet Manager | GPLv3") v odstupňované zelené/šedé.

## 3. Vyčištění logu v `src/droid/core/adb_wrapper.py`
- `adb_run`: místo `f"[ADB] {' '.join(cmd)}"` (kde `cmd[0]` je celá cesta k
  binárce) zkrátit na `f"[ADB] {' '.join(args)}"` — tiskne jen příkaz a
  argumenty, cesta se schová.
- `scrcpy_run`: totéž pro `[SCRCPY]`.
- Volitelně: cestu k binárce předat přes `os.path.basename()` pro jistotu.

## 4. Orámování výstupů (režim A)
- Command moduly (device/apps/files/monitor/mirror/wifi/pairing) obalí
  výstup `adb_run(...)` do `style.box(title, output)`.
- Konkrétně: v každém modulu nahradit `print(adb_run([...]))` voláním
  `print(style.box("devices -l", adb_run([...])))`. Titulek = stručný popis
  příkazu (např. `"devices -l"`, `"pm list packages"`).
- Surový adb text zůstává uvnitř rámu nezměněn.

## 5. logcat — nová položka v `monitor.py`
Přidána položka `7. Logcat (živý stream)` do menu *System Monitoring*.

### Nová funkce v `adb_wrapper.py`: `adb_logcat_stream(filters)`
- Spustí `adb logcat` přes `subprocess.Popen(stdout=PIPE, text=True,
  bufsize=1)` a čte řádky **průběžně** (streaming, ne `capture_output`).
- `filters` dict: `{"priority": "W", "tag": "...", "keyword": "..."}`
  (vše volitelné). Filtrování probíhá **klientsky** na každém řádku:
  - priorita: zachovat řádky s prioritou `>=` zvolené (E nejvyšší).
  - tag: řádek obsahuje tag (substring, case-insensitive).
  - keyword: zpráva obsahuje klíčové slovo (substring, case-insensitive).
- Každý vyhovující řádek se před výpisem obarví přes `style.logcat_color`.
- Běží dokud uživatel nezmáčkne Ctrl+C (odsatnout `KeyboardInterrupt` →
  vrátit se do menu). Před spuštěním vytiskne info o aktivních filtrech.

### UI v `monitor.py`
- `logcat()` zeptá se na: minimální prioritu (V/D/I/W/E/F, výchozí V),
  tag (prázdné = bez filtru), klíčové slovo (prázdné = bez filtru).
- Zavolá `adb_logcat_stream(...)` v `try/except KeyboardInterrupt`.

## 6. Mimo rozsah (YAGNI)
- Žádné parsování surových výstupů do tabulek (režim B zamítnut).
- Žádná knihovna `rich`/`colorama`.
- Žádná změna bezpečnostních guardrailů.

## Soubory k úpravě / vytvoření
| Soubor | Změna |
|---|---|
| `src/droid/ui/style.py` | NOVÝ modul (barvy + box + logcat_color) |
| `src/droid/app.py` | zelené logo |
| `src/droid/core/adb_wrapper.py` | čistý log + `adb_logcat_stream` |
| `src/droid/commands/device.py` | orámování výstupu |
| `src/droid/commands/apps.py` | orámování výstupu |
| `src/droid/commands/files.py` | orámování výstupu |
| `src/droid/commands/monitor.py` | orámování + položka logcat |
| `src/droid/commands/mirror.py` | orámování výstupu |
| `src/droid/commands/wifi.py` | orámování výstupu |
| `src/droid/commands/pairing.py` | orámování výstupu (volitelné) |

## Testování
- Ruční: `python -m droid` → ověřit zelené logo, čistý `[ADB]` log,
  orámované výstupy, a živý logcat s filtry (vyžaduje připojené zařízení).
- Bez zařízení: ověřit, že helpery `style` fungují a že `NO_COLOR` vypíná barvy.
