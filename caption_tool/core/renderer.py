"""
Caption rendering and video processing.
"""

import cv2
import numpy as np
import subprocess
import tempfile
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from utils import parse_time_to_seconds, ProgressTracker
from exceptions import RenderingError, FontError


class CaptionRenderer:
    """Handles caption rendering and video processing."""
    
    def __init__(self, font_path: Optional[str] = None, font_size_scale: float = 0.045,
                 text_color: List[int] = None, highlight_color: List[int] = None,
                 background_color: Optional[List[int]] = None, 
                 highlight_background_color: List[int] = None,
                 position: Tuple[float, float] = (0.5, 0.8),
                 highlighting_mode: str = "text",
                 word_spacing: int = 10, blur_radius: int = 5,
                 rotation_degrees: int = 0,
                 progress_tracker: Optional[ProgressTracker] = None):
        """
        Initialize caption renderer.
        
        Args:
            font_path: Path to TTF font file
            font_size_scale: Font size as ratio of video height
            text_color: RGB color for normal text [R, G, B]
            highlight_color: RGB color for highlighted text [R, G, B]
            background_color: RGB color for background, None for transparent
            highlight_background_color: RGB color for highlight background
            position: (x, y) position ratios (0.0 to 1.0)
            highlighting_mode: "text", "background", "both", or "current_word_only"
            word_spacing: Spacing between words in pixels
            blur_radius: Blur radius for text shadow
            rotation_degrees: Degrees to rotate video (0, 90, 180, 270)
            progress_tracker: Optional progress tracker
        """
        self.font_path = font_path
        self.font_size_scale = font_size_scale
        self.text_color = text_color or [255, 255, 255]
        self.highlight_color = highlight_color or [255, 255, 0]
        self.background_color = background_color
        self.highlight_background_color = highlight_background_color or [0, 255, 0]
        self.position = position
        self.highlighting_mode = highlighting_mode
        self.word_spacing = word_spacing
        self.blur_radius = blur_radius
        self.rotation_degrees = rotation_degrees
        self.progress_tracker = progress_tracker
        
        # Parse highlighting mode
        self.highlight_text = highlighting_mode in ["text", "both"]
        self.highlight_background = highlighting_mode in ["background", "both"]
        self.show_current_word_only = highlighting_mode == "current_word_only"
    
    def _load_font(self, font_size: int) -> ImageFont.ImageFont:
        """Load font for rendering with project fonts support."""
        try:
            # Get the project root directory (where main.py is located)
            if hasattr(self, '_project_root'):
                project_root = self._project_root
            else:
                # Try to find project root automatically
                current_file = Path(__file__).resolve()
                project_root = current_file.parent.parent  # Go up from core/ to caption_tool/
                
                # Alternative: look for main.py
                for parent in current_file.parents:
                    if (parent / 'main.py').exists():
                        project_root = parent
                        break
            
            fonts_dir = project_root / 'fonts'
            
            # 1. Try the specified font path first (if absolute or relative to project)
            if self.font_path:
                font_path = Path(self.font_path)
                
                # If it's not absolute, try relative to project root
                if not font_path.is_absolute():
                    font_path = project_root / self.font_path
                
                if font_path.exists():
                    font = ImageFont.truetype(str(font_path), font_size)
                    self._log_font_use(f"Using specified font: {font_path} at {font_size}px")
                    return font
            
            # 2. Try project fonts directory
            if fonts_dir.exists():
                # Priority order for project fonts
                project_fonts = [
                    'roboto.ttf',
                    'roboto-regular.ttf', 
                    'Roboto-Regular.ttf',
                    'opensans.ttf',
                    'opensans-regular.ttf',
                    'OpenSans-Regular.ttf', 
                    'inter.ttf',
                    'inter-regular.ttf',
                    'Inter-Regular.ttf',
                    'arial.ttf',
                    'Arial.ttf'
                ]
                
                for font_name in project_fonts:
                    font_path = fonts_dir / font_name
                    if font_path.exists():
                        try:
                            font = ImageFont.truetype(str(font_path), font_size)
                            self._log_font_use(f"Using project font: {font_name} at {font_size}px")
                            return font
                        except Exception as e:
                            self._log_font_use(f"Failed to load {font_name}: {e}")
                            continue
            
            # 3. Try system fonts as fallback
            system_fonts = self._get_system_fonts()
            
            for font_path in system_fonts:
                if os.path.exists(font_path):
                    try:
                        font = ImageFont.truetype(font_path, font_size)
                        self._log_font_use(f"Using system font: {font_path} at {font_size}px")
                        return font
                    except Exception:
                        continue
            
            # 4. Try font names without full paths (let system find them)
            font_names = [
                "arial.ttf", "Arial.ttf",
                "calibri.ttf", "Calibri.ttf", 
                "roboto.ttf", "Roboto.ttf",
                "opensans.ttf", "OpenSans.ttf"
            ]
            
            for font_name in font_names:
                try:
                    font = ImageFont.truetype(font_name, font_size)
                    self._log_font_use(f"Using system font by name: {font_name} at {font_size}px")
                    return font
                except Exception:
                    continue
            
            # 5. Last resort: default font with warning
            self._log_font_use("WARNING: Using PIL default font - text may be tiny!")
            self._log_font_use("Consider downloading fonts to the 'fonts/' directory")
            self._log_font_use("Recommended: Download Roboto from https://fonts.google.com/specimen/Roboto")
            
            return ImageFont.load_default()
            
        except Exception as e:
            raise FontError(f"Failed to load font: {e}")

    def _get_system_fonts(self):
        """Get list of common system font paths."""
        system_fonts = []
        
        # Windows fonts
        windows_fonts_dir = Path("C:/Windows/Fonts")
        if windows_fonts_dir.exists():
            system_fonts.extend([
                str(windows_fonts_dir / "arial.ttf"),
                str(windows_fonts_dir / "Arial.ttf"),
                str(windows_fonts_dir / "calibri.ttf"), 
                str(windows_fonts_dir / "Calibri.ttf"),
                str(windows_fonts_dir / "tahoma.ttf"),
                str(windows_fonts_dir / "Tahoma.ttf"),
            ])
        
        # Linux fonts
        linux_font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/roboto/Roboto-Regular.ttf",
        ]
        system_fonts.extend(linux_font_paths)
        
        # macOS fonts
        macos_font_paths = [
            "/System/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial.ttf",
        ]
        system_fonts.extend(macos_font_paths)
        
        return system_fonts

    def _log_font_use(self, message: str):
        """Log font usage information (only once)."""
        # Only log font selection once, not for every frame
        if not hasattr(self, '_font_logged'):
            self._font_logged = False

        if not self._font_logged:
            if hasattr(self, 'progress_tracker') and self.progress_tracker:
                self.progress_tracker.log(message)
            self._font_logged = True
    
    def _draw_rounded_rectangle(self, draw: ImageDraw.ImageDraw, coords: Tuple[int, int, int, int], 
                               radius: int, color: Tuple[int, int, int, int]) -> None:
        """Draw a rounded rectangle."""
        x1, y1, x2, y2 = coords
        diameter = radius * 2
        
        # Main rectangles
        draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=color)
        draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=color)
        
        # Corner circles
        draw.ellipse([x1, y1, x1 + diameter, y1 + diameter], fill=color)
        draw.ellipse([x2 - diameter, y1, x2, y1 + diameter], fill=color)
        draw.ellipse([x1, y2 - diameter, x1 + diameter, y2], fill=color)
        draw.ellipse([x2 - diameter, y2 - diameter, x2, y2], fill=color)
    
    def _render_caption_on_frame(self, frame: np.ndarray, segments: List[Dict[str, Any]], 
                                current_time: float) -> np.ndarray:
        """
        Render captions on a single video frame.
        
        Args:
            frame: Video frame as numpy array
            segments: List of segment dictionaries
            current_time: Current time in seconds
            
        Returns:
            Frame with captions rendered
        """
        # Convert frame to PIL Image
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
        width, height = image.size
        
        # Calculate font size
        font_size = int(height * self.font_size_scale)
        font = self._load_font(font_size)
        
        # Find active segment
        active_segment = None
        for segment in segments:
            start_time = parse_time_to_seconds(segment['start_time'])
            end_time = parse_time_to_seconds(segment['end_time'])
            
            if start_time <= current_time < end_time:
                active_segment = segment
                break
        
        if not active_segment:
            # Convert back to BGR for OpenCV
            return cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)
        
        # Create layers
        shadow_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        text_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        bg_layer = Image.new("RGBA", image.size, (0, 0, 0, 0)) if self.background_color else None
        highlight_bg_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        
        shadow_draw = ImageDraw.Draw(shadow_layer)
        text_draw = ImageDraw.Draw(text_layer)
        bg_draw = ImageDraw.Draw(bg_layer) if bg_layer else None
        highlight_bg_draw = ImageDraw.Draw(highlight_bg_layer)
        
        # Get segment words
        segment_words = active_segment.get('words', [])
        
        if self.show_current_word_only:
            # Show only current word
            active_word = None
            for word_data in segment_words:
                word_start = parse_time_to_seconds(word_data.get('start'))
                word_end = parse_time_to_seconds(word_data.get('end'))
                if word_start <= current_time < word_end:
                    active_word = word_data
                    break
            
            if active_word:
                self._render_single_word(
                    active_word, font, width, height,
                    shadow_draw, text_draw, bg_draw, highlight_bg_draw,
                    is_highlighted=True
                )
        else:
            # Show full segment with highlighting
            self._render_full_segment(
                active_segment, current_time, font, width, height,
                shadow_draw, text_draw, bg_draw, highlight_bg_draw
            )
        
        # Apply blur to shadow
        blurred_shadow = shadow_layer.filter(ImageFilter.GaussianBlur(self.blur_radius))
        
        # Composite layers
        result = image
        if bg_layer:
            result = Image.alpha_composite(result, bg_layer)
        result = Image.alpha_composite(result, highlight_bg_layer)
        result = Image.alpha_composite(result, blurred_shadow)
        result = Image.alpha_composite(result, text_layer)
        
        # Convert back to BGR for OpenCV
        return cv2.cvtColor(np.array(result.convert("RGB")), cv2.COLOR_RGB2BGR)
    
    def _render_single_word(self, word_data: Dict[str, Any], font: ImageFont.ImageFont,
                           width: int, height: int, shadow_draw: ImageDraw.ImageDraw,
                           text_draw: ImageDraw.ImageDraw, bg_draw: Optional[ImageDraw.ImageDraw],
                           highlight_bg_draw: ImageDraw.ImageDraw, is_highlighted: bool) -> None:
        """Render a single word (for current_word_only mode)."""
        word_text = word_data.get('text', '')
        
        # Calculate dimensions
        bbox = font.getbbox(word_text)
        word_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Calculate position
        x_position = int(width * self.position[0]) - (word_width // 2)
        y_position = int(height * self.position[1]) - (text_height // 2)
        
        # Render background if enabled
        if bg_draw and self.background_color:
            h_padding = int(font.size * 0.5)
            v_padding = int(font.size * 0.3)
            bg_color = tuple(self.background_color + [180])  # Add alpha
            
            self._draw_rounded_rectangle(
                bg_draw,
                (x_position - h_padding, y_position - v_padding,
                 x_position + word_width + h_padding, y_position + text_height + v_padding),
                int(font.size * 0.3),
                bg_color
            )
        
        # Render highlight background if enabled
        if self.highlight_background and is_highlighted:
            highlight_color = tuple(self.highlight_background_color + [200])
            self._draw_rounded_rectangle(
                highlight_bg_draw,
                (x_position - int(font.size * 0.2), y_position - int(font.size * 0.2),
                 x_position + word_width + int(font.size * 0.2), y_position + text_height + int(font.size * 0.2)),
                int(font.size * 0.15),
                highlight_color
            )
        
        # Render shadow
        shadow_draw.text((x_position, y_position), word_text, font=font, fill=(0, 0, 0, 255))
        
        # Render text
        text_color = self.highlight_color if (self.highlight_text and is_highlighted) else self.text_color
        text_draw.text((x_position, y_position), word_text, font=font, fill=tuple(text_color + [255]))
    
    def _render_full_segment(self, segment: Dict[str, Any], current_time: float,
                            font: ImageFont.ImageFont, width: int, height: int,
                            shadow_draw: ImageDraw.ImageDraw, text_draw: ImageDraw.ImageDraw,
                            bg_draw: Optional[ImageDraw.ImageDraw], highlight_bg_draw: ImageDraw.ImageDraw) -> None:
        """Render full segment with word highlighting."""
        segment_words = segment.get('words', [])
        if not segment_words:
            return
        
        # Calculate word widths and total width
        word_widths = []
        for word_data in segment_words:
            bbox = font.getbbox(word_data.get('text', ''))
            word_widths.append(bbox[2] - bbox[0])
        
        total_width = sum(word_widths) + self.word_spacing * (len(segment_words) - 1)
        text_height = font.getbbox('Aj')[3]
        
        # Calculate starting position
        start_x = int(width * self.position[0]) - (total_width // 2)
        y_position = int(height * self.position[1]) - (text_height // 2)
        
        # Render background if enabled
        if bg_draw and self.background_color:
            h_padding = int(font.size * 0.5)
            v_padding = int(font.size * 0.3)
            bg_color = tuple(self.background_color + [180])
            
            self._draw_rounded_rectangle(
                bg_draw,
                (start_x - h_padding, y_position - v_padding,
                 start_x + total_width + h_padding, y_position + text_height + v_padding),
                int(font.size * 0.3),
                bg_color
            )
        
        # Render each word
        current_x = start_x
        for i, (word_data, word_width) in enumerate(zip(segment_words, word_widths)):
            word_text = word_data.get('text', '')
            
            # Check if word is highlighted
            word_start = parse_time_to_seconds(word_data.get('start'))
            word_end = parse_time_to_seconds(word_data.get('end'))
            is_highlighted = word_start <= current_time < word_end
            
            # Render highlight background if enabled
            if self.highlight_background and is_highlighted:
                highlight_color = tuple(self.highlight_background_color + [200])
                self._draw_rounded_rectangle(
                    highlight_bg_draw,
                    (current_x - int(font.size * 0.2), y_position - int(font.size * 0.2),
                     current_x + word_width + int(font.size * 0.2), y_position + text_height + int(font.size * 0.2)),
                    int(font.size * 0.15),
                    highlight_color
                )
            
            # Render shadow
            shadow_draw.text((current_x, y_position), word_text, font=font, fill=(0, 0, 0, 255))
            
            # Render text
            text_color = self.highlight_color if (self.highlight_text and is_highlighted) else self.text_color
            text_draw.text((current_x, y_position), word_text, font=font, fill=tuple(text_color + [255]))
            
            # Update position for next word
            current_x += word_width + self.word_spacing
    
    def process_video(self, input_path: str, output_path: str, segments: List[Dict[str, Any]], 
                     temp_dir: str) -> None:
        """
        Process video with caption overlay.
        
        Args:
            input_path: Path to input video
            output_path: Path to output video
            segments: List of caption segments
            temp_dir: Temporary directory for intermediate files
            
        Raises:
            RenderingError: If video processing fails
        """
        try:
            if self.progress_tracker:
                self.progress_tracker.log(f"Starting video processing: {input_path}")
                self.progress_tracker.log(f"Output path: {output_path}")
                self.progress_tracker.log(f"Number of segments: {len(segments)}")
                self.progress_tracker.log(f"Rotation: {self.rotation_degrees} degrees")
            
            # Open video
            cap = cv2.VideoCapture(input_path)
            if not cap.isOpened():
                raise RenderingError(f"Cannot open video: {input_path}")
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if self.progress_tracker:
                self.progress_tracker.log(f"Video properties: {width}x{height}, {fps}fps, {total_frames} frames")
            
            # Calculate output dimensions based on rotation
            if self.rotation_degrees in [90, 270]:
                # 90° or 270° rotation swaps dimensions
                output_width, output_height = height, width
            else:
                # 0° or 180° rotation keeps dimensions
                output_width, output_height = width, height
            
            # Create temporary video file
            temp_video_path = os.path.join(temp_dir, "temp_video.mp4")
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(temp_video_path, fourcc, fps, (output_width, output_height))
            
            if not out.isOpened():
                raise RenderingError("Failed to create video writer")
            
            if self.progress_tracker:
                self.progress_tracker.log(f"Created temp video writer: {temp_video_path}")
                self.progress_tracker.log(f"Output dimensions: {output_width}x{output_height}")
            
            # Start progress tracking
            if self.progress_tracker:
                self.progress_tracker.start_stage("Video Processing", total_frames, "Adding captions")
            
            frame_count = 0
            processed_frames = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Apply rotation if specified
                if self.rotation_degrees == 90:
                    frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                elif self.rotation_degrees == 180:
                    frame = cv2.rotate(frame, cv2.ROTATE_180)
                elif self.rotation_degrees == 270:
                    frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
                # 0 degrees = no rotation
                
                # Calculate current time
                current_time = frame_count / fps
                
                # Render captions on frame
                processed_frame = self._render_caption_on_frame(frame, segments, current_time)
                
                # Write frame
                out.write(processed_frame)
                frame_count += 1
                processed_frames += 1
                
                # Update progress
                if self.progress_tracker and frame_count % 30 == 0:  # Update every 30 frames
                    self.progress_tracker.update(30)
            
            # Clean up
            cap.release()
            out.release()
            
            if self.progress_tracker:
                self.progress_tracker.finish_stage(f"Processed {processed_frames} frames")
                self.progress_tracker.log(f"Temp video created: {temp_video_path}")
                
                # Check if temp video exists and has content
                if os.path.exists(temp_video_path):
                    temp_size = os.path.getsize(temp_video_path)
                    self.progress_tracker.log(f"Temp video size: {temp_size} bytes")
                else:
                    raise RenderingError(f"Temp video file was not created: {temp_video_path}")
            
            # Merge with audio using FFmpeg
            self._merge_audio(input_path, temp_video_path, output_path)
            
        except Exception as e:
            if self.progress_tracker:
                self.progress_tracker.log(f"Video processing error: {e}")
            raise RenderingError(f"Video processing failed: {e}")
    
    def _merge_audio(self, original_video: str, processed_video: str, output_path: str) -> None:
        """Merge processed video with original audio using FFmpeg."""
        try:
            if self.progress_tracker:
                self.progress_tracker.log("Merging video with audio...")
                self.progress_tracker.log(f"Original video: {original_video}")
                self.progress_tracker.log(f"Processed video: {processed_video}")
                self.progress_tracker.log(f"Output path: {output_path}")
            
            # Ensure output directory exists (but handle case where output_path has no directory)
            output_dir = os.path.dirname(output_path)
            if output_dir:  # Only create directory if there is one
                os.makedirs(output_dir, exist_ok=True)
                if self.progress_tracker:
                    self.progress_tracker.log(f"Created output directory: {output_dir}")
            
            command = [
                'ffmpeg', '-y',  # Overwrite output
                '-i', processed_video,  # Processed video
                '-i', original_video,   # Original video with audio
                '-c:v', 'copy',         # Copy video
                '-c:a', 'aac',          # AAC audio codec
                '-map', '0:v:0',        # Video from first input
                '-map', '1:a:0',        # Audio from second input
                '-shortest',            # End when shortest stream ends
                output_path
            ]
            
            if self.progress_tracker:
                self.progress_tracker.log(f"FFmpeg command: {' '.join(command)}")
            
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300,  # 5 minute timeout
                text=True
            )
            
            if result.returncode != 0:
                if self.progress_tracker:
                    self.progress_tracker.log(f"FFmpeg stderr: {result.stderr}")
                    self.progress_tracker.log(f"FFmpeg stdout: {result.stdout}")
                raise RenderingError(f"FFmpeg failed with return code {result.returncode}: {result.stderr}")
            
            # Verify output file was created
            if os.path.exists(output_path):
                output_size = os.path.getsize(output_path)
                if self.progress_tracker:
                    self.progress_tracker.log(f"Audio merge complete. Output size: {output_size} bytes")
            else:
                raise RenderingError(f"FFmpeg completed but output file not found: {output_path}")
                
        except subprocess.TimeoutExpired:
            raise RenderingError("FFmpeg timeout - video too large or system too slow")
        except FileNotFoundError as e:
            # Better error handling for FFmpeg not found
            if self.progress_tracker:
                self.progress_tracker.log(f"FileNotFoundError details: {e}")
            
            # Check if this is a directory creation issue or FFmpeg missing
            if "ffmpeg" in str(e).lower():
                raise RenderingError("FFmpeg not found - please install FFmpeg and ensure it's in your PATH")
            else:
                raise RenderingError(f"File system error: {e}")
        except Exception as e:
            if self.progress_tracker:
                self.progress_tracker.log(f"Audio merge error: {e}")
            raise RenderingError(f"Audio merge failed: {e}")