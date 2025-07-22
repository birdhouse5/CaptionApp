#!/usr/bin/env python3
"""
Caption Tool - Fixed version with correct imports
"""

import sys
import os

# FIXED: Add the caption_tool directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'caption_tool'))

import argparse
import json
from pathlib import Path
from typing import List, Optional

# Import the working components directly
from core.transcriber import Transcriber
from core.segmenter import Segmenter
from core.renderer import CaptionRenderer
from utils import TempFileManager, get_video_info, ensure_output_directory, validate_input_video
from exceptions import CaptionToolError
from config import Config


def parse_color(color_str: str) -> List[int]:
    """Parse color string to RGB list."""
    if ',' in color_str:
        try:
            return [int(x.strip()) for x in color_str.split(',')]
        except ValueError:
            raise argparse.ArgumentTypeError(f"Invalid RGB color format: {color_str}")
    else:
        # Named color or hex
        color_map = {
            'white': [255, 255, 255], 'black': [0, 0, 0], 'red': [255, 0, 0],
            'green': [0, 255, 0], 'blue': [0, 0, 255], 'yellow': [255, 255, 0],
            'cyan': [0, 255, 255], 'magenta': [255, 0, 255], 'orange': [255, 165, 0],
            'purple': [128, 0, 128], 'pink': [255, 192, 203]
        }
        
        if color_str.lower() in color_map:
            return color_map[color_str.lower()]
        elif color_str.startswith('#') and len(color_str) == 7:
            try:
                return [int(color_str[1:3], 16), int(color_str[3:5], 16), int(color_str[5:7], 16)]
            except ValueError:
                raise argparse.ArgumentTypeError(f"Invalid hex color: {color_str}")
        else:
            raise argparse.ArgumentTypeError(f"Unknown color: {color_str}")


def parse_position(pos_str: str) -> tuple:
    """Parse position string to (x, y) tuple."""
    try:
        if ',' in pos_str:
            x, y = pos_str.split(',')
            return (float(x.strip()), float(y.strip()))
        else:
            return (0.5, float(pos_str))
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid position format: {pos_str}")


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Add captions to videos using AI transcription",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Required arguments
    parser.add_argument('input', help='Input video file')
    parser.add_argument('output', help='Output file (video or text)')
    
    # Mode selection
    parser.add_argument('--transcript-only', action='store_true',
                       help='Generate transcript only (no video captions)')
    
    # Configuration
    parser.add_argument('--config', type=str, help='JSON configuration file')
    
    # Font settings
    parser.add_argument('--font-path', type=str, help='Path to TTF font file')
    parser.add_argument('--font-size', type=str, choices=['small', 'medium', 'large', 'extra-large'],
                       help='Font size preset')
    parser.add_argument('--font-scale', type=float,
                       help='Font size as ratio of video height (0.01-0.1)')
    
    # Colors
    parser.add_argument('--text-color', type=parse_color, help='Text color')
    parser.add_argument('--highlight-color', type=parse_color, help='Highlight color for current word')
    parser.add_argument('--background-color', type=parse_color, help='Background color (optional)')
    parser.add_argument('--highlight-bg-color', type=parse_color, help='Background highlight color')
    
    # Positioning
    parser.add_argument('--position', type=parse_position,
                       help='Caption position as "x,y" ratios (0.0-1.0) or just "y" for vertical')
    
    # Highlighting
    parser.add_argument('--highlight-mode', type=str,
                       choices=['text', 'background', 'both', 'current_word_only'],
                       help='Highlighting mode')
    
    # Segmentation
    parser.add_argument('--max-width', type=int, help='Maximum caption width in pixels')
    parser.add_argument('--max-duration', type=float, help='Maximum segment duration in seconds')
    
    # Video processing
    parser.add_argument('--rotation', type=int, choices=[0, 90, 180, 270],
                       help='Rotate video by degrees')
    
    # Transcription
    parser.add_argument('--whisper-model', type=str,
                       choices=['tiny', 'base', 'small', 'medium', 'large'],
                       help='Whisper model size')
    
    # Output options
    parser.add_argument('--quiet', '-q', action='store_true', help='Suppress progress output')
    
    return parser


def process_video_direct(args: argparse.Namespace) -> bool:
    """Process video using direct component calls."""
    
    input_file = args.input
    output_file = args.output
    
    try:
        print(f"🎬 Processing: {input_file} → {output_file}")
        
        # Validate input
        validate_input_video(input_file, ['.mp4', '.mov', '.avi', '.mkv'])
        ensure_output_directory(output_file)
        
        # Load configuration
        config = Config(args.config)
        
        # Apply CLI overrides with debug output
        if args.font_scale:
            config.set('fonts.size_scale', args.font_scale)
            print(f"📏 Font scale set to: {args.font_scale}")
        elif args.font_size:
            size_scales = {'small': 0.03, 'medium': 0.045, 'large': 0.06, 'extra-large': 0.075}
            config.set('fonts.size_scale', size_scales[args.font_size])
            print(f"📏 Font size preset '{args.font_size}' = {size_scales[args.font_size]}")
        
        if args.font_path:
            config.set('fonts.path', args.font_path)
        if args.text_color:
            config.set('colors.text', args.text_color)
        if args.highlight_color:
            config.set('colors.highlight', args.highlight_color)
        if args.background_color:
            config.set('colors.background', args.background_color)
        if args.highlight_bg_color:
            config.set('colors.highlight_background', args.highlight_bg_color)
        if args.position:
            config.set('positioning.horizontal', args.position[0])
            config.set('positioning.vertical', args.position[1])
        if args.highlight_mode:
            config.set('highlighting.mode', args.highlight_mode)
        if args.max_width:
            config.set('video.max_width_pixels', args.max_width)
        if args.max_duration:
            config.set('segments.max_duration_seconds', args.max_duration)
        if args.rotation is not None:
            config.set('video.rotation_degrees', args.rotation)
        if args.whisper_model:
            config.set('transcription.model', args.whisper_model)
        
        # Get video info
        video_info = get_video_info(input_file)
        print(f"📹 Video: {video_info['width']}x{video_info['height']}, {video_info['fps']:.1f}fps, {video_info['duration']:.1f}s")
        
        # Calculate dimensions based on rotation
        rotation_degrees = config.get('video.rotation_degrees', 0)
        if rotation_degrees in [90, 270]:
            effective_width = video_info['height']
            effective_height = video_info['width']
            print(f"🔄 Rotation {rotation_degrees}° → Effective: {effective_width}x{effective_height}")
        else:
            effective_width = video_info['width']
            effective_height = video_info['height']
        
        # Calculate font size with debug output
        font_scale = config.get('fonts.size_scale', 0.045)
        font_size = int(effective_height * font_scale)
        print(f"🔤 Font calculation: {effective_height} × {font_scale} = {font_size}px")
        
        with TempFileManager(cleanup=config.get('processing.cleanup_temp_files', True)) as temp_manager:
            print("🎙️  Extracting and transcribing audio...")
            
            # Step 1: Transcription
            transcriber = Transcriber(config.get('transcription.model', 'base'))
            full_text, word_timestamps = transcriber.process_media(input_file, temp_manager.temp_dir)
            
            print(f"✅ Transcribed {len(word_timestamps['words'])} words")
            
            if len(word_timestamps.get('words', [])) == 0:
                print("❌ ERROR: No words found in transcription")
                return False
            
            # Step 2: Segmentation
            print("📝 Creating caption segments...")
            
            segmenter = Segmenter(
                font_path=config.get('fonts.path'),
                font_size=font_size,  # Use our calculated font size
                max_width_pixels=min(config.get('video.max_width_pixels', 800), int(effective_width * 0.8)),
                max_duration_seconds=config.get('segments.max_duration_seconds', 1.5),
                word_spacing=config.get('segments.word_spacing', 10)
            )
            
            segments_dict = segmenter.create_segments(word_timestamps)
            
            print(f"✅ Created {len(segments_dict['segments'])} segments")
            
            if len(segments_dict.get('segments', [])) == 0:
                print("❌ ERROR: No segments created")
                return False
            
            # Convert segments for renderer
            segments = []
            for segment in segments_dict['segments']:
                prepared_segment = {
                    'start_time': segment.get('start_time'),
                    'end_time': segment.get('end_time'),
                    'text': segment.get('text', ''),
                    'words': []
                }
                
                for word in segment.get('words', []):
                    prepared_word = {
                        'text': word.get('text', ''),
                        'start': word.get('start'),
                        'end': word.get('end')
                    }
                    prepared_segment['words'].append(prepared_word)
                
                segments.append(prepared_segment)
            
            # Step 3: Video rendering
            print("🎨 Processing video with captions...")
            print(f"🔤 Using font size: {font_size}px (scale: {font_scale})")
            
            # Simple progress tracker for CLI
            class CLIProgress:
                def __init__(self, quiet=False):
                    self.quiet = quiet
                
                def log(self, message):
                    if not self.quiet:
                        print(f"   {message}")
                
                def start_stage(self, stage, total, description):
                    if not self.quiet:
                        print(f"   {stage}: {description}")
                
                def update(self, increment):
                    pass
                
                def finish_stage(self, message=""):
                    if not self.quiet and message:
                        print(f"   ✅ {message}")
            
            progress = CLIProgress(args.quiet)
            
            renderer = CaptionRenderer(
                font_path=config.get('fonts.path'),
                font_size_scale=font_scale,  # This should be the large value!
                text_color=config.get('colors.text', [255, 255, 255]),
                highlight_color=config.get('colors.highlight', [255, 255, 0]),
                background_color=config.get('colors.background'),
                highlight_background_color=config.get('colors.highlight_background', [0, 255, 0]),
                position=(config.get('positioning.horizontal', 0.5), config.get('positioning.vertical', 0.8)),
                highlighting_mode=config.get('highlighting.mode', 'text'),
                word_spacing=config.get('segments.word_spacing', 10),
                blur_radius=config.get('segments.blur_radius', 5),
                rotation_degrees=rotation_degrees,
                progress_tracker=progress
            )
            
            print(f"🎬 Starting video rendering...")
            renderer.process_video(input_file, output_file, segments, temp_manager.temp_dir)
            
            # Verify output
            if os.path.exists(output_file):
                size = os.path.getsize(output_file)
                print(f"🎉 Successfully created captioned video: {output_file} ({size:,} bytes)")
                return True
            else:
                print(f"❌ ERROR: Output file not created: {output_file}")
                return False
    
    except Exception as e:
        print(f"❌ ERROR: {e}")
        if not args.quiet:
            import traceback
            traceback.print_exc()
        return False


def transcribe_only(args: argparse.Namespace) -> bool:
    """Transcribe audio to text file only."""
    try:
        config = Config(args.config)
        if args.whisper_model:
            config.set('transcription.model', args.whisper_model)
        
        validate_input_video(args.input, ['.mp4', '.mov', '.avi', '.mkv', '.mp3', '.wav', '.m4a', '.flac'])
        ensure_output_directory(args.output)
        
        with TempFileManager() as temp_manager:
            print(f"🎙️  Transcribing: {args.input}")
            
            transcriber = Transcriber(config.get('transcription.model', 'base'))
            full_text, _ = transcriber.process_media(args.input, temp_manager.temp_dir)
            
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(full_text)
            
            print(f"📝 Transcript saved to: {args.output}")
            print(f"📊 Transcript length: {len(full_text)} characters")
            return True
    
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    try:
        # Validate inputs
        if not os.path.exists(args.input):
            print(f"❌ Error: Input file not found: {args.input}", file=sys.stderr)
            return 1
        
        print("🚀 Caption Tool - Fixed Version")
        print(f"📁 Working directory: {os.getcwd()}")
        print(f"📂 Python path includes: {sys.path[0]}")
        
        # Process based on mode
        if args.transcript_only:
            success = transcribe_only(args)
        else:
            success = process_video_direct(args)
        
        return 0 if success else 1
    
    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"💥 Unexpected error: {e}", file=sys.stderr)
        if not args.quiet:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())