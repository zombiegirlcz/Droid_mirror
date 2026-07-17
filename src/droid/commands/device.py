"""Device Management -- list, connect, disconnect, info, reboot, shell."""

import subprocess
import sys

from droid.core.adb_wrapper import adb_run, find_binary, select_device
from droid.ui import style


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
    if not select_device():
        return
    print(style.box("getprop", adb_run(["shell", "getprop"])))


def reboot_menu():
    if not select_device():
        return
    print("\n── Reboot ──")
    print("  1. Normal (system)")
    print("  2. Bootloader")
    print("  3. Recovery")
    print("  4. Zpet")
    choice = input("Vyber možnost (1-4): ").strip()
    match choice:
        case "1": print(style.box("reboot", adb_run(["reboot"])))
        case "2": print(style.box("reboot bootloader", adb_run(["reboot", "bootloader"])))
        case "3": print(style.box("reboot recovery", adb_run(["reboot", "recovery"])))
        case _: return


def shell():
    """Interactive adb shell passthrough."""
    try:
        adb_path = find_binary("adb")
        print("[*] Spoustím adb shell. Pro ukoncení zadej 'exit' nebo Ctrl+D.")
        subprocess.run([adb_path, "shell"], check=False)
    except FileNotFoundError as e:
        print(f"[CHYBA] {e}", file=sys.stderr)


def menu():
    while True:
        print("\n── Device Management ──\n")
        print("  1. List devices          (adb devices -l)")
        print("  2. Connect (WiFi)        (adb connect <ip>:<port>)")
        print("  3. Disconnect            (adb disconnect)")
        print("  4. Device info           (adb shell getprop)")
        print("  5. Reboot                (normal / bootloader / recovery)")
        print("  6. Shell                 (interaktivní adb shell)")
        print("  7. Zpet\n")
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
            input("\nStiskni Enter pro pokracování...")
