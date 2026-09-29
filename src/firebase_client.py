"""
Firebase client with seamless Mock / Local mode.

When MOCK_MODE=true (default), all reads/writes go to a local JSON file.
When MOCK_MODE=false and credentials are present, it uses Firebase REST API.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

import requests

from .config import (
    MOCK_MODE,
    FIREBASE_API_KEY,
    FIREBASE_DATABASE_URL,
    FIREBASE_USER_EMAIL,
    FIREBASE_USER_PASSWORD,
    FIREBASE_DATABASE_PATH,
    LOCAL_DB_PATH,
)


class FirebaseClient:
    def __init__(self):
        self.mock = MOCK_MODE or not all(
            [FIREBASE_API_KEY, FIREBASE_DATABASE_URL, FIREBASE_USER_EMAIL, FIREBASE_USER_PASSWORD]
        )
        self._id_token: Optional[str] = None
        self._token_expiry: float = 0

        if self.mock:
            LOCAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            if not LOCAL_DB_PATH.exists():
                LOCAL_DB_PATH.write_text("{}")
            print("[FirebaseClient] Running in MOCK / LOCAL mode →", LOCAL_DB_PATH)
        else:
            print("[FirebaseClient] Running against real Firebase")

    # ------------------------------------------------------------------
    # Auth (real Firebase only)
    # ------------------------------------------------------------------
    def _ensure_token(self) -> str:
        if self.mock:
            return "mock-token"

        if self._id_token and time.time() < self._token_expiry - 60:
            return self._id_token

        url = (
            f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
            f"?key={FIREBASE_API_KEY}"
        )
        payload = {
            "email": FIREBASE_USER_EMAIL,
            "password": FIREBASE_USER_PASSWORD,
            "returnSecureToken": True,
        }
        r = requests.post(url, json=payload, timeout=15)
        r.raise_for_status()
        data = r.json()
        self._id_token = data["idToken"]
        self._token_expiry = time.time() + int(data.get("expiresIn", 3600))
        return self._id_token

    # ------------------------------------------------------------------
    # Low-level helpers
    # ------------------------------------------------------------------
    def _local_read(self) -> Dict[str, Any]:
        try:
            return json.loads(LOCAL_DB_PATH.read_text())
        except Exception:
            return {}

    def _local_write(self, data: Dict[str, Any]) -> None:
        LOCAL_DB_PATH.write_text(json.dumps(data, indent=2, default=str))

    def _rest_url(self, path: str) -> str:
        # path should start with /
        return f"{FIREBASE_DATABASE_URL}{path}.json"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set(self, relative_path: str, data: Dict[str, Any]) -> bool:
        """
        Write data under FIREBASE_DATABASE_PATH / relative_path
        Example: relative_path = "20260928145530"
        """
        full_path = f"{FIREBASE_DATABASE_PATH.rstrip('/')}/{relative_path.lstrip('/')}"

        if self.mock:
            store = self._local_read()
            # Navigate / create nested dict
            parts = [p for p in full_path.strip("/").split("/") if p]
            node = store
            for p in parts[:-1]:
                node = node.setdefault(p, {})
            node[parts[-1]] = data
            self._local_write(store)
            return True

        try:
            token = self._ensure_token()
            url = self._rest_url(full_path)
            r = requests.put(url, json=data, params={"auth": token}, timeout=15)
            r.raise_for_status()
            return True
        except Exception as e:
            print(f"[FirebaseClient] set() failed: {e}")
            return False

    def get_all(self) -> Dict[str, Any]:
        """Return the entire tree under FIREBASE_DATABASE_PATH"""
        if self.mock:
            store = self._local_read()
            parts = [p for p in FIREBASE_DATABASE_PATH.strip("/").split("/") if p]
            node = store
            for p in parts:
                node = node.get(p, {})
            return node if isinstance(node, dict) else {}

        try:
            token = self._ensure_token()
            url = self._rest_url(FIREBASE_DATABASE_PATH)
            r = requests.get(url, params={"auth": token}, timeout=15)
            r.raise_for_status()
            data = r.json()
            return data if isinstance(data, dict) else {}
        except Exception as e:
            print(f"[FirebaseClient] get_all() failed: {e}")
            return {}

    def get_latest_n(self, n: int = 50) -> List[Dict[str, Any]]:
        """
        Return the most recent n snapshots, newest first.
        Each item: {"key": "20260928145530", "data": {...}}
        """
        tree = self.get_all()
        if not tree:
            return []

        # Keys are YYYYMMDDHHMMSS → lexicographical sort works
        keys = sorted(tree.keys(), reverse=True)[:n]
        return [{"key": k, "data": tree[k]} for k in keys if isinstance(tree.get(k), dict)]


# Singleton-style helper
_client: Optional[FirebaseClient] = None


def get_client() -> FirebaseClient:
    global _client
    if _client is None:
        _client = FirebaseClient()
    return _client