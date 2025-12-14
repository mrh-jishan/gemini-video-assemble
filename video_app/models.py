from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Scene:
    title: str
    narration: str
    visual_prompt: str
    duration_sec: float
    subtitle: Optional[str] = None
    image_path: Optional[Path] = None
    audio_path: Optional[Path] = None


