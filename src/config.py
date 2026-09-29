"""
Configuration loader with mock-mode support.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() in ("true", "1", "yes")

FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY", "")
FIREBASE_DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL", "").rstrip("/")
FIREBASE_USER_EMAIL = os.getenv("FIREBASE_USER_EMAIL", "")
FIREBASE_USER_PASSWORD = os.getenv("FIREBASE_USER_PASSWORD", "")
FIREBASE_DATABASE_PATH = os.getenv("FIREBASE_DATABASE_PATH", "/dev1gf")

# Local storage used in mock mode
LOCAL_DB_PATH = ROOT / "data" / "local_store.json"

# Simulator defaults
SIMULATOR_INTERVAL_SEC = 20
NUM_SENSORS = 3