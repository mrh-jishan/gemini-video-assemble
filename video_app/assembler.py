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

    def _get_subtitle_fontsize(self) -> int:
        """Calculate font size based on aspect ratio (horizontal vs vertical)."""
        if not self.target_size:
            return self.subtitle_opts.get("fontsize", 40)
        
        width, height = self.target_size
        # For horizontal (16:9 - 1920x1080): larger font
        # For vertical (9:16 - 1080x1920): smaller font
        if width > height:  # Horizontal aspect ratio
            return self.subtitle_opts.get("fontsize", 50)
        else:  # Vertical aspect ratio
            return self.subtitle_opts.get("fontsize", 32)

    def _get_interactive_fontsize(self, index: int, total: int) -> int:
        """Get varied font size for each segment to create visual interest."""
        base_size = self._get_subtitle_fontsize()
        # Alternate between large and normal sizes for emphasis
        if index % 2 == 0:
            return int(base_size * 1.2)  # Larger (emphasized)
        else:
            return int(base_size * 0.85)  # Smaller (supporting)

    def _create_text_clip(self, text: str, duration: float, box_width: Optional[int], fontsize: Optional[int] = None):
        """Create a TextClip with font size adjusted for aspect ratio."""
        # List of fonts to try in order
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
        
        # Get font size (use provided or default)
        if fontsize is None:
            fontsize = self._get_subtitle_fontsize()
        last_error = None

        for font_name in fonts_to_try:
            try:
                clip = TextClip(
                    text=text,
                    font=font_name,
                    font_size=fontsize,
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
            duration = audio_clip.duration

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
                for idx, seg in enumerate(segments):
                    # Get interactive font size (varies by segment index)
                    interactive_fontsize = self._get_interactive_fontsize(idx, len(segments))
                    text_clip = self._create_text_clip(seg["text"], seg["duration"], clip_width, fontsize=interactive_fontsize)
                    if text_clip:
                        # Add pop-in animation (scale from 0.5 to 1.0 in first 0.2 seconds)
                        pop_duration = min(0.2, seg["duration"] * 0.3)
                        text_clip = text_clip.with_position(("center", 80))
                        
                        # Apply pop-in effect with scale animation
                        def make_pop_animation(pop_dur, full_dur):
                            def anim(t):
                                if t < pop_dur:
                                    return 0.5 + 0.5 * (t / pop_dur)  # Scale from 0.5 to 1.0
                                return 1.0
                            return anim
                        
                        text_clip = text_clip.resized(make_pop_animation(pop_duration, seg["duration"]))
                        # Add fade out at the end
                        if seg["duration"] > 0.3:
                            text_clip = text_clip.with_effects([vfx.FadeOut(0.2)])
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
            bitrate="8000k",
            threads=4,
            temp_audiofile=str(output_path.with_suffix(".temp-audio.m4a")),
            remove_temp=True,
            preset="slow",
        )
        return output_path
