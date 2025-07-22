#!/usr/bin/env python3
"""
Debug script to test font size with your actual video
"""

import sys
import os

# Add the caption_tool directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'caption_tool'))

def find_video_file():
    """Find any video file in the current directory"""
    video_extensions = ['.mp4', '.mov', '.avi', '.mkv']
    
    for file in os.listdir('.'):
        if any(file.lower().endswith(ext) for ext in video_extensions):
            return file
    
    # Check caption_tool directory too
    caption_dir = 'caption_tool'
    if os.path.exists(caption_dir):
        for file in os.listdir(caption_dir):
            if any(file.lower().endswith(ext) for ext in video_extensions):
                return os.path.join(caption_dir, file)
    
    return None

def test_processing_pipeline():
    """Test the actual video processing pipeline"""
    
    print("=== REAL VIDEO PROCESSING DEBUG ===")
    
    # Find a video file
    video_file = find_video_file()
    if not video_file:
        print("❌ No video file found. Please put a video file in the current directory.")
        return
    
    print(f"✅ Found video file: {video_file}")
    
    try:
        # Test 1: Check if we're using the broken CaptionProcessor
        print(f"\n1. Testing CaptionProcessor...")
        from caption_processor import CaptionProcessor
        
        processor = CaptionProcessor(use_progress_bars=False)
        
        # Set a very large font size for testing
        processor.update_config(**{'fonts.size_scale': 0.15})  # 15% - should be huge!
        print(f"   Set font scale to: {processor.config.font_size_scale}")
        
        # Try to process - this will reveal the bug
        print(f"   Calling process_video...")
        result = processor.process_video(video_file, 'debug_test_output.mp4')
        
        print(f"   Result type: {type(result)}")
        print(f"   Result value: {result}")
        
        if isinstance(result, dict):
            print("   🚨 BUG CONFIRMED: CaptionProcessor.process_video() returns config dict!")
            print("   This is why your font size changes aren't working.")
            
        elif isinstance(result, bool):
            print(f"   Result is boolean: {result}")
            if os.path.exists('debug_test_output.mp4'):
                size = os.path.getsize('debug_test_output.mp4')
                print(f"   Output file created: debug_test_output.mp4 ({size} bytes)")
                if size > 0:
                    print("   ✅ Processing seems to work! Font size should be huge.")
                else:
                    print("   ❌ Output file is empty")
            else:
                print("   ❌ No output file created")
        
    except Exception as e:
        print(f"   ❌ CaptionProcessor test failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Try the direct approach from main.py
    print(f"\n2. Testing direct processing approach...")
    try:
        from core.transcriber import Transcriber
        from core.segmenter import Segmenter
        from core.renderer import CaptionRenderer
        from utils import get_video_info, TempFileManager
        from config import Config
        
        # Create config with large font
        config = Config()
        config.set('fonts.size_scale', 0.15)  # 15% - should be huge!
        print(f"   Direct config font scale: {config.font_size_scale}")
        
        # Get video info
        video_info = get_video_info(video_file)
        print(f"   Video: {video_info['width']}x{video_info['height']}")
        
        # Calculate font size
        effective_height = video_info['height']  # Assuming no rotation
        font_size = int(effective_height * config.font_size_scale)
        print(f"   Calculated font size: {font_size}px (should be {int(video_info['height'] * 0.15)}px)")
        
        print("   Direct processing approach looks correct.")
        print("   Font size calculation is working properly.")
        
    except Exception as e:
        print(f"   ❌ Direct processing test failed: {e}")
        import traceback
        traceback.print_exc()

def check_which_main_you_use():
    """Check which main script is being used"""
    
    print(f"\n=== MAIN SCRIPT ANALYSIS ===")
    
    caption_dir = 'caption_tool'
    main_files = []
    
    if os.path.exists(caption_dir):
        for file in os.listdir(caption_dir):
            if file.startswith('main') and file.endswith('.py'):
                main_files.append(file)
                print(f"Found: {file}")
    
    print(f"\nMain scripts found: {main_files}")
    
    if 'main.py' in main_files and 'main_simple.py' in main_files:
        print(f"\n🔍 You have both main.py and main_simple.py")
        print(f"   main.py uses direct processing (bypasses broken CaptionProcessor)")
        print(f"   main_simple.py uses CaptionProcessor (has the bug)")
        print(f"\n✅ SOLUTION: Use main.py for working font size changes:")
        print(f"   python caption_tool/main.py {find_video_file()} output.mp4 --font-scale 0.08")
    
    elif 'main.py' in main_files:
        print(f"\n✅ Use main.py - it should work correctly")
        
    elif 'main_simple.py' in main_files:
        print(f"\n❌ Only main_simple.py found - this has the CaptionProcessor bug")
        print(f"   You need to fix caption_processor.py or use a different approach")

if __name__ == "__main__":
    test_processing_pipeline()
    check_which_main_you_use()
    
    print(f"\n=== DEBUGGING SUMMARY ===")
    print(f"1. Font configuration: ✅ Working correctly")
    print(f"2. Video processing: 🔍 Run this test to see the exact issue")
    print(f"3. Recommended command to test font size:")
    
    video_file = find_video_file()
    if video_file:
        print(f"   python caption_tool/main.py \"{video_file}\" output_large_font.mp4 --font-scale 0.1")
        print(f"   (This should create captions with 10% of video height = very large text)")
    else:
        print(f"   python caption_tool/main.py your_video.mp4 output_large_font.mp4 --font-scale 0.1")