"""App Management -- list, install, uninstall, clear, force-stop, launch, backup."""

from droid.core.adb_wrapper import adb_run
from droid.ui import style


def list_packages():
    print("  Filtrovat: 1 = vse | 2 = third-party (-3) | 3 = system (-s)")
    choice = input("Vyber (1-3): ").strip()
    match choice:
        case "2": print(style.box("pm list packages -3", adb_run(["shell", "pm", "list", "packages", "-3"])))
        case "3": print(style.box("pm list packages -s", adb_run(["shell", "pm", "list", "packages", "-s"])))
        case _: print(style.box("pm list packages", adb_run(["shell", "pm", "list", "packages"])))


def install_apk():
    path = input("Cesta k APK souboru: ").strip()
    if path:
        print(style.box(f"install -r {path}", adb_run(["install", "-r", path])))


def uninstall():
    pkg = input("Package name (napr. com.example.app): ").strip()
    if pkg:
        print(style.box(f"uninstall {pkg}", adb_run(["uninstall", pkg])))


def clear_data():
    pkg = input("Package name: ").strip()
    if pkg:
        print(style.box(f"pm clear {pkg}", adb_run(["shell", "pm", "clear", pkg])))


def force_stop():
    pkg = input("Package name: ").strip()
    if pkg:
        print(style.box(f"am force-stop {pkg}", adb_run(["shell", "am", "force-stop", pkg])))


def launch_app():
    pkg = input("Package name: ").strip()
    activity = input("Activity name: ").strip()
    if pkg and activity:
        print(style.box(f"am start {pkg}/{activity}", adb_run(["shell", "am", "start", "-n", f"{pkg}/{activity}"])))


def backup_app():
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
