"""
Droid Mirror -- hlavní menu loop s ASCII logem.
Ciselované menu, žádné externí závislosti.
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


def main():
    """Hlavní vstupnj bod -- zobrazí logo a main menu."""
    while True:
        print_header()
        print("  ── HLAVNÍ MENU ──\n")
        print("  1. Device Management")
        print("  2. App Management")
        print("  3. File Operations")
        print("  4. System Monitoring")
        print("  5. Screen Mirroring")
        print("  6. WiFi / Fleet")
        print("  7. Wireless Debugging Pairing")
        print("  8. Exit\n")
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
