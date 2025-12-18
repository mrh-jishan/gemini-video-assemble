import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Mapping, Optional


def _bool_from_env(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return str(value).lower() not in {"0", "false", "no", "off", ""}


@dataclass
class Settings:
    google_api_key: Optional[str] = None
    gemini_text_model: str = "gemini-1.5-flash-latest"
    gemini_image_model: str = "imagen-3.0-generate-001"
    tts_lang: str = "en"
    tts_voice: str = "en-US-JennyNeural"
    default_image_provider: str = "gemini"
    pixabay_key: Optional[str] = None
    freesound_key: Optional[str] = None
    output_dir: Path = field(default_factory=lambda: Path("renders").resolve())
    crossfade_sec: float = 0.6
    kenburns_zoom: float = 0.04
    enable_subtitles: bool = True
    subtitle_font: str = "Arial-Bold"
    subtitle_fontsize: int = 40
    subtitle_color: str = "white"
    subtitle_stroke_color: str = "black"
    subtitle_stroke_width: int = 1
    image_style: str = (
        "cinematic, cohesive color palette, volumetric light, ultra detailed, 16:9"
    )
    default_aspect: str = "horizontal"
    horizontal_size: tuple[int, int] = (1920, 1080)
    vertical_size: tuple[int, int] = (1080, 1920)
    port: int = 5000

    @classmethod
    def from_sources(cls, overrides: Optional[Mapping[str, str]] = None) -> "Settings":
        overrides = overrides or {}

        def pick(name: str, default: str | None = None) -> str | None:
            return overrides.get(name) or os.getenv(name, default)

        settings = cls(
            google_api_key=pick("GOOGLE_API_KEY"),
            gemini_text_model=pick("GEMINI_TEXT_MODEL", cls.gemini_text_model),
            gemini_image_model=pick("GEMINI_IMAGE_MODEL", cls.gemini_image_model),
            tts_lang=pick("TTS_LANG", cls.tts_lang),
            tts_voice=pick("TTS_VOICE", cls.tts_voice),
            default_image_provider=pick("DEFAULT_IMAGE_PROVIDER", cls.default_image_provider),
            pixabay_key=pick("PIXABAY_KEY"),
            freesound_key=pick("FREESOUND_KEY"),
            output_dir=Path(pick("OUTPUT_DIR", "renders")).resolve(),
            crossfade_sec=float(pick("CROSSFADE_SEC", str(cls.crossfade_sec))),
            kenburns_zoom=float(pick("KENBURNS_ZOOM", str(cls.kenburns_zoom))),
            enable_subtitles=_bool_from_env(
                pick("SUBTITLES_ENABLED", "1" if cls.enable_subtitles else "0"),
                default=cls.enable_subtitles,
            ),
            subtitle_font=pick("SUBTITLE_FONT", cls.subtitle_font),
            subtitle_fontsize=int(pick("SUBTITLE_FONTSIZE", str(cls.subtitle_fontsize))),
            subtitle_color=pick("SUBTITLE_COLOR", cls.subtitle_color),
            subtitle_stroke_color=pick("SUBTITLE_STROKE_COLOR", cls.subtitle_stroke_color),
            subtitle_stroke_width=int(
                pick("SUBTITLE_STROKE_WIDTH", str(cls.subtitle_stroke_width))
            ),
            image_style=pick("IMAGE_STYLE", cls.image_style),
            default_aspect=pick("VIDEO_ASPECT", cls.default_aspect),
            horizontal_size=(
                int(pick("HORIZONTAL_WIDTH", str(cls.horizontal_size[0]))),
                int(pick("HORIZONTAL_HEIGHT", str(cls.horizontal_size[1]))),
            ),
            vertical_size=(
                int(pick("VERTICAL_WIDTH", str(cls.vertical_size[0]))),
                int(pick("VERTICAL_HEIGHT", str(cls.vertical_size[1]))),
            ),
            port=int(pick("PORT", str(cls.port))),
        )

        settings.output_dir.mkdir(parents=True, exist_ok=True)
        return settings

    def to_public_dict(self, mask_secrets: bool = True) -> Dict[str, str]:
        data = {
            "GOOGLE_API_KEY": self.google_api_key,
            "GEMINI_TEXT_MODEL": self.gemini_text_model,
            "GEMINI_IMAGE_MODEL": self.gemini_image_model,
            "TTS_LANG": self.tts_lang,
            "TTS_VOICE": self.tts_voice,
            "PIXABAY_KEY": self.pixabay_key,
            "FREESOUND_KEY": self.freesound_key,
            "CROSSFADE_SEC": self.crossfade_sec,
            "KENBURNS_ZOOM": self.kenburns_zoom,
            "SUBTITLES_ENABLED": self.enable_subtitles,
            "SUBTITLE_FONT": self.subtitle_font,
            "SUBTITLE_FONTSIZE": self.subtitle_fontsize,
            "SUBTITLE_COLOR": self.subtitle_color,
            "SUBTITLE_STROKE_COLOR": self.subtitle_stroke_color,
            "SUBTITLE_STROKE_WIDTH": self.subtitle_stroke_width,
            "IMAGE_STYLE": self.image_style,
            "VIDEO_ASPECT": self.default_aspect,
            "HORIZONTAL_WIDTH": self.horizontal_size[0],
            "HORIZONTAL_HEIGHT": self.horizontal_size[1],
            "VERTICAL_WIDTH": self.vertical_size[0],
            "VERTICAL_HEIGHT": self.vertical_size[1],
            "OUTPUT_DIR": str(self.output_dir),
            "DEFAULT_IMAGE_PROVIDER": self.default_image_provider,
            "PORT": self.port,
        }

        if mask_secrets:
            for key in ("GOOGLE_API_KEY", "PIXABAY_KEY", "FREESOUND_KEY"):
                value = data.get(key)
                if value:
                    data[key] = f"{str(value)[:4]}***"
        return data

    def require_core_keys(self) -> None:
        if not self.google_api_key:
            raise RuntimeError(
                "GOOGLE_API_KEY is required. Set it via environment variables or the config UI."
            )
