"""Screen Mirroring -- scrcpy passthrough."""

from droid.core.adb_wrapper import scrcpy_run


def mirror_screen():
    print("[*] Spoustím scrcpy -- pro ukoncení zavri okno scrcpy.")
    scrcpy_run([])


def record_screen():
    path = input("Cílová cesta (napr. record.mp4): ").strip() or "record.mp4"
    print(f"[*] Nahrávám obrazovku do {path} -- Ctrl+C pro ukoncení.")
    scrcpy_run(["--record", path])


def menu():
    while True:
        print("\n── Screen Mirroring ──\n")
        print("  1. Mirror screen      (scrcpy)")
        print("  2. Record screen      (scrcpy --record)")
        print("  3. Zpet\n")
        choice = input("Vyber možnost (1-3): ").strip()

        match choice:
            case "1": mirror_screen()
            case "2": record_screen()
            case "3": break
            case _: print("\nNeplatná volba.")

        if choice != "3":
            input("\nStiskni Enter pro pokracování...")
