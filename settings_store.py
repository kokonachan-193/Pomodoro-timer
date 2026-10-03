"""Shared app settings (lang / audio / AGIU) — data/settings.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SettingsStore:
    def __init__(self, path: Path):
        self.path = path
        self.data: dict[str, Any] = {
            "lang": "ja",
            "audio_output_name": "",  # empty = not chosen yet (force pick)
            "audio_output_index": None,
            "agiu_auto_check": True,
            "custom_bg_path": "",
            "background_dim": 0.30,
            "home_scale": 1.0,
            "focus_visual_strength": 1.0,
        }
        self.load()

    def load(self) -> None:
        try:
            if self.path.exists():
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    self.data.update(raw)
        except Exception:
            pass

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(self.data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any, *, persist: bool = True) -> None:
        self.data[key] = value
        if persist:
            self.save()
