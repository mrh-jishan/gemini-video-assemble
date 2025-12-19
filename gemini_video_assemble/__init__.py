"""
Alias package so the project can be invoked as `python -m gemini_video_assemble`.
"""

try:
    from ._version import version as __version__
except ImportError:
    __version__ = "0.0.0+unknown"

from .server import create_app

__all__ = ["create_app", "__version__"]
