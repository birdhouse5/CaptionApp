"""
Utility functions and progress tracking for the caption tool.
"""

import os
import tempfile
import shutil
from typing import Callable, Optional, Any
from pathlib import Path
from tqdm import tqdm

from exceptions import VideoNotFoundError, UnsupportedFormatError


def validate_input_video(video_path: str, supported_formats: list) -> None:
    """
    Validate input video file.
    
    Args:
        video_path: Path to video file
        supported_formats: List of supported file extensions
        
    Raises:
        VideoNotFoundError: If file doesn't exist
        UnsupportedFormatError: If format not supported
    """
    if not os.path.exists(video_path):
        raise VideoNotFoundError(f"Video file not found: {video_path}")
    
    file_ext = Path(video_path).suffix.lower()
    if file_ext not in supported_formats:
        raise UnsupportedFormatError(
            f"Unsupported format: {file_ext}. Supported: {supported_formats}"
        )


def parse_time_to_seconds(time_str: str) -> float:
    """
    Convert a time string to seconds.
    Format: HH:MM:SS,mmm or HH:MM:SS.mmm
    
    Args:
        time_str: Time string to parse
        
    Returns:
        Time in seconds as float
    """
    # Handle both comma and dot as decimal separator
    time_str = time_str.replace(',', '.')
    
    # Split into base time and milliseconds
    if '.' in time_str:
        time_base, milliseconds_str = time_str.rsplit('.', 1)
        milliseconds = int(milliseconds_str.ljust(3, '0')[:3])  # Ensure 3 digits
    else:
        time_base = time_str
        milliseconds = 0
    
    # Parse hours, minutes, seconds
    parts = time_base.split(':')
    if len(parts) != 3:
        raise ValueError(f"Invalid time format: {time_str}")
    
    hours, minutes, seconds = map(int, parts)
    total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
    return total_seconds


def format_srt_timestamp(seconds: float) -> str:
    """
    Convert seconds to SRT timestamp format (HH:MM:SS,mmm).
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted timestamp string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millisecs = int((seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"


class ProgressTracker:
    """Progress tracking for different processing stages."""
    
    def __init__(self, callback: Optional[Callable[[str, float, str], None]] = None, 
                 use_tqdm: bool = True):
        """
        Initialize progress tracker.
        
        Args:
            callback: Optional callback function(stage, percentage, message)
            use_tqdm: Whether to use tqdm progress bars for CLI
        """
        self.callback = callback
        self.use_tqdm = use_tqdm
        self.current_stage = None
        self.current_pbar = None
    
    def start_stage(self, stage: str, total: int, description: str = "") -> None:
        """Start a new processing stage."""
        self.current_stage = stage
        
        if self.use_tqdm:
            self.current_pbar = tqdm(
                total=total,
                desc=f"{stage}: {description}",
                unit="frames" if "video" in stage.lower() else "items"
            )
        
        if self.callback:
            self.callback(stage, 0.0, f"Starting {description}")
    
    def update(self, increment: int = 1, message: str = "") -> None:
        """Update progress for current stage."""
        if self.current_pbar:
            self.current_pbar.update(increment)
            
            # Calculate percentage
            percentage = (self.current_pbar.n / self.current_pbar.total) * 100
            
            if self.callback:
                self.callback(self.current_stage, percentage, message)
    
    def finish_stage(self, message: str = "Complete") -> None:
        """Finish current stage."""
        if self.current_pbar:
            self.current_pbar.close()
            self.current_pbar = None
        
        if self.callback:
            self.callback(self.current_stage, 100.0, message)
    
    def log(self, message: str) -> None:
        """Log a message without affecting progress."""
        if self.current_pbar:
            self.current_pbar.write(message)
        elif not self.callback:  # Only print if no callback
            print(message)


class TempFileManager:
    """Manages temporary files with automatic cleanup."""
    
    def __init__(self, cleanup: bool = True):
        """
        Initialize temp file manager.
        
        Args:
            cleanup: Whether to automatically clean up temp files
        """
        self.cleanup = cleanup
        self.temp_dir = None
        self.temp_files = []
    
    def __enter__(self):
        """Create temporary directory."""
        self.temp_dir = tempfile.mkdtemp(prefix="caption_tool_")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up temporary files."""
        if self.cleanup and self.temp_dir:
            try:
                shutil.rmtree(self.temp_dir)
            except OSError:
                pass  # Best effort cleanup
    
    def get_temp_path(self, suffix: str = "", prefix: str = "temp_") -> str:
        """
        Get a temporary file path.
        
        Args:
            suffix: File suffix/extension
            prefix: File prefix
            
        Returns:
            Path to temporary file
        """
        if not self.temp_dir:
            raise RuntimeError("TempFileManager not initialized (use with context manager)")
        
        temp_file = tempfile.NamedTemporaryFile(
            dir=self.temp_dir,
            suffix=suffix,
            prefix=prefix,
            delete=False
        )
        temp_path = temp_file.name
        temp_file.close()
        
        self.temp_files.append(temp_path)
        return temp_path


def ensure_output_directory(output_path: str) -> None:
    """Ensure output directory exists."""
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)


def get_video_info(video_path: str) -> dict:
    """
    Get basic video information using OpenCV.
    
    Args:
        video_path: Path to video file
        
    Returns:
        Dict with video info (width, height, fps, frame_count)
    """
    import cv2
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise UnsupportedFormatError(f"Cannot open video file: {video_path}")
    
    try:
        info = {
            'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'fps': cap.get(cv2.CAP_PROP_FPS),
            'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            'duration': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / cap.get(cv2.CAP_PROP_FPS)
        }
        return info
    finally:
        cap.release()