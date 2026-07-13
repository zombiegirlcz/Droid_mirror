"""Wireless Debugging Pairing -- QR generování + adb pair wrapper."""

import os
import sys
from pathlib import Path

from droid.core.adb_wrapper import adb_run

_QR_AVAILABLE = False
_PIL_AVAILABLE = False

try:
    import qrcode
    _QR_AVAILABLE = True
    try:
        from PIL import Image  # noqa: F401
        _PIL_AVAILABLE = True
    except ImportError:
        pass
except ImportError:
    pass


def _generate_qr(data: str, filename: str = "pairing_qr.png") -> None:
    """Generate QR code, show ASCII art in terminal, save PNG if possible."""
    qr = qrcode.QRCode(border=2, box_size=2)
    qr.add_data(data)
    qr.make(fit=True)

    # ASCII art (vzdy funguje)
    print("\n── QR kód pro spárování ──")
    print("  Naskenuj tento QR kód kamerou telefonu:")
    print()
    qr.print_ascii()
    print()

    # PNG (jen pokud je Pillow k dispozici)
    if _PIL_AVAILABLE:
        img = qr.make_image()
        save_path = Path(filename).resolve()
        img.save(save_path)
        print(f"  QR uložen také jako: {save_path}")
        # Zkus otevřít v default vieweru
        try:
            if sys.platform == "win32":
                os.startfile(save_path)
            elif sys.platform == "darwin":
                os.system(f"open {save_path}")
            else:
                os.system(f"xdg-open {save_path}")
        except Exception:
            pass


def pair_device():
    """Pair device -- nabídne QR generování nebo manuální adb pair."""

    print("\n── Wireless Debugging Pairing ──")
    print("Na telefonu otevri: Vývojárské možnosti -> Bezdrátové lade ní ->")
    print("Spárovat zarízení pomocí párovacího kódu\n")
    print("Zadej údaje zobrazené na telefonu:\n")

    host = input("IP adresa a port (napr. 192.168.1.10:42345): ").strip()
    code = input("Párovací kód (napr. 123456): ").strip()

    if not host or not code:
        print("[!] Musíš zadat IP:port i párovací kód.")
        return

    # Vygenerovat QR
    if _QR_AVAILABLE:
        qr_data = f"WIFI:T:ADB;S:{host};P:{code};;"
        _generate_qr(qr_data)
        print(f"  Data: {qr_data}\n")
        print("  Po naskenování QR telefonem by se měl telefon automaticky")
        print("  spárovat. Pokud ne, pouzij možnost 2 (manualní pair).\n")
    else:
        print("[!] Knihovna 'qrcode' není nainstalována.")
        print("    Spust: pip install qrcode")
        print()

    # Nabídnout i manuální adb pair
    do_pair = input("Chceš také spustit 'adb pair' ručně? (a/n): ").strip().lower()
    if do_pair in ("a", "ano", "y", "yes", ""):
        print(f"[*] Páruji s {host}...")
        result = adb_run(["pair", host, code])
        print(result)


def pair_manual():
    """Manual adb pair (fallback)."""
    print("\n── Manualní Párování ──")
    print("Na telefonu otevri: Vývojárské možnosti -> Bezdrátové lade ní ->")
    print("Spárovat zarízení pomocí párovacího kódu\n")

    host = input("IP adresa a port (napr. 192.168.1.10:42345): ").strip()
    code = input("Párovací kód: ").strip()

    if host and code:
        print(f"[*] Páruji s {host}...")
        print(adb_run(["pair", host, code]))
    else:
        print("[!] Musíš zadat IP:port i párovací kód.")


def menu():
    while True:
        print("\n── Wireless Debugging Pairing ──\n")
        print("  1. Vygenerovat QR + párovat  (QR kód na PC, telefon skenuje)")
        print("  2. Manualní párování         (adb pair <host>:<port> <code>)")
        print("  3. Zpet\n")

        if not _QR_AVAILABLE:
            print("  [!] QR funkce nedostupné. Spust: pip install qrcode")
            print()

        choice = input("Vyber možnost (1-3): ").strip()

        match choice:
            case "1":
                pair_device()
            case "2":
                pair_manual()
            case "3":
                break
            case _:
                print("\nNeplatná volba.")

        if choice != "3":
            input("\nStiskni Enter pro pokracování...")
