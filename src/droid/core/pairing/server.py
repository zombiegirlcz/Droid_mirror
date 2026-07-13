"""
ADB QR pairing -- správný flow podle adbqr.

Flow:
1. PC vygeneruje service_name + 6-místný code
2. PC ukáže QR: WIFI:T:ADB;S:<service>;P:<code>;;
3. Telefon naskenuje QR, spustí vlastní párovací server a vyhlásí mDNS
4. PC detekuje telefon pres `adb mdns services`
5. PC spustí `adb pair <ip>:<port> <code>` → Noise handshake mezi adb + telefonem
6. Hotovo (žádný vlastní Noise server)
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

    def _adb_mdns_services(self):
        """Vrati seznam (ip:port, service_name) z adb mdns services."""
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
                if len(parts) >= 3 and "_adb-tls-pairing" in line:
                    services.append((parts[-1], parts[0]))
            return services
        except Exception:
            return []

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

            if "Successfully paired" in output or "pair" in output.lower() and "success" in output.lower():
                print("✓ Párování bylo úspešné!")
                return True
            else:
                print("✗ Párování se nezdařilo")
                return False

        except subprocess.TimeoutExpired:
            print("[!] adb pair timeout (30s)")
            return False
        except Exception as e:
            print(f"[!] Chyba: {e}")
            return False
