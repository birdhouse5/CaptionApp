import os
import torch
import whisper
import moviepy as mp
from datetime import datetime
import cv2
import shutil
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import tempfile
import subprocess
import json
from datetime import datetime
import logging

# Other imports...

logger = logging.getLogger(__name__)  # Get a logger with the module's name


# Audio Extraction Functions


def extract_audio(media_path):
    """
    Extract audio from the input media file (MP4 or MP3).
    Returns the path to the extracted/copied audio file.
    """
    try:
        # Get file extension and base name
        file_ext = os.path.splitext(media_path)[1].lower()
        
        # If it's already an MP3, just return the path
        if file_ext == '.mp3':
            return media_path
            
        # If it's an MP4, extract audio
        elif file_ext == '.mp4':
            video = mp.VideoFileClip(media_path)
            audio_path = os.path.splitext(media_path)[0] + '.wav'
            video.audio.write_audiofile(audio_path)
            return audio_path
        else:
            raise ValueError(f"Unsupported file format: {file_ext}. Only .mp4 and .mp3 files are supported.")
    
    except Exception as e:
        print(f"Error extracting audio: {e}")
        raise


def transcribe_audio(audio_path):
    """
    Transcribe audio using OpenAI Whisper.
    Returns the transcription result and deletes the audio file afterward.
    """
    try:
        model = whisper.load_model("base")
       
        result = model.transcribe(
            audio_path,
            word_timestamps=True,
            fp16=torch.cuda.is_available()
        )
            
        return result
   
    except Exception as e:
        print(f"Transcription error: {e}")
        # Don't delete the file if transcription failed
        # This helps with debugging the issue
        raise

# Subtitle Formatting Functions
def format_srt_timestamp(seconds):
    """
    Convert seconds to SRT timestamp format (HH:MM:SS,MS).
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millisecs = int((seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"


def create_word_timestamps(result):
    """
    Process transcription result and return a structured dictionary.
   
    Args:
        result (dict): The original transcription result
       
    Returns:
        dict: A structured dictionary containing the word-level data
    """
    # Create a structured dictionary
    words = {
        'words': []
    }
   
    for segment in result['segments']:
        for word in segment['words']:
            if word['word'].strip() and len(word['word'].strip()) > 0:
                words['words'].append({
                    'text': word['word'].strip(),
                    'start': format_srt_timestamp(max(0, word['start'])),
                    'end': format_srt_timestamp(word['end'])
                })

    return words

# Subtitle Formatting Functions
def format_srt_timestamp(seconds):
    """
    Convert seconds to SRT timestamp format (HH:MM:SS,MS).
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millisecs = int((seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"

# Helper function to parse time strings
def parse_time(time_str):
    hours, minutes, rest = time_str.split(':')
    seconds, milliseconds = rest.split(',')
    return datetime.strptime(f"{hours}:{minutes}:{seconds}.{milliseconds}", "%H:%M:%S.%f")

def create_word_segments_with_max_width(words_dict, max_width_pixels=700, font_path=None, font_size=40, max_duration_seconds=1.5):
    """
    Merges individual word segments into larger subtitle segments with a maximum width constraint.
    
    Args:
        words_dict (dict): Dictionary with a 'words' list containing word objects with 'text', 'start', 'end'
        max_width_pixels (int): Maximum width of a segment in pixels
        font_path (str): Path to the font file to use for width calculation
        font_size (int): Font size for width calculation
        max_duration_seconds (float): Maximum duration of a segment in seconds
    
    Returns:
        dict: Dictionary with 'segments' list containing merged subtitle segments
    """
    from PIL import ImageFont, ImageDraw, Image
    import os
    
    print(f"Using max width: {max_width_pixels} pixels, font size: {font_size} pixels")
    
    # Load font for width calculation
    try:
        if font_path and os.path.exists(font_path):
            try:
                font = ImageFont.truetype(font_path, font_size)
                print(f"Using font: {font_path} at size {font_size}")
            except Exception as e:
                print(f"Error loading font: {e}, using default")
                font = ImageFont.load_default()
        else:
            print(f"Font path not found or not specified: {font_path}, using default")
            font = ImageFont.load_default()
    except Exception as e:
        print(f"Error in font loading: {e}, using fallback approach")
        font = None
    
    # Create a temporary image for text measurement
    temp_image = Image.new('RGB', (max_width_pixels * 2, 100))  # Make it wide enough for measurements
    draw = ImageDraw.Draw(temp_image)
    
    words = words_dict.get('words', [])
    if not words:
        return {'segments': []}
    
    # Pre-process to identify sentence endings
    is_sentence_end = []
    for i, word in enumerate(words):
        text = word['text'].strip()
        is_sentence_end.append(any(text.endswith(punct) for punct in [".", "!", "?"]))
    
    # Create a function to measure text width that handles different PIL versions
    def measure_text_width(text):
        try:
            if hasattr(draw, 'textlength'):
                # For newer PIL versions (>= 8.0.0)
                return draw.textlength(text, font=font)
            elif hasattr(draw, 'textsize'):
                # For older PIL versions
                width, _ = draw.textsize(text, font=font)
                return width
            else:
                # Fallback if neither method exists
                return len(text) * (font_size // 2)  # Rough estimate
        except Exception as e:
            print(f"Error measuring text width for '{text}': {e}")
            return len(text) * (font_size // 2)  # Rough estimate if error
    
    # Measure space width once
    space_width = measure_text_width(" ")
    
    # Pre-compute word widths for efficiency
    word_widths = {}
    for word in words:
        text = word['text'].strip()
        if text not in word_widths:
            word_widths[text] = measure_text_width(text)
    
    # Print some samples for debugging
    sample_words = list(word_widths.items())[:5]
    print("Sample word widths:")
    for word, width in sample_words:
        print(f"  '{word}': {width} pixels")
    
    # Now build segments with width constraint
    merged_segments = []
    current_text = ""
    current_words = []
    current_start_time = None
    current_end_time = None
    current_width = 0
    
    i = 0
    while i < len(words):
        word = words[i]
        text = word['text'].strip()
        start_time = word['start']
        end_time = word['end']
        word_width = word_widths.get(text, measure_text_width(text))
        
        # If this is the first entry or we need to start a new segment
        if current_start_time is None:
            current_start_time = start_time
            current_text = text
            current_words = [text]
            current_end_time = end_time
            current_width = word_width
            i += 1
            continue
        
        # Calculate potential new segment width
        potential_width = current_width + space_width + word_width
        
        # Calculate potential new segment duration
        potential_duration = (parse_time(end_time) - parse_time(current_start_time)).total_seconds()
        
        # Check if adding this text would exceed limits
        potential_text = f"{current_text} {text}"
        potential_words = current_words + [text]
        exceed_width_limit = potential_width > max_width_pixels
        exceed_time_limit = potential_duration > max_duration_seconds
        end_of_sentence = is_sentence_end[i-1]  # Check if previous word ended a sentence
        
        # Debug output for width constraint
        if exceed_width_limit:
            print(f"Width limit exceeded: {potential_width} > {max_width_pixels} for: '{potential_text}'")
        
        # If any limit is exceeded or we reached end of sentence, start a new segment
        if exceed_width_limit or exceed_time_limit or end_of_sentence:
            merged_segments.append({
                "index": len(merged_segments) + 1,
                "start_time": current_start_time,
                "end_time": current_end_time,
                "text": current_text,
                "width_pixels": current_width
            })
            current_start_time = start_time
            current_text = text
            current_words = [text]
            current_end_time = end_time
            current_width = word_width
        else:
            # Merge with previous segment
            current_text = potential_text
            current_words = potential_words
            current_end_time = end_time
            current_width = potential_width
        
        i += 1
    
    # Add the last segment if there's any pending text
    if current_text:
        merged_segments.append({
            "index": len(merged_segments) + 1,
            "start_time": current_start_time,
            "end_time": current_end_time,
            "text": current_text,
            "width_pixels": current_width
        })
    
    # Print some debugging info about the segments
    print(f"Created {len(merged_segments)} segments with max width {max_width_pixels} pixels")
    for i, segment in enumerate(merged_segments[:3]):  # Show first 3 as examples
        print(f"Segment {i+1}: '{segment['text']}' - Width: {segment.get('width_pixels', 'N/A')} pixels")
    if len(merged_segments) > 3:
        print(f"... and {len(merged_segments) - 3} more segments")
    
    return {'segments': merged_segments}


def create_word_segments_with_max_width(words_dict, max_width_pixels=700, font_path=None, font_size=40, max_duration_seconds=1.5):
    """
    Merges individual word segments into larger subtitle segments with a maximum width constraint.
    
    Args:
        words_dict (dict): Dictionary with a 'words' list containing word objects with 'text', 'start', 'end'
        max_width_pixels (int): Maximum width of a segment in pixels
        font_path (str): Path to the font file to use for width calculation
        font_size (int): Font size for width calculation
        max_duration_seconds (float): Maximum duration of a segment in seconds
    
    Returns:
        dict: Dictionary with 'segments' list containing merged subtitle segments
    """
    from PIL import ImageFont, ImageDraw, Image
    
    # Load font for width calculation
    if font_path and os.path.exists(font_path):
        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception as e:
            print(f"Error loading font: {e}, using default")
            font = ImageFont.load_default()
    else:
        font = ImageFont.load_default()
    
    # Create a temporary image for text measurement
    temp_image = Image.new('RGB', (1, 1))
    draw = ImageDraw.Draw(temp_image)
    
    words = words_dict.get('words', [])
    if not words:
        return {'segments': []}
    
    # Pre-process to identify sentence endings
    is_sentence_end = []
    for i, word in enumerate(words):
        text = word['text'].strip()
        is_sentence_end.append(any(text.endswith(punct) for punct in [".", "!", "?"]))
    
    merged_segments = []
    current_text = ""
    current_start_time = None
    current_end_time = None
    current_width = 0
    
    i = 0
    while i < len(words):
        word = words[i]
        text = word['text'].strip()
        start_time = word['start']
        end_time = word['end']
        
        # Calculate width of this word
        word_width = draw.textlength(text, font=font)
        
        # If this is the first entry or we need to start a new segment
        if current_start_time is None:
            current_start_time = start_time
            current_text = text
            current_end_time = end_time
            current_width = word_width
            i += 1
            continue
        
        # Calculate potential new segment width
        space_width = draw.textlength(" ", font=font)
        potential_width = current_width + space_width + word_width
        
        # Calculate potential new segment duration
        potential_duration = (parse_time(end_time) - parse_time(current_start_time)).total_seconds()
        
        # Check if adding this text would exceed limits
        potential_text = f"{current_text} {text}" if current_text else text
        exceed_width_limit = potential_width > max_width_pixels
        exceed_time_limit = potential_duration > max_duration_seconds
        end_of_sentence = is_sentence_end[i-1]  # Check if previous word ended a sentence
        
        # If any limit is exceeded or we reached end of sentence, start a new segment
        if exceed_width_limit or exceed_time_limit or end_of_sentence:
            merged_segments.append({
                "index": len(merged_segments) + 1,
                "start_time": current_start_time,
                "end_time": current_end_time,
                "text": current_text,
                "width_pixels": current_width
            })
            current_start_time = start_time
            current_text = text
            current_end_time = end_time
            current_width = word_width
        else:
            # Merge with previous segment
            current_text = potential_text
            current_end_time = end_time
            current_width = potential_width
        
        i += 1
    
    # Add the last segment if there's any pending text
    if current_text:
        merged_segments.append({
            "index": len(merged_segments) + 1,
            "start_time": current_start_time,
            "end_time": current_end_time,
            "text": current_text,
            "width_pixels": current_width
        })
    
    return {'segments': merged_segments}

def create_word_segments_with_integrity(words_dict, max_width_pixels=700, font_path=None, 
                               font_size=40, max_duration_seconds=1.5, video_width=None):
    """
    Create word segments with respect to maximum width, duration, and word integrity.
    
    Args:
        words_dict (dict): Dictionary with a 'words' list containing word objects
        max_width_pixels (int): Maximum width of a segment in pixels
        font_path (str): Path to the font file to use for width calculation
        font_size (int): Font size for width calculation
        max_duration_seconds (float): Maximum duration of a segment in seconds
        video_width (int): Width of the video frame (after rotation)
        
    Returns:
        dict: Dictionary with 'segments' list containing merged subtitle segments
    """
    from PIL import ImageFont, ImageDraw, Image
    import os
    from core.media_processer import parse_time_to_seconds, format_srt_timestamp
    
    # If video_width is provided, calculate margin and adjust max_width
    if video_width:
        margin_percent = 0.05  # 5% margin
        margin_pixels = int(video_width * margin_percent)
        max_width_pixels = min(max_width_pixels, video_width - (2 * margin_pixels))
    
    print(f"Creating segments with max width: {max_width_pixels} pixels, font size: {font_size} pixels")
    
    # Load font for width calculation
    try:
        if font_path and os.path.exists(font_path):
            try:
                font = ImageFont.truetype(font_path, font_size)
                print(f"Using font: {font_path} at size {font_size}")
            except Exception as e:
                print(f"Error loading font: {e}, using default")
                font = ImageFont.load_default()
        else:
            print(f"Font path not found or not specified: {font_path}, using default")
            font = ImageFont.load_default()
    except Exception as e:
        print(f"Error in font loading: {e}, using fallback approach")
        font = None
    
    # Create a temporary image for text measurement
    temp_image = Image.new('RGB', (max_width_pixels * 2, 100))
    draw = ImageDraw.Draw(temp_image)
    
    # Get space width once
    space_width = 0
    try:
        if hasattr(draw, 'textlength'):
            space_width = draw.textlength(" ", font=font)
        elif hasattr(draw, 'textsize'):
            space_width, _ = draw.textsize(" ", font=font)
        else:
            space_width = font_size // 4  # Rough estimate
    except Exception as e:
        print(f"Error measuring space width: {e}")
        space_width = font_size // 4  # Fallback
    
    words = words_dict.get('words', [])
    if not words:
        return {'segments': []}
    
    # Pre-compute all word widths
    word_widths = {}
    for word in words:
        text = word['text'].strip()
        if text not in word_widths:
            try:
                if hasattr(draw, 'textlength'):
                    word_widths[text] = draw.textlength(text, font=font)
                elif hasattr(draw, 'textsize'):
                    width, _ = draw.textsize(text, font=font)
                    word_widths[text] = width
                else:
                    word_widths[text] = len(text) * (font_size // 2)  # Rough estimate
            except Exception as e:
                print(f"Error measuring text width for '{text}': {e}")
                word_widths[text] = len(text) * (font_size // 2)  # Fallback
    
    # Build segments with word integrity and constraints
    segments = []
    current_segment = {
        'text': '',
        'start_time': None,
        'end_time': None,
        'words': [],
        'width_pixels': 0
    }
    
    for word in words:
        word_text = word['text'].strip()
        start_time = word['start']
        end_time = word['end']
        
        # Convert times to seconds for calculation
        start_time_sec = parse_time_to_seconds(start_time) if isinstance(start_time, str) else start_time
        end_time_sec = parse_time_to_seconds(end_time) if isinstance(end_time, str) else end_time
        
        word_width = word_widths.get(word_text, 0)
        
        # Check if this is the first word in the segment
        if current_segment['start_time'] is None:
            current_segment['start_time'] = start_time
            current_segment['text'] = word_text
            current_segment['words'] = [word]
            current_segment['width_pixels'] = word_width
            current_segment['end_time'] = end_time
            continue
        
        # Calculate potential new width
        potential_width = current_segment['width_pixels'] + space_width + word_width
        
        # Check duration constraint
        current_start_sec = parse_time_to_seconds(current_segment['start_time']) if isinstance(current_segment['start_time'], str) else current_segment['start_time']
        potential_duration = end_time_sec - current_start_sec
        
        # Conditions for creating a new segment:
        # 1. Width would exceed max width
        # 2. Duration would exceed max duration 
        # 3. Word ends with end-of-sentence punctuation
        if (potential_width > max_width_pixels or 
            potential_duration > max_duration_seconds or 
            word_text[-1:] in ['.', '!', '?']):
            
            # Check if the current word alone exceeds max width
            if word_width > max_width_pixels:
                print(f"Warning: Word '{word_text}' exceeds max width ({word_width} > {max_width_pixels})")
                # Add current segment to the list if it has content
                if current_segment['text']:
                    segments.append(current_segment)
                
                # Create a new segment with just this oversized word
                # (it will be displayed even though it overflows)
                current_segment = {
                    'text': word_text,
                    'start_time': start_time,
                    'end_time': end_time,
                    'words': [word],
                    'width_pixels': word_width
                }
            else:
                # Finish current segment
                segments.append(current_segment)
                
                # Start a new segment with this word
                current_segment = {
                    'text': word_text,
                    'start_time': start_time,
                    'end_time': end_time,
                    'words': [word],
                    'width_pixels': word_width
                }
        else:
            # Add word to current segment
            current_segment['text'] += f" {word_text}"
            current_segment['words'].append(word)
            current_segment['width_pixels'] = potential_width
            current_segment['end_time'] = end_time
    
    # Add the last segment if it has content
    if current_segment['text']:
        segments.append(current_segment)
    
    # Create the final segments dictionary
    result = {'segments': []}
    
    # Format each segment for the output
    for i, segment in enumerate(segments):
        formatted_segment = {
            'index': i + 1,
            'start_time': segment['start_time'],
            'end_time': segment['end_time'],
            'text': segment['text'],
            'width_pixels': segment['width_pixels'],
            'words': segment['words']
        }
        result['segments'].append(formatted_segment)
    
    print(f"Created {len(result['segments'])} segments")
    return result

# Function to parse time in hh:mm:ss,msmsms format to total seconds
def parse_time_to_seconds(time_str):
    time_parts = time_str.split(',')
    time_base = time_parts[0]
    milliseconds = int(time_parts[1]) if len(time_parts) > 1 else 0
    
    hours, minutes, seconds = map(int, time_base.split(':'))
    total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
    return total_seconds

def process_complete_video_with_audio_rotated_extended(input_video_path, output_video_path, segments, font_path, 
                                     normal_color, text_highlight_color, bg_highlight_color, font_scale=0.1, position_ratio=(0.5, 0.1), 
                                     blur_radius=5, word_spacing=10, segment_spacing=50, bg_color=None,
                                     highlight_text=True, highlight_background=False, show_current_word_only=False):
    """
    Process the entire video with 90-degree clockwise rotation and add text segments with highlighting
    while preserving the audio track.
    
    Args:
        input_video_path: Path to the input video file
        output_video_path: Path to save the output video file
        segments: List of segment dictionaries with text, timing, and word data
        font_path: Path to the TTF font file
        normal_color: RGB or RGBA tuple for normal text color
        text_highlight_color: RGB or RGBA tuple for text highlight color
        bg_highlight_color: RGB or RGBA tuple for background highlight color
        font_scale: Font size as a ratio of the video height
        position_ratio: (x, y) tuple for position as a ratio of video dimensions
        blur_radius: Radius for the text shadow blur
        word_spacing: Spacing between words in pixels
        segment_spacing: Vertical spacing between segments in pixels
        bg_color: RGB or RGBA tuple for background color, or None for no background
        highlight_text: Whether to highlight text with a different color (boolean)
        highlight_background: Whether to highlight word backgrounds (boolean)
        show_current_word_only: Whether to show only the current word being spoken (boolean)
    """
    
    # Create a temporary directory for intermediate files
    temp_dir = None
    try:
        # Create a unique temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Temporary file for video without audio
        temp_video_path = os.path.join(temp_dir, "temp_video.mp4")
        
        # Open the video
        cap = cv2.VideoCapture(input_video_path)
        
        # Get the video properties
        frame_rate = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # When rotated 90 degrees, width and height need to be swapped
        rotated_width, rotated_height = height, width
        
        # Define codec and create VideoWriter to save the processed video
        # Note: dimensions are swapped because of 90-degree rotation
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # H.264 codec
        out = cv2.VideoWriter(temp_video_path, fourcc, frame_rate, (rotated_width, rotated_height))
        
        if not out.isOpened():
            print(f"ERROR: Could not create output video writer")
            cap.release()
            # Clean up
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            return
        
        # Process all frames
        frame_count = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Rotate frame 90 degrees clockwise
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
            
            # Get the current timestamp of the frame in seconds
            current_time = frame_count / frame_rate  # More reliable than CAP_PROP_POS_MSEC
            
            # Process the frame with the appropriate segments and word highlights
            # Pass the highlight options and separate colors and current word only option
            processed_frame = add_text_with_segments_and_color_highlights(
                frame, segments, current_time, font_path, normal_color, text_highlight_color,
                font_scale, position_ratio, blur_radius, word_spacing, segment_spacing, bg_color,
                highlight_text, highlight_background, bg_highlight_color, show_current_word_only
            )
            
            # Write the processed frame
            out.write(processed_frame)
            
            # Increment the frame counter
            frame_count += 1
            
            # Print progress
            if frame_count % 100 == 0:
                progress = (frame_count / total_frames) * 100
                print(f"Progress: {progress:.1f}% ({frame_count}/{total_frames} frames)")
        
        # Release the video objects
        cap.release()
        out.release()
        
        print(f"Processed {frame_count} frames. Now merging with audio...")
        
        # Use FFmpeg to merge the processed video with the audio from the original video
        print("Merging video with audio using FFmpeg...")
        
        # Add error log file
        error_log = os.path.join(temp_dir, "ffmpeg_error.log")
        
        command = [
            'ffmpeg',
            '-y',               # Overwrite output file if it exists
            '-i', temp_video_path,  # Processed video without audio
            '-i', input_video_path,  # Original video with audio
            '-c:v', 'copy',     # Copy the video stream as is
            '-c:a', 'aac',      # Use AAC codec for audio
            '-map', '0:v:0',    # Use video from the first input
            '-map', '1:a:0',    # Use audio from the second input
            '-shortest',        # End when the shortest input ends
            output_video_path   # Output file
        ]
        
        # Run the FFmpeg command
        try:
            # Set a timeout and redirect stderr to a log file
            with open(error_log, 'w') as f_err:
                process = subprocess.run(
                    command, 
                    stdout=subprocess.PIPE, 
                    stderr=f_err,
                    timeout=300,  # 5-minute timeout
                    text=True
                )
            print(f"Successfully merged video and audio. Output saved as {output_video_path}")
        except Exception as e:
            print(f"Error with ffmpeg: {e}")
            # Fallback to copying the video without audio
            print("Could not preserve audio. Saving video without audio.")
            shutil.copy(temp_video_path, output_video_path)
            
        # Clean up
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"Warning: Could not clean up temporary directory: {e}")
            
    except Exception as e:
        print(f"Error in video processing: {e}")
        import traceback
        traceback.print_exc()
        # Make sure to clean up
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

# New function to process segment dictionary
def process_segment_dict(segment_dict):
    """
    Process a dictionary of segments to the format needed for processing
    
    Args:
        segment_dict (dict): Dictionary with 'segments' key containing segment data
        
    Returns:
        list: A list of segment dictionaries with text, start_time, and end_time
    """
    segments = []
    
    for segment in segment_dict['segments']:
        start_time = parse_time_to_seconds(segment['start_time'])
        end_time = parse_time_to_seconds(segment['end_time'])
        
        # Create the segment
        processed_segment = {
            'text': segment['text'],
            'start_time': start_time,
            'end_time': end_time,
            'words': []  # Will be filled in by the word processor
        }
        
        segments.append(processed_segment)
    
    return segments

# New function to process word dictionary and match to segments
def process_word_dict(word_dict, segments):
    """
    Process a dictionary of words and match them to segments
    
    Args:
        word_dict (dict): Dictionary with 'words' key containing word data
        segments (list): List of segment dictionaries to add words to
        
    Returns:
        list: Updated list of segment dictionaries with words added
    """
    words_data = []
    
    # First, extract all word data from the dictionary
    for word in word_dict['words']:
        start_time = parse_time_to_seconds(word['start'])
        end_time = parse_time_to_seconds(word['end'])
        
        # Add the word data
        words_data.append({
            'text': word['text'],
            'start_time': start_time,
            'end_time': end_time
        })
    
    # Now match words to segments based on timing
    for segment in segments:
        segment_start = segment['start_time']
        segment_end = segment['end_time']
        segment_words = []
        
        # Find all words that belong to this segment
        for word in words_data:
            word_start = word['start_time']
            word_end = word['end_time']
            
            # Word belongs to segment if its timing overlaps with the segment
            if (word_start >= segment_start and word_start < segment_end) or \
               (word_end > segment_start and word_end <= segment_end) or \
               (word_start <= segment_start and word_end >= segment_end):
                segment_words.append(word)
        
        # Sort words by start time
        segment_words.sort(key=lambda w: w['start_time'])
        
        # Add words to segment
        segment['words'] = segment_words
    
    return segments

# Function to ensure segment text matches its words
def reconcile_segment_text_with_words(segments):
    """
    Ensure that each segment's text matches the words it contains, 
    or update the words to match spell-corrected text.
    
    Args:
        segments (list): List of segment dictionaries with words
        
    Returns:
        list: Updated segments with reconciled text
    """
    for segment in segments:
        if segment['words']:
            # Check if the segment text was spell-corrected
            segment_text = segment['text']
            words_text = ' '.join([word['text'] for word in segment['words']])
            
            # If segment text and words don't match, this suggests spelling correction was applied
            if segment_text != words_text:
                print(f"Detected spell-corrected text: '{segment_text}' (was: '{words_text}')")
                
                # We could update the individual words to match the corrected text
                # But this is complex and might not be worth it
                # For now, just update the segment text to match the words
                # to ensure timing stays correct
                segment['text'] = words_text
                
                # Alternatively, we could try to map corrected words to original words,
                # but this requires more complex text difference analysis
    
    return segments

# Updated text processing function with current word only option
def add_text_with_segments_and_color_highlights(image, segments, current_time, font_path, 
                                                normal_color, text_highlight_color, font_scale=0.1,
                                                position_ratio=(0.5, 0.8), blur_radius=5, 
                                                word_spacing=10, segment_spacing=50, bg_color=None,
                                                highlight_text=True, highlight_background=False,
                                                bg_highlight_color=None, show_current_word_only=False):
        """
        Add text to an image with segments and highlighting based on the specified options.
        Modified to strictly enforce one segment at a time.
        """
        # If bg_highlight_color is not provided, use text_highlight_color
        if bg_highlight_color is None:
            bg_highlight_color = text_highlight_color
            
        # Convert to RGBA
        image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB)).convert("RGBA")
        width, height = image.size
        
        # Calculate font size
        font_size = int(height * font_scale)
        font = ImageFont.truetype(font_path, font_size)
        
        # Create a layer for the shadows
        shadow_layer = Image.new("RGBA", image.size, (255, 255, 255, 0))
        shadow_draw = ImageDraw.Draw(shadow_layer)
        
        # Create a layer for the text
        text_layer = Image.new("RGBA", image.size, (255, 255, 255, 0))
        draw_text = ImageDraw.Draw(text_layer)
        
        # Create a layer for the background (if needed)
        bg_layer = Image.new("RGBA", image.size, (255, 255, 255, 0))
        draw_bg = ImageDraw.Draw(bg_layer)
        
        # Create a layer for highlighted word backgrounds (only used when highlight_background is True)
        highlight_bg_layer = Image.new("RGBA", image.size, (255, 255, 255, 0))
        highlight_bg_draw = ImageDraw.Draw(highlight_bg_layer)
        
        # Get horizontal and vertical position
        horizontal_ratio, vertical_ratio = position_ratio
        
        # Starting y position
        base_y_position = int(height * vertical_ratio)
        
        # Function to draw a rounded rectangle
        def draw_rounded_rectangle(draw, coords, radius, color):
            x1, y1, x2, y2 = coords
            diameter = radius * 2
            
            # Draw the main rectangle
            draw.rectangle([x1+radius, y1, x2-radius, y2], fill=color)
            draw.rectangle([x1, y1+radius, x2, y2-radius], fill=color)
            
            # Draw the four corner circles
            draw.ellipse([x1, y1, x1+diameter, y1+diameter], fill=color)  # Top left
            draw.ellipse([x2-diameter, y1, x2, y1+diameter], fill=color)  # Top right
            draw.ellipse([x1, y2-diameter, x1+diameter, y2], fill=color)  # Bottom left
            draw.ellipse([x2-diameter, y2-diameter, x2, y2], fill=color)  # Bottom right
        
        # *** CRITICAL MODIFICATION: Find ONLY the current active segment ***
        active_segment = None
        
        # First, strictly find the ONE current segment that should be displayed
        for segment_idx, segment in enumerate(segments):
            segment_start = segment['start_time']
            segment_end = segment['end_time']
            
            # If this segment is active right now, use it (strict time range check)
            if segment_start <= current_time < segment_end:
                active_segment = segment
                active_segment_idx = segment_idx
                break  # Only use the first active segment we find
        
        # If we didn't find an active segment, don't display anything
        if not active_segment:
            # Just return the original image without any text
            result_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            return result_image
            
        # For "current word only" mode, find the single active word in the active segment
        if show_current_word_only:
            # Keep track of the active word
            active_word = None
            
            # Search for the currently active word in the active segment
            segment_words = active_segment['words']
            
            # Skip if no words
            if segment_words:
                # Check each word to see if it's currently active
                for word_data in segment_words:
                    if word_data['start_time'] <= current_time < word_data['end_time']:
                        active_word = word_data
                        break
                        
            # If we found an active word, draw it
            if active_word:
                # Get text height
                text_height = font.getbbox('Aj')[3]  # Use characters with ascenders and descenders
                
                # Calculate word width
                word_text = active_word['text']
                bbox = font.getbbox(word_text)
                word_width = bbox[2] - bbox[0]
                
                # Calculate the x position (centered)
                x_position = int(width * horizontal_ratio) - (word_width // 2)
                y_position = base_y_position
                
                # Calculate padding and background dimensions
                h_padding = int(font_size * 0.5)  # Horizontal padding
                v_padding = int(font_size * 0.3)  # Vertical padding
                
                # Word position
                word_position = (x_position, y_position)
                
                # Draw the word on the shadow layer (always black)
                shadow_draw.text(word_position, word_text, font=font, fill=(0, 0, 0))
                
                # For background highlight, draw the rectangle
                if highlight_background:
                    # Calculate the background for the word
                    word_bg_left = x_position - int(font_size * 0.2)
                    word_bg_top = y_position - int(font_size * 0.2)
                    word_bg_right = x_position + word_width + int(font_size * 0.2)
                    word_bg_bottom = y_position + text_height + int(font_size * 0.2)
                    
                    # Make sure we have RGBA format for highlight color
                    if bg_highlight_color is not None:
                        if len(bg_highlight_color) == 3:
                            highlight_bg_color = (bg_highlight_color[0], bg_highlight_color[1], bg_highlight_color[2], 220)
                        else:
                            highlight_bg_color = bg_highlight_color
                            
                        # Draw the highlight background with rounded corners
                        draw_rounded_rectangle(
                            highlight_bg_draw,
                            (word_bg_left, word_bg_top, word_bg_right, word_bg_bottom),
                            int(font_size * 0.15),  # Smaller corner radius
                            highlight_bg_color
                        )
                
                # Calculate background dimensions for the word
                bg_left = x_position - h_padding
                bg_top = y_position - v_padding
                bg_right = x_position + word_width + h_padding
                bg_bottom = y_position + text_height + v_padding
                
                # If using a background, draw it
                if bg_color is not None:
                    corner_radius = int(font_size * 0.3)  # Adjust for desired roundness
                    
                    # Make sure we have RGBA format
                    if len(bg_color) == 3:
                        # Convert RGB to RGBA by adding alpha of 180
                        actual_bg_color = (bg_color[0], bg_color[1], bg_color[2], 180)
                    else:
                        actual_bg_color = bg_color
                    
                    # Draw the background
                    draw_rounded_rectangle(
                        draw_bg, 
                        (bg_left, bg_top, bg_right, bg_bottom), 
                        corner_radius, 
                        actual_bg_color
                    )
                
                # Determine text color based on settings
                if highlight_text:
                    # Use highlight color for text
                    text_color = text_highlight_color[:3] if text_highlight_color and len(text_highlight_color) >= 3 else (255, 255, 0)
                else:
                    # Use normal text color
                    text_color = normal_color[:3] if normal_color and len(normal_color) >= 3 else (255, 255, 255)
                
                # Draw the word on the text layer
                draw_text.text(word_position, word_text, font=font, fill=text_color)
        else:
            # Process the active segment with all words (only one segment)
            segment = active_segment
            segment_words = segment['words']
            
            # Skip if no words are available
            if not segment_words:
                result_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                return result_image
            
            # Calculate width and height of each word
            word_widths = []
            for word_data in segment_words:
                bbox = font.getbbox(word_data['text'])
                width_of_word = bbox[2] - bbox[0]
                word_widths.append(width_of_word)
            
            # Calculate the total width of all words with spacing
            total_segment_width = sum(word_widths) + word_spacing * (len(segment_words) - 1)
            
            # Calculate the starting x position based on horizontal_ratio
            start_x = int(width * horizontal_ratio) - (total_segment_width // 2)
            
            # Get text height
            text_height = font.getbbox('Aj')[3]  # Use characters with ascenders and descenders
            
            # Calculate padding and background dimensions
            h_padding = int(font_size * 0.5)  # Horizontal padding
            v_padding = int(font_size * 0.3)  # Vertical padding
            
            # Background rectangle coordinates
            bg_left = start_x - h_padding
            bg_top = base_y_position - v_padding
            bg_right = start_x + total_segment_width + h_padding
            bg_bottom = base_y_position + text_height + v_padding
            
            # Ensure background stays within image bounds
            min_margin = int(width * 0.01)
            if bg_left < min_margin:
                # Shift background and text right
                offset = min_margin - bg_left
                bg_left += offset
                bg_right += offset
                start_x += offset
            
            if bg_right > width - min_margin:
                # Shift background and text left
                offset = bg_right - (width - min_margin)
                bg_left -= offset
                bg_right -= offset
                start_x -= offset
            
            # Draw background rectangle with rounded corners if bg_color is provided
            if bg_color is not None:
                corner_radius = int(font_size * 0.3)  # Adjust for desired roundness
                
                # Make sure we have RGBA format
                if len(bg_color) == 3:
                    # Convert RGB to RGBA by adding alpha of 180
                    actual_bg_color = (bg_color[0], bg_color[1], bg_color[2], 180)
                else:
                    actual_bg_color = bg_color
                
                # Draw the background
                draw_rounded_rectangle(
                    draw_bg, 
                    (bg_left, bg_top, bg_right, bg_bottom), 
                    corner_radius, 
                    actual_bg_color
                )
            
            # Current x position
            current_x = start_x
            
            # Process each word in the segment
            for i, word_data in enumerate(segment_words):
                # Current word's width
                word_width = word_widths[i]
                word_text = word_data['text']
                
                # Position for the text
                word_position = (current_x, base_y_position)
                
                # Determine if this word is highlighted (currently playing)
                is_highlighted = word_data['start_time'] <= current_time < word_data['end_time']
                
                # Draw the word on the shadow layer (always black)
                shadow_draw.text(word_position, word_text, font=font, fill=(0, 0, 0))
                
                # For background highlighting, draw highlight background for highlighted words
                if highlight_background and is_highlighted:
                    # Calculate the background for this specific word
                    word_bg_left = current_x - int(font_size * 0.2)
                    word_bg_top = base_y_position - int(font_size * 0.2)
                    word_bg_right = current_x + word_width + int(font_size * 0.2)
                    word_bg_bottom = base_y_position + text_height + int(font_size * 0.2)
                    
                    # Make sure we have RGBA format for highlight color
                    if bg_highlight_color is not None:
                        if len(bg_highlight_color) == 3:
                            highlight_bg_color = (bg_highlight_color[0], bg_highlight_color[1], bg_highlight_color[2], 220)
                        else:
                            highlight_bg_color = bg_highlight_color
                        
                        # Draw the highlight background with rounded corners
                        draw_rounded_rectangle(
                            highlight_bg_draw,
                            (word_bg_left, word_bg_top, word_bg_right, word_bg_bottom),
                            int(font_size * 0.15),  # Smaller corner radius
                            highlight_bg_color
                        )
                
                # Determine text color based on highlighting options
                if highlight_text and is_highlighted:
                    # For text highlighting: Use text highlight color for highlighted words
                    text_color = text_highlight_color[:3] if text_highlight_color and len(text_highlight_color) >= 3 else (255, 255, 0)
                else:
                    # Use normal text color for non-highlighted words or if text highlighting is disabled
                    text_color = normal_color[:3] if normal_color and len(normal_color) >= 3 else (255, 255, 255)
                
                # Draw the actual word on the text layer with the appropriate color
                draw_text.text(word_position, word_text, font=font, fill=text_color)
                
                # Update the current_x for the next word
                current_x += word_width + word_spacing
        
        # Apply Gaussian blur to the shadow
        blurred_shadow = shadow_layer.filter(ImageFilter.GaussianBlur(blur_radius))
        
        # Composite the layers in the correct order
        result = image
        
        # Only add background if bg_color is provided
        if bg_color is not None:
            result = Image.alpha_composite(result, bg_layer)  # Add background
        
        # Add highlight background layer (only visible when highlight_background is True)
        result = Image.alpha_composite(result, highlight_bg_layer)
        
        result = Image.alpha_composite(result, blurred_shadow)
        result = Image.alpha_composite(result, text_layer)
        
        # Convert the image back to BGR (for OpenCV compatibility)
        result_image = cv2.cvtColor(np.array(result), cv2.COLOR_RGB2BGR)
        
        return result_image


# Function to process entire video with audio preservation - with rotation
def process_complete_video_with_audio_rotated(input_video_path, output_video_path, segments, font_path, 
                                     normal_color, highlight_color, font_scale=0.1, position_ratio=(0.5, 0.1), 
                                     blur_radius=5, word_spacing=10, segment_spacing=50, bg_color=None,
                                     highlight_text=True, highlight_background=False):
    """
    Process the entire video with 90-degree clockwise rotation and add text segments with highlighting
    while preserving the audio track.
    
    Args:
        input_video_path: Path to the input video file
        output_video_path: Path to save the output video file
        segments: List of segment dictionaries with text, timing, and word data
        font_path: Path to the TTF font file
        normal_color: RGB or RGBA tuple for normal text color
        highlight_color: RGB or RGBA tuple for highlighted text/background color
        font_scale: Font size as a ratio of the video height
        position_ratio: (x, y) tuple for position as a ratio of video dimensions
        blur_radius: Radius for the text shadow blur
        word_spacing: Spacing between words in pixels
        segment_spacing: Vertical spacing between segments in pixels
        bg_color: RGB or RGBA tuple for background color, or None for no background
        highlight_text: Whether to highlight text with a different color (boolean)
        highlight_background: Whether to highlight word backgrounds (boolean)
    """
    # Create a temporary directory for intermediate files
    temp_dir = None
    try:
        # Create a unique temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Temporary file for video without audio
        temp_video_path = os.path.join(temp_dir, "temp_video.mp4")
        
        # Open the video
        cap = cv2.VideoCapture(input_video_path)
        
        # Get the video properties
        frame_rate = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # When rotated 90 degrees, width and height need to be swapped
        rotated_width, rotated_height = height, width
        
        # Define codec and create VideoWriter to save the processed video
        # Note: dimensions are swapped because of 90-degree rotation
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # H.264 codec
        out = cv2.VideoWriter(temp_video_path, fourcc, frame_rate, (rotated_width, rotated_height))
        
        if not out.isOpened():
            print(f"ERROR: Could not create output video writer")
            cap.release()
            # Clean up
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            return
        
        # Process all frames
        frame_count = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Rotate frame 90 degrees clockwise
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
            
            # Get the current timestamp of the frame in seconds
            current_time = frame_count / frame_rate  # More reliable than CAP_PROP_POS_MSEC
            
            # Process the frame with the appropriate segments and word highlights
            # Now passing the highlight options
            processed_frame = add_text_with_segments_and_color_highlights(
                frame, segments, current_time, font_path, normal_color, highlight_color,
                font_scale, position_ratio, blur_radius, word_spacing, segment_spacing, bg_color,
                highlight_text, highlight_background
            )
            
            # Write the processed frame
            out.write(processed_frame)
            
            # Increment the frame counter
            frame_count += 1
            
            # Print progress
            if frame_count % 100 == 0:
                progress = (frame_count / total_frames) * 100
                print(f"Progress: {progress:.1f}% ({frame_count}/{total_frames} frames)")
        
        # Release the video objects
        cap.release()
        out.release()
        
        print(f"Processed {frame_count} frames. Now merging with audio...")
        
        # Use FFmpeg to merge the processed video with the audio from the original video
        print("Merging video with audio using FFmpeg...")
        
        # Add error log file
        error_log = os.path.join(temp_dir, "ffmpeg_error.log")
        
        command = [
            'ffmpeg',
            '-y',               # Overwrite output file if it exists
            '-i', temp_video_path,  # Processed video without audio
            '-i', input_video_path,  # Original video with audio
            '-c:v', 'copy',     # Copy the video stream as is
            '-c:a', 'aac',      # Use AAC codec for audio
            '-map', '0:v:0',    # Use video from the first input
            '-map', '1:a:0',    # Use audio from the second input
            '-shortest',        # End when the shortest input ends
            output_video_path   # Output file
        ]
        
        # Run the FFmpeg command with proper timeout and pipe handling
        try:
            # Set a timeout and redirect stderr to a log file
            with open(error_log, 'w') as f_err:
                process = subprocess.run(
                    command, 
                    stdout=subprocess.PIPE, 
                    stderr=f_err,
                    timeout=300,  # 5-minute timeout
                    text=True
                )
            print(f"Successfully merged video and audio. Output saved as {output_video_path}")
        except subprocess.TimeoutExpired:
            print("FFmpeg process timed out after 5 minutes. Trying alternative method...")
            # Try to terminate the process if it's still running
            try:
                process.terminate()
            except:
                pass
            
            # Alternative method
            try:
                command_alt = [
                    'ffmpeg',
                    '-y',
                    '-i', temp_video_path,
                    '-i', input_video_path,
                    '-c:v', 'copy',
                    '-c:a', 'copy',
                    '-map', '0:v:0',
                    '-map', '1:a:0?',  # The ? makes the audio stream optional
                    output_video_path
                ]
                
                with open(error_log, 'w') as f_err:
                    alt_process = subprocess.run(
                        command_alt, 
                        stdout=subprocess.PIPE, 
                        stderr=f_err,
                        timeout=300,  # 5-minute timeout
                        text=True
                    )
                print(f"Successfully merged video and audio using alternative method. Output saved as {output_video_path}")
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e2:
                print(f"Error with alternative method: {e2}")
                print("Could not preserve audio. Saving video without audio.")
                
                # Just copy the processed video without audio as a last resort
                shutil.copy(temp_video_path, output_video_path)
        except subprocess.CalledProcessError as e:
            print(f"Error merging video and audio: {e}")
            
            # Proceed to alternative method (same as in timeout case)
            try:
                command_alt = [
                    'ffmpeg',
                    '-y',
                    '-i', temp_video_path,
                    '-i', input_video_path,
                    '-c:v', 'copy',
                    '-c:a', 'copy',
                    '-map', '0:v:0',
                    '-map', '1:a:0?',  # The ? makes the audio stream optional
                    output_video_path
                ]
                
                with open(error_log, 'w') as f_err:
                    alt_process = subprocess.run(
                        command_alt, 
                        stdout=subprocess.PIPE, 
                        stderr=f_err,
                        timeout=300,
                        text=True
                    )
                print(f"Successfully merged video and audio using alternative method. Output saved as {output_video_path}")
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e2:
                print(f"Error with alternative method: {e2}")
                print("Could not preserve audio. Saving video without audio.")
                
                # Just copy the processed video without audio as a last resort
                shutil.copy(temp_video_path, output_video_path)
            
        # Clean up
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"Warning: Could not clean up temporary directory: {e}")
            
    except Exception as e:
        print(f"Error in video processing: {e}")
        import traceback
        traceback.print_exc()
        # Make sure to clean up
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

# New function to process a single video using dictionaries
def process_single_video_with_dicts(input_video_path, segments_dict, words_dict, output_video_path, 
                        font_path, normal_color, highlight_color, font_scale=0.03, 
                        position_ratio=(0.5, 0.8), blur_radius=2, 
                        word_spacing=10, segment_spacing=50, bg_color=None,
                        highlight_text=True, highlight_background=False):
    """
    Process a single video with segment and word dictionaries
    
    Args:
        input_video_path: Path to the input video file
        segments_dict: Dictionary with segments data
        words_dict: Dictionary with words data
        output_video_path: Path to save the output video file
        font_path: Path to the TTF font file
        normal_color: RGB or RGBA tuple for normal text color
        highlight_color: RGB or RGBA tuple for highlighted text/background color
        font_scale: Font size as a ratio of the video height
        position_ratio: (x, y) tuple for position as a ratio of video dimensions
                       - x: horizontal position (0.0 to 1.0, where 0.5 is center)
                       - y: vertical position (0.0 to 1.0, where 0.0 is top)
        blur_radius: Radius for the text shadow blur
        word_spacing: Spacing between words in pixels
        segment_spacing: Vertical spacing between segments in pixels
        bg_color: RGB or RGBA tuple for background color, or None for no background
        highlight_text: Whether to highlight text with a different color (boolean)
        highlight_background: Whether to highlight word backgrounds (boolean)
    """
    print(f"Processing video: {input_video_path}")
    print(f"Highlight text: {highlight_text}")
    print(f"Highlight background: {highlight_background}")
    
    try:
        # Check if input video exists
        if not os.path.exists(input_video_path):
            print(f"Error: Input video not found: {input_video_path}")
            return
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_video_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # Process the dictionaries
        print("Processing dictionaries...")
        segments = process_segment_dict(segments_dict)
        segments = process_word_dict(words_dict, segments)
        
        # After spell checking, we need to reconcile text and words
        # This ensures that the segment text matches the words it contains, even after spell correction
        segments = reconcile_segment_text_with_words(segments)
        
        # Process the video with rotation - pass all parameters including highlight options
        process_complete_video_with_audio_rotated(
            input_video_path, output_video_path, segments, font_path, 
            normal_color, highlight_color, font_scale, position_ratio,
            blur_radius, word_spacing, segment_spacing, bg_color,
            highlight_text, highlight_background
        )
        
        print(f"Completed processing: {output_video_path}")
        
    except Exception as e:
        print(f"Error processing video {input_video_path}: {e}")
        import traceback
        traceback.print_exc()

# Function to process multiple videos using dictionaries
def process_multiple_videos_with_dicts(video_files, segments_dicts, words_dicts, output_files, 
                          font_path, normal_color, highlight_color, font_scale=0.03, 
                          position_ratio=(0.5, 0.6), blur_radius=2, 
                          word_spacing=10, segment_spacing=50):
    """
    Process multiple videos with dictionaries
    
    Args:
        video_files: List of paths to input video files
        segments_dicts: List of segment dictionaries
        words_dicts: List of word dictionaries
        output_files: List of paths to save output video files
        font_path: Path to the TTF font file
        normal_color: RGB or RGBA tuple for normal text color
        highlight_color: RGB or RGBA tuple for highlighted text color
        font_scale: Font size as a ratio of the video height
        position_ratio: (x, y) tuple for position as a ratio of video dimensions
        blur_radius: Radius for the text shadow blur
        word_spacing: Spacing between words in pixels
        segment_spacing: Vertical spacing between segments in pixels
    """
    print(f"Processing {len(video_files)} videos")
    
    # Check that all lists have the same length
    if not (len(video_files) == len(segments_dicts) == len(words_dicts) == len(output_files)):
        print("Error: All input lists must have the same length")
        return
    
    # Process each video
    for i, (video_file, segments_dict, words_dict, output_file) in enumerate(
            zip(video_files, segments_dicts, words_dicts, output_files)):
        print(f"\nProcessing video {i+1}/{len(video_files)}: {video_file}")
        
        process_single_video_with_dicts(
            video_file, segments_dict, words_dict, output_file,
            font_path, normal_color, highlight_color, font_scale,
            position_ratio, blur_radius, word_spacing, segment_spacing
        )


def process_media_for_gui(
    transcribe_only,
    path,
    font_path,
    text_color,
    text_highlight_color,
    bg_highlight_color,
    word_spacing,
    segment_spacing,
    font_scale,
    position_ratio,
    blur_radius,
    max_duration_seconds,
    max_chars,
    bg_color=None,
    highlight_text=True,
    highlight_background=False,
    show_current_word_only=False
):
    """
    Process media file to create either transcript or captions.
    This is the main entry point for the GUI application.
    
    Args:
        transcribe_only (bool): If True, only create transcript. If False, create captions.
        path (str): Path to the input media file
        font_path (str): Path to the font file
        text_color (tuple): RGBA values for text color
        text_highlight_color (tuple): RGBA values for text highlight color
        bg_highlight_color (tuple): RGBA values for background highlight color
        word_spacing (int): Space between words
        segment_spacing (int): Space between segments
        font_scale (float): Scale factor for font size
        position_ratio (tuple): Horizontal and vertical position ratio (0.0 to 1.0)
        blur_radius (int): Blur radius for background
        max_duration_seconds (float): Maximum duration in seconds for segment
        max_chars (int): Maximum characters per segment
        bg_color (tuple): RGBA values for background color, or None for transparent
        highlight_text (bool): Enable text highlighting (color change)
        highlight_background (bool): Enable background highlighting (colored rectangle)
        show_current_word_only (bool): Show only the current word being spoken
        
    Returns:
        str: Path to the output file
    """
    logger.info(f"Processing media: {path}")
    try:
        # Create output filename based on current date/time
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(path)
        name, ext = os.path.splitext(filename)
        
        # Create output directory if needed
        output_dir = os.path.join(os.path.dirname(path), "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # Extract audio from media file
        print("Extracting audio...")
        audio_path = extract_audio(path)
        
        # Transcribe audio
        print("Transcribing audio...")
        transcription = transcribe_audio(audio_path)
        
        # Create word timestamps
        print("Processing word timestamps...")
        words = create_word_timestamps(transcription)
        
        # Determine output path and type
        if transcribe_only:
            # Create transcript output path
            output_path = os.path.join(output_dir, f"{name}_{timestamp}_transcript.txt")
            
            # Write transcription to file
            with open(output_path, 'w', encoding='utf-8') as f:
                try:
                    f.write(transcription['text'])
                except Exception as e:
                    logging.error(f"Error when writing to file: {e}", exc_info=True)

            # Also save word timestamps to a JSON file
            words_json_path = os.path.join(output_dir, f"{name}_{timestamp}_words.json")
            with open(words_json_path, 'w', encoding='utf-8') as f:
                json.dump(words, f, indent=2)
                
            print(f"Transcript saved to: {output_path}")
            print(f"Word timestamps saved to: {words_json_path}")
        else:
            # Create captions output path
            output_path = os.path.join(output_dir, f"{name}_{timestamp}_captioned{ext}")
            
            # Get video dimensions to calculate maximum caption width
            cap = cv2.VideoCapture(path)
            orig_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            orig_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            
            # After 90-degree clockwise rotation:
            # - Original width becomes the new height
            # - Original height becomes the new width
            rotated_width = orig_height
            rotated_height = orig_width
            
            # Calculate maximum caption width (80% of rotated width)
            max_caption_width_pixels = int(rotated_width * 0.8)
            
            # Estimate font size based on video dimensions and font scale
            # For accurate measurement, use the new height (original width) of the rotated video
            estimated_font_size = int(rotated_height * font_scale)
            
            print(f"Original video dimensions: {orig_width}x{orig_height}")
            print(f"Rotated dimensions: {rotated_width}x{rotated_height}")
            print(f"Maximum caption width: {max_caption_width_pixels} pixels")
            print(f"Estimated font size: {estimated_font_size} pixels")
            print(f"Highlight text: {highlight_text}")
            print(f"Highlight background: {highlight_background}")
            print(f"Show current word only: {show_current_word_only}")
            
            # Create word segments with pixel width constraint
            print("Creating word segments...")
            
            # Use width-based segmentation
            segments = create_word_segments_with_max_width(
                words,
                max_width_pixels=max_caption_width_pixels,
                font_path=font_path,
                font_size=estimated_font_size,
                max_duration_seconds=max_duration_seconds
            )
            
            # Also save segments to a JSON file
            segments_json_path = os.path.join(output_dir, f"{name}_{timestamp}_segments.json")
            with open(segments_json_path, 'w', encoding='utf-8') as f:
                json.dump(segments, f, indent=2)
            
            # Process video with captions - pass highlight options
            print("Processing video with captions...")
            
            # Define an extended process_single_video_with_dicts function that passes our highlight options
            def process_single_video_with_dicts_extended(input_video_path, segments_dict, words_dict, output_video_path, 
                        font_path, normal_color, text_highlight_color, bg_highlight_color, font_scale=0.03, 
                        position_ratio=(0.5, 0.8), blur_radius=2, 
                        word_spacing=10, segment_spacing=50, bg_color=None,
                        highlight_text=True, highlight_background=False, show_current_word_only=False):
                """
                Extended version of process_single_video_with_dicts that handles edited transcripts.
                Uses only the edited transcription for captioning.
                """
                print(f"Processing video: {input_video_path}")
                print(f"Highlight text: {highlight_text}")
                print(f"Highlight background: {highlight_background}")
                print(f"Show current word only: {show_current_word_only}")
                
                try:
                    # Import media processing functions here (deferred import)
                    from core.media_processer import process_segment_dict, process_complete_video_with_audio_rotated_extended
                    
                    # Check if input video exists
                    if not os.path.exists(input_video_path):
                        print(f"Error: Input video not found: {input_video_path}")
                        return
                    
                    # Ensure output directory exists
                    output_dir = os.path.dirname(output_video_path)
                    if output_dir and not os.path.exists(output_dir):
                        os.makedirs(output_dir, exist_ok=True)
                    
                    # Process the dictionaries
                    print("Processing dictionaries...")
                    
                    # Reconcile edited text with original timings
                    # This will ensure the edited text gets proper timing info from original words
                    reconciled_segments = reconcile_edited_text_with_timings(segments_dict, words_dict)
                    
                    # Process the segment dictionary to get the formatted segments
                    # This is the only data we need - no need to process words from the original
                    segments = process_segment_dict(reconciled_segments)
                    
                    # We skip the process_word_dict step which would merge in original words
                    # This ensures we ONLY use the edited text
                    
                    # Call the video processing function with all parameters
                    process_complete_video_with_audio_rotated_extended(
                        input_video_path, output_video_path, segments, font_path, 
                        normal_color, text_highlight_color, bg_highlight_color, font_scale, position_ratio,
                        blur_radius, word_spacing, segment_spacing, bg_color,
                        highlight_text, highlight_background, show_current_word_only
                    )
                    
                    print(f"Completed processing: {output_video_path}")
                    
                except Exception as e:
                    print(f"Error processing video {input_video_path}: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Use our extended function with highlight options and separate colors
            process_single_video_with_dicts_extended(
                path, segments, words, output_path,
                font_path, text_color, text_highlight_color, bg_highlight_color, font_scale,
                position_ratio, blur_radius, word_spacing, segment_spacing, bg_color,
                highlight_text, highlight_background, show_current_word_only
            )
            
            print(f"Captioned video saved to: {output_path}")
            print(f"Word timestamps saved to: {segments_json_path}")
            
    except Exception as e:
        logger.error(f"Error processing media: {e}", exc_info=True)
        raise
    
    return output_path



def extract_full_transcript(segments_dict=None, words_dict=None):
    """
    Extract the full transcript text from either segments or words.
    
    Args:
        segments_dict: Dictionary containing segment data (optional)
        words_dict: Dictionary containing word data (optional)
        
    Returns:
        str: The full transcript text
    """
    if segments_dict:
        # Extract from segments
        full_text = ""
        for segment in segments_dict.get('segments', []):
            segment_text = segment.get('text', '').strip()
            if segment_text:
                full_text += segment_text + " "
        return full_text.strip()
    
    elif words_dict:
        # Extract from words
        words = []
        for word in words_dict.get('words', []):
            word_text = word.get('text', '').strip()
            if word_text:
                words.append(word_text)
        return " ".join(words)
    
    else:
        return ""