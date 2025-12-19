import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from google import genai

from .assembler import VideoAssembler
from .config import Settings
from .images import GeminiImageClient, PixabayImageClient
from .media import PixabayVideoClient
from .music import FreesoundClient
from .models import Scene
from .planner import PromptBuilder, ScenePlanner
from .tts import AmazonPollySynthesizer, GoogleTTSSynthesizer, TTSSynthesizer


class VideoPipeline:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.settings.require_core_keys()
        self.gemini_client = genai.Client(api_key=self.settings.google_api_key)
        self.scene_planner = ScenePlanner(self.gemini_client, self.settings.gemini_text_model)
        self.prompt_builder = PromptBuilder(self.settings.image_style)
        self.tts_client = self._build_tts_client()

    def _build_tts_client(self) -> TTSSynthesizer:
        if self.settings.tts_provider == "polly":
            if not self.settings.aws_access_key_id or not self.settings.aws_secret_access_key:
                print("Warning: AWS credentials missing, falling back to Google TTS")
                return GoogleTTSSynthesizer(self.settings.tts_lang)
            
            try:
                return AmazonPollySynthesizer(
                    aws_access_key_id=self.settings.aws_access_key_id,
                    aws_secret_access_key=self.settings.aws_secret_access_key,
                    region_name=self.settings.aws_region,
                    voice_id=self.settings.polly_voice_id,
                    engine=self.settings.polly_engine,
                )
            except RuntimeError as e:
                print(f"Warning: Failed to initialize Amazon Polly ({e}), falling back to Google TTS")
                return GoogleTTSSynthesizer(self.settings.tts_lang)
        return GoogleTTSSynthesizer(self.settings.tts_lang)

    def _build_image_client(self) -> GeminiImageClient:
        model = self.settings.gemini_image_model
        method = "generate_images" if "imagen" in model.lower() else "generate_content"
        return GeminiImageClient(self.settings.google_api_key, model, method)

    def _aspect_to_size(self, aspect: str) -> tuple[int, int]:
        if aspect == "vertical":
            return self.settings.vertical_size
        return self.settings.horizontal_size

    def _build_assembler(
        self, aspect: str, background_music_path: Optional[Path] = None
    ) -> VideoAssembler:
        target_size = self._aspect_to_size(aspect)
        return VideoAssembler(
            crossfade_sec=self.settings.crossfade_sec,
            kenburns_zoom=self.settings.kenburns_zoom,
            enable_subtitles=self.settings.enable_subtitles,
            subtitle_opts={
                "fontsize": self.settings.subtitle_fontsize,
                "font": self.settings.subtitle_font,
                "color": self.settings.subtitle_color,
                "stroke_color": self.settings.subtitle_stroke_color,
                "stroke_width": self.settings.subtitle_stroke_width,
                "target_size": target_size,
            },
            background_music_path=background_music_path,
        )

    def build_video_from_prompt(
        self,
        prompt: str,
        duration: int,
        scenes: int,
        aspect: str | None = None,
        image_provider: str | None = None,
    ) -> Path:
        working_dir = Path(tempfile.mkdtemp(prefix="video-job-"))
        scene_plan = self.scene_planner.plan(prompt, duration, scenes)
        aspect_choice = aspect or self.settings.default_aspect

        background_music_path = None
        if self.settings.freesound_key:
            print("[Music] Freesound key available, attempting to get background music...")
            try:
                freesound_client = FreesoundClient(self.settings.freesound_key)
                music_query = None
                for idx, scene in enumerate(scene_plan):
                    print(f"[Music] Scene {idx}: music_keywords = '{scene.music_keywords}'")
                    if scene.music_keywords:
                        music_query = scene.music_keywords
                        break
                if music_query:
                    print(f"[Music] Using planner keywords for Freesound: '{music_query}'")
                    background_music_path = working_dir / "background_music.mp3"
                    freesound_client.generate_background_music(music_query, background_music_path)
                    print(f"[Music] Background music saved to: {background_music_path}")
                    exists = background_music_path.exists()
                    size = background_music_path.stat().st_size if exists else "N/A"
                    print(f"[Music] File exists: {exists}, Size: {size} bytes")
                else:
                    print(
                        "[Music] No planner-provided music keywords found in any scene; skipping background music."
                    )
            except Exception as e:
                print(f"Warning: Could not get background music: {e}")
        else:
            print("[Music] FREESOUND_KEY not set; skipping background music.")

        assembler = self._build_assembler(aspect_choice, background_music_path)
        provider = (image_provider or "").lower()
        if provider not in {"gemini", "stock"}:
            raise RuntimeError("image_provider is required and must be 'gemini' or 'stock'")
        target_size = self._aspect_to_size(aspect_choice)
        orientation = "vertical" if aspect_choice == "vertical" else "horizontal"

        pixabay_image_client = None
        pixabay_video_client = None
        if provider == "stock":
            if not self.settings.pixabay_key:
                raise RuntimeError("PIXABAY_KEY required for stock provider")
            pixabay_image_client = PixabayImageClient(self.settings.pixabay_key)
            pixabay_video_client = PixabayVideoClient(self.settings.pixabay_key)

        freesound_client = None
        if self.settings.freesound_key:
            freesound_client = FreesoundClient(self.settings.freesound_key)

        print(f"Planned {len(scene_plan)} scenes for prompt '{prompt}'")

        for idx, scene in enumerate(scene_plan):
            scene.image_path = working_dir / f"scene_{idx}.png"
            scene.audio_path = working_dir / f"scene_{idx}.mp3"
            scene.video_path = working_dir / f"scene_{idx}.mp4"
            scene.sfx_path = working_dir / f"scene_{idx}_sfx.mp3"
            scene.break_audio_path = working_dir / f"scene_{idx}_break_audio.mp3"
            full_prompt = self.prompt_builder.build(scene)
            search_term = (scene.search_query or scene.visual_prompt or prompt).strip()
            if len(search_term) > 100:
                search_term = search_term[:100]
            if provider == "stock":
                try:
                    pixabay_video_client.generate_video(
                        search_term, scene.video_path, target_size=target_size
                    )
                except Exception:
                    pixabay_image_client.generate_image(
                        search_term, scene.image_path, orientation=orientation
                    )
            else:
                self._build_image_client().generate(full_prompt, scene.image_path)
            self.tts_client.synthesize(scene.narration, scene.audio_path)
            scene.subtitle = scene.narration

            if freesound_client and scene.sfx_keywords:
                try:
                    print(f"[SFX] Fetching sound effect for scene {idx}: '{scene.sfx_keywords}'")
                    freesound_client.generate_sound_effect(scene.sfx_keywords, scene.sfx_path)
                except Exception as e:
                    print(f"[SFX] Warning: Could not get SFX for scene {idx}: {e}")
                    scene.sfx_path = None

            if freesound_client:
                try:
                    print(f"[Break Audio] Fetching transition audio for break after scene {idx}")
                    freesound_client.generate_sound_effect("transition whoosh", scene.break_audio_path)
                except Exception as e:
                    print(f"[Break Audio] Warning: Could not get break audio for scene {idx}: {e}")
                    scene.break_audio_path = None

        output_path = self.settings.output_dir / f"{uuid.uuid4()}.mp4"
        assembler.build(scene_plan, output_path)

        shutil.rmtree(working_dir, ignore_errors=True)
        return output_path
