"""Wireless Debugging Pairing -- wrapper over 'adb pair'.

QV:
- Varianta A (budoucnost): PC generuje QR + mDNS + SPAKE2 handshake.
  Vyžaduje zeroconf + implementaci párovacího protokolu z AOSP.
- Varianta B (v1, aktuální): Uživatel zadá IP:port + kód z obrazovky telefonu.
"""

from droid.core.adb_wrapper import adb_run


def pair_device():
    print("\n── Wireless Debugging Pairing ──")
    print("Na telefonu otevri: Vývojárské možnosti -> Bezdrátové lade ní ->")
    print("Spárovat zarízení pomocí párovacího kódu")
    print("A zadej údaje níže.\n")
    host = input("IP adresa a port (napr. 192.168.1.10:42345): ").strip()
    code = input("Párovací kód (napr. 123456): ").strip()

    if host and code:
        print(f"[*] Páruji s {host}...")
        print(adb_run(["pair", host, code]))
    else:
        print("[!] Musíš zadat IP:port i párovací kód.")


def menu():
    while True:
        print("\n── Wireless Debugging Pairing ──\n")
        print("  1. Párovat pres kód   (adb pair <host>:<port> <code>)")
        print("  2. Zpet\n")
        choice = input("Vyber možnost (1-2): ").strip()

        match choice:
            case "1": pair_device()
            case "2": break
            case _: print("\nNeplatná volba.")

        if choice != "2":
            input("\nStiskni Enter pro pokracování...")
