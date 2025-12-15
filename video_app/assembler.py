import re
import textwrap
from pathlib import Path
from typing import Dict, List, Optional

from moviepy import (
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    VideoFileClip,
    concatenate_videoclips,
    vfx,
)
import platform
from .models import Scene


class VideoAssembler:
    def __init__(
        self,
        fps: int = 24,
        crossfade_sec: float = 0.6,
        kenburns_zoom: float = 0.04,
        enable_subtitles: bool = True,
        subtitle_opts: Optional[Dict] = None,
    ):
        self.fps = fps
        self.crossfade_sec = crossfade_sec
        self.kenburns_zoom = kenburns_zoom
        self.enable_subtitles = enable_subtitles
        self.subtitle_opts = subtitle_opts or {}
        self.target_size = subtitle_opts.get("target_size") if subtitle_opts else None

    def _subtitle_segments(self, text: str, duration: float) -> List[Dict]:
        """Split subtitle text into paced segments to reduce crowding."""
        if not text:
            return []
        words = text.strip().split()
        max_words = 6
        parts = [" ".join(words[i:i + max_words]) for i in range(0, len(words), max_words)]

        seg_duration = duration / len(parts)
        segments = []
        cursor = 0.0
        for part in parts:
            segments.append({"text": part, "start": cursor, "duration": seg_duration})
            cursor += seg_duration
        return segments

    def _create_text_clip(self, text: str, duration: float, box_width: Optional[int]):
        """
        Tries to create a TextClip with the user's font.
        If that fails, falls back to common system fonts to prevent crashing.
        """
        # 1. List of fonts to try in order
        #    Priority: User's config -> Arial (Win) -> Helvetica (Mac) -> DejaVu (Linux)
        fonts_to_try = [
            self.subtitle_opts.get("font"),  # Try user input first
            "Arial.ttf",                     # Standard Windows
            "arial.ttf",                     # Standard lowercase
            "Helvetica.ttc",                 # Standard macOS
            "DejaVuSans.ttf",                # Standard Linux
            "LiberationSans-Regular.ttf",    # Common Linux alternative
        ]
        
        # Remove None values and duplicates
        fonts_to_try = list(dict.fromkeys([f for f in fonts_to_try if f]))

        last_error = None

        for font_name in fonts_to_try:
            try:
                clip = TextClip(
                    text=text,
                    font=font_name,
                    font_size=self.subtitle_opts.get("fontsize", 40),
                    color=self.subtitle_opts.get("color", "white"),
                    stroke_color=self.subtitle_opts.get("stroke_color", "black"),
                    stroke_width=self.subtitle_opts.get("stroke_width", 1),
                    method="caption",
                    size=(box_width, None) if box_width else None,
                ).with_duration(duration)
                
                # If successful, return immediately
                return clip
            except Exception as e:
                # Store error and try next font
                last_error = e
                continue

        # If we run out of fonts, raise the last error so the user knows
        print(f"Failed to render subtitle '{text}'. Last error: {last_error}")
        return None

    def _fit_to_frame(self, clip):
        """Resize/crop to target size while preserving aspect ratio."""
        if not self.target_size or not hasattr(clip, "size") or not clip.size:
            return clip
        tw, th = self.target_size
        try:
            cw, ch = clip.size
            if not cw or not ch:
                return clip
            scale = max(tw / cw, th / ch)
            resized = clip.resize(newsize=(int(cw * scale), int(ch * scale)))
            # Center crop to exact size.
            cropped = resized.crop(
                x_center=resized.w / 2,
                y_center=resized.h / 2,
                width=tw,
                height=th,
            )
            return cropped
        except Exception:
            return clip
    
    def build(self, scenes: List[Scene], output_path: Path) -> Path:
        print(f"Building video at {output_path} with {len(scenes)} scenes")
        clips = []

        for idx, scene in enumerate(scenes):
            if not scene.audio_path:
                raise RuntimeError("Scene missing audio")
            audio_clip = AudioFileClip(str(scene.audio_path))
            duration = max(scene.duration_sec, audio_clip.duration + 0.2)

            if scene.video_path and Path(scene.video_path).exists():
                image_clip = VideoFileClip(str(scene.video_path)).with_duration(duration)
            elif scene.image_path and Path(scene.image_path).exists():
                image_clip = ImageClip(str(scene.image_path)).with_duration(duration)
            else:
                raise RuntimeError("Scene missing visual asset")
            image_clip = self._fit_to_frame(image_clip)
            if self.kenburns_zoom > 0:
                image_clip = image_clip.resized(
                    lambda t: 1 + (self.kenburns_zoom * (t / duration))
                )
            clip = image_clip.with_audio(audio_clip)
            if self.enable_subtitles and scene.subtitle:
                # Derive a width that keeps subtitles within frame bounds.
                clip_width = None
                clip_width = None
                try:
                    base_width = (
                        self.target_size[0]
                        if self.target_size
                        else (image_clip.size[0] if image_clip.size else None)
                    )
                    if base_width:
                        clip_width = int(base_width * 0.9)
                except Exception:
                    clip_width = None

                segments = self._subtitle_segments(scene.subtitle, duration)
                overlays = []
                for seg in segments:
                    text_clip = self._create_text_clip(seg["text"], seg["duration"], clip_width)
                    if text_clip:
                        text_clip = text_clip.with_position(("center", "center"))
                        overlays.append(text_clip.with_start(seg["start"]))
                if overlays:
                    clip = CompositeVideoClip([clip, *overlays])
            if idx > 0 and self.crossfade_sec > 0:
                clip = clip.with_effects([vfx.FadeIn(self.crossfade_sec)])
            clips.append(clip)

        padding = -self.crossfade_sec if self.crossfade_sec > 0 else 0
        final = concatenate_videoclips(clips, method="compose", padding=padding)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        final.write_videofile(
            str(output_path),
            fps=self.fps,
            codec="libx264",
            audio_codec="aac",
            bitrate="4000k",
            threads=4,
            temp_audiofile=str(output_path.with_suffix(".temp-audio.m4a")),
            remove_temp=True,
        )
        return output_path
