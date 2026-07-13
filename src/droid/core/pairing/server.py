"""
ADB pairing server -- mDNS + Noise_NKpsk0 + QR.

Flow:
1. PC generuje service_name + pairing code
2. PC vyhlásí mDNS _adb-tls-pairing._tcp
3. PC zobrazí QR: WIFI:T:ADB;S:<service>;P:<code>;;
4. Telefon naskenuje QR, najde service pres mDNS, pripojí se TCP
5. Noise_NKpsk0 handshake (PSK = SHA256(heslo))
6. Po handshaku: telefon pošle heslo + svuj certifikát
7. Server overí heslo a uloží certifikát
8. Hotovo
"""

import os
import random
import socket
import struct
import string
import sys
import threading
import time
from pathlib import Path

from noise.connection import NoiseConnection, Keypair
from zeroconf import ServiceInfo, Zeroconf
import qrcode

ADB_KEY_DIR = Path.home() / ".android"
_RECV_TIMEOUT = 10  # seconds pro kazde cteni

# ============================================================
# ADB key management
# ============================================================

def _ensure_adb_keypair() -> tuple[bytes, bytes]:
    """Vrati (private, public) klic pro ADB.
    Pouzije existujici ~/.android/adbkey pokud existuje,
    jinak vygeneruje novy."""
    priv_path = ADB_KEY_DIR / "adbkey"
    pub_path = ADB_KEY_DIR / "adbkey.pub"

    # Pouzit existujici klic pokud uz existuje
    if priv_path.exists() and pub_path.exists():
        import base64
        try:
            pem = priv_path.read_text()
            lines = pem.split("\n")
            b64 = "".join(l for l in lines if l and not l.startswith("---"))
            der = base64.b64decode(b64)
            raw_priv = der[-32:]
            pub_line = pub_path.read_text().strip()
            raw_pub = base64.b64decode(pub_line.split()[0])
            print(f"[ADB] Pouzit existujici klic: {priv_path}")
            return raw_priv, raw_pub
        except Exception as e:
            print(f"[ADB] Chyba cteni klice, generuji novy: {e}")

    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
    priv = X25519PrivateKey.generate()
    raw_priv = priv.private_bytes_raw()
    raw_pub = priv.public_key().public_bytes_raw()
    ADB_KEY_DIR.mkdir(parents=True, exist_ok=True)
    _save_adb_private_key(raw_priv, priv_path)
    import base64
    pub_b64 = base64.b64encode(raw_pub).decode()
    pub_path.write_text(f"{pub_b64} droid-mirror@pc\n")
    print(f"[ADB] Vygenerovan novy klic: {priv_path}")
    return raw_priv, raw_pub


def _save_adb_private_key(raw_priv: bytes, path: Path):
    import base64
    prefix = bytes.fromhex("308187020100301306072a8648ce3d020106082a8648ce3d030107046d306b0201010420")
    suffix = bytes.fromhex("a144034200")
    pkcs8 = prefix + raw_priv + suffix + raw_priv
    b64 = base64.b64encode(pkcs8).decode()
    pem = f"-----BEGIN PRIVATE KEY-----\n{b64}\n-----END PRIVATE KEY-----\n"
    path.write_text(pem)


# ============================================================
# Pairing server
# ============================================================

class AdbPairingServer:
    def __init__(self, password: str | None = None):
        self.password = password or self._generate_password()
        self.service_name = self._generate_service_name()
        # Pro Noise handshake generujeme FRESH X25519 klic (ne ADB RSA klic)
        self._noise_priv, self._noise_pub = self._generate_noise_keypair()
        self.host = self._get_local_ip()
        self.port = self._find_free_port()
        self.server_sock: socket.socket | None = None
        self._running = False
        self._paired_ok = False
        self.zeroconf: Zeroconf | None = None
        self.service_info: ServiceInfo | None = None

    @staticmethod
    def _generate_noise_keypair() -> tuple[bytes, bytes]:
        from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
        priv = X25519PrivateKey.generate()
        return priv.private_bytes_raw(), priv.public_key().public_bytes_raw()

    @staticmethod
    def _generate_password(length=6):
        return "".join(random.choices(string.digits, k=length))

    @staticmethod
    def _generate_service_name(length=10):
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=length))
        return f"adb-pair-{suffix}"

    @staticmethod
    def _get_local_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
        except:
            return "127.0.0.1"
        finally:
            s.close()

    @staticmethod
    def _find_free_port():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            return s.getsockname()[1]

    def get_qr_data(self):
        return f"WIFI:T:ADB;S:{self.service_name};P:{self.password};;"

    def show_qr(self):
        qr_data = self.get_qr_data()
        qr = qrcode.QRCode(border=2, box_size=10)
        qr.add_data(qr_data)
        qr.make(fit=True)

        print("\n── QR KÓD PRO SPÁROVÁNÍ ──")
        print("  Otevrelo se okno s QR kódem v prohlížeci obrazku.")
        print()
        print(f"  Na telefonu otevri: Vývojárské možnosti ->")
        print(f"  Bezdrátové lade ní -> Spárovat zarízení pomocí QR")
        print(f"  a naskenuj QR kamerou telefonu.\n")
        print(f"  IP:Port:   {self.host}:{self.port}")
        print(f"  Heslo:     {self.password}")
        print(f"  QR data:   {qr_data}\n")

        # Ulozit jako PNG a otevrit
        from PIL import Image as PILImage
        img = qr.make_image(fill_color="black", back_color="white")
        save_path = Path("pairing_qr.png").resolve()
        img.save(save_path)
        print(f"  QR ulozen: {save_path}")

        # Otevrit v default vieweru
        try:
            os.startfile(save_path)
            print(f"  Otevren v defaultním prohlížeci obrazku")
        except Exception:
            print(f"  Pokud se neotevre, otevri rucne: {save_path}")

    # ---- mDNS ----

    def start_mdns(self):
        import base64
        pub_b64 = base64.b64encode(self._noise_pub).decode()
        service_type = "_adb-tls-pairing._tcp.local."
        fqdn = f"{self.service_name}.{service_type}"
        self.service_info = ServiceInfo(
            type_=service_type,
            name=fqdn,
            addresses=[socket.inet_aton(self.host)],
            port=self.port,
            properties={"K": pub_b64},
        )
        self.zeroconf = Zeroconf()
        self.zeroconf.register_service(self.service_info)
        print(f"[mDNS] Vyhláseno: {self.service_name} na {self.host}:{self.port}")

    def stop_mdns(self):
        if self.zeroconf:
            try:
                self.zeroconf.unregister_service(self.service_info)
                self.zeroconf.close()
            except Exception as e:
                print(f"[mDNS] Chyba pri ukoncovani: {e}")
            self.zeroconf = None
            self.service_info = None

    # ---- TCP server ----

    def start_server(self):
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind(("0.0.0.0", self.port))
        self.server_sock.listen(1)
        self.server_sock.settimeout(1.0)  # kratky timeout, hlavni smycka ridi celkovy timeout
        self._running = True
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def _accept_loop(self):
        try:
            conn, addr = self.server_sock.accept()
            print(f"\n[Pripojeni] Telefon: {addr[0]}:{addr[1]}")
            conn.settimeout(_RECV_TIMEOUT)
            self._handle_connection(conn)
            self._running = False  # uspesne dokonceno
        except socket.timeout:
            pass  # hlavni smycka rozhodne o celkovem timeoutu
        except Exception as e:
            print(f"\n[!] Chyba v accept: {e}")
            import traceback
            traceback.print_exc()
            self._running = False
        if self.server_sock:
            try: self.server_sock.close()
            except: pass

    # ---- Handshake ----

    def _handle_connection(self, conn: socket.socket):
        try:
            import hashlib
            psk = hashlib.sha256(self.password.encode()).digest()

            noise = NoiseConnection.from_name(b"Noise_NKpsk0_25519_AESGCM_SHA256")
            noise.set_as_responder()
            noise.set_keypair_from_private_bytes(Keypair.STATIC, self._noise_priv)
            noise.set_psks(psk=psk)
            noise.start_handshake()

            # Msg1: client -> server (48B = 32 ephem + 16 tag)
            raw1 = self._recv_exact(conn, 48)
            noise.read_message(raw1)
            print("[Noise] Msg1 OK")

            # Msg2: server -> client (48B)
            raw2 = noise.write_message(b"")
            self._send_all(conn, raw2)
            print("[Noise] Msg2 OK – kanal encrypted")

            # encrypted payload: [2B delka][data]
            len_raw = self._recv_exact(conn, 2)
            payload_len = struct.unpack("!H", len_raw)[0]
            encrypted = self._recv_exact(conn, payload_len)
            payload = noise.decrypt(bytes(encrypted))

            code = payload[:6].decode("ascii", errors="replace")
            phone_pub = payload[6:]
            print(f"[Data] Kod='{code}' pubkey={phone_pub.hex()[:20]}...")

            if code != self.password:
                print(f"[!] CHYBA: kód {code} != {self.password}")
                return

            print("[OK] Heslo souhlasí, ukladám klíc")
            self._store_phone_key(phone_pub)
            self._paired_ok = True

            # odpoved: OK + nase pubkey
            resp = noise.encrypt(b"OK" + self._noise_pub)
            self._send_all(conn, struct.pack("!H", len(resp)) + resp)
            print("[OK] Párování dokonceno!")
            print(f"[OK] Nyní pripoj: adb connect {self.host}:5555\n")

        except socket.timeout:
            print(f"[!] Timeout - telefon neposlal data do {_RECV_TIMEOUT}s")
        except ConnectionError as e:
            print(f"[!] Spojení preruseno: {e}")
        except Exception as e:
            print(f"[!] Chyba: {e}")
            import traceback
            traceback.print_exc()
        finally:
            try: conn.close()
            except: pass

    def _store_phone_key(self, pub_key: bytes):
        keys_path = ADB_KEY_DIR / "adb_keys"
        ADB_KEY_DIR.mkdir(parents=True, exist_ok=True)
        import base64
        pub_b64 = base64.b64encode(pub_key).decode()
        with open(keys_path, "a") as f:
            f.write(f"{pub_b64} droid-mirror-paired\n")
        print(f"[ADB] Klíc ulozen do {keys_path}")

    # ---- I/O helpers ----

    @staticmethod
    def _recv_exact(sock: socket.socket, n: int) -> bytes:
        data = b""
        while len(data) < n:
            chunk = sock.recv(n - len(data))
            if not chunk:
                raise ConnectionError("Spojení ukonceno")
            data += chunk
        return data

    @staticmethod
    def _send_all(sock: socket.socket, data: bytes):
        sock.sendall(data)

    # ---- Run / Stop ----

    def run(self, timeout=120):
        print("\n=== DROID MIRROR PÁROVACÍ SERVER ===\n")
        print(f"  Heslo:     {self.password}")
        print(f"  Service:   {self.service_name}")
        print(f"  IP:Port:   {self.host}:{self.port}")

        # Otestovat jestli je port dosazitelny
        print(f"\n  Poznámka: Telefon a PC musí být ve stejné WiFi síti.")
        print(f"  Pokud pripojeni selze, zkus vypnout Windows Firewall")
        print(f"  nebo pridej pravidlo pro port {self.port}.")

        self.start_mdns()
        self.start_server()
        self.show_qr()

        print(f"\n  Cekam na pripojeni telefonu (max {timeout}s)...")
        print("  Ctrl+C pro zruseni.\n")

        start = time.time()
        try:
            while self._running:
                if timeout and (time.time() - start) > timeout:
                    print(f"\n[!] Timeout {timeout}s")
                    break
                time.sleep(0.2)
        except KeyboardInterrupt:
            print("\n[!] Zruseno uzivatelem")
        finally:
            self.stop()

        if self._paired_ok:
            print("\n✓ Spárování bylo úspešné!")
        else:
            print("\n✗ Párování se nezdarilo")

    def stop(self):
        self._running = False
        self.stop_mdns()
        if self.server_sock:
            try: self.server_sock.close()
            except: pass
