#!/usr/bin/env python3
"""
Caption Tool - CLI interface for video captioning.
Simple version without package structure.
"""

import sys
import os

# Add the current directory to Python path to find our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
import json
from pathlib import Path
from typing import List, Optional

from caption_processor import CaptionProcessor
from exceptions import CaptionToolError
from config import Config


def parse_color(color_str: str) -> List[int]:
    """Parse color string to RGB list."""
    if ',' in color_str:
        # RGB format: "255,255,255"
        try:
            return [int(x.strip()) for x in color_str.split(',')]
        except ValueError:
            raise argparse.ArgumentTypeError(f"Invalid RGB color format: {color_str}")
    else:
        # Named color or hex
        color_map = {
            'white': [255, 255, 255],
            'black': [0, 0, 0],
            'red': [255, 0, 0],
            'green': [0, 255, 0],
            'blue': [0, 0, 255],
            'yellow': [255, 255, 0],
            'cyan': [0, 255, 255],
            'magenta': [255, 0, 255],
            'orange': [255, 165, 0],
            'purple': [128, 0, 128],
            'pink': [255, 192, 203]
        }
        
        if color_str.lower() in color_map:
            return color_map[color_str.lower()]
        elif color_str.startswith('#') and len(color_str) == 7:
            # Hex color: "#FF0000"
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
            # Single value for vertical position, center horizontally
            return (0.5, float(pos_str))
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid position format: {pos_str}")


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Add captions to videos using AI transcription",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.mp4 output.mp4
  %(prog)s input.mp4 output.mp4 --config my_config.json
  %(prog)s input.mp4 output.mp4 --font-path fonts/arial.ttf --text-color white
  %(prog)s input.mp4 output.mp4 --preset large_text --highlight-mode background
  %(prog)s input.mp4 transcript.txt --transcript-only
        """
    )
    
    # Required arguments
    parser.add_argument('input', help='Input video file')
    parser.add_argument('output', help='Output file (video or text)')
    
    # Mode selection
    parser.add_argument('--transcript-only', action='store_true',
                       help='Generate transcript only (no video captions)')
    
    # Configuration
    parser.add_argument('--config', type=str,
                       help='JSON configuration file')
    parser.add_argument('--preset', type=str, 
                       choices=['default', 'large_text', 'minimal', 'current_word', 'background_highlight'],
                       help='Use preset configuration')
    
    # Font settings
    parser.add_argument('--font-path', type=str,
                       help='Path to TTF font file')
    parser.add_argument('--font-size', type=str, choices=['small', 'medium', 'large', 'extra-large'],
                       help='Font size preset')
    parser.add_argument('--font-scale', type=float,
                       help='Font size as ratio of video height (0.01-0.1)')
    
    # Colors
    parser.add_argument('--text-color', type=parse_color,
                       help='Text color (RGB: "255,255,255", hex: "#FFFFFF", or name: "white")')
    parser.add_argument('--highlight-color', type=parse_color,
                       help='Highlight color for current word')
    parser.add_argument('--background-color', type=parse_color,
                       help='Background color (optional)')
    parser.add_argument('--highlight-bg-color', type=parse_color,
                       help='Background highlight color')
    
    # Positioning
    parser.add_argument('--position', type=parse_position,
                       help='Caption position as "x,y" ratios (0.0-1.0) or just "y" for vertical')
    
    # Highlighting
    parser.add_argument('--highlight-mode', type=str,
                       choices=['text', 'background', 'both', 'current_word_only'],
                       help='Highlighting mode')
    
    # Segmentation
    parser.add_argument('--max-width', type=int,
                       help='Maximum caption width in pixels')
    parser.add_argument('--max-duration', type=float,
                       help='Maximum segment duration in seconds')
    
    # Transcription
    parser.add_argument('--whisper-model', type=str,
                       choices=['tiny', 'base', 'small', 'medium', 'large'],
                       help='Whisper model size')
    
    # Output options
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Suppress progress output')
    parser.add_argument('--save-config', type=str,
                       help='Save effective configuration to file')
    
    return parser


def build_overrides(args: argparse.Namespace) -> dict:
    """Build configuration overrides from command line arguments."""
    overrides = {}
    
    # Font settings
    if args.font_path:
        overrides['fonts.path'] = args.font_path
    if args.font_scale:
        overrides['fonts.size_scale'] = args.font_scale
    elif args.font_size:
        size_scales = {
            'small': 0.03,
            'medium': 0.045,
            'large': 0.06,
            'extra-large': 0.075
        }
        overrides['fonts.size_scale'] = size_scales[args.font_size]
    
    # Colors
    if args.text_color:
        overrides['colors.text'] = args.text_color
    if args.highlight_color:
        overrides['colors.highlight'] = args.highlight_color
    if args.background_color:
        overrides['colors.background'] = args.background_color
    if args.highlight_bg_color:
        overrides['colors.highlight_background'] = args.highlight_bg_color
    
    # Positioning
    if args.position:
        overrides['positioning.horizontal'] = args.position[0]
        overrides['positioning.vertical'] = args.position[1]
    
    # Highlighting
    if args.highlight_mode:
        overrides['highlighting.mode'] = args.highlight_mode
    
    # Segmentation
    if args.max_width:
        overrides['video.max_width_pixels'] = args.max_width
    if args.max_duration:
        overrides['segments.max_duration_seconds'] = args.max_duration
    
    # Transcription
    if args.whisper_model:
        overrides['transcription.model'] = args.whisper_model
    
    return overrides


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    try:
        # Validate inputs
        if not os.path.exists(args.input):
            print(f"Error: Input file not found: {args.input}", file=sys.stderr)
            return 1
        
        # Build configuration overrides
        overrides = build_overrides(args)
        
        # Create processor
        if args.preset:
            processor = CaptionProcessor.with_presets(
                args.preset, 
                config_file=args.config,
                use_progress_bars=not args.quiet,
                **overrides
            )
        else:
            processor = CaptionProcessor(
                config_file=args.config,
                use_progress_bars=not args.quiet,
                **overrides
            )
        
        # Save configuration if requested
        if args.save_config:
            with open(args.save_config, 'w') as f:
                json.dump(processor.get_config(), f, indent=2)
            print(f"Configuration saved to: {args.save_config}")
        
        # Process based on mode
        if args.transcript_only:
            # Transcription only
            if not args.quiet:
                print(f"Transcribing: {args.input}")
            
            transcript = processor.transcribe_only(args.input, args.output)
            
            if not args.quiet:
                print(f"Transcript saved to: {args.output}")
                print(f"Transcript length: {len(transcript)} characters")
        else:
            # Full video captioning
            if not args.quiet:
                print(f"Processing video: {args.input}")
                print(f"Output will be saved to: {args.output}")
            
            success = processor.process_video(args.input, args.output)
            
            if success:
                if not args.quiet:
                    print(f"Successfully created captioned video: {args.output}")
                return 0
            else:
                print("Video processing failed", file=sys.stderr)
                return 1
    
    except CaptionToolError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if not args.quiet:
            import traceback
            traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())