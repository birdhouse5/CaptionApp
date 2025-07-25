#!/usr/bin/env python3
"""
Debug script to trace exactly what's happening with font size
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_font_processing():
    """Debug the font size issue step by step"""
    
    print("=== FONT SIZE DEBUG TRACE ===")
    
    try:
        # Import components
        from config import Config
        from utils import get_video_info
        
        # Test video file
        test_video = "data/test.mp4"
        if not os.path.exists(test_video):
            print(f"❌ Test video not found: {test_video}")
            return
        
        print(f"✅ Test video found: {test_video}")
        
        # Step 1: Test config with large font
        print("\n1. Testing config with large font scale...")
        config = Config()
        
        # Simulate --font-size large (should be 0.06)
        size_scales = {'small': 0.03, 'medium': 0.045, 'large': 0.06, 'extra-large': 0.075}
        font_scale = size_scales['large']
        config.set('fonts.size_scale', font_scale)
        
        print(f"   Config font_size_scale: {config.font_size_scale}")
        print(f"   Config get('fonts.size_scale'): {config.get('fonts.size_scale')}")
        
        # Step 2: Get video info and calculate font size
        print("\n2. Getting video info and calculating font size...")
        video_info = get_video_info(test_video)
        print(f"   Video dimensions: {video_info['width']}x{video_info['height']}")
        
        # Calculate font size like the main.py does
        effective_height = video_info['height']  # Assuming no rotation
        calculated_font_size = int(effective_height * font_scale)
        
        print(f"   Font scale: {font_scale}")
        print(f"   Effective height: {effective_height}")
        print(f"   Calculated font size: {calculated_font_size}px")
        print(f"   As percentage of height: {(calculated_font_size/effective_height)*100:.1f}%")
        
        # Step 3: Test what happens in segmenter
        print("\n3. Testing font size in segmenter...")
        from core.segmenter import Segmenter
        
        segmenter = Segmenter(
            font_path=None,  # Default font
            font_size=calculated_font_size,
            max_width_pixels=800,
            max_duration_seconds=1.5
        )
        
        print(f"   Segmenter font_size: {segmenter.font_size}")
        print(f"   Segmenter font loaded: {type(segmenter.font)}")
        
        # Test text measurement
        test_text = "Hello World"
        text_width = segmenter._measure_text_width(test_text)
        print(f"   Text '{test_text}' width: {text_width}px")
        
        # Step 4: Test what happens in renderer
        print("\n4. Testing font size in renderer...")
        from core.renderer import CaptionRenderer
        
        renderer = CaptionRenderer(
            font_path=None,
            font_size_scale=font_scale,  # This should be 0.06
            text_color=[255, 255, 255],
            highlight_color=[255, 255, 0],
            position=(0.5, 0.8),
            highlighting_mode="text"
        )
        
        print(f"   Renderer font_size_scale: {renderer.font_size_scale}")
        
        # Test font loading in renderer
        renderer_font_size = int(effective_height * renderer.font_size_scale)
        print(f"   Renderer calculated font size: {renderer_font_size}px")
        
        try:
            test_font = renderer._load_font(renderer_font_size)
            print(f"   Renderer font loaded: {type(test_font)}")
            print(f"   Font size from loaded font: {getattr(test_font, 'size', 'unknown')}")
        except Exception as e:
            print(f"   ❌ Font loading failed: {e}")
        
        # Step 5: Compare with default
        print(f"\n5. Comparison with default font size...")
        default_scale = 0.045
        default_font_size = int(effective_height * default_scale)
        print(f"   Default font size: {default_font_size}px")
        print(f"   Large font size: {calculated_font_size}px")
        print(f"   Difference: {calculated_font_size - default_font_size}px ({((calculated_font_size/default_font_size-1)*100):.1f}% larger)")
        
        if calculated_font_size <= default_font_size:
            print("   🚨 PROBLEM: Large font is not actually larger!")
        else:
            print("   ✅ Font size calculation looks correct")
            
        # Step 6: Check if there's a path issue
        print(f"\n6. Checking execution path...")
        print(f"   Current working directory: {os.getcwd()}")
        print(f"   Script directory: {os.path.dirname(os.path.abspath(__file__))}")
        print(f"   Python path[0]: {sys.path[0]}")
        
        # Are we using the fixed main.py or something else?
        main_py_path = os.path.join(os.getcwd(), "main.py")
        if os.path.exists(main_py_path):
            print(f"   main.py exists: {main_py_path}")
            # Check first few lines to see which version
            with open(main_py_path, 'r') as f:
                first_lines = [f.readline().strip() for _ in range(10)]
            
            if any("Fixed version" in line for line in first_lines):
                print("   ✅ Using fixed main.py")
            else:
                print("   ⚠️  May be using old main.py")
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_font_processing()