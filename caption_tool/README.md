# Caption Tool

A streamlined command-line tool for adding AI-generated captions to videos using OpenAI Whisper.

## Features

- **AI Transcription**: Uses OpenAI Whisper for high-quality speech-to-text
- **Smart Segmentation**: Automatically splits captions based on width and duration constraints
- **Flexible Highlighting**: Multiple highlighting modes (text color, background, current word only)
- **Customizable Styling**: Font selection, colors, positioning, and sizing options
- **Video Rotation**: Automatically rotates videos 90° clockwise during processing
- **Audio Preservation**: Maintains original audio quality using FFmpeg
- **Progress Tracking**: Real-time progress bars and status updates

## Installation

### Prerequisites

1. **Python 3.8+**
2. **FFmpeg** - Required for audio processing
   ```bash
   # Ubuntu/Debian
   sudo apt install ffmpeg
   
   # macOS
   brew install ffmpeg
   
   # Windows
   # Download from https://ffmpeg.org/download.html
   ```

### Install Dependencies

```bash
pip install -r requirements.txt
```

## Quick Start

### Basic Usage

```bash
# Add captions to a video
python main.py input.mp4 output.mp4

# Generate transcript only
python main.py input.mp4 transcript.txt --transcript-only
```

### Common Examples

```bash
# Use a custom font and larger text
python main.py video.mp4 captioned.mp4 \
  --font-path fonts/arial.ttf \
  --font-size large

# Yellow text with background highlighting
python main.py video.mp4 captioned.mp4 \
  --text-color yellow \
  --highlight-mode background \
  --highlight-bg-color blue

# Show only current word being spoken
python main.py video.mp4 captioned.mp4 \
  --highlight-mode current_word_only \
  --font-size extra-large

# Use preset configuration
python main.py video.mp4 captioned.mp4 --preset large_text
```

## Configuration

### Using Config Files

Create a JSON configuration file for consistent settings:

```json
{
  "fonts": {
    "path": "fonts/arial.ttf",
    "size_scale": 0.055
  },
  "colors": {
    "text": [255, 255, 255],
    "highlight": [255, 255, 0],
    "background": null,
    "highlight_background": [0, 255, 0]
  },
  "positioning": {
    "horizontal": 0.5,
    "vertical": 0.8
  },
  "highlighting": {
    "mode": "text"
  },
  "segments": {
    "max_duration_seconds": 1.5,
    "max_width_pixels": 800
  }
}
```

Use the config file:
```bash
python main.py video.mp4 output.mp4 --config my_config.json
```

### Available Presets

- `default`: Standard settings
- `large_text`: Bigger font, longer segments
- `minimal`: Clean, simple appearance
- `current_word`: Shows only the word being spoken
- `background_highlight`: Uses background highlighting instead of text color

```bash
python main.py video.mp4 output.mp4 --preset large_text
```

## Module Usage

You can also use the tool as a Python module:

```python
from caption_processor import CaptionProcessor

# Simple usage
processor = CaptionProcessor()
processor.process_video("input.mp4", "output.mp4")

# With custom configuration
processor = CaptionProcessor(
    font_path="fonts/arial.ttf",
    text_color=[255, 255, 255],
    highlight_color=[255, 255, 0],
    highlighting_mode="text"
)
processor.process_video("input.mp4", "output.mp4")

# With progress callback
def progress_callback(stage, percentage, message):
    print(f"{stage}: {percentage:.1f}% - {message}")

processor = CaptionProcessor(progress_callback=progress_callback)
processor.process_video("input.mp4", "output.mp4")

# Transcription only
transcript = processor.transcribe_only("input.mp4", "transcript.txt")
print(transcript)
```

## Command Line Options

### Input/Output
- `input`: Input video file (MP4, MOV, AVI, MKV)
- `output`: Output file path
- `--transcript-only`: Generate text transcript only

### Font Settings
- `--font-path PATH`: Path to TTF font file
- `--font-size {small,medium,large,extra-large}`: Font size preset
- `--font-scale FLOAT`: Font size as ratio of video height (0.01-0.1)

### Colors
- `--text-color COLOR`: Text color (RGB, hex, or name)
- `--highlight-color COLOR`: Highlight color for current word
- `--background-color COLOR`: Background color (optional)
- `--highlight-bg-color COLOR`: Background highlight color

Color formats:
- RGB: `255,255,255`
- Hex: `#FFFFFF`
- Named: `white`, `red`, `blue`, etc.

### Positioning
- `--position X,Y`: Caption position as ratios (0.0-1.0)
- `--position Y`: Vertical position only (centers horizontally)

### Highlighting Modes
- `text`: Change text color for current word
- `background`: Add colored rectangle behind current word
- `both`: Use both text and background highlighting
- `current_word_only`: Show only the word being spoken

### Segmentation
- `--max-width PIXELS`: Maximum caption width in pixels
- `--max-duration SECONDS`: Maximum segment duration in seconds

### Transcription
- `--whisper-model {tiny,base,small,medium,large}`: Whisper model size

### Other Options
- `--config FILE`: JSON configuration file
- `--preset NAME`: Use preset configuration
- `--save-config FILE`: Save effective configuration to file
- `--quiet`: Suppress progress output

## Supported Formats

### Input
- **Video**: MP4, MOV, AVI, MKV
- **Audio**: MP3, WAV, M4A, FLAC (for transcript-only mode)

### Output
- **Video**: MP4 (with original audio preserved)
- **Text**: UTF-8 encoded text files

## Performance Notes

- **Whisper Models**: 
  - `tiny`: Fastest, lower accuracy
  - `base`: Good balance (default)
  - `large`: Best accuracy, slower
- **GPU Support**: Install PyTorch with CUDA for faster processing
- **Memory Usage**: Larger models require more RAM
- **Processing Time**: Roughly 2-5x video length depending on hardware

## Troubleshooting

### Common Issues

1. **FFmpeg not found**
   ```
   Error: FFmpeg not found - please install FFmpeg
   ```
   Install FFmpeg and ensure it's in your PATH.

2. **Font loading errors**
   ```
   Error: Failed to load font
   ```
   Check that the font path is correct and the file exists.

3. **CUDA out of memory**
   Use a smaller Whisper model:
   ```bash
   python main.py video.mp4 output.mp4 --whisper-model tiny
   ```

4. **Video file not supported**
   Convert to MP4 first or check that the file isn't corrupted.

### Performance Optimization

- Use GPU acceleration: Install `torch` with CUDA support
- Use smaller Whisper models for faster processing
- Reduce video resolution before processing for very large files
- Use SSD storage for temporary files

## License

MIT License - see LICENSE file for details.