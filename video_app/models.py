from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Scene:
    title: str
    narration: str
    visual_prompt: str
    duration_sec: float
    search_query: Optional[str] = None
    music_keywords: Optional[str] = None
    sfx_keywords: Optional[str] = None
    subtitle: Optional[str] = None
    image_path: Optional[Path] = None
    audio_path: Optional[Path] = None
    video_path: Optional[Path] = None
    sfx_path: Optional[Path] = None
