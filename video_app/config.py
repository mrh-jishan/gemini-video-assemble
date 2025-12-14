import os
from pathlib import Path


class Settings:
    def __init__(self):
        # Core keys
        self.google_api_key = os.getenv("GOOGLE_API_KEY")

        # LLM/TTS
        self.gemini_text_model = os.getenv("GEMINI_TEXT_MODEL", "gemini-1.5-flash-latest")
        self.tts_lang = os.getenv("TTS_LANG", "en")

        # Images
        self.gemini_image_model = os.getenv(
            "GEMINI_IMAGE_MODEL", "imagen-3.0-generate-001"
        )

        # Paths
        self.output_dir = Path(os.getenv("OUTPUT_DIR", "renders")).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir = Path(
            os.getenv("IMAGE_CACHE_DIR", self.output_dir / "image-cache")
        ).resolve()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Video styling
        self.crossfade_sec = float(os.getenv("CROSSFADE_SEC", "0.6"))
        self.kenburns_zoom = float(os.getenv("KENBURNS_ZOOM", "0.04"))
        self.enable_subtitles = os.getenv("SUBTITLES_ENABLED", "1").lower() not in (
            "0",
            "false",
        )
        self.subtitle_font = os.getenv("SUBTITLE_FONT", "Arial-Bold")
        self.subtitle_fontsize = int(os.getenv("SUBTITLE_FONTSIZE", "40"))
        self.subtitle_color = os.getenv("SUBTITLE_COLOR", "white")
        self.subtitle_stroke_color = os.getenv("SUBTITLE_STROKE_COLOR", "black")
        self.subtitle_stroke_width = int(os.getenv("SUBTITLE_STROKE_WIDTH", "1"))
        self.image_style = os.getenv(
            "IMAGE_STYLE",
            "cinematic, cohesive color palette, volumetric light, ultra detailed, 16:9",
        )

        self.port = int(os.getenv("PORT", "5000"))

        if not self.google_api_key:
            raise RuntimeError("GOOGLE_API_KEY is required for Gemini text/images")
