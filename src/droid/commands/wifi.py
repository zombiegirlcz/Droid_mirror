"""WiFi / Fleet -- enable TCP/IP mode + batch connect."""

from droid.core.adb_wrapper import adb_run, select_device
from droid.ui import style


def enable_tcpip():
    if not select_device():
        return
    port = input("Port (vychozí 5555): ").strip() or "5555"
    print("[*] Nastavuji TCP/IP mód (vyžaduje aktivní USB spojení).")
    print(style.box(f"tcpip {port}", adb_run(["tcpip", port])))


def batch_connect():
    print("Zadej IP adresy zarízení (oddelené mezerou nebo cárkou).")
    print("Príklad: 192.168.1.10 192.168.1.11 192.168.1.12")
    ips = input("IP adresy: ").strip().replace(",", " ").split()
    port = input("Port (vychozí 5555): ").strip() or "5555"

    if not ips:
        print("[!] Nezadána žádná IP adresa.")
        return

    for ip in ips:
        ip = ip.strip()
        if ip:
            print(f"[*] Pripojuji {ip}:{port}...")
            print(style.box(f"connect {ip}:{port}", adb_run(["connect", f"{ip}:{port}"])))


def menu():
    while True:
        print("\n── WiFi / Fleet ──\n")
        print("  1. Enable TCP/IP mode    (adb tcpip 5555)")
        print("  2. Batch connect         (adb connect pres seznam IP)")
        print("  3. Zpet\n")
        choice = input("Vyber možnost (1-3): ").strip()

        match choice:
            case "1": enable_tcpip()
            case "2": batch_connect()
            case "3": break
            case _: print("\nNeplatná volba.")

        if choice != "3":
            input("\nStiskni Enter pro pokracování...")
