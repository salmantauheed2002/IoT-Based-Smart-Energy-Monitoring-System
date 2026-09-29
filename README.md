# ⚡ Smart Extension Monitor

**Multi-channel IoT energy & environment monitoring system**

A complete portfolio project that monitors power consumption from **three independent sockets** (PZEM-004T) plus ambient temperature & humidity (DHT22), then logs everything to the cloud (or runs fully offline in mock mode).

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![MicroPython](https://img.shields.io/badge/MicroPython-ESP32-orange)
![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-red)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **3× PZEM-004T** | Voltage, Current, Power, Energy, Power Factor, Frequency |
| **DHT22** | Temperature & Humidity |
| **Firebase RTDB** | Real-time cloud storage (optional) |
| **Mock / Local mode** | Fully offline – perfect for demos & portfolio |
| **Realistic Simulator** | Generates plausible sensor data with daily patterns |
| **Streamlit Dashboard** | Live charts, KPIs, history table |
| **MicroPython Firmware** | Ready-to-flash ESP32 code |

---

## 🏗️ Project Structure

```
smart-extension-monitor/
├── README.md
├── requirements.txt
├── .env.example
├── LICENSE
├── firmware/
│   └── main.py                 # MicroPython firmware for ESP32
├── simulator/
│   └── sensor_simulator.py     # Pure-Python sensor simulator
├── dashboard/
│   └── app.py                  # Streamlit web dashboard
└── src/
    ├── config.py
    ├── data_models.py
    └── firebase_client.py      # Shared client (mock + real Firebase)
```

---

## 🚀 Quick Start

### 1. Clone & install

```bash
git clone https://github.com/YOUR_USERNAME/smart-extension-monitor.git
cd smart-extension-monitor

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run in Mock mode (default)

```bash
# Terminal 1 – start generating realistic sensor data
python -m simulator.sensor_simulator

# Terminal 2 – launch the dashboard
streamlit run dashboard/app.py
```

Open the browser at the URL Streamlit prints (usually http://localhost:8501).

You will immediately see live power charts, energy bars, temperature/humidity, and a history table – all stored locally in `data/local_store.json`.

---

## ☁️ Optional: Connect Real Firebase

1. Create a Firebase project → enable **Realtime Database** + **Email/Password** auth.
2. Copy `.env.example` → `.env` and fill in:

```env
MOCK_MODE=false
FIREBASE_API_KEY=...
FIREBASE_DATABASE_URL=https://YOUR_PROJECT-default-rtdb.firebaseio.com
FIREBASE_USER_EMAIL=...
FIREBASE_USER_PASSWORD=...
FIREBASE_DATABASE_PATH=/dev1gf
```

3. Restart the simulator and dashboard. Data now goes to the cloud.

---

## 🔌 Hardware Version (ESP32)

### Wiring

| Component | ESP32 Pin | Notes |
|-----------|-----------|-------|
| PZEM TX | GPIO 16 (RX2) | All 3 PZEMs share the bus |
| PZEM RX | GPIO 17 (TX2) | Different Modbus addresses |
| DHT22 Data | GPIO 21 | |
| Common GND | GND | |

**PZEM Addresses used:** `0x01`, `0x32`, `0x42`

### Flash MicroPython firmware

```bash
# Install mpremote if needed
pip install mpremote

# Copy the firmware
mpremote cp firmware/main.py :main.py

# Reset
mpremote reset
```

> **Note:** A proper PZEM Modbus library (e.g. [kizniche/pzem-004t-micropython](https://github.com/kizniche/pzem-004t-micropython)) should be installed on the device.

---

## 📊 Dashboard Preview

The Streamlit dashboard shows:

- Live power of all 3 sensors
- Voltage trends
- Temperature & humidity
- Cumulative energy (kWh)
- Auto-refresh every 15 seconds
- Raw data table

---

## 🛠️ Tech Stack

- **Language:** Python 3.10+
- **Dashboard:** Streamlit + Plotly
- **Data:** Pandas, local JSON (mock) or Firebase REST API
- **Firmware:** MicroPython (ESP32)
- **Hardware:** ESP32, PZEM-004T v3.0, DHT22

---

## 📄 License

MIT – feel free to use in your own projects and portfolio.

---

## 👤 Author

Built as a portfolio project demonstrating IoT, embedded systems, cloud integration, and modern Python data visualization.
