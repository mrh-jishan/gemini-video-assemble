import json
import os
from pathlib import Path
from typing import Dict, Iterable, Mapping

from .storage import DataStore, default_data_dir


class ConfigStore:
    """Config persistence backed by SQLite; reads legacy JSON on first load for migration."""

    DEFAULT_KEYS = {
        "GOOGLE_API_KEY",
        "GEMINI_TEXT_MODEL",
        "GEMINI_IMAGE_MODEL",
        "TTS_LANG",
        "TTS_VOICE",
        "PIXABAY_KEY",
        "FREESOUND_KEY",
        "CROSSFADE_SEC",
        "KENBURNS_ZOOM",
        "SUBTITLES_ENABLED",
        "SUBTITLE_FONT",
        "SUBTITLE_FONTSIZE",
        "SUBTITLE_COLOR",
        "SUBTITLE_STROKE_COLOR",
        "SUBTITLE_STROKE_WIDTH",
        "IMAGE_STYLE",
        "VIDEO_ASPECT",
        "HORIZONTAL_WIDTH",
        "HORIZONTAL_HEIGHT",
        "VERTICAL_WIDTH",
        "VERTICAL_HEIGHT",
        "OUTPUT_DIR",
        "DEFAULT_IMAGE_PROVIDER",
        "PORT",
    }

    def __init__(
        self,
        path: str | Path | None = None,
        allowed_keys: Iterable[str] | None = None,
        legacy_json_path: str | Path | None = None,
    ):
        self.allowed_keys = set(allowed_keys or self.DEFAULT_KEYS)
        data_dir = default_data_dir()
        db_path = path or os.getenv("GVA_DB_PATH") or data_dir / "data.db"
        self.store = DataStore(db_path)
        legacy_default = Path(
            legacy_json_path
            or os.getenv("GVA_CONFIG_PATH")
            or data_dir / "config.json"
        )
        self.legacy_path = Path(legacy_default)

    def _load_legacy(self) -> Dict[str, str]:
        if not self.legacy_path.exists():
            return {}
        try:
            with self.legacy_path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
                return {k: v for k, v in data.items() if k in self.allowed_keys}
        except json.JSONDecodeError:
            return {}

    def load(self) -> Dict[str, str]:
        config = self.store.get_config()
        if config:
            return config
        legacy = self._load_legacy()
        if legacy:
            self.save(legacy)
            return legacy
        return {}

    def save(self, values: Mapping[str, str]) -> Dict[str, str]:
        filtered = {k: v for k, v in values.items() if k in self.allowed_keys and v is not None}
        return self.store.set_config(filtered)

    def update(self, updates: Mapping[str, str]) -> Dict[str, str]:
        current = self.load()
        current.update({k: v for k, v in updates.items() if k in self.allowed_keys and v is not None})
        return self.save(current)
