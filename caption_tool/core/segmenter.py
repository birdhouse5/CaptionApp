"""
Segment creation with width and duration constraints.
"""

import re
import os
from typing import Dict, List, Any, Optional
from PIL import Image, ImageFont, ImageDraw

from utils import parse_time_to_seconds
from exceptions import FontError


class Segmenter:
    """Creates optimized caption segments from word data."""
    
    def __init__(self, font_path: Optional[str] = None, font_size: int = 40, 
                 max_width_pixels: int = 800, max_duration_seconds: float = 1.5,
                 word_spacing: int = 10):
        """
        Initialize segmenter.
        
        Args:
            font_path: Path to TTF font file, None for default
            font_size: Font size in pixels
            max_width_pixels: Maximum segment width in pixels
            max_duration_seconds: Maximum segment duration in seconds
            word_spacing: Spacing between words in pixels
        """
        self.font_path = font_path
        self.font_size = font_size
        self.max_width_pixels = max_width_pixels
        self.max_duration_seconds = max_duration_seconds
        self.word_spacing = word_spacing
        self.font = self._load_font()
        
        # Create temp image for text measurement
        self.temp_image = Image.new('RGB', (max_width_pixels * 2, 100))
        self.draw = ImageDraw.Draw(self.temp_image)
    
    def _load_font(self) -> ImageFont.ImageFont:
        """Load font for text measurement."""
        try:
            if self.font_path and os.path.exists(self.font_path):
                return ImageFont.truetype(self.font_path, self.font_size)
            else:
                return ImageFont.load_default()
        except Exception as e:
            raise FontError(f"Failed to load font: {e}")
    
    def _measure_text_width(self, text: str) -> int:
        """Measure text width in pixels."""
        try:
            if hasattr(self.draw, 'textlength'):
                # Newer PIL versions
                return int(self.draw.textlength(text, font=self.font))
            elif hasattr(self.draw, 'textsize'):
                # Older PIL versions
                width, _ = self.draw.textsize(text, font=self.font)
                return int(width)
            else:
                # Fallback estimation
                return len(text) * (self.font_size // 2)
        except Exception:
            # Ultimate fallback
            return len(text) * (self.font_size // 2)
    
    def _is_punctuation(self, text: str) -> bool:
        """Check if text is punctuation."""
        return re.match(r'^[^\w\s]$', text) is not None
    
    def _group_words_with_punctuation(self, words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group punctuation with preceding words and handle contractions."""
        grouped_words = []
        current_group = None
        i = 0
        
        while i < len(words):
            word = words[i]
            word_text = word.get('text', '')
            
            if self._is_punctuation(word_text):
                # Handle apostrophes in contractions
                if word_text in ["'", "'"]:  # Apostrophe
                    if i + 1 < len(words):
                        next_word = words[i + 1]
                        next_text = next_word.get('text', '')
                        
                        # Common contraction endings
                        contraction_endings = ['re', 'll', 've', 's', 't', 'd', 'm']
                        
                        if any(next_text.lower() == ending for ending in contraction_endings):
                            # This is a contraction
                            if current_group:
                                combined_text = current_group['text'] + word_text + next_text
                                current_group['text'] = combined_text
                                current_group['end'] = next_word.get('end')
                                i += 2  # Skip next word
                                continue
                
                # Regular punctuation
                if current_group:
                    current_group['text'] = current_group['text'] + word_text
                    current_group['end'] = word.get('end')
                else:
                    # Standalone punctuation
                    current_group = word.copy()
                    grouped_words.append(current_group)
                    current_group = None
            else:
                # Regular word
                if current_group:
                    grouped_words.append(current_group)
                current_group = word.copy()
            
            i += 1
        
        # Add last group
        if current_group:
            grouped_words.append(current_group)
        
        return grouped_words
    
    def create_segments(self, words_dict: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Create optimized segments from word data.
        
        Args:
            words_dict: Dictionary with 'words' key containing word data
            
        Returns:
            Dictionary with 'segments' key containing segment data
        """
        words = words_dict.get('words', [])
        if not words:
            return {'segments': []}
        
        # Group words with punctuation
        grouped_words = self._group_words_with_punctuation(words)
        
        # Create segments
        segments = []
        current_segment = {
            'text': '',
            'start_time': None,
            'end_time': None,
            'words': []
        }
        
        current_width = 0
        space_width = self._measure_text_width(' ')
        
        for word in grouped_words:
            word_text = word.get('text', '')
            if not word_text.strip():
                continue
            
            word_width = self._measure_text_width(word_text)
            
            # Check if this is the first word in segment
            if current_segment['start_time'] is None:
                current_segment['start_time'] = word.get('start')
                current_segment['text'] = word_text
                current_segment['words'] = [word]
                current_segment['end_time'] = word.get('end')
                current_width = word_width
                continue
            
            # Calculate new width and duration
            new_width = current_width + space_width + word_width
            
            # Calculate duration
            start_time_sec = parse_time_to_seconds(current_segment['start_time'])
            end_time_sec = parse_time_to_seconds(word.get('end'))
            duration = end_time_sec - start_time_sec
            
            # Check if we need to start a new segment
            width_exceeded = new_width > self.max_width_pixels
            duration_exceeded = duration > self.max_duration_seconds
            
            if (width_exceeded or duration_exceeded) and not self._is_punctuation(word_text):
                # Finish current segment
                segments.append(current_segment)
                
                # Start new segment
                current_segment = {
                    'text': word_text,
                    'start_time': word.get('start'),
                    'end_time': word.get('end'),
                    'words': [word]
                }
                current_width = word_width
            else:
                # Add to current segment
                if self._is_punctuation(word_text):
                    # Append punctuation without space
                    current_segment['text'] += word_text
                else:
                    # Add space before regular words
                    current_segment['text'] += ' ' + word_text
                
                current_segment['words'].append(word)
                current_segment['end_time'] = word.get('end')
                current_width = new_width
        
        # Add final segment
        if current_segment['start_time'] is not None:
            segments.append(current_segment)
        
        # Format segments with indices
        formatted_segments = []
        for i, segment in enumerate(segments):
            formatted_segments.append({
                'index': i + 1,
                'start_time': segment['start_time'],
                'end_time': segment['end_time'],
                'text': segment['text'],
                'words': segment['words']
            })
        
        return {'segments': formatted_segments}