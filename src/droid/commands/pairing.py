"""Wireless Debugging Pairing -- QR pairing server + manual adb pair."""

from droid.core.adb_wrapper import adb_run


def pair_qr():
    """Spustí párovací server s QR kódem."""
    from droid.core.pairing.server import AdbPairingServer

    print("\n── QR Párování ──")
    print("Tool vygeneruje QR + vyhlásí mDNS, telefon skenuje.\n")

    # Nechat vygenerovat náhodné heslo nebo zadat vlastní?
    custom = input("Chceš zadat vlastní párovací kód? (a/n, výchozí n): ").strip().lower()
    password = None
    if custom in ("a", "ano", "y", "yes"):
        password = input("6-místný kód: ").strip()
        if not password.isdigit() or len(password) != 6:
            print("[!] Kód musí být 6 číslic. Použiji náhodný.")
            password = None

    server = AdbPairingServer(password=password)
    server.run(timeout=120)


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
        print("  1. QR párování            (PC vygeneruje QR, telefon skenuje)")
        print("  2. Manualní párování      (adb pair <host>:<port> <code>)")
        print("  3. Zpet\n")
        choice = input("Vyber možnost (1-3): ").strip()

        match choice:
            case "1": pair_qr()
            case "2": pair_manual()
            case "3": break
            case _: print("\nNeplatná volba.")

        if choice != "3":
            input("\nStiskni Enter pro pokracování...")
