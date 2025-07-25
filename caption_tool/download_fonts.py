#!/usr/bin/env python3
"""
Download and setup fonts for caption_tool - FIXED VERSION
"""

import os
import requests
from pathlib import Path
import zipfile
import shutil

def download_fonts():
    """Download free fonts for the caption tool."""
    
    # Create fonts directory
    fonts_dir = Path(__file__).parent / 'fonts'
    fonts_dir.mkdir(exist_ok=True)
    
    print(f"📁 Created fonts directory: {fonts_dir}")
    
    # Font download URLs (FIXED - these work!)
    fonts_to_download = {
        'roboto.ttf': {
            'url': 'https://github.com/PolymerElements/font-roboto-local/raw/master/fonts/roboto/Roboto-Regular.ttf',
            'description': 'Roboto Regular - Google\'s modern font'
        },
        'opensans.ttf': {
            'url': 'https://github.com/google/fonts/raw/main/apache/opensans/OpenSans%5Bwdth,wght%5D.ttf',
            'description': 'Open Sans - Clean, readable font',
            'fallback_url': 'https://github.com/google/fonts/raw/main/apache/opensans/static/OpenSans-Regular.ttf'
        },
        'inter.ttf': {
            'url': 'https://github.com/rsms/inter/raw/master/docs/font-files/Inter-Regular.otf',
            'description': 'Inter Regular - Designed for computer screens'
        },
        'liberation-sans.ttf': {
            'url': 'https://github.com/liberationfonts/liberation-fonts/raw/main/src/v2/LiberationSans-Regular.ttf',
            'description': 'Liberation Sans - Free alternative to Arial'
        }
    }
    
    # Download each font
    for font_name, font_info in fonts_to_download.items():
        font_path = fonts_dir / font_name
        
        if font_path.exists():
            print(f"✅ {font_name} already exists")
            continue
        
        print(f"⬇️  Downloading {font_name}...")
        print(f"   {font_info['description']}")
        
        # Try main URL first
        success = False
        for url_key in ['url', 'fallback_url']:
            if url_key not in font_info:
                continue
                
            url = font_info[url_key]
            if url_key == 'fallback_url':
                print(f"   Trying fallback URL...")
            
            try:
                print(f"   Requesting: {url}")
                response = requests.get(url, timeout=30, allow_redirects=True)
                response.raise_for_status()
                
                with open(font_path, 'wb') as f:
                    f.write(response.content)
                
                # Verify it's actually a font file (basic check)
                if font_path.stat().st_size > 1000:  # Font files should be at least 1KB
                    print(f"✅ Downloaded {font_name} ({len(response.content):,} bytes)")
                    success = True
                    break
                else:
                    print(f"⚠️  File too small, trying next URL...")
                    font_path.unlink()  # Delete small file
                
            except Exception as e:
                print(f"❌ Failed to download from {url}: {e}")
                if font_path.exists():
                    font_path.unlink()  # Clean up partial download
        
        if not success:
            print(f"❌ All download attempts failed for {font_name}")
    
    # Add a simple backup option - copy from Windows fonts if available
    print(f"\n🔍 Checking for Windows system fonts as backup...")
    windows_fonts_dir = Path("C:/Windows/Fonts")
    
    if windows_fonts_dir.exists():
        backup_fonts = {
            'arial.ttf': 'arial.ttf',
            'calibri.ttf': 'calibri.ttf', 
            'tahoma.ttf': 'tahoma.ttf'
        }
        
        for system_font, local_name in backup_fonts.items():
            system_path = windows_fonts_dir / system_font
            local_path = fonts_dir / local_name
            
            if system_path.exists() and not local_path.exists():
                try:
                    shutil.copy2(system_path, local_path)
                    print(f"✅ Copied system font: {system_font}")
                except Exception as e:
                    print(f"⚠️  Could not copy {system_font}: {e}")
    
    # Create README for fonts directory
    readme_content = """# Fonts Directory

This directory contains fonts used by the caption tool.

## Current Fonts

- **roboto.ttf**: Roboto Regular by Google - Modern, clean font
- **opensans.ttf**: Open Sans - Highly readable font  
- **inter.ttf**: Inter Regular - Optimized for screens
- **liberation-sans.ttf**: Liberation Sans - Free alternative to Arial
- **arial.ttf**: Arial (if copied from system)
- **calibri.ttf**: Calibri (if copied from system)

## Adding More Fonts

You can add more TTF font files to this directory. The caption tool will automatically detect and use them.

Popular free font sources:
- Google Fonts: https://fonts.google.com/
- Font Squirrel: https://www.fontsquirrel.com/
- Liberation Fonts: https://github.com/liberationfonts/liberation-fonts

## Usage

The caption tool will automatically use fonts from this directory. You can also specify a specific font:

```bash
python main.py video.mp4 output.mp4 --font-path fonts/roboto.ttf
```

## Font Licenses

- Roboto: Apache License 2.0
- Open Sans: Apache License 2.0
- Inter: SIL Open Font License 1.1
- Liberation Sans: SIL Open Font License 1.1

All fonts in this directory are free for commercial and personal use.
"""
    
    readme_path = fonts_dir / 'README.md'
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"📝 Created {readme_path}")
    
    # Test fonts
    print(f"\n🧪 Testing fonts...")
    test_fonts(fonts_dir)
    
    print(f"\n🎉 Font setup complete!")
    print(f"📁 Fonts location: {fonts_dir.absolute()}")
    print(f"\n▶️  Now you can use:")
    print(f"   python main.py data/test.mp4 data/output.mp4 --font-size large")
    print(f"   (Will automatically use project fonts)")

def test_fonts(fonts_dir):
    """Test that fonts can be loaded."""
    try:
        from PIL import ImageFont
        
        working_fonts = []
        for font_file in fonts_dir.glob('*.ttf'):
            try:
                font = ImageFont.truetype(str(font_file), 50)
                print(f"   ✅ {font_file.name} loads correctly")
                working_fonts.append(font_file.name)
            except Exception as e:
                print(f"   ❌ {font_file.name} failed to load: {e}")
        
        for font_file in fonts_dir.glob('*.otf'):  # Also check OTF files
            try:
                font = ImageFont.truetype(str(font_file), 50)
                print(f"   ✅ {font_file.name} loads correctly")
                working_fonts.append(font_file.name)
            except Exception as e:
                print(f"   ❌ {font_file.name} failed to load: {e}")
        
        if working_fonts:
            print(f"   🎉 {len(working_fonts)} fonts ready to use!")
        else:
            print(f"   ⚠️  No working fonts found. Caption tool will use system fonts.")
                
    except ImportError:
        print(f"   ⚠️  PIL not available for font testing")

if __name__ == '__main__':
    download_fonts()