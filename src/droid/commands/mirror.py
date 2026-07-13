"""Screen Mirroring -- scrcpy passthrough."""

from droid.core.adb_wrapper import scrcpy_run
from droid.ui import style


def mirror_screen():
    print(style.box("scrcpy", "Spuštěno na pozadí — zavři okno scrcpy pro ukončení.\nmůžeš používat další adb příkazy v menu."))
    scrcpy_run([])


def record_screen():
    path = input("Cílová cesta (napr. record.mp4): ").strip() or "record.mp4"
    print(style.box(f"scrcpy --record {path}", f"Nahrávám na pozadí do {path} — zavři okno scrcpy pro ukončení."))
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
