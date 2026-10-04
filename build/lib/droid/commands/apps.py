"""App Management -- list, install, uninstall, clear, force-stop, launch, backup."""

from droid.core.adb_wrapper import adb_run, select_device
from droid.ui import style


def list_packages():
    if not select_device():
        return
    print("  Filtrovat: 1 = vse | 2 = third-party (-3) | 3 = system (-s)")
    choice = input("Vyber (1-3): ").strip()
    match choice:
        case "2": print(style.box("pm list packages -3", adb_run(["shell", "pm", "list", "packages", "-3"])))
        case "3": print(style.box("pm list packages -s", adb_run(["shell", "pm", "list", "packages", "-s"])))
        case _: print(style.box("pm list packages", adb_run(["shell", "pm", "list", "packages"])))


def install_apk():
    if not select_device():
        return
    path = input("Cesta k APK souboru: ").strip()
    if path:
        print(style.box(f"install -r {path}", adb_run(["install", "-r", path])))


def uninstall():
    if not select_device():
        return
    pkg = input("Package name (napr. com.example.app): ").strip()
    if pkg:
        print(style.box(f"uninstall {pkg}", adb_run(["uninstall", pkg])))


def clear_data():
    if not select_device():
        return
    pkg = input("Package name: ").strip()
    if pkg:
        print(style.box(f"pm clear {pkg}", adb_run(["shell", "pm", "clear", pkg])))


def force_stop():
    if not select_device():
        return
    pkg = input("Package name: ").strip()
    if pkg:
        print(style.box(f"am force-stop {pkg}", adb_run(["shell", "am", "force-stop", pkg])))


def launch_app():
    if not select_device():
        return
    pkg = input("Package name (napr. com.example.app, nebo Enter pro vyhledani): ").strip()
    if not pkg:
        # Nabidneme vyhledavani v third-party balíčcích
        print("[*] Vyhledavam balíček (zadej cast nazvu, Enter = vsechny third-party):")
        query = input("  Hledany retezec: ").strip().lower()
        raw = adb_run(["shell", "pm", "list", "packages", "-3"])
        pkgs = sorted(
            line.split(":", 1)[1].strip()
            for line in raw.splitlines()
            if line.startswith("package:")
        )
        if query:
            pkgs = [p for p in pkgs if query in p.lower()]
        if not pkgs:
            print(style.red("[!] Žádný balíček neodpovídá."))
            return
        print(f"\nNalezeno {len(pkgs)} balíčků:")
        for i, p in enumerate(pkgs[:50], 1):
            print(f"  {i:2}. {p}")
        if len(pkgs) > 50:
            print(f"  ... a dalších {len(pkgs) - 50}")
        choice = input(f"\nVyber balíček (1-{min(len(pkgs), 50)}): ").strip()
        if not choice.isdigit() or not (1 <= int(choice) <= min(len(pkgs), 50)):
            print(style.red("[!] Neplatná volba."))
            return
        pkg = pkgs[int(choice) - 1]

    # Zkusíme automaticky najít hlavní spustitelnou aktivitu
    activity = None
    raw = adb_run(["shell", "cmd", "package", "resolve-activity", "--brief", pkg])
    if raw:
        # Výstup: "com.example.app/.MainActivity"
        line = raw.strip().splitlines()[-1].strip()
        if line and "/" in line and not line.startswith("Error"):
            activity = line

    if not activity:
        # Fallback: ruční zadání nebo zkusíme najít všechny aktivity
        print(style.yellow(f"[!] Nepodařilo se automaticky najít aktivitu pro {pkg}."))
        print("  Zkusím vypsat všechny aktivity balíčku...")
        raw = adb_run(["shell", "dumpsys", "package", pkg])
        acts = []
        in_activity = False
        for line in raw.splitlines():
            if "Activity:" in line:
                # Hledáme řádky typu "  Activity: com.example.app/.MainActivity"
                stripped = line.strip()
                if stripped.startswith("Activity:"):
                    act = stripped.split("Activity:", 1)[1].strip().split()[0]
                    if "/" in act:
                        acts.append(act)
        if acts:
            print(f"\nNalezeno {len(acts)} aktivit:")
            for i, a in enumerate(acts[:20], 1):
                print(f"  {i:2}. {a}")
            if len(acts) > 20:
                print(f"  ... a dalších {len(acts) - 20}")
            ch = input(f"\nVyber aktivitu (1-{min(len(acts), 20)}, Enter = první): ").strip()
            if not ch:
                activity = acts[0]
            elif ch.isdigit() and 1 <= int(ch) <= min(len(acts), 20):
                activity = acts[int(ch) - 1]
            else:
                activity = input("Zadej aktivitu ručně (napr. .MainActivity): ").strip()
        else:
            activity = input("Zadej aktivitu ručně (napr. .MainActivity): ").strip()

    if not activity:
        print(style.red("[!] Aktivita nezadána."))
        return

    # Normalizace: pokud aktivita začíná tečkou, přidáme package prefix
    if activity.startswith("."):
        activity = pkg + activity
    elif "/" not in activity:
        activity = pkg + "/." + activity

    print(style.box(f"am start {activity}", adb_run(["shell", "am", "start", "-n", activity])))


def backup_app():
    if not select_device():
        return
    pkg = input("Package name: ").strip()
    out = input("Výstupní soubor (vychozí backup.ab): ").strip() or "backup.ab"
    if pkg:
        print(style.box(f"backup -f {out} {pkg}", adb_run(["backup", "-f", out, pkg])))


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
        print("  8. Zpet\n")
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
            input("\nStiskni Enter pro pokracování...")
