"""File Operations -- push, pull, ls, rm, mkdir."""

from droid.core.adb_wrapper import adb_run
from droid.ui import style


def push_file():
    local = input("Lokální cesta: ").strip()
    remote = input("Vzdálená cesta: ").strip()
    if local and remote:
        print(style.box(f"push {local} -> {remote}", adb_run(["push", local, remote])))


def pull_file():
    remote = input("Vzdálená cesta: ").strip()
    local = input("Lokální cíl (vychozí .): ").strip() or "."
    if remote:
        print(style.box(f"pull {remote} -> {local}", adb_run(["pull", remote, local])))


def list_dir():
    path = input("Cesta (vychozí /sdcard): ").strip() or "/sdcard"
    print(style.box(f"ls -la {path}", adb_run(["shell", "ls", "-la", path])))


def delete_file():
    path = input("Cesta k souboru: ").strip()
    if path:
        print(style.box(f"rm {path}", adb_run(["shell", "rm", path])))


def mkdir():
    path = input("Cesta k adresári: ").strip()
    if path:
        print(style.box(f"mkdir -p {path}", adb_run(["shell", "mkdir", "-p", path])))


def menu():
    while True:
        print("\n── File Operations ──\n")
        print("  1. Push file   (adb push <local> <remote>)")
        print("  2. Pull file   (adb pull <remote> <local>)")
        print("  3. List dir    (adb shell ls -la)")
        print("  4. Delete file (adb shell rm)")
        print("  5. Mkdir       (adb shell mkdir)")
        print("  6. Zpet\n")
        choice = input("Vyber možnost (1-6): ").strip()

        match choice:
            case "1": push_file()
            case "2": pull_file()
            case "3": list_dir()
            case "4": delete_file()
            case "5": mkdir()
            case "6": break
            case _: print("\nNeplatná volba.")

        if choice != "6":
            input("\nStiskni Enter pro pokracování...")
