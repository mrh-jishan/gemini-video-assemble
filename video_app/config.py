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
        
        # UI-driven provider selection; default fallback is gemini.
        self.default_image_provider = "stock"  # gemini | stock | mix (overridden per request)
        self.pixabay_key = os.getenv("PIXABAY_KEY")  # for stock image search
        self.freesound_key = os.getenv("FREESOUND_KEY")  # for background music/sound effects

        # Paths
        self.output_dir = Path(os.getenv("OUTPUT_DIR", "renders")).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

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
        self.default_aspect = os.getenv("VIDEO_ASPECT", "horizontal")  # horizontal | vertical
        # Target sizes for horizontal (16:9) and vertical (9:16).
        self.horizontal_size = (
            int(os.getenv("HORIZONTAL_WIDTH", "1920")),
            int(os.getenv("HORIZONTAL_HEIGHT", "1080")),
        )
        self.vertical_size = (
            int(os.getenv("VERTICAL_WIDTH", "1080")),
            int(os.getenv("VERTICAL_HEIGHT", "1920")),
        )

        self.port = int(os.getenv("PORT", "5000"))

        if not self.google_api_key:
            raise RuntimeError("GOOGLE_API_KEY is required for Gemini text/images")
