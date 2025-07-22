"""
Custom exceptions for the caption tool.
"""


class CaptionToolError(Exception):
    """Base exception for caption tool."""
    pass


class VideoNotFoundError(CaptionToolError):
    """Raised when input video file is not found."""
    pass


class UnsupportedFormatError(CaptionToolError):
    """Raised when video format is not supported."""
    pass


class TranscriptionError(CaptionToolError):
    """Raised when audio transcription fails."""
    pass


class RenderingError(CaptionToolError):
    """Raised when video rendering fails."""
    pass


class ConfigurationError(CaptionToolError):
    """Raised when configuration is invalid."""
    pass


class FontError(CaptionToolError):
    """Raised when font loading fails."""
    pass