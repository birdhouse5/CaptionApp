#!/usr/bin/env python3
"""
Debug test script to identify where the processing is failing.
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from caption_processor import CaptionProcessor
from exceptions import CaptionToolError

def test_processing():
    """Test each step of the processing pipeline."""
    
    input_file = "test.mp4"
    output_file = "testout_debug.mp4"
    
    # Verify input exists
    if not os.path.exists(input_file):
        print(f"ERROR: Input file not found: {input_file}")
        return
    
    print(f"=== DEBUG TEST ===")
    print(f"Input: {input_file}")
    print(f"Output: {output_file}")
    print(f"Current directory: {os.getcwd()}")
    
    try:
        # Create processor with verbose logging
        print("\n1. Creating processor...")
        processor = CaptionProcessor(use_progress_bars=True)
        print("   ✓ Processor created successfully")
        
        # Test video info
        print("\n2. Getting video info...")
        from utils import get_video_info
        video_info = get_video_info(input_file)
        print(f"   ✓ Video info: {video_info}")
        
        # Test transcription step
        print("\n3. Testing transcription...")
        from core.transcriber import Transcriber
        from utils import TempFileManager
        
        transcriber = Transcriber("base")
        
        with TempFileManager() as temp_manager:
            print(f"   Temp directory: {temp_manager.temp_dir}")
            
            try:
                full_text, word_timestamps = transcriber.process_media(input_file, temp_manager.temp_dir)
                print(f"   ✓ Transcription successful")
                print(f"   ✓ Text length: {len(full_text)} characters")
                print(f"   ✓ Words found: {len(word_timestamps.get('words', []))}")
                print(f"   ✓ Sample text: {full_text[:100]}...")
                
                if len(word_timestamps.get('words', [])) == 0:
                    print("   ⚠️  WARNING: No words found in transcription!")
                    return
                    
            except Exception as e:
                print(f"   ❌ Transcription failed: {e}")
                import traceback
                traceback.print_exc()
                return
        
        # Test segmentation
        print("\n4. Testing segmentation...")
        try:
            from core.segmenter import Segmenter
            
            # Calculate font size based on video
            rotated_height = video_info['width']  # After rotation
            font_size = int(rotated_height * 0.045)
            
            segmenter = Segmenter(
                font_path=None,
                font_size=font_size,
                max_width_pixels=800,
                max_duration_seconds=1.5
            )
            
            segments_dict = segmenter.create_segments(word_timestamps)
            print(f"   ✓ Segmentation successful")
            print(f"   ✓ Segments created: {len(segments_dict.get('segments', []))}")
            
            for i, seg in enumerate(segments_dict.get('segments', [])[:3]):
                print(f"   ✓ Segment {i+1}: '{seg.get('text', '')[:50]}...'")
                
            if len(segments_dict.get('segments', [])) == 0:
                print("   ⚠️  WARNING: No segments created!")
                return
                
        except Exception as e:
            print(f"   ❌ Segmentation failed: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Test FFmpeg availability
        print("\n5. Testing FFmpeg...")
        import subprocess
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print("   ✓ FFmpeg is available")
                # Show version info
                version_line = result.stdout.split('\n')[0]
                print(f"   ✓ {version_line}")
            else:
                print(f"   ❌ FFmpeg returned error code: {result.returncode}")
        except FileNotFoundError:
            print("   ❌ FFmpeg not found in PATH")
            print("   Please install FFmpeg and add it to your PATH")
            return
        except Exception as e:
            print(f"   ❌ FFmpeg test failed: {e}")
            return
        
        # Test output directory permissions
        print("\n6. Testing output permissions...")
        output_dir = os.path.dirname(output_file) or "."
        try:
            test_file = os.path.join(output_dir, "test_write_permissions.tmp")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            print(f"   ✓ Can write to output directory: {os.path.abspath(output_dir)}")
        except Exception as e:
            print(f"   ❌ Cannot write to output directory: {e}")
            return
        
        # Now try full processing with detailed logging
        print("\n7. Running full processing with detailed logging...")
        try:
            # Create a custom progress callback to see what's happening
            def debug_callback(stage, percentage, message):
                print(f"   [{stage}] {percentage:.1f}% - {message}")
            
            # Create processor with our debug callback
            debug_processor = CaptionProcessor(
                use_progress_bars=False,  # Disable tqdm to avoid conflicts
                progress_callback=debug_callback
            )
            
            print("   Starting video processing...")
            success = debug_processor.process_video(input_file, output_file)
            
            if success:
                print("   ✓ Processing reported success")
                
                # Check if file actually exists
                if os.path.exists(output_file):
                    size = os.path.getsize(output_file)
                    print(f"   ✓ Output file exists: {output_file} ({size} bytes)")
                    
                    if size == 0:
                        print("   ⚠️  WARNING: Output file is empty!")
                    else:
                        print("   ✓ SUCCESS: Video processing completed successfully!")
                else:
                    print(f"   ❌ Output file does not exist: {output_file}")
                    
                    # Check if any temporary files were created
                    temp_files = []
                    for root, dirs, files in os.walk("."):
                        for file in files:
                            if "temp" in file.lower() and file.endswith(('.mp4', '.avi')):
                                temp_files.append(os.path.join(root, file))
                    
                    if temp_files:
                        print(f"   Found temporary video files: {temp_files}")
                    else:
                        print("   No temporary video files found")
            else:
                print("   ❌ Processing reported failure")
                
        except Exception as e:
            print(f"   ❌ Full processing failed: {e}")
            import traceback
            traceback.print_exc()
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_processing()