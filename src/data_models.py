"""
Simple data models / helpers for sensor readings.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any
from datetime import datetime


@dataclass
class PZEMReading:
    voltage: float
    current: float
    power: float
    energy: float
    power_factor: float
    frequency: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "Voltage": round(self.voltage, 2),
            "Current": round(self.current, 3),
            "Power": round(self.power, 2),
            "Energy": round(self.energy, 3),
            "PowerFactor": round(self.power_factor, 3),
            "Frequency": round(self.frequency, 1),
        }


@dataclass
class EnvironmentReading:
    temperature: float
    humidity: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "Temperature": round(self.temperature, 1),
            "Humidity": round(self.humidity, 1),
        }


@dataclass
class Snapshot:
    """One complete reading from all sensors at a point in time."""
    timestamp: datetime
    sensors: Dict[str, PZEMReading]          # "Sensor1", "Sensor2", ...
    environment: EnvironmentReading

    def path_key(self) -> str:
        """Firebase-style path key: YYYYMMDDHHMMSS"""
        return self.timestamp.strftime("%Y%m%d%H%M%S")

    def to_firebase_dict(self) -> Dict[str, Any]:
        data = {}
        for name, reading in self.sensors.items():
            data[name] = reading.to_dict()
        data["Environment"] = self.environment.to_dict()
        return data