#!/usr/bin/env python3
"""
Direct test of core components to identify the exact failure point.
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_direct_processing():
    """Test core components directly."""
    
    input_file = "test.mp4"
    output_file = "testout_direct.mp4"
    
    print(f"=== DIRECT CORE TEST ===")
    
    try:
        # Import core components
        from core.transcriber import Transcriber
        from core.segmenter import Segmenter
        from core.renderer import CaptionRenderer
        from utils import TempFileManager, get_video_info
        
        # Get video info
        video_info = get_video_info(input_file)
        print(f"Video: {video_info['width']}x{video_info['height']}, {video_info['fps']:.1f}fps")
        
        # Calculate dimensions after rotation
        rotated_width = video_info['height']
        rotated_height = video_info['width']
        font_size = int(rotated_height * 0.045)
        
        with TempFileManager(cleanup=False) as temp_manager:  # Don't cleanup so we can inspect
            print(f"Temp directory: {temp_manager.temp_dir}")
            
            # Step 1: Transcription
            print("\n1. Running transcription...")
            transcriber = Transcriber("base")
            full_text, word_timestamps = transcriber.process_media(input_file, temp_manager.temp_dir)
            print(f"   ✓ Transcribed {len(word_timestamps['words'])} words")
            
            # Step 2: Segmentation
            print("\n2. Running segmentation...")
            segmenter = Segmenter(
                font_path=None,
                font_size=font_size,
                max_width_pixels=min(800, int(rotated_width * 0.8)),
                max_duration_seconds=1.5
            )
            segments_dict = segmenter.create_segments(word_timestamps)
            print(f"   ✓ Created {len(segments_dict['segments'])} segments")
            
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
            
            print(f"   ✓ Prepared {len(segments)} segments for rendering")
            
            # Step 3: Rendering
            print("\n3. Running video rendering...")
            
            # Create renderer with simple progress tracking
            class SimpleProgress:
                def log(self, message):
                    print(f"   RENDERER: {message}")
                def start_stage(self, stage, total, description):
                    print(f"   RENDERER: Starting {stage} - {description}")
                def update(self, increment):
                    pass  # Skip frequent updates
                def finish_stage(self, message=""):
                    print(f"   RENDERER: Stage complete - {message}")
            
            progress = SimpleProgress()
            
            renderer = CaptionRenderer(
                font_path=None,
                font_size_scale=0.045,
                text_color=[255, 255, 255],
                highlight_color=[255, 255, 0],
                background_color=None,
                highlight_background_color=[0, 255, 0],
                position=(0.5, 0.8),
                highlighting_mode="text",
                word_spacing=10,
                blur_radius=5,
                progress_tracker=progress
            )
            
            try:
                print(f"   Starting renderer.process_video()")
                print(f"   Input: {input_file}")
                print(f"   Output: {output_file}")
                print(f"   Segments: {len(segments)}")
                print(f"   Temp dir: {temp_manager.temp_dir}")
                
                renderer.process_video(input_file, output_file, segments, temp_manager.temp_dir)
                
                print(f"   ✓ Renderer completed without exceptions")
                
            except Exception as e:
                print(f"   ❌ Renderer failed: {e}")
                import traceback
                traceback.print_exc()
                return
            
            # Check results
            print(f"\n4. Checking results...")
            if os.path.exists(output_file):
                size = os.path.getsize(output_file)
                print(f"   ✓ Output file created: {output_file} ({size} bytes)")
                if size > 0:
                    print(f"   ✓ SUCCESS!")
                else:
                    print(f"   ⚠️  Output file is empty")
            else:
                print(f"   ❌ Output file not created: {output_file}")
                
                # Check temp directory for clues
                print(f"   Checking temp directory: {temp_manager.temp_dir}")
                if os.path.exists(temp_manager.temp_dir):
                    temp_files = os.listdir(temp_manager.temp_dir)
                    print(f"   Temp files: {temp_files}")
                    
                    for file in temp_files:
                        if file.endswith('.mp4'):
                            temp_path = os.path.join(temp_manager.temp_dir, file)
                            temp_size = os.path.getsize(temp_path)
                            print(f"   Temp video: {file} ({temp_size} bytes)")
                else:
                    print(f"   Temp directory not found")
    
    except Exception as e:
        print(f"❌ Direct test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_direct_processing()