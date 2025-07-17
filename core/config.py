# core/config.py
import os

# Application paths
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCES_DIR = os.path.join(ROOT_DIR, 'resources')
FONTS_DIR = os.path.join(RESOURCES_DIR, 'fonts')

# Default settings
DEFAULT_SETTINGS = {
    'word_spacing': 5,
    'segment_spacing': 15,
    'blur_radius': 10,
    'max_duration_seconds': 3600,  # 1 hour
    'max_chars': 100,
    'default_font': 'a',
    'default_font_size': 'medium',
    'default_text_color': 'yellow',
    'default_bg_color': 'none',
    'default_position': 80,  # 80%
}

# File format settings
SUPPORTED_AUDIO_FORMATS = ['.mp3', '.wav', '.m4a', '.flac']
SUPPORTED_VIDEO_FORMATS = ['.mp4', '.mov', '.avi', '.mkv']