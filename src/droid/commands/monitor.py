"""System Monitoring -- battery, memory, CPU, storage, processes."""

from droid.core.adb_wrapper import adb_run


def battery():
    print(adb_run(["shell", "dumpsys", "battery"]))


def memory():
    print(adb_run(["shell", "dumpsys", "meminfo"]))


def cpu():
    print(adb_run(["shell", "dumpsys", "cpuinfo"]))


def storage():
    print(adb_run(["shell", "df", "-h"]))


def processes():
    print(adb_run(["shell", "ps", "-A"]))


def menu():
    while True:
        print("\n── System Monitoring ──\n")
        print("  1. Battery   (dumpsys battery)")
        print("  2. Memory    (dumpsys meminfo)")
        print("  3. CPU       (dumpsys cpuinfo)")
        print("  4. Storage   (df -h)")
        print("  5. Processes (ps -A)")
        print("  6. Zpet\n")
        choice = input("Vyber možnost (1-6): ").strip()

        match choice:
            case "1": battery()
            case "2": memory()
            case "3": cpu()
            case "4": storage()
            case "5": processes()
            case "6": break
            case _: print("\nNeplatná volba.")

        if choice != "6":
            input("\nStiskni Enter pro pokracování...")
