from __future__ import annotations

import time
from dataclasses import dataclass

import requests


DEFAULT_FIREBASE_URL = "https://smartwarehouse-f36ba-default-rtdb.asia-southeast1.firebasedatabase.app"
DEFAULT_COLOR_PATH = "devices/esp32_01/color"
SUPPORTED_COLORS = {"red", "blue", "yellow"}
CAPACITY_SETTING_KEYS = {
    "red": "capacity_red",
    "blue": "capacity_blue",
    "yellow": "capacity_yellow",
}
DEFAULT_COUNTS = {
    "red": 0,
    "blue": 0,
    "yellow": 0,
    "last_detected": "none",
    "last_detected_label": "chua co",
    "last_update": 0,
}


class ShelfFullError(RuntimeError):
    def __init__(self, color_en: str, current_count: int, capacity: int) -> None:
        self.color_en = color_en
        self.current_count = current_count
        self.capacity = capacity
        super().__init__(f"Ke {color_en} da day ({current_count}/{capacity})")


@dataclass
class FirebaseColorClient:
    database_url: str = DEFAULT_FIREBASE_URL
    color_path: str = DEFAULT_COLOR_PATH
    timeout_seconds: float = 5.0

    def __post_init__(self) -> None:
        self.database_url = self.database_url.rstrip("/")
        self.color_path = self.color_path.strip("/")

    def _url(self, path: str = "") -> str:
        clean_path = path.strip("/")
        full_path = f"{self.color_path}/{clean_path}" if clean_path else self.color_path
        return f"{self.database_url}/{full_path}.json"

    def _device_base_path(self) -> str:
        if self.color_path.endswith("/color"):
            return self.color_path[: -len("/color")]
        return self.color_path.rsplit("/", 1)[0]

    def _device_url(self, path: str) -> str:
        clean_path = path.strip("/")
        return f"{self.database_url}/{self._device_base_path()}/{clean_path}.json"

    def _get(self, path: str = ""):
        response = requests.get(self._url(path), timeout=self.timeout_seconds)
        response.raise_for_status()
        return response.json()

    def _get_device_value(self, path: str):
        response = requests.get(self._device_url(path), timeout=self.timeout_seconds)
        response.raise_for_status()
        return response.json()

    def _patch(self, payload: dict, path: str = "") -> None:
        response = requests.patch(self._url(path), json=payload, timeout=self.timeout_seconds)
        response.raise_for_status()

    def ensure_color_defaults(self) -> None:
        current = self._get()
        if not isinstance(current, dict):
            self._patch(DEFAULT_COUNTS)
            return

        missing_values = {
            key: value
            for key, value in DEFAULT_COUNTS.items()
            if key not in current
        }
        if missing_values:
            self._patch(missing_values)

    def increment_color(self, color_en: str, color_vi: str) -> int:
        if color_en not in SUPPORTED_COLORS:
            raise ValueError(f"Mau khong duoc ho tro de gui Firebase: {color_en}")

        current_count = self._get(color_en)
        if not isinstance(current_count, int):
            current_count = 0

        capacity = self.get_capacity(color_en)
        if capacity is not None and current_count >= capacity:
            raise ShelfFullError(color_en, current_count, capacity)

        next_count = current_count + 1
        self._patch(
            {
                color_en: next_count,
                "last_detected": color_en,
                "last_detected_label": color_vi,
                "last_update": int(time.time()),
            }
        )
        return next_count

    def get_capacity(self, color_en: str) -> int | None:
        setting_key = CAPACITY_SETTING_KEYS[color_en]
        value = self._get_device_value(f"settings/{setting_key}")
        if isinstance(value, (int, float)) and value > 0:
            return int(value)
        return None
