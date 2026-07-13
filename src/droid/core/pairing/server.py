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

# ----- ADB key management -----

ADB_KEY_DIR = Path.home() / ".android"


def _ensure_adb_keypair() -> tuple[bytes, bytes]:
    """Return (private_key_bytes, public_key_bytes) for this PC."""
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

    priv = X25519PrivateKey.generate()
    raw_priv = priv.private_bytes_raw()
    raw_pub = priv.public_key().public_bytes_raw()

    ADB_KEY_DIR.mkdir(parents=True, exist_ok=True)

    # Uloz ADB privátní klíc
    _save_adb_private_key(raw_priv, ADB_KEY_DIR / "adbkey")
    # Uloz ADB pub klíc (base64 + jméno)
    import base64
    pub_b64 = base64.b64encode(raw_pub).decode()
    (ADB_KEY_DIR / "adbkey.pub").write_text(f"{pub_b64} droid-mirror@pc\n")

    return raw_priv, raw_pub


def _save_adb_private_key(raw_priv: bytes, path: Path):
    """Uloz 32B X25519 private key do PKCS#8 PEM."""
    import base64
    # PKCS#8 wrapper pro X25519 private key
    prefix = bytes.fromhex(
        "308187020100301306072a8648ce3d020106082a8648ce3d030107046d306b0201010420"
    )
    suffix = bytes.fromhex(
        "a144034200"
    )
    pkcs8 = prefix + raw_priv + suffix + raw_priv
    b64 = base64.b64encode(pkcs8).decode()
    pem = f"-----BEGIN PRIVATE KEY-----\n{b64}\n-----END PRIVATE KEY-----\n"
    path.write_text(pem)


# ----- Pairing server -----

class AdbPairingServer:
    """TCP server pro ADB pairing s QR."""

    def __init__(self, password: str | None = None):
        self.password = password or self._generate_password()
        self.service_name = self._generate_service_name()

        # Server keypair
        self.priv_bytes, self.pub_bytes = _ensure_adb_keypair()

        # Network
        self.host = self._get_local_ip()
        self.port = self._find_free_port()
        self.server_sock: socket.socket | None = None
        self._running = False

        # mDNS
        self.zeroconf: Zeroconf | None = None
        self.service_info: ServiceInfo | None = None

    @staticmethod
    def _generate_password(length: int = 6) -> str:
        return "".join(random.choices(string.digits, k=length))

    @staticmethod
    def _generate_service_name(length: int = 10) -> str:
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=length))
        return f"adb-pair-{suffix}"

    @staticmethod
    def _get_local_ip() -> str:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"
        finally:
            s.close()

    @staticmethod
    def _find_free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            return s.getsockname()[1]

    def get_qr_data(self) -> str:
        return f"WIFI:T:ADB;S:{self.service_name};P:{self.password};;"

    def show_qr(self):
        """Zobraz QR v terminálu + uloz PNG."""
        qr_data = self.get_qr_data()
        qr = qrcode.QRCode(border=2, box_size=2)
        qr.add_data(qr_data)
        qr.make(fit=True)

        print("\n── QR KÓD PRO SPÁROVÁNÍ ──")
        print("  1. Na telefonu otevri: Vývojárské možnosti ->")
        print("     Bezdrátové lade ní -> Spárovat zarízení pomocí QR")
        print("  2. Naskenuj tento QR kamerou telefonu:\n")
        qr.print_ascii()
        print()
        print(f"  Service:  {self.service_name}")
        print(f"  Password: {self.password}")
        print(f"  IP:       {self.host}:{self.port}")
        print(f"  QR data:  {qr_data}")

        try:
            from PIL import Image as PILImage
            img = qr.make_image()
            save_path = Path("pairing_qr.png").resolve()
            img.save(save_path)
            print(f"\n  QR ulozen: {save_path}")
            try:
                os.startfile(save_path)
            except Exception:
                pass
        except ImportError:
            pass

    def start_mdns(self):
        """Vyhlas mDNS _adb-tls-pairing._tcp."""
        service_type = "_adb-tls-pairing._tcp.local."
        fqdn = f"{self.service_name}.{service_type}"

        self.service_info = ServiceInfo(
            type_=service_type,
            name=fqdn,
            addresses=[socket.inet_aton(self.host)],
            port=self.port,
        )

        self.zeroconf = Zeroconf()
        self.zeroconf.register_service(self.service_info)
        print(f"[mDNS] Vyhláseno: {self.service_name} -> {self.host}:{self.port}")

    def stop_mdns(self):
        if self.zeroconf and self.service_info:
            self.zeroconf.unregister_service(self.service_info)
            self.zeroconf.close()
            self.zeroconf = None
            self.service_info = None

    def start_server(self):
        """Start TCP server v background thread."""
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind(("0.0.0.0", self.port))
        self.server_sock.listen(1)
        self.server_sock.settimeout(60)
        self._running = True
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def _accept_loop(self):
        try:
            conn, addr = self.server_sock.accept()
            print(f"\n[>] Telefon se pripojil z {addr[0]}:{addr[1]}")
            self._handle_connection(conn)
        except socket.timeout:
            print("\n[!] Cas vyprsel - nikdo se nepripojil")
        except Exception as e:
            print(f"\n[!] Chyba: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._running = False
            if self.server_sock:
                try:
                    self.server_sock.close()
                except Exception:
                    pass

    def _handle_connection(self, conn: socket.socket):
        """Noise_NKpsk0 handshake + overeni kodu + vymena klicu."""
        try:
            # PSK = SHA256(password)
            import hashlib
            psk = hashlib.sha256(self.password.encode()).digest()

            # Server-side Noise_NKpsk0
            noise = NoiseConnection.from_name(b"Noise_NKpsk0_25519_AESGCM_SHA256")
            noise.set_as_responder()
            noise.set_keypair_from_private_bytes(Keypair.STATIC, self.priv_bytes)
            noise.set_psks(psk=psk)
            noise.start_handshake()

            # --- Msg 1: client -> server (ephemeral) ---
            raw1 = self._recv_exact(conn, 48)  # 32 ephem + 16 tag
            noise.read_message(raw1)
            print(f"[Noise] Msg1 - client ephemeral prijat")

            # --- Msg 2: server -> client (ephemeral) ---
            raw2 = noise.write_message(b"")
            self._send_all(conn, raw2)
            print(f"[Noise] Msg2 - server ephemeral odeslán")

            # --- Handshake dokoncen, kanal je encrypted ---

            # Prijmout encrypted payload: [delka:2][encrypted_data:delka]
            len_raw = self._recv_exact(conn, 2)
            payload_len = struct.unpack("!H", len_raw)[0]
            encrypted = self._recv_exact(conn, payload_len)
            payload = noise.decrypt(bytes(encrypted))

            # Parsovat: 6B kod + 32B public key (X25519)
            code = payload[:6].decode("ascii", errors="replace")
            phone_pub = payload[6:]

            print(f"[Pripojeni] Kod: '{code}' | Klíc: {phone_pub.hex()[:32]}...")

            if code != self.password:
                print(f"[!] CHYBA: nespravny kod ({code} != {self.password})")
                resp = noise.encrypt(b"FAIL")
                self._send_all(conn, struct.pack("!H", len(resp)) + resp)
                return

            print(f"[OK] Párovací kód souhlasí!")

            # Ulozit klíc telefonu do ADB trusted keys
            self._store_phone_key(phone_pub)

            # Odeslat OK + náš public key
            resp_data = b"OK" + self.pub_bytes
            encrypted_resp = noise.encrypt(resp_data)
            self._send_all(conn, struct.pack("!H", len(encrypted_resp)) + encrypted_resp)

            print(f"[OK] Párování dokonceno! Klíc telefonu ulozen.")
            print(f"[OK] Nyní muzeš pripojit: adb connect {self.host}:5555")

        except Exception as e:
            print(f"[!] Chyba behem párování: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.close()

    def _store_phone_key(self, pub_key: bytes):
        """Uloz telefonní klíc do ~/.android/adb_keys."""
        keys_path = ADB_KEY_DIR / "adb_keys"
        ADB_KEY_DIR.mkdir(parents=True, exist_ok=True)
        import base64
        pub_b64 = base64.b64encode(pub_key).decode()
        entry = f"{pub_b64} droid-mirror-paired\n"
        with open(keys_path, "a") as f:
            f.write(entry)
        print(f"[ADB] Klíc ulozen do {keys_path}")

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

    def run(self, timeout: int = 120):
        """Spust server a cekej na pripojeni."""
        print("\n=== DROID MIRROR PÁROVACÍ SERVER ===\n")
        print(f"  Heslo:     {self.password}")
        print(f"  Service:   {self.service_name}")
        print(f"  IP:Port:   {self.host}:{self.port}\n")

        self.start_mdns()
        self.start_server()
        self.show_qr()

        print(f"\n  Cekam na pripojeni telefonu (timeout: {timeout}s)...")
        print("  Ctrl+C pro zruseni.\n")

        start = time.time()
        try:
            while self._running:
                if timeout and (time.time() - start) > timeout:
                    print(f"\n[!] Timeout {timeout}s")
                    break
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n[!] Zruseno")
        finally:
            self.stop()

    def stop(self):
        self._running = False
        self.stop_mdns()
        if self.server_sock:
            try:
                self.server_sock.close()
            except Exception:
                pass
