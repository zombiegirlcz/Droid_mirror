"""
ADB QR pairing -- správný flow podle adbqr.

Flow:
1. PC vygeneruje service_name + 6-místný code
2. PC ukáže QR: WIFI:T:ADB;S:<service>;P:<code>;;
3. Telefon naskenuje QR, spustí vlastní párovací server a vyhlásí mDNS
4. PC detekuje telefon pres `adb mdns services`
5. PC spustí `adb pair <ip>:<port> <code>` → Noise handshake mezi adb + telefonem
6. Po úspešném párování telefon (má-li zapnuté Wireless debugging) porad
   vysílá `_adb-tls-connect._tcp` na JINÉM portu nez byl pairing port.
   PC ho najde pres `adb mdns services` a sám zavolá `adb connect <ip>:<port>`
   -- uzivatel tedy IP:port nezadává rucne, jen ho tool na konci vypíše.
"""

import os
import random
import string
import subprocess
import time
from pathlib import Path

import qrcode


class AdbPairingServer:
    def __init__(self, password: str | None = None):
        self.password = password or self._generate_password()
        self.service_name = self._generate_service_name()

    @staticmethod
    def _generate_password(length=6):
        return "".join(random.choices(string.digits, k=length))

    @staticmethod
    def _generate_service_name():
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return f"adbqr-{suffix}"

    # ---- QR ----

    def get_qr_data(self):
        return f"WIFI:T:ADB;S:{self.service_name};P:{self.password};;"

    def show_qr(self):
        qr_data = self.get_qr_data()

        print("\n── QR KÓD PRO SPÁROVÁNÍ ──")
        print("  Otevrelo se okno s QR kódem v prohlížeci obrazku.\n")
        print("  Na telefonu otevri: Vývojárské možnosti ->")
        print("  Bezdrátové lade ní -> Spárovat zarízení pomocí QR")
        print("  a naskenuj QR kamerou telefonu.\n")
        print(f"  Service:   {self.service_name}")
        print(f"  Heslo:     {self.password}")
        print(f"  QR data:   {qr_data}\n")

        qr = qrcode.QRCode(border=2, box_size=10)
        qr.add_data(qr_data)
        qr.make(fit=True)

        from PIL import Image as PILImage
        img = qr.make_image(fill_color="black", back_color="white")
        save_path = Path("pairing_qr.png").resolve()
        img.save(save_path)
        print(f"  QR ulozen: {save_path}")

        try:
            os.startfile(save_path)
            print(f"  Otevren v defaultním prohlížeci obrazku")
        except Exception:
            print(f"  Pokud se neotevre, otevri rucne: {save_path}")

    # ---- mDNS detekce + párování ----

    def _adb_mdns_services(self, service_filter: str = "_adb-tls-pairing"):
        """
        Vrati seznam (ip:port, service_name) z `adb mdns services`.

        `adb mdns services` vypisuje vsechny tri typy sluzeb, ktere adbd
        vysila po siti (viz AOSP docs/dev/adb_wifi.md):
          - _adb._tcp             legacy `adb tcpip` mod
          - _adb-tls-pairing._tcp beží behem parovani (QR / kod)
          - _adb-tls-connect._tcp beží porad, dokud je zapnute
                                   "Wireless debugging" -- tohle je adresa,
                                   na kterou se ma volat `adb connect`.
        `service_filter` urcuje, ktery typ chceme vytahnout.
        """
        try:
            r = subprocess.run(
                [self._find_adb(), "mdns", "services"],
                capture_output=True, text=True, timeout=5,
            )
            services = []
            for line in r.stdout.split("\n"):
                line = line.strip()
                if not line or line.startswith("List"):
                    continue
                # Format: "ServiceName _adb-tls-pairing._tcp IP:Port"
                parts = line.split()
                if len(parts) >= 3 and service_filter in line:
                    services.append((parts[-1], parts[0]))
            return services
        except Exception:
            return []

    def _find_connect_addr(self, host_ip: str, timeout: int = 10):
        """
        Po uspesnem `adb pair` telefon (pokud ma zapnute Wireless debugging)
        porad vysila `_adb-tls-connect._tcp` -- ale na JINEM portu nez byl
        pairing port. Najdeme tenhle port podle IP adresy, kterou uz zname
        z parovani, a vratime "ip:port" pripravene pro `adb connect`.
        """
        start = time.time()
        while time.time() - start < timeout:
            for addr, _name in self._adb_mdns_services(service_filter="_adb-tls-connect"):
                if addr.split(":")[0] == host_ip:
                    return addr
            time.sleep(1)
        return None

    @staticmethod
    def _find_adb():
        """Najde adb executable (nejdriv v PATH, pak bundled)."""
        import shutil
        import sys
        # Zkusit PATH
        adb = shutil.which("adb")
        if adb:
            return adb
        # Zkusit bundled
        bundled = Path(__file__).parent.parent.parent / "bin" / "adb.exe"
        if bundled.exists():
            return str(bundled)
        # Zkusit v current directory
        if (Path.cwd() / "adb.exe").exists():
            return str(Path.cwd() / "adb.exe")
        return "adb.exe"

    def run(self, timeout=120):
        print("\n=== DROID MIRROR QR PÁROVÁNÍ ===\n")
        print(f"  Service:   {self.service_name}")
        print(f"  Heslo:     {self.password}\n")
        print("  Toto není párovací server — telefon po naskenování QR")
        print("  spustí svuj vlastní server. PC ho detekuje pres mDNS")
        print("  a automaticky spustí `adb pair`.\n")

        self.show_qr()

        print(f"\n  Hledám telefon pres mDNS (max {timeout}s)...")
        print("  Ctrl+C pro zruseni.\n")

        start = time.time()
        found_addr = None
        nudged = False

        while time.time() - start < timeout:
            services = self._adb_mdns_services()
            for addr, name in services:
                if name == self.service_name:
                    found_addr = addr
                    break

            if found_addr:
                break

            elapsed = int(time.time() - start)
            if elapsed >= 15 and not nudged:
                nudged = True
                print("  Pořád nic. Pokud už jsi QR naskenoval,")
                print("  tahle síť pravděpodobně blokuje mDNS.")
                print("  Zkus místo QR použít USB (adb tcpip) nebo hotspot.\n")

            time.sleep(1)

        if not found_addr:
            print(f"\n[!] Telefon se neobjevil do {timeout}s.")
            print("    Ujisti se že:")
            print("    - Telefon je ve stejné WiFi síti jako PC")
            print("    - Bezdrátové ladění je ZAPNUTÉ")
            print("    - QR kód byl naskenovaný")
            return False

        print(f"\n  Nalezen telefon: {found_addr} ({self.service_name})")
        print(f"  Spouštím: adb pair {found_addr} {self.password}\n")

        try:
            adb = self._find_adb()
            r = subprocess.run(
                [adb, "pair", found_addr, self.password],
                capture_output=True, text=True, timeout=30,
            )
            output = (r.stdout + r.stderr).strip()
            print(f"  {output}\n")

            paired_ok = "Successfully paired" in output or (
                "pair" in output.lower() and "success" in output.lower()
            )

            if not paired_ok:
                print("✗ Párování se nezdařilo")
                return False

            print("✓ Párování bylo úspešné!")
            print("  Hledám adresu pro pripojení (_adb-tls-connect._tcp)...")

            host_ip = found_addr.split(":")[0]
            connect_addr = self._find_connect_addr(host_ip, timeout=10)

            if not connect_addr:
                print("[!] Connect sluzba se neobjevila automaticky.")
                print(f"    Zkus rucne pripojit pres Device Management -> Connect,")
                print(f"    IP adresa telefonu je: {host_ip}")
                return True  # parovani samo o sobe probehlo uspesne

            print(f"  Nalezeno: {connect_addr}")
            print(f"  Spouštím: adb connect {connect_addr}\n")

            c = subprocess.run(
                [adb, "connect", connect_addr],
                capture_output=True, text=True, timeout=15,
            )
            connect_output = (c.stdout + c.stderr).strip()
            print(f"  {connect_output}\n")

            if "connected" in connect_output.lower():
                print(f"✓ Pripojeno: {connect_addr}")
            else:
                print(f"[!] `adb connect` neuspel, zkus rucne: adb connect {connect_addr}")

            return True

        except subprocess.TimeoutExpired:
            print("[!] adb pair timeout (30s)")
            return False
        except Exception as e:
            print(f"[!] Chyba: {e}")
            return False
