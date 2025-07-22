"""
Main caption processor that orchestrates the entire pipeline.
"""

import os
from typing import Optional, Callable, Dict, Any, List
from pathlib import Path

from config import Config
from utils import (
    validate_input_video, 
    ensure_output_directory, 
    get_video_info,
    ProgressTracker, 
    TempFileManager
)
from core.transcriber import Transcriber
from core.segmenter import Segmenter
from core.renderer import CaptionRenderer
from exceptions import CaptionToolError


class CaptionProcessor:
    """Main caption processing class."""
    
    def __init__(self, config_file: Optional[str] = None, 
                 progress_callback: Optional[Callable[[str, float, str], None]] = None,
                 use_progress_bars: bool = True, **overrides):
        """
        Initialize caption processor.
        
        Args:
            config_file: Path to JSON config file
            progress_callback: Optional callback function(stage, percentage, message)
            use_progress_bars: Whether to show progress bars in CLI mode
            **overrides: Configuration overrides as keyword arguments
        """
        # Load configuration
        self.config = Config(config_file, overrides)
        
        # Set up progress tracking
        self.progress_tracker = ProgressTracker(progress_callback, use_progress_bars)
        
        # Initialize components
        self.transcriber = None
        self.segmenter = None
        self.renderer = None
        
        # Initialize components lazily
        self._init_components()
    
    def _init_components(self) -> None:
        """Initialize processing components with current config."""
        # Transcriber
        self.transcriber = Transcriber(
            model_name=self.config.whisper_model,
            progress_tracker=self.progress_tracker
        )
        
        # Get video info to calculate font size (will be set per video)
        # Segmenter will be initialized in process_video with actual video dimensions
        
        # Renderer will also be initialized in process_video with actual config
    

    def process_video(self, input_path: str, output_path: str, 
                    progress_callback: Optional[Callable[[str, float, str], None]] = None) -> bool:
        """
        Process video with captions.
        
        Args:
            input_path: Path to input video file
            output_path: Path to output video file
            progress_callback: Optional progress callback for this specific job
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            CaptionToolError: If processing fails
        """
        try:
            # Validate input
            validate_input_video(input_path, self.config.get('video.supported_input_formats'))
            ensure_output_directory(output_path)
            
            # Get video information
            video_info = get_video_info(input_path)
            self.progress_tracker.log(f"Video info: {video_info['width']}x{video_info['height']}, "
                                    f"{video_info['fps']:.1f}fps, {video_info['duration']:.1f}s")
            
            # Get rotation setting
            rotation_degrees = self.config.get('video.rotation_degrees', 0)
            
            # Calculate dimensions based on rotation
            if rotation_degrees in [90, 270]:
                # Rotation swaps dimensions
                effective_width = video_info['height']
                effective_height = video_info['width']
            else:
                # No rotation or 180° keeps dimensions
                effective_width = video_info['width']
                effective_height = video_info['height']
            
            # Calculate font size based on effective height
            font_size = int(effective_height * self.config.font_size_scale)
            
            # Initialize segmenter with video-specific parameters
            self.segmenter = Segmenter(
                font_path=self.config.font_path,
                font_size=font_size,
                max_width_pixels=min(self.config.max_width_pixels, int(effective_width * 0.8)),
                max_duration_seconds=self.config.get('segments.max_duration_seconds', 1.5),
                word_spacing=self.config.get('segments.word_spacing', 10)
            )
            
            # Initialize renderer
            self.renderer = CaptionRenderer(
                font_path=self.config.font_path,
                font_size_scale=self.config.font_size_scale,
                text_color=self.config.text_color,
                highlight_color=self.config.highlight_color,
                background_color=self.config.background_color,
                highlight_background_color=self.config.highlight_background_color,
                position=self.config.position,
                highlighting_mode=self.config.highlighting_mode,
                word_spacing=self.config.get('segments.word_spacing', 10),
                blur_radius=self.config.get('segments.blur_radius', 5),
                rotation_degrees=rotation_degrees,
                progress_tracker=self.progress_tracker
            )
            
            # Process with temporary file management
            with TempFileManager(cleanup=self.config.get('processing.cleanup_temp_files', True)) as temp_manager:
                # THIS WAS THE BUG - it returned config instead of processing!
                # OLD BROKEN LINE: return self.config.to_dict()
                # FIXED LINE:
                return self._process_pipeline(input_path, output_path, temp_manager)

        except Exception as e:
            if isinstance(e, CaptionToolError):
                raise
            else:
                raise CaptionToolError(f"Processing failed: {e}")


    def update_config(self, **updates) -> None:
        """
        Update configuration and reinitialize components.
        
        Args:
            **updates: Configuration updates as keyword arguments
        """
        for key, value in updates.items():
            self.config.set(key, value)
        
        # Reinitialize components with new config
        self._init_components()
    
    @classmethod
    def from_config_file(cls, config_file: str, **overrides) -> 'CaptionProcessor':
        """
        Create processor from configuration file.
        
        Args:
            config_file: Path to JSON config file
            **overrides: Configuration overrides
            
        Returns:
            Configured CaptionProcessor instance
        """
        return cls(config_file=config_file, **overrides)
    
    @classmethod
    def with_presets(cls, preset: str = "default", **overrides) -> 'CaptionProcessor':
        """
        Create processor with preset configuration.
        
        Args:
            preset: Preset name ("default", "large_text", "minimal", etc.)
            **overrides: Configuration overrides
            
        Returns:
            Configured CaptionProcessor instance
        """
        presets = {
            "default": {},
            "large_text": {
                "fonts.size_scale": 0.06,
                "segments.max_duration_seconds": 2.0
            },
            "minimal": {
                "highlighting.mode": "text",
                "colors.background": None,
                "segments.blur_radius": 2
            },
            "current_word": {
                "highlighting.mode": "current_word_only",
                "colors.highlight": [255, 255, 0],
                "fonts.size_scale": 0.055
            },
            "background_highlight": {
                "highlighting.mode": "background",
                "colors.highlight_background": [0, 0, 255],
                "segments.blur_radius": 3
            }
        }
        
        preset_config = presets.get(preset, {})
        preset_config.update(overrides)
        
        return cls(**preset_config)._process_pipeline(input_path, output_path, temp_manager)
            
    
    def _process_pipeline(self, input_path: str, output_path: str, temp_manager: TempFileManager) -> bool:
        """Execute the main processing pipeline."""
        try:
            # Step 1: Transcription
            self.progress_tracker.start_stage("Transcription", 1, "Extracting and transcribing audio")
            
            full_text, word_timestamps = self.transcriber.process_media(input_path, temp_manager.temp_dir)
            
            self.progress_tracker.update(1, f"Transcribed {len(word_timestamps['words'])} words")
            self.progress_tracker.finish_stage()
            
            # Debug: Check if we got words
            if not word_timestamps.get('words'):
                self.progress_tracker.log("WARNING: No words found in transcription")
                return False
            
            # Step 2: Segmentation
            self.progress_tracker.start_stage("Segmentation", 1, "Creating caption segments")
            
            segments_dict = self.segmenter.create_segments(word_timestamps)
            
            self.progress_tracker.update(1, f"Created {len(segments_dict['segments'])} segments")
            self.progress_tracker.finish_stage()
            
            # Debug: Check if we got segments
            if not segments_dict.get('segments'):
                self.progress_tracker.log("WARNING: No segments created")
                return False
            
            # Convert segments to format expected by renderer
            segments = self._prepare_segments_for_rendering(segments_dict['segments'])
            
            # Debug: Log first few segments
            self.progress_tracker.log(f"Sample segments: {len(segments)} total")
            for i, seg in enumerate(segments[:2]):  # Show first 2 segments
                self.progress_tracker.log(f"  Segment {i+1}: '{seg.get('text', '')[:50]}...'")
            
            # Step 3: Video rendering
            self.progress_tracker.log(f"Starting video rendering to: {output_path}")
            self.renderer.process_video(input_path, output_path, segments, temp_manager.temp_dir)
            
            # Verify output file was created
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                self.progress_tracker.log(f"Successfully created captioned video: {output_path} ({file_size} bytes)")
                return True
            else:
                self.progress_tracker.log(f"ERROR: Output file was not created: {output_path}")
                return False
            
        except Exception as e:
            self.progress_tracker.log(f"Pipeline failed: {e}")
            import traceback
            self.progress_tracker.log(f"Full traceback: {traceback.format_exc()}")
            raise
    
    def _prepare_segments_for_rendering(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare segments for the renderer by ensuring proper format."""
        prepared_segments = []
        
        for segment in segments:
            # Ensure all required fields are present
            prepared_segment = {
                'start_time': segment.get('start_time'),
                'end_time': segment.get('end_time'),
                'text': segment.get('text', ''),
                'words': []
            }
            
            # Process words
            for word in segment.get('words', []):
                prepared_word = {
                    'text': word.get('text', ''),
                    'start': word.get('start'),
                    'end': word.get('end')
                }
                prepared_segment['words'].append(prepared_word)
            
            prepared_segments.append(prepared_segment)
        
        return prepared_segments
    
    def transcribe_only(self, input_path: str, output_path: str) -> str:
        """
        Transcribe audio/video to text file only.
        
        Args:
            input_path: Path to input media file
            output_path: Path to output text file
            
        Returns:
            Transcribed text
            
        Raises:
            CaptionToolError: If transcription fails
        """
        try:
            # Validate input
            validate_input_video(input_path, 
                self.config.get('video.supported_input_formats') + ['.mp3', '.wav', '.m4a', '.flac'])
            ensure_output_directory(output_path)
            
            # Process with temporary file management
            with TempFileManager(cleanup=self.config.get('processing.cleanup_temp_files', True)) as temp_manager:
                self.progress_tracker.start_stage("Transcription", 1, "Transcribing audio")
                
                full_text, _ = self.transcriber.process_media(input_path, temp_manager.temp_dir)
                
                # Write to file
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(full_text)
                
                self.progress_tracker.update(1, f"Saved transcript to {output_path}")
                self.progress_tracker.finish_stage()
                
                return full_text
                
        except Exception as e:
            if isinstance(e, CaptionToolError):
                raise
            else:
                raise CaptionToolError(f"Transcription failed: {e}")
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration as dictionary."""
        return self