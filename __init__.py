"""
Caption Tool - AI-powered video captioning toolkit.
"""

from caption_processor import CaptionProcessor
from config import Config
from exceptions import (
    CaptionToolError, 
    VideoNotFoundError, 
    UnsupportedFormatError,
    TranscriptionError,
    RenderingError,
    ConfigurationError,
    FontError
)

__version__ = "1.0.0"
__author__ = "Caption Tool Team"

__all__ = [
    "CaptionProcessor",
    "Config", 
    "CaptionToolError",
    "VideoNotFoundError",
    "UnsupportedFormatError", 
    "TranscriptionError",
    "RenderingError",
    "ConfigurationError",
    "FontError"
]