import re
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
from .tts import GoogleTTSSynthesizer


settings = Settings()
gemini_client = genai.Client(api_key=settings.google_api_key)
scene_planner = ScenePlanner(gemini_client, settings.gemini_text_model)
prompt_builder = PromptBuilder(settings.image_style)


def _build_image_client():
    model = settings.gemini_image_model
    method = "generate_images" if "imagen" in model.lower() else "generate_content"
    return GeminiImageClient(settings.google_api_key, model, method)


tts_client = GoogleTTSSynthesizer(settings.tts_lang)


def _aspect_to_size(aspect: str) -> tuple[int, int]:
    if aspect == "vertical":
        return settings.vertical_size
    return settings.horizontal_size


def _build_assembler(aspect: str, background_music_path: Optional[Path] = None) -> VideoAssembler:
    target_size = _aspect_to_size(aspect)
    return VideoAssembler(
        crossfade_sec=settings.crossfade_sec,
        kenburns_zoom=settings.kenburns_zoom,
        enable_subtitles=settings.enable_subtitles,
        subtitle_opts={
            "fontsize": settings.subtitle_fontsize,
            "font": settings.subtitle_font,
            "color": settings.subtitle_color,
            "stroke_color": settings.subtitle_stroke_color,
            "stroke_width": settings.subtitle_stroke_width,
            "target_size": target_size,
        },
        background_music_path=background_music_path,
    )


def build_video_from_prompt(
    prompt: str,
    duration: int,
    scenes: int,
    aspect: str | None = None,
    image_provider: str | None = None,
) -> Path:
    working_dir = Path(tempfile.mkdtemp(prefix="video-job-"))
    scene_plan = scene_planner.plan(prompt, duration, scenes)
    aspect_choice = aspect or settings.default_aspect
    
    # Try to download background music if Freesound is available (Gemini-only keywords)
    background_music_path = None
    if settings.freesound_key:
        try:
            freesound_client = FreesoundClient(settings.freesound_key)
            # Use the first scene's music keywords as the overall music mood
            music_query = None
            for scene in scene_plan:
                if scene.music_keywords:
                    music_query = scene.music_keywords
                    break
            if music_query:
                print(f"[Music] Using planner keywords for Freesound: '{music_query}'")
                background_music_path = working_dir / "background_music.mp3"
                freesound_client.generate_background_music(music_query, background_music_path)
            else:
                print("[Music] No planner-provided music keywords; skipping background music.")
        except Exception as e:
            print(f"Warning: Could not get background music: {e}")
    
    assembler = _build_assembler(aspect_choice, background_music_path)
    # Select image provider: gemini (default) or stock (from UI).
    provider = (image_provider or settings.default_image_provider).lower()
    target_size = _aspect_to_size(aspect_choice)
    orientation = "vertical" if aspect_choice == "vertical" else "horizontal"
    
    pixabay_image_client = None
    pixabay_video_client = None
    if provider == "stock":
        if not settings.pixabay_key:
            raise RuntimeError("PIXABAY_KEY required for stock provider")
        pixabay_image_client = PixabayImageClient(settings.pixabay_key)
        pixabay_video_client = PixabayVideoClient(settings.pixabay_key)

    freesound_client = None
    if settings.freesound_key:
        freesound_client = FreesoundClient(settings.freesound_key)

    print(f"Planned {len(scene_plan)} scenes for prompt '{prompt}'")

    for idx, scene in enumerate(scene_plan):
        scene.image_path = working_dir / f"scene_{idx}.png"
        scene.audio_path = working_dir / f"scene_{idx}.mp3"
        scene.video_path = working_dir / f"scene_{idx}.mp4"
        scene.sfx_path = working_dir / f"scene_{idx}_sfx.mp3"
        full_prompt = prompt_builder.build(scene)
        search_term = (scene.search_query or scene.visual_prompt or prompt).strip()
        if len(search_term) > 100:
            search_term = search_term[:100]
        if provider == "stock":
            try:
                pixabay_video_client.generate_video(search_term, scene.video_path, target_size=target_size)
            except Exception:
                pixabay_image_client.generate_image(search_term, scene.image_path, orientation=orientation)
        else:
            _build_image_client().generate(full_prompt, scene.image_path)
        tts_client.synthesize(scene.narration, scene.audio_path)
        scene.subtitle = scene.narration
        
        # Generate per-scene sound effects if available
        if freesound_client and scene.sfx_keywords:
            try:
                print(f"[SFX] Fetching sound effect for scene {idx}: '{scene.sfx_keywords}'")
                freesound_client.generate_sound_effect(scene.sfx_keywords, scene.sfx_path)
            except Exception as e:
                print(f"[SFX] Warning: Could not get SFX for scene {idx}: {e}")
                scene.sfx_path = None

    output_path = settings.output_dir / f"{uuid.uuid4()}.mp4"
    assembler.build(scene_plan, output_path)
    
    shutil.rmtree(working_dir, ignore_errors=True)
    return output_path
