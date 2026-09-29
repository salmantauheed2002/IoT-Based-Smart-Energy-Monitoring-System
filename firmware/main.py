"""
MicroPython firmware for ESP32 – Smart Extension Monitor (v9 equivalent)

Hardware:
  - 3 × PZEM-004T v3.0 on UART2 (GPIO16 RX, GPIO17 TX)
    Addresses: 0x01, 0x32, 0x42
  - DHT22 on GPIO21

Notes:
  - MicroPython does not have a mature official Firebase library.
    This version uses the Firebase Realtime Database REST API via urequests.
  - For production, prefer the original Arduino (FirebaseESP32) version
    or switch to MQTT + a cloud broker.
  - Install required libraries via upip or mpremote:
        mpremote mip install urequests
        mpremote mip install ntptime
        (DHT is built-in on most ESP32 ports)

Copy this file as main.py to the ESP32 filesystem.
"""

import network
import time
import json
import urequests
import ntptime
from machine import Pin, UART
import dht

# ---------------------------------------------------------------------------
# USER CONFIG – change these
# ---------------------------------------------------------------------------
WIFI_SSID = "Bhatti"
WIFI_PASSWORD = "robotics"

FIREBASE_API_KEY = "YOUR_API_KEY"
FIREBASE_DB_URL = "https://YOUR_PROJECT-default-rtdb.firebaseio.com"
FIREBASE_EMAIL = "your@email.com"
FIREBASE_PASSWORD = "yourpassword"
DB_PATH = "/dev1gf"

UPLOAD_INTERVAL_S = 20
WIFI_RETRY_S = 60

# ---------------------------------------------------------------------------
# Hardware setup
# ---------------------------------------------------------------------------
# Note: A proper PZEM Modbus library for MicroPython is required.
# One popular choice is: https://github.com/kizniche/pzem-004t-micropython
# For this portfolio example we show the structure and a stub reader.

try:
    from pzem import PZEM
    pzem1 = PZEM(uart=UART(2, baudrate=9600, tx=17, rx=16), addr=0x01)
    pzem2 = PZEM(uart=UART(2, baudrate=9600, tx=17, rx=16), addr=0x32)
    pzem3 = PZEM(uart=UART(2, baudrate=9600, tx=17, rx=16), addr=0x42)
    HAS_PZEM = True
except ImportError:
    print("PZEM library not found – using stub values")
    HAS_PZEM = False

dht_sensor = dht.DHT22(Pin(21))

# ---------------------------------------------------------------------------
# WiFi
# ---------------------------------------------------------------------------
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        for _ in range(30):
            if wlan.isconnected():
                break
            time.sleep(1)
    if wlan.isconnected():
        print("WiFi OK:", wlan.ifconfig()[0])
        return True
    print("WiFi failed")
    return False

# ---------------------------------------------------------------------------
# Firebase REST helpers
# ---------------------------------------------------------------------------
_id_token = None
_token_exp = 0

def get_id_token():
    global _id_token, _token_exp
    if _id_token and time.time() < _token_exp - 60:
        return _id_token

    url = (
        "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
        f"?key={FIREBASE_API_KEY}"
    )
    payload = {
        "email": FIREBASE_EMAIL,
        "password": FIREBASE_PASSWORD,
        "returnSecureToken": True,
    }
    r = urequests.post(url, json=payload)
    data = r.json()
    r.close()
    _id_token = data["idToken"]
    _token_exp = time.time() + int(data.get("expiresIn", 3600))
    return _id_token

def firebase_put(path: str, data: dict) -> bool:
    try:
        token = get_id_token()
        url = f"{FIREBASE_DB_URL}{path}.json?auth={token}"
        r = urequests.put(url, json=data)
        ok = 200 <= r.status_code < 300
        r.close()
        return ok
    except Exception as e:
        print("Firebase error:", e)
        return False

# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------
def sync_time():
    try:
        ntptime.host = "pool.ntp.org"
        ntptime.settime()
        print("NTP synced")
    except Exception as e:
        print("NTP failed:", e)

def path_key():
    # UTC+5 approximation (ESP32 RTC after NTP is UTC)
    t = time.localtime(time.time() + 5 * 3600)
    return "{:04d}{:02d}{:02d}{:02d}{:02d}{:02d}".format(*t[:6])

# ---------------------------------------------------------------------------
# Sensor reading
# ---------------------------------------------------------------------------
def read_pzem(pzem):
    if not HAS_PZEM:
        # Stub for testing without hardware
        import random
        return {
            "Voltage": 220 + random.uniform(-3, 3),
            "Current": random.uniform(0.1, 2.0),
            "Power": random.uniform(20, 400),
            "Energy": random.uniform(1, 10),
            "PowerFactor": random.uniform(0.8, 0.98),
            "Frequency": 50.0,
        }
    try:
        return {
            "Voltage": pzem.voltage,
            "Current": pzem.current,
            "Power": pzem.power,
            "Energy": pzem.energy,
            "PowerFactor": pzem.pf,
            "Frequency": pzem.frequency,
        }
    except Exception:
        return None

def read_dht():
    try:
        dht_sensor.measure()
        return {
            "Temperature": dht_sensor.temperature(),
            "Humidity": dht_sensor.humidity(),
        }
    except Exception:
        return {"Temperature": None, "Humidity": None}

def is_valid(reading: dict) -> bool:
    if reading is None:
        return False
    for k in ("Voltage", "Current", "Power", "Energy"):
        v = reading.get(k)
        if v is None or v != v or v == 0:  # NaN or zero
            return False
    return True

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def main():
    if not connect_wifi():
        return
    sync_time()

    last_upload = 0
    last_wifi_check = 0

    while True:
        now = time.time()

        # WiFi reconnect
        if now - last_wifi_check > WIFI_RETRY_S:
            last_wifi_check = now
            wlan = network.WLAN(network.STA_IF)
            if not wlan.isconnected():
                print("Reconnecting WiFi...")
                connect_wifi()

        if now - last_upload >= UPLOAD_INTERVAL_S:
            last_upload = now

            r1 = read_pzem(pzem1 if HAS_PZEM else None)
            r2 = read_pzem(pzem2 if HAS_PZEM else None)
            r3 = read_pzem(pzem3 if HAS_PZEM else None)
            env = read_dht()

            if is_valid(r1) and is_valid(r2) and is_valid(r3):
                key = path_key()
                payload = {
                    "Sensor1": r1,
                    "Sensor2": r2,
                    "Sensor3": r3,
                    "Environment": env,
                }
                path = f"{DB_PATH}/{key}"
                ok = firebase_put(path, payload)
                print(f"Upload {key}: {'OK' if ok else 'FAIL'}")
            else:
                print("Sensor data invalid – skip upload")

        time.sleep(1)

if __name__ == "__main__":
    main()