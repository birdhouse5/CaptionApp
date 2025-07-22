"""
Configuration management for the caption tool.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, Union

from exceptions import ConfigurationError


class Config:
    """Configuration manager for caption tool."""
    
    def __init__(self, config_file: Optional[str] = None, overrides: Optional[Dict[str, Any]] = None):
        """
        Initialize configuration.
        
        Args:
            config_file: Path to JSON config file. If None, uses default config.
            overrides: Dictionary of configuration overrides.
        """
        self._config = self._load_default_config()
        
        if config_file:
            self._load_config_file(config_file)
            
        if overrides:
            self._apply_overrides(overrides)
            
        self._validate_config()
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load the default configuration."""
        default_config_path = Path(__file__).parent / "default_config.json"
        try:
            with open(default_config_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise ConfigurationError(f"Failed to load default config: {e}")
    
    def _load_config_file(self, config_file: str) -> None:
        """Load configuration from file and merge with defaults."""
        if not os.path.exists(config_file):
            raise ConfigurationError(f"Config file not found: {config_file}")
            
        try:
            with open(config_file, 'r') as f:
                user_config = json.load(f)
            self._deep_merge(self._config, user_config)
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in config file: {e}")
    
    def _apply_overrides(self, overrides: Dict[str, Any]) -> None:
        """Apply configuration overrides using dot notation."""
        for key, value in overrides.items():
            self._set_nested_value(self._config, key, value)
    
    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> None:
        """Deep merge two dictionaries."""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def _set_nested_value(self, config: Dict[str, Any], key_path: str, value: Any) -> None:
        """Set a nested value using dot notation (e.g., 'colors.text')."""
        keys = key_path.split('.')
        current = config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
            
        current[keys[-1]] = value
    
    def _validate_config(self) -> None:
        """Validate configuration values."""
        # Validate colors
        for color_key in ['text', 'highlight', 'highlight_background']:
            color = self.get(f'colors.{color_key}')
            if color is not None and not self._is_valid_color(color):
                raise ConfigurationError(f"Invalid color format for {color_key}: {color}")
        
        # Validate positioning
        for pos_key in ['horizontal', 'vertical']:
            pos = self.get(f'positioning.{pos_key}')
            if not (0.0 <= pos <= 1.0):
                raise ConfigurationError(f"Position {pos_key} must be between 0.0 and 1.0")
        
        # Validate highlighting mode
        valid_modes = ['text', 'background', 'both', 'current_word_only']
        mode = self.get('highlighting.mode')
        if mode not in valid_modes:
            raise ConfigurationError(f"Invalid highlighting mode: {mode}. Must be one of {valid_modes}")
        
        # Validate font path if specified
        font_path = self.get('fonts.path')
        if font_path and not os.path.exists(font_path):
            raise ConfigurationError(f"Font file not found: {font_path}")
    
    def _is_valid_color(self, color: Union[list, tuple]) -> bool:
        """Check if color is a valid RGB/RGBA tuple."""
        if not isinstance(color, (list, tuple)):
            return False
        if len(color) not in [3, 4]:
            return False
        return all(isinstance(c, int) and 0 <= c <= 255 for c in color)
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            key_path: Dot-separated key path (e.g., 'colors.text')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key_path.split('.')
        current = self._config
        
        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any) -> None:
        """
        Set configuration value using dot notation.
        
        Args:
            key_path: Dot-separated key path
            value: Value to set
        """
        self._set_nested_value(self._config, key_path, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary."""
        return self._config.copy()
    
    def save(self, filepath: str) -> None:
        """Save current configuration to file."""
        try:
            with open(filepath, 'w') as f:
                json.dump(self._config, f, indent=2)
        except IOError as e:
            raise ConfigurationError(f"Failed to save config: {e}")
    
    # Convenience properties for commonly used values
    @property
    def font_path(self) -> Optional[str]:
        return self.get('fonts.path')
    
    @property
    def font_size_scale(self) -> float:
        return self.get('fonts.size_scale', 0.045)
    
    @property
    def text_color(self) -> list:
        return self.get('colors.text', [255, 255, 255])
    
    @property
    def highlight_color(self) -> list:
        return self.get('colors.highlight', [255, 255, 0])
    
    @property
    def background_color(self) -> Optional[list]:
        return self.get('colors.background')
    
    @property
    def highlight_background_color(self) -> list:
        return self.get('colors.highlight_background', [0, 255, 0])
    
    @property
    def position(self) -> tuple:
        return (self.get('positioning.horizontal', 0.5), self.get('positioning.vertical', 0.8))
    
    @property
    def highlighting_mode(self) -> str:
        return self.get('highlighting.mode', 'text')
    
    @property
    def max_width_pixels(self) -> int:
        return self.get('video.max_width_pixels', 800)
    
    @property
    def whisper_model(self) -> str:
        return self.get('transcription.model', 'base')