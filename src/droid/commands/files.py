"""File Operations -- push, pull, ls, rm, mkdir, interactive shell."""

import subprocess
import sys

from droid.core.adb_wrapper import adb_run, find_binary
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


def interactive_shell():
    """Klasický interaktivní adb shell (PTY passthrough).

    Spustí `adb shell` a propojí stdin/stdout terminálu, takže máš plnohodnotný
    Android shell (zadej `exit` nebo Ctrl+D pro návrat do menu).
    """
    try:
        adb_path = find_binary("adb")
        print("[*] Spouštím adb shell. Pro ukoncení zadej 'exit' nebo Ctrl+D.")
        subprocess.run([adb_path, "shell"], check=False)
    except FileNotFoundError as e:
        print(f"[CHYBA] {e}", file=sys.stderr)


def menu():
    while True:
        print("\n── File Operations ──\n")
        print("  1. Push file   (adb push <local> <remote>)")
        print("  2. Pull file   (adb pull <remote> <local>)")
        print("  3. List dir    (adb shell ls -la)")
        print("  4. Delete file (adb shell rm)")
        print("  5. Mkdir       (adb shell mkdir)")
        print("  6. Shell       (interaktivní adb shell)")
        print("  7. Zpet\n")
        choice = input("Vyber možnost (1-7): ").strip()

        match choice:
            case "1": push_file()
            case "2": pull_file()
            case "3": list_dir()
            case "4": delete_file()
            case "5": mkdir()
            case "6": interactive_shell()
            case "7": break
            case _: print("\nNeplatná volba.")

        if choice != "7":
            input("\nStiskni Enter pro pokracování...")
