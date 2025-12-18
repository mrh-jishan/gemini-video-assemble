"""
Alias package so the project can be invoked as `python -m gemini_video_assemble`.
"""

from .server import create_app

__all__ = ["create_app"]
