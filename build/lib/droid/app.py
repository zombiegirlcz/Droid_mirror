"""
Droid Mirror -- hlavní menu loop s ASCII logem.
Ciselované menu, žádné externí závislosti.
"""

import sys

from droid.core.adb_wrapper import select_device, get_device_serial
from droid.ui import style

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
    print(style.green(LOGO))
    serial = get_device_serial()
    dev = style.yellow(serial) if serial else style.dim("žádné")
    print(style.dim(f"  Aktivní zařízení: {dev}"))
    print()


def main():
    """Hlavní vstupnj bod -- zobrazí logo a main menu."""
    while True:
        print_header()
        print(style.green("  ── HLAVNÍ MENU ──\n"))
        serial = get_device_serial()
        dev = serial or "žádné"
        print(f"  0. Vybrat zařízení      (active: {dev})")
        print("  1. Device Management")
        print("  2. App Management")
        print("  3. File Operations")
        print("  4. System Monitoring")
        print("  5. Screen Mirroring")
        print("  6. WiFi / Fleet")
        print("  7. Wireless Debugging Pairing")
        print("  8. Exit\n")
        choice = input("Vyber možnost (0-8): ").strip()

        match choice:
            case "0":
                select_device(force=True)
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
