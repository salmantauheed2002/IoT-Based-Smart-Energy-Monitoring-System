#!/usr/bin/env python3
"""
Realistic multi-PZEM + DHT sensor simulator.

Generates plausible AC energy data for 3 channels + environment
and pushes it to Firebase (or local mock store) every N seconds.

Usage:
    python -m simulator.sensor_simulator
    # or
    python simulator/sensor_simulator.py
"""

from __future__ import annotations

import math
import random
import signal
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Allow running both as module and as script
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import SIMULATOR_INTERVAL_SEC, NUM_SENSORS
from src.data_models import PZEMReading, EnvironmentReading, Snapshot
from src.firebase_client import get_client


# Pakistan Standard Time (UTC+5)
PKT = timezone(timedelta(hours=5))


class SensorSimulator:
    def __init__(self, num_sensors: int = NUM_SENSORS):
        self.num_sensors = num_sensors
        self.client = get_client()
        self.running = True

        # Persistent energy counters (kWh) so they accumulate realistically
        self.energy = [random.uniform(0.5, 12.0) for _ in range(num_sensors)]

        # Base load profiles (different for each "socket")
        # (base_power_W, variability, pf_base)
        self.profiles = [
            (85.0, 25.0, 0.92),   # Sensor1 – laptop / electronics
            (420.0, 80.0, 0.85),  # Sensor2 – appliance / heater-ish
            (55.0, 15.0, 0.95),   # Sensor3 – phone chargers / lights
        ]

        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

    def _shutdown(self, *args):
        print("\n[Simulator] Shutting down...")
        self.running = False

    def _generate_pzem(self, idx: int) -> PZEMReading:
        base_p, var, pf_base = self.profiles[idx % len(self.profiles)]

        # Slight daily + random variation
        t = time.time()
        daily = 1.0 + 0.15 * math.sin(2 * math.pi * (t % 86400) / 86400)
        power = max(0.0, base_p * daily + random.gauss(0, var))

        voltage = 220.0 + random.gauss(0, 3.5)          # ~220 V ± noise
        pf = max(0.6, min(1.0, pf_base + random.gauss(0, 0.03)))
        current = power / (voltage * pf) if pf > 0 else 0.0
        frequency = 50.0 + random.gauss(0, 0.05)

        # Accumulate energy (very rough: power_kW * hours)
        dt_h = SIMULATOR_INTERVAL_SEC / 3600.0
        self.energy[idx] += (power / 1000.0) * dt_h

        return PZEMReading(
            voltage=voltage,
            current=current,
            power=power,
            energy=self.energy[idx],
            power_factor=pf,
            frequency=frequency,
        )

    def _generate_environment(self) -> EnvironmentReading:
        # Mild daily temperature swing + noise
        hour = datetime.now(PKT).hour
        temp_base = 26.0 + 4.0 * math.sin((hour - 6) / 24 * 2 * math.pi)
        temp = temp_base + random.gauss(0, 0.4)
        humidity = 55.0 + random.gauss(0, 4.0)
        humidity = max(20.0, min(95.0, humidity))
        return EnvironmentReading(temperature=temp, humidity=humidity)

    def create_snapshot(self) -> Snapshot:
        sensors = {}
        for i in range(self.num_sensors):
            sensors[f"Sensor{i+1}"] = self._generate_pzem(i)

        return Snapshot(
            timestamp=datetime.now(PKT),
            sensors=sensors,
            environment=self._generate_environment(),
        )

    def run(self, interval: int = SIMULATOR_INTERVAL_SEC):
        print("=" * 60)
        print("  Smart Extension – Sensor Simulator")
        print(f"  Mode     : {'MOCK / LOCAL' if self.client.mock else 'REAL FIREBASE'}")
        print(f"  Interval : {interval}s")
        print(f"  Sensors  : {self.num_sensors} × PZEM + DHT")
        print("=" * 60)
        print("Press Ctrl+C to stop\n")

        while self.running:
            snap = self.create_snapshot()
            key = snap.path_key()
            payload = snap.to_firebase_dict()

            ok = self.client.set(key, payload)
            status = "OK" if ok else "FAILED"

            # Pretty console output
            s1 = snap.sensors["Sensor1"]
            env = snap.environment
            print(
                f"[{snap.timestamp.strftime('%H:%M:%S')}] "
                f"S1: {s1.power:6.1f} W  "
                f"S2: {snap.sensors['Sensor2'].power:6.1f} W  "
                f"S3: {snap.sensors['Sensor3'].power:6.1f} W  "
                f"| {env.temperature:4.1f}°C  {env.humidity:4.1f}%  → {status}"
            )

            # Sleep in small steps so Ctrl+C is responsive
            for _ in range(interval):
                if not self.running:
                    break
                time.sleep(1)


def main():
    sim = SensorSimulator()
    sim.run()


if __name__ == "__main__":
    main()