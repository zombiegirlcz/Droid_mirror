"""System Monitoring -- battery, memory, CPU, storage, processes, logcat."""

from droid.core.adb_wrapper import adb_run, adb_logcat_stream, select_device
from droid.ui import style


def battery():
    if not select_device():
        return
    print(style.box("dumpsys battery", adb_run(["shell", "dumpsys", "battery"])))

def memory():
    if not select_device():
        return
    print(style.box("dumpsys meminfo", adb_run(["shell", "dumpsys", "meminfo"])))

def cpu():
    if not select_device():
        return
    print(style.box("dumpsys cpuinfo", adb_run(["shell", "dumpsys", "cpuinfo"])))

def storage():
    if not select_device():
        return
    print(style.box("df -h", adb_run(["shell", "df", "-h"])))

def processes():
    if not select_device():
        return
    print(style.box("ps -A", adb_run(["shell", "ps", "-A"])))

def logcat():
    """Živý, filtrovatelný logcat stream (cílí na vybrané zařízení)."""
    serial = select_device()
    if serial is None:
        return
    print("\n── Logcat (živý stream) ──")
    print("  Minimální priorita: V / D / I / W / E / F (výchozí V)")
    prio = input("  Priorita: ").strip().upper() or "V"
    if prio not in ("V", "D", "I", "W", "E", "F"):
        prio = "V"
    tag = input("  Tag (prázdné = bez filtru): ").strip()
    kw = input("  Klíčové slovo (prázdné = bez filtru): ").strip()
    filters = {"priority": prio, "tag": tag, "keyword": kw}
    adb_logcat_stream(filters, serial=serial)


def menu():
    while True:
        print("\n── System Monitoring ──\n")
        print("  1. Battery   (dumpsys battery)")
        print("  2. Memory    (dumpsys meminfo)")
        print("  3. CPU       (dumpsys cpuinfo)")
        print("  4. Storage   (df -h)")
        print("  5. Processes (ps -A)")
        print("  6. Logcat    (živý stream, filtry)")
        print("  7. Zpet\n")
        choice = input("Vyber možnost (1-7): ").strip()

        match choice:
            case "1": battery()
            case "2": memory()
            case "3": cpu()
            case "4": storage()
            case "5": processes()
            case "6": logcat()
            case "7": break
            case _: print("\nNeplatná volba.")

        if choice != "7":
            input("\nStiskni Enter pro pokracování...")
