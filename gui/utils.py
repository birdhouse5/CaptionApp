# gui/utils.py
import os
from pathlib import Path
from core.media_processer import parse_time_to_seconds, format_srt_timestamp


def map_color_to_rgb(color_choice):
    """
    Maps color selection to RGB tuple (no alpha).
    
    Args:
        color_choice: String color name
        
    Returns:
        tuple: RGB values as (R, G, B)
    """
    # Direct mapping of color names to RGB values (no alpha)
    color_map = {
        # Logo colors
        'Purple': (217, 210, 233, 255),  # #d9d2e9
        'Green': (155, 187, 89, 255),    # #9bbb59
        'Orange': (248, 201, 84, 255),   # #f8c954
        
        # Supporting & print colors
        'Red': (254, 105, 110, 255),     # #fe696e
        'Pink': (248, 120, 205, 255),    # #f878cd
        'Light Blue': (96, 180, 200, 255), # #60b4c8
        'Dark Blue': (11, 99, 128, 255), # #0b6380
        'Olive': (139, 168, 70, 255),    # #8ba846
        'Yellow': (199, 200, 4, 255),    # #c7c804
        'Sand': (248, 201, 84, 255),     # #f8c954
        
        # Basic colors
        'White': (255, 255, 255, 255),
        'Black': (0, 0, 0, 255),
        'None': None  # Special case for transparent
    }
    
    # Return the RGB tuple
    if color_choice == 'None':
        return None  # Special case for transparent background
    
    if color_choice in color_map:
        return color_map[color_choice]
    else:
        return (255, 255, 255, 255)  # Default to white
    

def get_fonts_directory():
    """
    Get the path to the fonts directory.
    
    Returns:
        Path: Path object pointing to the fonts directory
    """
    # Root directory - 2 levels up from the utils.py file location
    root_dir = Path(__file__).parent.parent
    fonts_dir = os.path.join(root_dir, 'resources', 'fonts')
    
    # Make sure the fonts directory exists
    os.makedirs(fonts_dir, exist_ok=True)
    
    return fonts_dir

def get_available_fonts():
    """
    Scan the fonts directory and return a list of available fonts.
    
    Returns:
        list: List of dictionaries with font display names and file paths
    """
    fonts_dir = get_fonts_directory()
    
    # Font file extensions to look for
    font_extensions = ['.ttf', '.otf', '.TTF', '.OTF']
    
    available_fonts = []
    
    try:
        for file in os.listdir(fonts_dir):
            # Check if the file is a font file
            file_path = os.path.join(fonts_dir, file)
            if os.path.isfile(file_path):
                name, ext = os.path.splitext(file)
                if ext in font_extensions:
                    # Create a display name (remove underscores, capitalize)
                    display_name = name.replace('_', ' ').replace('-', ' ')
                    
                    # Add to the list
                    available_fonts.append({
                        'name': display_name,
                        'file_path': file_path,
                        'file_name': file
                    })
    except Exception as e:
        print(f"Error scanning fonts directory: {e}")
    
    # If no fonts were found, add a default
    if not available_fonts:
        default_font_path = os.path.join(fonts_dir, "default.ttf")
        available_fonts.append({
            'name': 'Default',
            'file_path': default_font_path,
            'file_name': 'default.ttf'
        })
    
    return available_fonts

def map_font_to_path(font_name):
    """
    Maps font name to actual font file path.
    
    Args:
        font_name: Display name of the font
        
    Returns:
        str: Path to the font file
    """
    available_fonts = get_available_fonts()
    
    # Look for a matching font by name
    for font in available_fonts:
        if font['name'] == font_name:
            return font['file_path']
    
    # If no match found, return the first available font
    if available_fonts:
        return available_fonts[0]['file_path']
    
    # Fallback to a system font if no fonts are available
    return None

def map_font_size_to_scale(size_choice):
    """
    Maps font size selection to scale factor.
    
    Args:
        size_choice: String size ('small', 'medium', 'large', 'very large')
        
    Returns:
        float: Scale factor for font
    """
    size_mapping = {
        'small': 0.025,
        'medium': 0.035,
        'large': 0.045,
        'very large': 0.055
    }
    
    return size_mapping.get(size_choice, 0.035)

def get_supported_file_extensions():
    """
    Returns supported file extensions for media files.
    
    Returns:
        dict: Dictionaries of supported file extensions
    """
    return {
        'audio': ['.mp3', '.wav', '.m4a', '.flac'],
        'video': ['.mp4', '.mov', '.avi', '.mkv']
    }


def reconcile_edited_text_with_timings(edited_segments, original_words):
    """
    Reconcile edited segment text with original word timings.
    
    This function attempts to match words in the edited text with words in the original
    transcription to preserve timing information as much as possible.
    
    Args:
        edited_segments (dict): Dictionary containing edited segments
        original_words (dict): Dictionary containing original word data with timings
        
    Returns:
        dict: Updated segments with timing information
    """
    import re
    from difflib import SequenceMatcher
    
    # Make a deep copy of the segments to avoid modifying the original
    import copy
    updated_segments = copy.deepcopy(edited_segments)
    
    # Extract all original words with their timing data
    original_word_list = []
    for word_data in original_words.get('words', []):
        original_word_list.append({
            'text': word_data['text'].lower().strip(),
            'start': word_data['start'],
            'end': word_data['end']
        })
    
    # Process each segment
    for segment_idx, segment in enumerate(updated_segments.get('segments', [])):
        # Get the edited text
        edited_text = segment['text']
        
        # Split the edited text into words
        # Use regex to handle punctuation properly
        edited_words = re.findall(r'\b\w+\b', edited_text.lower())
        
        # Create a list to store matched words with timing
        matched_words = []
        
        # Start position in the original word list
        pos = 0
        
        # For each edited word, try to find a match in the original words
        for edited_word in edited_words:
            best_match = None
            best_score = 0
            best_pos = 0
            
            # Look ahead in original words to find the best match
            search_range = min(len(original_word_list) - pos, 50)  # Limit search range for efficiency
            
            for i in range(search_range):
                if pos + i >= len(original_word_list):
                    break
                    
                original_word = original_word_list[pos + i]['text']
                
                # Calculate similarity score
                similarity = SequenceMatcher(None, edited_word, original_word).ratio()
                
                # If this is the best match so far, remember it
                if similarity > best_score:
                    best_score = similarity
                    best_match = original_word_list[pos + i]
                    best_pos = pos + i
            
            # If we found a good match, use its timing data
            if best_match and best_score > 0.6:  # Threshold for considering a match
                matched_words.append({
                    'text': edited_word,
                    'start_time': best_match['start'],
                    'end_time': best_match['end']
                })
                
                # Update position to continue after the matched word
                pos = best_pos + 1
            else:
                # If no good match was found, estimate timing based on surrounding words
                if matched_words:
                    # Use the end time of the previous word
                    prev_end = matched_words[-1]['end_time']
                    
                    # Check if prev_end is a timestamp string or a float
                    if isinstance(prev_end, str):
                        # Convert from timestamp format to seconds
                        prev_end_seconds = parse_time_to_seconds(prev_end)
                        # Estimate a reasonable duration
                        estimated_duration = 0.3
                        # Convert back to timestamp format
                        new_start_time = format_srt_timestamp(prev_end_seconds)
                        new_end_time = format_srt_timestamp(prev_end_seconds + estimated_duration)
                        
                        matched_words.append({
                            'text': edited_word,
                            'start_time': new_start_time,
                            'end_time': new_end_time
                        })
                    else:
                        # Already in seconds (float)
                        estimated_duration = 0.3
                        matched_words.append({
                            'text': edited_word,
                            'start_time': prev_end,
                            'end_time': prev_end + estimated_duration
                        })
                else:
                    # If this is the first word with no match, use the segment start time
                    segment_start = segment.get('start_time', 0)
                    
                    # Check if segment_start is a timestamp string or a float
                    if isinstance(segment_start, str):
                        # Convert from timestamp format to seconds
                        segment_start_seconds = parse_time_to_seconds(segment_start)
                        # Estimate a reasonable duration
                        estimated_duration = 0.3
                        # Convert back to timestamp format
                        new_start_time = format_srt_timestamp(segment_start_seconds)
                        new_end_time = format_srt_timestamp(segment_start_seconds + estimated_duration)
                        
                        matched_words.append({
                            'text': edited_word,
                            'start_time': new_start_time,
                            'end_time': new_end_time
                        })
                    else:
                        # Already in seconds (float)
                        estimated_duration = 0.3
                        matched_words.append({
                            'text': edited_word,
                            'start_time': segment_start,
                            'end_time': segment_start + estimated_duration
                        })
        
        # Update the segment with matched words
        segment['words'] = matched_words
        
        # Adjust segment start and end times based on matched words
        if matched_words:
            segment['start_time'] = matched_words[0]['start_time']
            segment['end_time'] = matched_words[-1]['end_time']
    
    return updated_segments


def process_single_video_with_dicts_extended(input_video_path, segments_dict, words_dict, output_video_path, 
                        font_path, normal_color, text_highlight_color, bg_highlight_color, font_scale=0.03, 
                        position_ratio=(0.5, 0.8), blur_radius=2, 
                        word_spacing=10, segment_spacing=50, bg_color=None,
                        highlight_text=True, highlight_background=False, show_current_word_only=False):
    """
    Extended version of process_single_video_with_dicts that handles edited transcripts.
    """
    print(f"Processing video: {input_video_path}")
    print(f"Highlight text: {highlight_text}")
    print(f"Highlight background: {highlight_background}")
    print(f"Show current word only: {show_current_word_only}")
    
    try:
        # Import media processing functions here (deferred import)
        from core.media_processer import process_segment_dict, process_word_dict, process_complete_video_with_audio_rotated_extended
        
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
        reconciled_segments = reconcile_edited_text_with_timings(segments_dict, words_dict)
        
        # Process the segment dictionary to get the formatted segments
        segments = process_segment_dict(reconciled_segments)
        
        # Process the word dictionary to match words to segments
        segments = process_word_dict(words_dict, segments)
        
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

def process_edited_transcript_video(input_video_path, edited_segments, original_words, output_video_path, 
                        font_path, normal_color, text_highlight_color, bg_highlight_color, font_scale=0.03, 
                        position_ratio=(0.5, 0.8), blur_radius=2, 
                        word_spacing=10, segment_spacing=50, bg_color=None,
                        highlight_text=True, highlight_background=False, show_current_word_only=False,
                        max_chars=80, max_duration_seconds=3.0, segment_gap_seconds=0.1):
    """
    Process a video with the edited transcript, ensuring only the edited text is used.
    Automatically optimizes segments that are too long for display and ensures no temporal overlap.
    Also ensures segments don't exceed the video width.
    
    Args:
        input_video_path: Path to the input video file
        edited_segments: Dictionary containing edited segment data
        original_words: Dictionary containing original word data
        output_video_path: Path to save the output video file
        font_path: Path to the TTF font file
        normal_color: RGB or RGBA tuple for normal text color
        text_highlight_color: RGB or RGBA tuple for text highlight color
        bg_highlight_color: RGB or RGBA tuple for background highlight color
        font_scale: Font size as a ratio of the video height
        position_ratio: (x, y) tuple for position as a ratio of video dimensions
        blur_radius: Radius for the text shadow blur
        word_spacing: Spacing between words in pixels
        segment_spacing: Vertical spacing between segments in pixels
        bg_color: RGB or RGBA tuple for background color, or None for transparent
        highlight_text: Enable text highlighting
        highlight_background: Enable background highlighting
        show_current_word_only: Show only the current word being spoken
        max_chars: Maximum characters per segment
        max_duration_seconds: Maximum seconds per segment
        segment_gap_seconds: Gap between segments in seconds
    """
    print(f"Processing video with edited transcript: {input_video_path}")
    
    try:
        # Import media processing functions here (deferred import)
        from core.media_processer import (
            process_segment_dict, 
            process_complete_video_with_audio_rotated_extended,
            parse_time_to_seconds, 
            format_srt_timestamp
        )
        import cv2
        
        # Check if input video exists
        if not os.path.exists(input_video_path):
            print(f"Error: Input video not found: {input_video_path}")
            return
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_video_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # Step 1: Get video dimensions to calculate maximum caption width
        cap = cv2.VideoCapture(input_video_path)
        orig_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        
        # After 90-degree clockwise rotation:
        rotated_width = orig_height
        rotated_height = orig_width
        
        # Calculate maximum caption width (80% of rotated width)
        max_caption_width_pixels = int(rotated_width * 0.8)
        
        # Calculate font size based on video dimensions
        font_size = int(rotated_height * font_scale)
        
        # Step 2: Optimize segments for width and duration
        print("Optimizing segments for width and duration constraints...")
        from gui.utils import optimize_segments_with_timing_preservation
        
        optimized_segments = optimize_segments_with_timing_preservation(
            edited_segments,
            max_width_pixels=max_caption_width_pixels,
            font_path=font_path,
            font_size=font_size,
            max_duration_seconds=max_duration_seconds,
            video_width=rotated_width,
            word_spacing=word_spacing
        )
        
        # Debug: Print sample segments after optimization
        print("\nOptimized segments (first few):")
        for i, segment in enumerate(optimized_segments.get('segments', [])[:3]):
            print(f"Segment {i+1}: {segment.get('text', 'N/A')}")
            print(f"  Time: {segment.get('start_time')} - {segment.get('end_time')}")
            
            # Print a few words with their timing
            segment_words = segment.get('words', [])
            if segment_words:
                print(f"  Words: {len(segment_words)}")
                for j, word in enumerate(segment_words[:3]):
                    print(f"    Word {j+1}: '{word.get('text', '')}' - {word.get('start_time')} to {word.get('end_time')}")
                if len(segment_words) > 3:
                    print(f"    ... and {len(segment_words) - 3} more words")
        
        # Step 3: Convert the optimized segments to the format needed by the video processor
        segments = []
        
        for segment in optimized_segments['segments']:
            # Extract start and end times
            start_time = segment['start_time']
            end_time = segment['end_time']
            
            # Convert times to seconds if they're in string format
            if isinstance(start_time, str):
                start_time_sec = parse_time_to_seconds(start_time)
            else:
                start_time_sec = start_time
                
            if isinstance(end_time, str):
                end_time_sec = parse_time_to_seconds(end_time)
            else:
                end_time_sec = end_time
            
            # Create the processed segment
            processed_segment = {
                'text': segment['text'],
                'start_time': start_time_sec,
                'end_time': end_time_sec,
                'words': []  # Will be filled with the word data
            }
            
            # Add the word data with proper timing
            for word in segment.get('words', []):
                word_text = word.get('text', '')
                word_start = word.get('start_time')
                word_end = word.get('end_time')
                
                # Convert times if needed
                if isinstance(word_start, str):
                    word_start_sec = parse_time_to_seconds(word_start)
                else:
                    word_start_sec = word_start
                    
                if isinstance(word_end, str):
                    word_end_sec = parse_time_to_seconds(word_end)
                else:
                    word_end_sec = word_end
                
                # Add the word with proper timing
                processed_segment['words'].append({
                    'text': word_text,
                    'start_time': word_start_sec,
                    'end_time': word_end_sec
                })
            
            segments.append(processed_segment)
        
        # Save the optimized segments to a JSON file for reference
        import json
        optimized_json_path = os.path.join(output_dir, os.path.basename(output_video_path) + "_optimized_segments.json")
        with open(optimized_json_path, 'w', encoding='utf-8') as f:
            json.dump(optimized_segments, f, indent=2)
        
        # Step 4: Process the video with the prepared segments
        print("\nProcessing video with prepared segments...")
        process_complete_video_with_audio_rotated_extended(
            input_video_path, output_video_path, segments, font_path, 
            normal_color, text_highlight_color, bg_highlight_color, font_scale, position_ratio,
            blur_radius, word_spacing, segment_spacing, bg_color,
            highlight_text, highlight_background, show_current_word_only
        )
        
        print(f"Completed processing: {output_video_path}")
        
    except Exception as e:
        print(f"Error processing video with edited transcript: {e}")
        import traceback
        traceback.print_exc()
        raise  # Re-raise to let the calling function handle it


def optimize_edited_segments(segments, max_chars=30, max_duration_seconds=1.5):
    """
    Optimize edited segments by splitting overly long segments into smaller ones
    and ensuring no temporal overlap between segments.
    
    Args:
        segments (dict): Dictionary containing edited segments
        max_chars (int): Maximum number of characters per segment
        max_duration_seconds (float): Maximum duration of a segment in seconds
        
    Returns:
        dict: Optimized segments
    """
    import copy
    import re
    from core.media_processer import parse_time_to_seconds, format_srt_timestamp
    
    optimized_segments = copy.deepcopy(segments)
    new_segments = []
    
    print(f"\nOptimizing segments: max_chars={max_chars}, max_duration={max_duration_seconds}s")
    
    for segment in optimized_segments.get('segments', []):
        text = segment.get('text', '')
        start_time = segment.get('start_time', '')
        end_time = segment.get('end_time', '')
        words = segment.get('words', [])
        
        # Convert time strings to seconds if needed
        if isinstance(start_time, str):
            start_time_sec = parse_time_to_seconds(start_time)
        else:
            start_time_sec = start_time
            
        if isinstance(end_time, str):
            end_time_sec = parse_time_to_seconds(end_time)
        else:
            end_time_sec = end_time
            
        # Calculate segment duration
        duration = end_time_sec - start_time_sec
        
        # Check if segment needs splitting
        # We split if either the text length or duration exceeds the max
        if len(text) > max_chars or duration > max_duration_seconds:
            print(f"Splitting segment: '{text[:30]}...' ({len(text)} chars, {duration:.2f}s)")
            
            if words and len(words) > 1:
                # If we have word timing data, use that for more accurate splitting
                new_segments.extend(split_segment_by_words(segment, max_chars, max_duration_seconds))
            else:
                # Otherwise split by sentence or phrase
                new_segments.extend(split_segment_by_text(segment, max_chars, max_duration_seconds))
        else:
            # If segment is already good, keep it as is
            new_segments.append(segment)
    
    # Post-process to ensure no overlapping segments
    non_overlapping_segments = ensure_non_overlapping_segments(new_segments)
    
    # Replace the segments with our optimized, non-overlapping ones
    optimized_segments['segments'] = non_overlapping_segments
    
    print(f"Optimization complete: {len(segments.get('segments', []))} segments → {len(non_overlapping_segments)} segments")
    
    return optimized_segments

def split_segment_by_words(segment, max_chars=25, max_duration_seconds=1.5):
    """
    Split a segment using word-level timing information.
    
    Args:
        segment (dict): Segment to split
        max_chars (int): Maximum number of characters per segment
        max_duration_seconds (float): Maximum duration of a segment in seconds
        
    Returns:
        list: List of split segments
    """
    from core.media_processer import format_srt_timestamp, parse_time_to_seconds
    
    text = segment.get('text', '')
    words = segment.get('words', [])
    
    # If no words data or only one word, fall back to text-based splitting
    if not words or len(words) <= 1:
        return split_segment_by_text(segment, max_chars, max_duration_seconds)
    
    # Prepare new segments
    new_segments = []
    current_words = []
    current_text = ""
    current_start = words[0]['start_time']
    current_end = words[0]['end_time']
    
    for word in words:
        # Check word timing format
        if isinstance(word['start_time'], str):
            word_start_sec = parse_time_to_seconds(word['start_time'])
        else:
            word_start_sec = word['start_time']
            
        if isinstance(word['end_time'], str):
            word_end_sec = parse_time_to_seconds(word['end_time'])
        else:
            word_end_sec = word['end_time']
        
        # Check if adding this word would exceed our limits
        new_text = (current_text + " " + word['text']).strip()
        new_duration = word_end_sec - parse_time_to_seconds(current_start) if isinstance(current_start, str) else word_end_sec - current_start
        
        if len(new_text) > max_chars or new_duration > max_duration_seconds:
            # Create a new segment with the current words
            if current_words:
                new_segment = {
                    'text': current_text,
                    'start_time': current_start,
                    'end_time': current_end,
                    'words': current_words.copy()
                }
                new_segments.append(new_segment)
            
            # Start a new segment with this word
            current_text = word['text']
            current_words = [word]
            current_start = word['start_time']
            current_end = word['end_time']
        else:
            # Add word to current segment
            current_text = new_text
            current_words.append(word)
            current_end = word['end_time']
    
    # Add the last segment if there's anything left
    if current_words:
        new_segment = {
            'text': current_text,
            'start_time': current_start,
            'end_time': current_end,
            'words': current_words
        }
        new_segments.append(new_segment)
    
    return new_segments

def split_segment_by_text(segment, max_chars=25, max_duration_seconds=1.5):
    """
    Split a segment based on text content (sentences and phrases) when word timing is not available.
    
    Args:
        segment (dict): Segment to split
        max_chars (int): Maximum number of characters per segment
        max_duration_seconds (float): Maximum duration of a segment in seconds
        
    Returns:
        list: List of split segments
    """
    import re
    from core.media_processer import parse_time_to_seconds, format_srt_timestamp
    
    text = segment.get('text', '')
    start_time = segment.get('start_time', '')
    end_time = segment.get('end_time', '')
    
    # Convert time strings to seconds if needed
    if isinstance(start_time, str):
        start_time_sec = parse_time_to_seconds(start_time)
    else:
        start_time_sec = start_time
        
    if isinstance(end_time, str):
        end_time_sec = parse_time_to_seconds(end_time)
    else:
        end_time_sec = end_time
        
    # Calculate total duration of the segment
    total_duration = end_time_sec - start_time_sec
    
    # First try to split by sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    # If there's only one sentence or sentences are still too long, split by phrases
    if len(sentences) <= 1 or any(len(s) > max_chars for s in sentences):
        phrases = re.split(r'(?<=[,;:])\s+', text)
        
        # If phrases are still too long or there's only one, split arbitrarily
        if len(phrases) <= 1 or any(len(p) > max_chars for p in phrases):
            # Split into roughly equal chunks below max_chars
            chunks = []
            current_chunk = ""
            
            words = text.split()
            for word in words:
                if len(current_chunk) + len(word) + 1 > max_chars:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = word
                else:
                    current_chunk = (current_chunk + " " + word).strip()
            
            if current_chunk:
                chunks.append(current_chunk)
                
            parts = chunks
        else:
            parts = phrases
    else:
        parts = sentences
    
    # Create new segments based on the parts
    new_segments = []
    time_per_char = total_duration / len(text) if len(text) > 0 else 0
    
    current_start = start_time_sec
    for part in parts:
        # Calculate duration based on character count
        part_duration = len(part) * time_per_char
        part_end = current_start + part_duration
        
        # Ensure time format consistency
        if isinstance(start_time, str):
            # If original times were strings, convert back to same format
            new_start = format_srt_timestamp(current_start)
            new_end = format_srt_timestamp(part_end)
        else:
            # Keep as seconds (float)
            new_start = current_start
            new_end = part_end
        
        # Create the new segment
        new_segment = {
            'text': part,
            'start_time': new_start,
            'end_time': new_end,
            'words': []  # Empty words as we don't have word-level timing for this part
        }
        
        new_segments.append(new_segment)
        current_start = part_end
    
    return new_segments


def ensure_non_overlapping_segments(segments_list, gap_seconds=0.1):
    """
    Post-process segments to ensure no temporal overlap between them.
    Adds a small gap between segments if specified.
    
    Args:
        segments_list (list): List of segment dictionaries
        gap_seconds (float): Gap to insert between segments in seconds
        
    Returns:
        list: List of segments with no temporal overlaps
    """
    from core.media_processer import format_srt_timestamp
    
    # Sort segments by start time
    sorted_segments = sorted(segments_list, key=lambda s: s['start_time'] if isinstance(s['start_time'], float) 
                          else parse_time_to_seconds(s['start_time']))
    
    # Ensure no overlaps
    for i in range(1, len(sorted_segments)):
        prev_seg = sorted_segments[i-1]
        curr_seg = sorted_segments[i]
        
        # Convert end time of previous segment to seconds
        if isinstance(prev_seg['end_time'], str):
            prev_end_sec = parse_time_to_seconds(prev_seg['end_time'])
        else:
            prev_end_sec = prev_seg['end_time']
            
        # Convert start time of current segment to seconds
        if isinstance(curr_seg['start_time'], str):
            curr_start_sec = parse_time_to_seconds(curr_seg['start_time'])
        else:
            curr_start_sec = curr_seg['start_time']
        
        # If current segment starts before previous ends (plus gap), adjust it
        if curr_start_sec < prev_end_sec + gap_seconds:
            new_start_sec = prev_end_sec + gap_seconds
            
            # Update the start time
            if isinstance(curr_seg['start_time'], str):
                curr_seg['start_time'] = format_srt_timestamp(new_start_sec)
            else:
                curr_seg['start_time'] = new_start_sec
                
            # If this would make the segment have end before start, adjust end too
            if isinstance(curr_seg['end_time'], str):
                curr_end_sec = parse_time_to_seconds(curr_seg['end_time'])
            else:
                curr_end_sec = curr_seg['end_time']
                
            if curr_end_sec < new_start_sec:
                # Calculate minimum segment duration (at least 0.5 seconds)
                min_duration = 0.5
                new_end_sec = new_start_sec + min_duration
                
                # Update the end time
                if isinstance(curr_seg['end_time'], str):
                    curr_seg['end_time'] = format_srt_timestamp(new_end_sec)
                else:
                    curr_seg['end_time'] = new_end_sec
    
    return sorted_segments




# Add to utils.py or create a new file transcript_correction.py

import difflib
import re
from typing import Dict, List, Tuple, Any

def extract_full_transcript(segments_dict: Dict) -> str:
    """
    Extract and combine the full transcript from all segments.
    
    Args:
        segments_dict: Dictionary containing segment data
        
    Returns:
        str: The full transcript text
    """
    # Extract all segment texts and join them with spaces
    full_text = ""
    
    for segment in segments_dict.get('segments', []):
        segment_text = segment.get('text', '').strip()
        if segment_text:
            full_text += segment_text + " "
    
    return full_text.strip()

def correct_transcript_grammar(transcript_text: str, chunk_size: int = 500, chunk_overlap: int = 100) -> str:
    """
    Correct grammar and spelling in a transcript using a pre-trained model.
    Process long transcripts in chunks to avoid model limitations.
    
    Args:
        transcript_text: The full transcript text
        chunk_size: Maximum size of each chunk to process
        chunk_overlap: Overlap between chunks to avoid boundary issues
        
    Returns:
        str: The corrected transcript text
    """
    try:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline
        import torch
        
        print("Loading grammar correction model...")
        model_name = "prithivida/grammar_error_correcter_v1"
        
        # Check for CUDA availability
        device = 0 if torch.cuda.is_available() else -1
        print(f"Using device: {'CUDA' if device == 0 else 'CPU'}")
        
        # Load model and tokenizer
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        
        # Create the correction pipeline
        corrector = pipeline("text2text-generation", model=model, tokenizer=tokenizer, device=device)
        
        # If the transcript is short enough, process it all at once
        if len(transcript_text) <= chunk_size:
            print(f"Correcting transcript (length: {len(transcript_text)})...")
            corrected = corrector(transcript_text, max_length=min(len(transcript_text) * 2, 512))[0]['generated_text']
            return corrected
        
        # For longer transcripts, split into chunks with overlap
        print(f"Transcript length ({len(transcript_text)}) exceeds chunk size. Processing in chunks...")
        
        # Split the transcript into sentences to avoid cutting in the middle of sentences
        sentences = re.split(r'(?<=[.!?])\s+', transcript_text)
        chunks = []
        current_chunk = ""
        
        # Create chunks of sentences
        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 > chunk_size and current_chunk:
                chunks.append(current_chunk)
                # Keep some overlap for context
                overlap_words = current_chunk.split()[-chunk_overlap//10:]
                current_chunk = " ".join(overlap_words) + " " + sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence
        
        # Add the last chunk if there's any content
        if current_chunk:
            chunks.append(current_chunk)
        
        # Process each chunk
        corrected_chunks = []
        for i, chunk in enumerate(chunks):
            print(f"Processing chunk {i+1}/{len(chunks)} (length: {len(chunk)})...")
            corrected_chunk = corrector(chunk, max_length=min(len(chunk) * 2, 512))[0]['generated_text']
            corrected_chunks.append(corrected_chunk)
        
        # Combine the corrected chunks, removing overlaps
        corrected_text = corrected_chunks[0]
        for i in range(1, len(corrected_chunks)):
            # Find overlap between the end of the previous chunk and the start of this chunk
            prev_chunk = corrected_chunks[i-1]
            curr_chunk = corrected_chunks[i]
            
            # Use difflib to find a good joining point
            matcher = difflib.SequenceMatcher(None, prev_chunk[-chunk_overlap:], curr_chunk[:chunk_overlap])
            match = matcher.find_longest_match(0, chunk_overlap, 0, chunk_overlap)
            
            if match.size > 0:
                # Join at the match point
                corrected_text += curr_chunk[match.b + match.size:]
            else:
                # If no good match, just append with a space
                corrected_text += " " + curr_chunk
        
        return corrected_text
        
    except ImportError as e:
        print(f"Error: Required libraries not installed. {e}")
        print("Please install the transformers library: pip install transformers torch")
        return transcript_text  # Return original if we can't correct
    except Exception as e:
        print(f"Error correcting transcript: {e}")
        return transcript_text  # Return original if correction fails

def map_corrections_to_segments(original_segments, corrected_text):
    """
    Map the corrected text back to the original segments using word-based matching.
    Preserves word-level timing for proper highlighting.
    
    Args:
        original_segments: Dictionary containing original segment data
        corrected_text: The corrected full transcript text
        
    Returns:
        Dict: Updated segments with corrected text
    """
    import copy
    import re
    
    # Create a deep copy to avoid modifying the original
    corrected_segments = copy.deepcopy(original_segments)
    
    # Split both texts into words, preserving punctuation
    # We use this regex to match words and punctuation as separate tokens
    word_pattern = r'\b\w+\b|[^\w\s]'
    
    # Extract words from original segments
    all_original_words = []
    segment_word_counts = []
    
    for segment in original_segments.get('segments', []):
        segment_text = segment.get('text', '').strip()
        if segment_text:
            # Extract words and punctuation
            segment_words = re.findall(word_pattern, segment_text)
            all_original_words.extend(segment_words)
            segment_word_counts.append(len(segment_words))
        else:
            segment_word_counts.append(0)
    
    # Extract words from corrected text
    corrected_words = re.findall(word_pattern, corrected_text)
    
    print(f"Original word count: {len(all_original_words)}")
    print(f"Corrected word count: {len(corrected_words)}")
    
    # Distribute corrected words to segments based on original word counts
    current_word_index = 0
    
    for i, segment in enumerate(corrected_segments.get('segments', [])):
        word_count = segment_word_counts[i]
        if word_count == 0:
            continue
            
        # Get words for this segment
        segment_end_index = min(current_word_index + word_count, len(corrected_words))
        segment_words = corrected_words[current_word_index:segment_end_index]
        
        # Join words with spaces, but handle punctuation properly
        segment_text = ""
        for word in segment_words:
            # Add space before word unless it's punctuation or the first word
            if re.match(r'[^\w\s]', word) and segment_text:
                segment_text = segment_text.rstrip() + word
            else:
                if segment_text:
                    segment_text += " " + word
                else:
                    segment_text = word
        
        # Update segment text
        segment['text'] = segment_text
        
        # Move to next segment's words
        current_word_index = segment_end_index
    
    # After mapping text, preserve word timing data
    corrected_segments = preserve_word_timing_in_correction(original_segments, corrected_segments)
    
    return corrected_segments

def sentence_based_segment_mapping(original_segments, original_sentences, corrected_sentences):
    """
    Map corrected sentences back to segments, preserving sentence boundaries.
    
    Args:
        original_segments: Dictionary containing original segment data
        original_sentences: List of original sentences
        corrected_sentences: List of corrected sentences
        
    Returns:
        Dict: Updated segments with corrected text
    """
    import copy
    
    corrected_segments = copy.deepcopy(original_segments)
    
    # First, build a map of which sentences belong to which segments
    segment_to_sentences = {}
    
    # Track position in the full text
    current_pos = 0
    
    # Build the original full text with sentence boundaries
    full_text = ""
    sentence_boundaries = []
    
    for sent in original_sentences:
        start_pos = len(full_text)
        full_text += sent + " "
        end_pos = len(full_text) - 1
        sentence_boundaries.append((start_pos, end_pos, sent))
    
    # Find which segments contain which sentences
    for i, segment in enumerate(original_segments.get('segments', [])):
        segment_text = segment.get('text', '').strip()
        if not segment_text:
            continue
            
        # Find where this segment is in the full text
        segment_start = full_text.find(segment_text)
        if segment_start == -1:
            # Try finding it with more flexible matching
            words = segment_text.split()
            if words:
                first_word = words[0]
                last_word = words[-1]
                
                # Find potential start and end positions
                potential_start = full_text.find(first_word)
                potential_end = full_text.find(last_word, potential_start) + len(last_word)
                
                if potential_start != -1 and potential_end > potential_start:
                    segment_start = potential_start
                    segment_end = potential_end
                else:
                    # If still can't find, skip this segment
                    print(f"WARNING: Couldn't locate segment in full text: '{segment_text}'")
                    continue
            else:
                continue
        else:
            segment_end = segment_start + len(segment_text)
        
        # Find which sentences are in this segment
        segment_sentences = []
        for j, (sent_start, sent_end, sent) in enumerate(sentence_boundaries):
            # Check if there's significant overlap
            overlap_start = max(segment_start, sent_start)
            overlap_end = min(segment_end, sent_end)
            
            if overlap_end > overlap_start:
                # Calculate overlap percentage with the sentence
                overlap_length = overlap_end - overlap_start
                sentence_length = sent_end - sent_start
                
                if overlap_length / sentence_length > 0.5:  # If over 50% of sentence is in segment
                    segment_sentences.append(j)
        
        segment_to_sentences[i] = segment_sentences
    
    # Now assign corrected sentences to segments
    for i, segment in enumerate(corrected_segments.get('segments', [])):
        if i not in segment_to_sentences or not segment_to_sentences[i]:
            continue
            
        # Get the corrected sentences for this segment
        segment_sentence_indices = segment_to_sentences[i]
        corrected_segment_text = ""
        
        for j in segment_sentence_indices:
            if j < len(corrected_sentences):
                if corrected_segment_text:
                    corrected_segment_text += " "
                corrected_segment_text += corrected_sentences[j]
        
        # Update segment with corrected text
        if corrected_segment_text:
            segment['text'] = corrected_segment_text
    
    return corrected_segments

def word_based_segment_mapping(original_segments, original_text, corrected_text):
    """
    Map the corrected text back to the original segments using word-level matching.
    
    Args:
        original_segments: Dictionary containing original segment data
        original_text: The full original transcript text
        corrected_text: The corrected full transcript text
        
    Returns:
        Dict: Updated segments with corrected text
    """
    import copy
    import re
    
    # Create a deep copy to avoid modifying the original
    corrected_segments = copy.deepcopy(original_segments)
    
    # Split both texts into words
    original_words = re.findall(r'\b\w+\b|\S+', original_text)
    corrected_words = re.findall(r'\b\w+\b|\S+', corrected_text)
    
    print(f"Original word count: {len(original_words)}")
    print(f"Corrected word count: {len(corrected_words)}")
    
    # If word counts are too different, use proportional mapping
    if abs(len(original_words) - len(corrected_words)) > max(10, len(original_words) * 0.3):
        print("Word counts too different, falling back to proportional mapping")
        return proportional_segment_mapping(original_segments, original_text, corrected_text)
    
    # Track which segment each original word belongs to
    word_to_segment = {}
    segment_word_counts = {}
    
    # Segment boundary tracking
    word_index = 0
    
    # First, determine which words belong to which segments
    for i, segment in enumerate(original_segments.get('segments', [])):
        segment_text = segment.get('text', '').strip()
        if not segment_text:
            continue
            
        # Count words in this segment
        segment_words = re.findall(r'\b\w+\b|\S+', segment_text)
        segment_word_counts[i] = len(segment_words)
        
        # Assign these words to this segment
        for _ in range(len(segment_words)):
            if word_index < len(original_words):
                word_to_segment[word_index] = i
                word_index += 1
    
    # Now map corrected words to segments
    segment_texts = {i: [] for i in range(len(corrected_segments.get('segments', [])))}
    
    # Try to maintain roughly the same number of words per segment
    current_segment = 0
    words_in_current_segment = 0
    
    # Special handling for the case where we have fewer corrected words
    if len(corrected_words) < len(original_words):
        # Scale the segment word counts
        scale_factor = len(corrected_words) / len(original_words)
        for i in segment_word_counts:
            segment_word_counts[i] = max(1, int(segment_word_counts[i] * scale_factor))
    
    # Distribute corrected words to segments
    for word in corrected_words:
        segment_texts[current_segment].append(word)
        words_in_current_segment += 1
        
        # Check if we've filled this segment
        if (current_segment in segment_word_counts and 
            words_in_current_segment >= segment_word_counts[current_segment]):
            current_segment += 1
            words_in_current_segment = 0
            
            # If we've gone past the last segment, wrap back to the last one
            if current_segment >= len(corrected_segments.get('segments', [])):
                current_segment = len(corrected_segments.get('segments', [])) - 1
    
    # Update segment texts
    for i, segment in enumerate(corrected_segments.get('segments', [])):
        if i in segment_texts and segment_texts[i]:
            segment['text'] = ' '.join(segment_texts[i])
    
    return corrected_segments

def proportional_segment_mapping(original_segments, original_text, corrected_text):
    """
    Map the corrected text back to the original segments proportionally.
    This is a fallback method when more precise methods fail.
    
    Args:
        original_segments: Dictionary containing original segment data
        original_text: The full original transcript text
        corrected_text: The corrected full transcript text
        
    Returns:
        Dict: Updated segments with corrected text
    """
    import copy
    
    # Create a deep copy to avoid modifying the original
    corrected_segments = copy.deepcopy(original_segments)
    
    # Calculate total lengths
    total_original_length = len(original_text)
    total_corrected_length = len(corrected_text)
    
    # Make sure we don't divide by zero
    if total_original_length == 0:
        return corrected_segments
    
    # Track current position in the corrected text
    current_pos = 0
    
    # Apply to each segment
    for segment in corrected_segments.get('segments', []):
        segment_text = segment.get('text', '').strip()
        if not segment_text:
            continue
            
        # Calculate proportion of original text this segment represents
        segment_proportion = len(segment_text) / total_original_length
        
        # Calculate how many characters this should be in the corrected text
        corrected_segment_length = int(total_corrected_length * segment_proportion)
        
        # Extract the corresponding portion of the corrected text
        # Make sure we don't exceed the text length
        end_pos = min(current_pos + corrected_segment_length, total_corrected_length)
        
        # Extract complete words (don't cut off in the middle of a word)
        if end_pos < total_corrected_length:
            # Find the next space after our calculated end position
            next_space = corrected_text.find(' ', end_pos)
            if next_space != -1:
                end_pos = next_space
            
        # Get the segment text
        if current_pos < end_pos:
            segment_text = corrected_text[current_pos:end_pos].strip()
            
            # Update the segment text
            if segment_text:
                segment['text'] = segment_text
                
            # Update current position, skipping the space
            current_pos = end_pos + 1
            
            # Make sure we don't exceed the text length
            if current_pos >= total_corrected_length:
                current_pos = total_corrected_length
    
    return corrected_segments

def apply_automatic_correction(input_path, segments_dict, words_dict):
    """
    Apply automatic grammar and spelling correction to a transcript.
    
    Args:
        input_path: Path to the input video file (for logging)
        segments_dict: Dictionary containing segment data
        words_dict: Dictionary containing word data
        
    Returns:
        Dict: Updated segments with corrected text
    """
    print(f"\nApplying automatic transcript correction for: {input_path}")
    
    # Step 1: Extract the full transcript
    full_transcript = extract_full_transcript(segments_dict)
    print(f"Extracted full transcript ({len(full_transcript)} characters)")
    
    # Debug: Show a sample of the transcript
    sample_length = min(200, len(full_transcript))
    print(f"Sample: \"{full_transcript[:sample_length]}...\"")
    
    # Step 2: Apply grammar and spelling correction
    corrected_transcript = correct_transcript_grammar(full_transcript)
    print("Grammar correction complete")
    
    # Debug: Show a sample of the corrected transcript
    sample_length = min(200, len(corrected_transcript))
    print(f"Corrected sample: \"{corrected_transcript[:sample_length]}...\"")
    
    # Step 3: Map corrections back to segments
    corrected_segments = map_corrections_to_segments(segments_dict, corrected_transcript)
    print(f"Mapped corrections to {len(corrected_segments.get('segments', []))} segments")
    
    # Debug: Show some sample corrections
    print("\nSample segment corrections:")
    for i, segment in enumerate(segments_dict.get('segments', [])[:3]):
        original_text = segment.get('text', '')
        corrected_text = corrected_segments.get('segments', [])[i].get('text', '')
        if original_text != corrected_text:
            print(f"Original: \"{original_text}\"")
            print(f"Corrected: \"{corrected_text}\"\n")
    
    return corrected_segments

def apply_automatic_correction(input_path: str, segments_dict: Dict, words_dict: Dict) -> Dict:
    """
    Apply automatic grammar and spelling correction to a transcript.
    
    Args:
        input_path: Path to the input video file (for logging)
        segments_dict: Dictionary containing segment data
        words_dict: Dictionary containing word data
        
    Returns:
        Dict: Updated segments with corrected text
    """
    print(f"\nApplying automatic transcript correction for: {input_path}")
    
    # Step 1: Extract the full transcript
    full_transcript = extract_full_transcript(segments_dict)
    print(f"Extracted full transcript ({len(full_transcript)} characters)")
    
    # Debug: Show a sample of the transcript
    sample_length = min(200, len(full_transcript))
    print(f"Sample: \"{full_transcript[:sample_length]}...\"")
    
    # Step 2: Apply grammar and spelling correction
    corrected_transcript = correct_transcript_grammar(full_transcript)
    print("Grammar correction complete")
    
    # Debug: Show a sample of the corrected transcript
    sample_length = min(200, len(corrected_transcript))
    print(f"Corrected sample: \"{corrected_transcript[:sample_length]}...\"")
    
    # Step 3: Map corrections back to segments
    corrected_segments = map_corrections_to_segments(segments_dict, corrected_transcript)
    print(f"Mapped corrections to {len(corrected_segments.get('segments', []))} segments")
    
    # Debug: Show some sample corrections
    print("\nSample segment corrections:")
    for i, segment in enumerate(segments_dict.get('segments', [])[:3]):
        original_text = segment.get('text', '')
        corrected_text = corrected_segments.get('segments', [])[i].get('text', '')
        if original_text != corrected_text:
            print(f"Original: \"{original_text}\"")
            print(f"Corrected: \"{corrected_text}\"\n")
    
    return corrected_segments


def optimize_segment_width(segments, max_width_pixels, font_path, font_size, word_spacing=10):
    """
    Optimize segments to ensure they don't exceed the maximum width.
    Handles both string and numeric timestamp formats.
    
    Args:
        segments (list): List of segment dictionaries
        max_width_pixels (int): Maximum width in pixels
        font_path (str): Path to the font file
        font_size (int): Font size in pixels
        word_spacing (int): Spacing between words
        
    Returns:
        list: List of optimized segments
    """
    from PIL import ImageFont, Image, ImageDraw
    import copy
    
    # Import time parsing functions
    from core.media_processer import parse_time_to_seconds, format_srt_timestamp
    
    # Create a deep copy to avoid modifying the original
    optimized_segments = copy.deepcopy(segments)
    result_segments = []
    
    # Load font for width calculation
    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception as e:
        print(f"Error loading font: {e}, using default")
        font = ImageFont.load_default()
    
    # Create a temporary image for text measurement
    temp_image = Image.new('RGB', (max_width_pixels * 2, 100))
    draw = ImageDraw.Draw(temp_image)
    
    # Function to measure text width
    def measure_text_width(text):
        try:
            if hasattr(draw, 'textlength'):
                # For newer PIL versions
                return draw.textlength(text, font=font)
            elif hasattr(draw, 'textsize'):
                # For older PIL versions
                width, _ = draw.textsize(text, font=font)
                return width
            else:
                # Fallback
                return len(text) * (font_size // 2)
        except Exception as e:
            print(f"Error measuring text width: {e}")
            return len(text) * (font_size // 2)
    
    # Process each segment
    for segment in optimized_segments:
        segment_text = segment.get('text', '')
        if not segment_text:
            # Keep empty segments as is
            result_segments.append(segment)
            continue
        
        # Split into words
        words = segment_text.split()
        if not words:
            result_segments.append(segment)
            continue
        
        # Calculate total width with word spacing
        word_widths = [measure_text_width(word) for word in words]
        total_width = sum(word_widths) + word_spacing * (len(words) - 1)
        
        # If the segment is within width constraints, keep it as is
        if total_width <= max_width_pixels:
            result_segments.append(segment)
            continue
        
        # If it exceeds the width, split it into multiple segments
        current_words = []
        current_width = 0
        
        # Get start and end times, converting to seconds if they're strings
        start_time = segment.get('start_time', 0)
        end_time = segment.get('end_time', 0)
        
        # Check if times are strings and convert to seconds for calculation
        if isinstance(start_time, str):
            start_time_sec = parse_time_to_seconds(start_time)
        else:
            start_time_sec = start_time
            
        if isinstance(end_time, str):
            end_time_sec = parse_time_to_seconds(end_time)
        else:
            end_time_sec = end_time
        
        # Calculate segment duration in seconds
        segment_duration = end_time_sec - start_time_sec
        
        # Track current start time for new segments
        current_start_time_sec = start_time_sec
        
        for i, (word, width) in enumerate(zip(words, word_widths)):
            # Check if adding this word would exceed the max width
            new_width = current_width + (word_spacing if current_words else 0) + width
            
            if new_width > max_width_pixels and current_words:
                # Create a new segment with accumulated words
                new_segment = copy.deepcopy(segment)
                new_segment['text'] = ' '.join(current_words)
                
                # Calculate timing for this segment
                # Distribute time proportionally based on word count
                proportion = len(current_words) / len(words)
                segment_portion = segment_duration * proportion
                
                # Set time values, converting back to original format if needed
                if isinstance(start_time, str):
                    new_segment['start_time'] = format_srt_timestamp(current_start_time_sec)
                    new_segment['end_time'] = format_srt_timestamp(current_start_time_sec + segment_portion)
                else:
                    new_segment['start_time'] = current_start_time_sec
                    new_segment['end_time'] = current_start_time_sec + segment_portion
                
                # Update for next segment
                current_start_time_sec += segment_portion
                
                result_segments.append(new_segment)
                
                # Reset for next segment
                current_words = [word]
                current_width = width
            else:
                # Add word to current segment
                current_words.append(word)
                current_width = new_width if current_words else width
        
        # Add the last segment if there are remaining words
        if current_words:
            new_segment = copy.deepcopy(segment)
            new_segment['text'] = ' '.join(current_words)
            
            # Set timing for the last segment
            if isinstance(start_time, str):
                new_segment['start_time'] = format_srt_timestamp(current_start_time_sec)
                new_segment['end_time'] = format_srt_timestamp(end_time_sec)
            else:
                new_segment['start_time'] = current_start_time_sec
                new_segment['end_time'] = end_time_sec
            
            result_segments.append(new_segment)
    
    return result_segments


def preserve_word_timing_in_correction(original_segments, corrected_segments):
    """
    Preserve word-level timing information when mapping corrections to segments.
    This ensures that word highlighting works correctly after text correction.
    
    Args:
        original_segments (dict): Dictionary containing original segments with word timing data
        corrected_segments (dict): Dictionary containing corrected segments without word timing
        
    Returns:
        dict: Updated corrected segments with word timing data
    """
    import copy
    import re
    from difflib import SequenceMatcher
    
    # Make a deep copy to avoid modifying inputs
    result_segments = copy.deepcopy(corrected_segments)
    
    # Process each segment
    for i, (orig_segment, corr_segment) in enumerate(zip(
            original_segments.get('segments', []),
            result_segments.get('segments', [])
        )):
        
        # If either segment is empty, skip
        if not orig_segment.get('text', '').strip() or not corr_segment.get('text', '').strip():
            continue
            
        # Split original and corrected text into words
        orig_words_text = re.findall(r'\b\w+\b|[^\w\s]', orig_segment.get('text', ''))
        corr_words_text = re.findall(r'\b\w+\b|[^\w\s]', corr_segment.get('text', ''))
        
        # Get original word data with timing
        orig_word_data = orig_segment.get('words', [])
        
        # If original has no word data or word counts don't match, we need to estimate
        if not orig_word_data or len(orig_words_text) != len(orig_word_data):
            # Estimate word timing using segment start/end times
            corr_segment['words'] = estimate_word_timing(corr_segment, corr_words_text)
            continue
            
        # Use sequence matching to map original words to corrected words
        matcher = SequenceMatcher(None, orig_words_text, corr_words_text)
        matched_blocks = matcher.get_matching_blocks()
        
        # Initialize corrected word data list
        corr_word_data = []
        
        # Process each matching block
        for orig_idx, corr_idx, size in matched_blocks:
            # Skip the empty block at the end
            if size == 0:
                continue
                
            # Map timing data for matching words
            for j in range(size):
                if orig_idx + j < len(orig_word_data) and corr_idx + j < len(corr_words_text):
                    # Create new word data with timing from original but text from corrected
                    word_data = copy.deepcopy(orig_word_data[orig_idx + j])
                    word_data['text'] = corr_words_text[corr_idx + j]
                    corr_word_data.append(word_data)
        
        # Handle any unmatched words in the corrected text
        if len(corr_word_data) < len(corr_words_text):
            # Find which words are missing
            matched_indices = set()
            for word_data in corr_word_data:
                if word_data['text'] in corr_words_text:
                    matched_indices.add(corr_words_text.index(word_data['text']))
                    
            # Fill in missing words with estimated timing
            for i, word in enumerate(corr_words_text):
                if i not in matched_indices:
                    # Estimate timing for this word
                    word_data = estimate_single_word_timing(
                        corr_segment, word, i, len(corr_words_text)
                    )
                    corr_word_data.append(word_data)
            
            # Sort word data by estimated start time
            corr_word_data.sort(key=lambda w: w.get('start_time', 0))
        
        # Update corrected segment with word data
        corr_segment['words'] = corr_word_data
    
    return result_segments

def estimate_word_timing(segment, words):
    """
    Estimate timing for words in a segment when original timing data is unavailable.
    
    Args:
        segment (dict): Segment dictionary with start_time and end_time
        words (list): List of words in the segment
        
    Returns:
        list: Estimated word timing data
    """
    from core.media_processer import format_srt_timestamp, parse_time_to_seconds
    
    # Get segment start and end times
    start_time = segment.get('start_time', 0)
    end_time = segment.get('end_time', 0)
    
    # Convert to seconds if they're strings
    if isinstance(start_time, str):
        start_time_sec = parse_time_to_seconds(start_time)
    else:
        start_time_sec = start_time
        
    if isinstance(end_time, str):
        end_time_sec = parse_time_to_seconds(end_time)
    else:
        end_time_sec = end_time
    
    # Calculate total duration
    total_duration = end_time_sec - start_time_sec
    
    # Distribute time evenly among words
    word_data = []
    word_count = len(words)
    
    if word_count == 0:
        return word_data
        
    if word_count == 1:
        # If only one word, use the full segment duration
        word_duration = total_duration
        word_start = start_time_sec
        word_end = end_time_sec
        
        # Create word data
        if isinstance(start_time, str):
            word_data.append({
                'text': words[0],
                'start_time': format_srt_timestamp(word_start),
                'end_time': format_srt_timestamp(word_end)
            })
        else:
            word_data.append({
                'text': words[0],
                'start_time': word_start,
                'end_time': word_end
            })
    else:
        # Distribute time among words, with extra time for longer words
        total_chars = sum(len(word) for word in words)
        
        # Current time position
        current_time = start_time_sec
        
        for word in words:
            # Calculate this word's proportion of the total segment duration
            # based on character count
            proportion = len(word) / total_chars
            word_duration = total_duration * proportion
            
            # Word timing
            word_start = current_time
            word_end = current_time + word_duration
            
            # Create word data
            if isinstance(start_time, str):
                word_data.append({
                    'text': word,
                    'start_time': format_srt_timestamp(word_start),
                    'end_time': format_srt_timestamp(word_end)
                })
            else:
                word_data.append({
                    'text': word,
                    'start_time': word_start,
                    'end_time': word_end
                })
            
            # Update current time for next word
            current_time = word_end
    
    return word_data

def estimate_single_word_timing(segment, word, word_index, total_words):
    """
    Estimate timing for a single word within a segment.
    
    Args:
        segment (dict): Segment dictionary with start_time and end_time
        word (str): The word to estimate timing for
        word_index (int): Index of the word in the sequence
        total_words (int): Total number of words in the segment
        
    Returns:
        dict: Word data with estimated timing
    """
    from core.media_processer import format_srt_timestamp, parse_time_to_seconds
    
    # Get segment start and end times
    start_time = segment.get('start_time', 0)
    end_time = segment.get('end_time', 0)
    
    # Convert to seconds if they're strings
    if isinstance(start_time, str):
        start_time_sec = parse_time_to_seconds(start_time)
    else:
        start_time_sec = start_time
        
    if isinstance(end_time, str):
        end_time_sec = parse_time_to_seconds(end_time)
    else:
        end_time_sec = end_time
    
    # Calculate total duration
    total_duration = end_time_sec - start_time_sec
    
    # Calculate position within segment based on word index
    if total_words <= 1:
        position = 0
    else:
        position = word_index / (total_words - 1)
    
    # Estimate word duration based on length (longer words take more time)
    # A word typically takes between 0.2 and 0.6 seconds based on length
    base_duration = 0.2
    char_duration = 0.05  # Each character adds this much time
    word_duration = min(0.6, base_duration + len(word) * char_duration)
    
    # Adjust if we would exceed segment boundaries
    word_start = start_time_sec + (total_duration - word_duration) * position
    word_end = word_start + word_duration
    
    # Ensure we don't go beyond segment boundaries
    if word_start < start_time_sec:
        word_start = start_time_sec
    if word_end > end_time_sec:
        word_end = end_time_sec
    
    # Create and return word data
    if isinstance(start_time, str):
        return {
            'text': word,
            'start_time': format_srt_timestamp(word_start),
            'end_time': format_srt_timestamp(word_end)
        }
    else:
        return {
            'text': word,
            'start_time': word_start,
            'end_time': word_end
        }
    

def optimize_segments_with_timing_preservation(segments, max_width_pixels, font_path, font_size, 
                                      max_duration_seconds=1.5, video_width=None, word_spacing=10):
    """
    Optimize segments for width and duration while preserving word timing for highlighting.
    Ensures proper handling of punctuation and contractions.
    
    Args:
        segments (dict): Dictionary with 'segments' list containing segment objects
        max_width_pixels (int): Maximum width of a segment in pixels
        font_path (str): Path to the font file for width calculation
        font_size (int): Font size for width calculation
        max_duration_seconds (float): Maximum duration of a segment in seconds
        video_width (int): Width of the video frame (after rotation)
        word_spacing (int): Spacing between words in pixels
        
    Returns:
        dict: Dictionary with optimized segments that maintain word timing integrity
    """
    from PIL import ImageFont, ImageDraw, Image
    import copy
    import os
    import re
    from core.media_processer import parse_time_to_seconds, format_srt_timestamp
    
    # If video_width is provided, calculate margin and adjust max_width
    if video_width:
        margin_percent = 0.05  # 5% margin
        margin_pixels = int(video_width * margin_percent)
        max_width_pixels = min(max_width_pixels, video_width - (2 * margin_pixels))
    
    print(f"Optimizing segments with max width: {max_width_pixels} pixels, font size: {font_size} pixels")
    
    # Make a deep copy to avoid modifying the original
    optimized_segments = copy.deepcopy(segments)
    result_segments = []
    
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
        font = ImageFont.load_default()
    
    # Create a temporary image for text measurement
    temp_image = Image.new('RGB', (max_width_pixels * 2, 100))
    draw = ImageDraw.Draw(temp_image)
    
    # Function to measure text width
    def measure_text_width(text):
        try:
            if hasattr(draw, 'textlength'):
                # For newer PIL versions
                return draw.textlength(text, font=font)
            elif hasattr(draw, 'textsize'):
                # For older PIL versions
                width, _ = draw.textsize(text, font=font)
                return width
            else:
                # Fallback
                return len(text) * (font_size // 2)
        except Exception as e:
            print(f"Error measuring text width: {e}")
            return len(text) * (font_size // 2)
    
    # Helper function to check if a string is a punctuation mark
    def is_punctuation(text):
        return re.match(r'^[^\w\s]$', text) is not None
        
    # Helper function to check if a string is an apostrophe (for contractions)
    def is_apostrophe(text):
        return text == "'" or text == "'"  # Handle both straight and curly apostrophes
    
    # Process each segment
    for segment in optimized_segments.get('segments', []):
        segment_text = segment.get('text', '')
        if not segment_text.strip():
            # Keep empty segments as is
            result_segments.append(segment)
            continue
        
        # Get original word data
        original_words = segment.get('words', [])
        
        # If no word data, create estimated word timing
        if not original_words:
            print(f"Warning: No word timing data for segment: '{segment_text}'")
            # We could add word timing estimation here if needed
            result_segments.append(segment)
            continue
        
        # Group punctuation with preceding words and handle contractions
        grouped_words = []
        current_group = None
        i = 0
        
        while i < len(original_words):
            word = original_words[i]
            word_text = word.get('text', '')
            
            # Check if this is a punctuation mark
            if is_punctuation(word_text):
                # Check if it's an apostrophe (part of a contraction)
                if is_apostrophe(word_text) and i + 1 < len(original_words):
                    # Look ahead to see if this is part of a contraction
                    next_word = original_words[i + 1]
                    next_text = next_word.get('text', '')
                    
                    # Common contraction endings
                    contraction_endings = ['re', 'll', 've', 's', 't', 'd', 'm']
                    
                    if any(next_text.lower() == ending for ending in contraction_endings):
                        # This is a contraction (e.g., you're, I'll, etc.)
                        if current_group:
                            # Combine the parts into one word
                            combined_text = current_group['text'] + word_text + next_text
                            current_group['text'] = combined_text
                            
                            # Keep the start time of the first part and the end time of the last part
                            current_group['end_time'] = next_word.get('end_time')
                            
                            # Skip the next word since we've incorporated it
                            i += 2
                            continue
                        else:
                            # Shouldn't happen (apostrophe with no preceding word)
                            # But handle it anyway by creating a new group
                            current_group = copy.deepcopy(word)
                            i += 1
                            continue
                
                # Regular punctuation (not part of a contraction)
                if current_group:
                    # Add this punctuation to the current group
                    current_group['text'] = current_group['text'] + word_text
                    current_group['end_time'] = word.get('end_time')
                else:
                    # This is a standalone punctuation, create a new group
                    current_group = copy.deepcopy(word)
                    grouped_words.append(current_group)
                    current_group = None
            else:
                # This is a regular word
                if current_group:
                    # Add the previous group
                    grouped_words.append(current_group)
                
                # Start a new group with this word
                current_group = copy.deepcopy(word)
            
            # Move to the next word
            i += 1
        
        # Add the last group if there is one
        if current_group:
            grouped_words.append(current_group)
        
        # Calculate total width of the segment with grouped words
        total_width = sum(measure_text_width(word.get('text', '')) for word in grouped_words)
        total_width += word_spacing * (len(grouped_words) - 1) if len(grouped_words) > 1 else 0
        
        # Check segment duration
        start_time = segment.get('start_time', 0)
        end_time = segment.get('end_time', 0)
        
        # Convert times to seconds if they're strings
        if isinstance(start_time, str):
            start_time_sec = parse_time_to_seconds(start_time)
        else:
            start_time_sec = start_time
            
        if isinstance(end_time, str):
            end_time_sec = parse_time_to_seconds(end_time)
        else:
            end_time_sec = end_time
        
        segment_duration = end_time_sec - start_time_sec
        
        # If segment is within constraints, keep it as is (with grouped words)
        if total_width <= max_width_pixels and segment_duration <= max_duration_seconds:
            # Create updated segment with grouped words
            updated_segment = copy.deepcopy(segment)
            updated_segment['words'] = grouped_words
            
            # Rebuild the text
            updated_segment['text'] = ' '.join(word.get('text', '') for word in grouped_words)
            
            result_segments.append(updated_segment)
            continue
        
        # Need to split the segment - first by duration, then by width
        # This ensures we don't exceed either constraint
        
        # Split by duration if needed
        duration_segments = []
        if segment_duration > max_duration_seconds:
            # Need to split by duration
            current_words = []
            current_start = start_time_sec
            current_duration = 0
            
            for word in grouped_words:
                word_start = word.get('start_time')
                word_end = word.get('end_time')
                
                # Convert to seconds if needed
                if isinstance(word_start, str):
                    word_start_sec = parse_time_to_seconds(word_start)
                else:
                    word_start_sec = word_start
                    
                if isinstance(word_end, str):
                    word_end_sec = parse_time_to_seconds(word_end)
                else:
                    word_end_sec = word_end
                
                # Calculate word duration
                word_duration = word_end_sec - word_start_sec
                
                # Check if adding this word would exceed max duration
                if current_duration + word_duration > max_duration_seconds and current_words:
                    # Create a new segment with current words
                    new_segment = copy.deepcopy(segment)
                    new_segment['words'] = current_words
                    
                    # Rebuild the text properly
                    new_segment['text'] = ' '.join(word.get('text', '') for word in current_words)
                    
                    # Set timing
                    if isinstance(start_time, str):
                        new_segment['start_time'] = format_srt_timestamp(current_start)
                        new_segment['end_time'] = format_srt_timestamp(current_start + current_duration)
                    else:
                        new_segment['start_time'] = current_start
                        new_segment['end_time'] = current_start + current_duration
                    
                    duration_segments.append(new_segment)
                    
                    # Reset for next segment
                    current_words = [word]
                    current_start = word_start_sec
                    current_duration = word_duration
                else:
                    # Add word to current segment
                    current_words.append(word)
                    current_duration += word_duration
            
            # Add the last segment if there are remaining words
            if current_words:
                new_segment = copy.deepcopy(segment)
                new_segment['words'] = current_words
                
                # Rebuild the text properly
                new_segment['text'] = ' '.join(word.get('text', '') for word in current_words)
                
                # Set timing
                if isinstance(start_time, str):
                    new_segment['start_time'] = format_srt_timestamp(current_start)
                    new_segment['end_time'] = format_srt_timestamp(current_start + current_duration)
                else:
                    new_segment['start_time'] = current_start
                    new_segment['end_time'] = current_start + current_duration
                
                duration_segments.append(new_segment)
        else:
            # No need to split by duration
            # Still update with grouped words
            updated_segment = copy.deepcopy(segment)
            updated_segment['words'] = grouped_words
            
            # Rebuild the text
            updated_segment['text'] = ' '.join(word.get('text', '') for word in grouped_words)
            
            duration_segments = [updated_segment]
        
        # Now check each duration segment for width and split if needed
        for dur_segment in duration_segments:
            # Calculate width
            words = dur_segment.get('words', [])
            word_widths = [measure_text_width(word.get('text', '')) for word in words]
            total_width = sum(word_widths) + word_spacing * (len(words) - 1) if len(words) > 1 else 0
            
            if total_width <= max_width_pixels:
                # Segment is within width constraint
                result_segments.append(dur_segment)
                continue
            
            # Need to split by width
            current_words = []
            current_width = 0
            
            for i, (word, width) in enumerate(zip(words, word_widths)):
                # Check if adding this word would exceed max width
                new_width = current_width + (word_spacing if current_words else 0) + width
                
                if new_width > max_width_pixels and current_words:
                    # Create a new segment with current words
                    new_segment = copy.deepcopy(dur_segment)
                    new_segment['words'] = current_words
                    
                    # Rebuild the text properly
                    new_segment['text'] = ' '.join(word.get('text', '') for word in current_words)
                    
                    # Calculate timing based on the words in this segment
                    word_start_times = [parse_time_to_seconds(w.get('start_time')) if isinstance(w.get('start_time'), str) 
                                       else w.get('start_time') for w in current_words]
                    word_end_times = [parse_time_to_seconds(w.get('end_time')) if isinstance(w.get('end_time'), str) 
                                     else w.get('end_time') for w in current_words]
                    
                    start_sec = min(word_start_times) if word_start_times else 0
                    end_sec = max(word_end_times) if word_end_times else 0
                    
                    # Set timing
                    if isinstance(dur_segment.get('start_time'), str):
                        new_segment['start_time'] = format_srt_timestamp(start_sec)
                        new_segment['end_time'] = format_srt_timestamp(end_sec)
                    else:
                        new_segment['start_time'] = start_sec
                        new_segment['end_time'] = end_sec
                    
                    result_segments.append(new_segment)
                    
                    # Reset for next segment
                    current_words = [word]
                    current_width = width
                else:
                    # Add word to current segment
                    current_words.append(word)
                    current_width = new_width
            
            # Add the last segment if there are remaining words
            if current_words:
                new_segment = copy.deepcopy(dur_segment)
                new_segment['words'] = current_words
                
                # Rebuild the text properly
                new_segment['text'] = ' '.join(word.get('text', '') for word in current_words)
                
                # Calculate timing based on the words in this segment
                word_start_times = [parse_time_to_seconds(w.get('start_time')) if isinstance(w.get('start_time'), str) 
                                   else w.get('start_time') for w in current_words]
                word_end_times = [parse_time_to_seconds(w.get('end_time')) if isinstance(w.get('end_time'), str) 
                                 else w.get('end_time') for w in current_words]
                
                start_sec = min(word_start_times) if word_start_times else 0
                end_sec = max(word_end_times) if word_end_times else 0
                
                # Set timing
                if isinstance(dur_segment.get('start_time'), str):
                    new_segment['start_time'] = format_srt_timestamp(start_sec)
                    new_segment['end_time'] = format_srt_timestamp(end_sec)
                else:
                    new_segment['start_time'] = start_sec
                    new_segment['end_time'] = end_sec
                
                result_segments.append(new_segment)
    
    # Ensure proper segment indices
    for i, segment in enumerate(result_segments):
        segment['index'] = i + 1
    
    # Return the optimized segments
    return {'segments': result_segments}


def word_level_correction(words_dict, corrected_text):
    """
    Apply corrections at the word level while preserving timing data.
    
    Args:
        words_dict (dict): Original words dictionary with timing data
        corrected_text (str): The corrected full transcript text
        
    Returns:
        dict: Updated words dictionary with corrected text
    """
    import copy
    import re
    from difflib import SequenceMatcher
    
    # Make a deep copy of the original words
    corrected_words = copy.deepcopy(words_dict)
    original_words_list = words_dict.get('words', [])
    
    # Debug output
    print(f"Original words count: {len(original_words_list)}")
    if len(original_words_list) > 0:
        first_word = original_words_list[0]
        print(f"First original word: '{first_word.get('text', '')}', " 
              f"timing: {first_word.get('start_time')} - {first_word.get('end_time')}")
    
    # Extract original text from words
    original_text = " ".join([word.get('text', '') for word in original_words_list])
    
    print(f"Original text: {original_text[:100]}...")
    print(f"Corrected text: {corrected_text[:100]}...")
    
    # Use a simpler approach - keep original words with their timing
    # but update the text based on corrections
    
    # If the corrected text is very different in length, we might need
    # a more sophisticated algorithm. For now, we'll just do a basic update.
    
    # If the texts are identical, no correction needed
    if original_text == corrected_text:
        print("No corrections needed - texts are identical")
        return words_dict
    
    # If the length difference is significant, use a more cautious approach
    if abs(len(original_text) - len(corrected_text)) > len(original_text) * 0.3:
        print("Significant text length difference detected - using conservative approach")
        # Create a single corrected word with the full corrected text
        # but keep timing from the first and last original words
        if len(original_words_list) > 0:
            new_word = {
                'text': corrected_text,
                'start_time': original_words_list[0].get('start_time'),
                'end_time': original_words_list[-1].get('end_time')
            }
            corrected_words['words'] = [new_word]
        return corrected_words
    
    # More typical case - apply corrections while keeping most words
    # We'll do a simple word-by-word update
    
    # Split the texts into words
    original_words = re.findall(r'\S+', original_text)
    corrected_words_text = re.findall(r'\S+', corrected_text)
    
    # If word counts are very different, use a conservative approach
    if abs(len(original_words) - len(corrected_words_text)) > len(original_words) * 0.3:
        print("Word count differs significantly - using conservative approach")
        # Similar to above, but create a single word with the full corrected text
        if len(original_words_list) > 0:
            new_word = {
                'text': corrected_text,
                'start_time': original_words_list[0].get('start_time'),
                'end_time': original_words_list[-1].get('end_time')
            }
            corrected_words['words'] = [new_word]
        return corrected_words
    
    # For similar word counts, do a word-by-word update
    # Use the shorter of the two lists to avoid index errors
    min_length = min(len(original_words_list), len(corrected_words_text))
    
    new_words = []
    for i in range(min_length):
        # Copy the original word with its timing
        new_word = copy.deepcopy(original_words_list[i])
        # Update the text with the corrected version
        new_word['text'] = corrected_words_text[i]
        new_words.append(new_word)
    
    # If the corrected text has more words, add them with estimated timing
    if len(corrected_words_text) > min_length:
        # Use the last word's timing as a basis
        if min_length > 0:
            last_word = original_words_list[min_length - 1]
            last_end_time = last_word.get('end_time')
            
            # Add the remaining words with estimated timing
            for i in range(min_length, len(corrected_words_text)):
                new_word = copy.deepcopy(last_word)
                new_word['text'] = corrected_words_text[i]
                # Keep the same end time for all additional words
                new_word['start_time'] = last_end_time
                new_word['end_time'] = last_end_time
                new_words.append(new_word)
    
    # Update the words dictionary
    corrected_words['words'] = new_words
    
    # Debug output
    print(f"Corrected words count: {len(new_words)}")
    if len(new_words) > 0:
        first_word = new_words[0]
        print(f"First corrected word: '{first_word.get('text', '')}', " 
              f"timing: {first_word.get('start_time')} - {first_word.get('end_time')}")
    
    return corrected_words

def apply_spelling_correction(input_path, words_dict):
    """
    Apply spelling and grammar correction to the transcript,
    while also generating timing data if missing.
    
    Args:
        input_path (str): Path to the original media file (for logging)
        words_dict (dict): Dictionary containing word data with timing
        
    Returns:
        dict: Updated words dictionary with corrected text and timing
    """
    try:
        # Extract the full transcript from word data
        words_text = [word.get('text', '') for word in words_dict.get('words', [])]
        full_transcript = " ".join(words_text)
        
        print(f"Extracted transcript for correction: {len(full_transcript)} characters")
        
        # Check if timing data is missing
        missing_timing = False
        for word in words_dict.get('words', []):
            if word.get('start_time') is None or word.get('end_time') is None:
                missing_timing = True
                break
        
        # Generate estimated timing if missing
        if missing_timing:
            print("Missing timing data detected - generating estimated timing")
            words_dict = generate_timing_data(words_dict)
        
        # Apply spelling and grammar correction
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline
        import nltk
        
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            print("Downloading NLTK punkt tokenizer...")
            nltk.download('punkt')
        
        print("Loading grammar correction model...")
        model_name = "prithivida/grammar_error_correcter_v1"
        
        # Load model and tokenizer
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        
        # Create correction pipeline
        corrector = pipeline("text2text-generation", model=model, tokenizer=tokenizer)
        
        # Split the transcript into sentences
        sentences = nltk.sent_tokenize(full_transcript)
        print(f"Split transcript into {len(sentences)} sentences")
        
        # Process each sentence
        corrected_sentences = []
        for i, sent in enumerate(sentences):
            if i % 10 == 0:
                print(f"Processing sentence {i+1}/{len(sentences)}")
                
            corrected = corrector(sent, max_length=min(len(sent) * 2, 128))[0]['generated_text']
            corrected_sentences.append(corrected)
        
        # Combine the corrected sentences
        corrected_transcript = " ".join(corrected_sentences)
        print("Grammar correction complete")
        
        # Apply corrections at the word level
        corrected_words = simple_word_level_correction(words_dict, corrected_transcript)
        
        return corrected_words
        
    except Exception as e:
        print(f"Error in spelling correction: {e}")
        import traceback
        traceback.print_exc()
        return generate_timing_data(words_dict)  # Return original with generated timing

def create_corrected_segments(words_dict, max_width_pixels=700, font_path=None, 
                         font_size=40, max_duration_seconds=1.5, video_width=None):
    """
    Create word segments with corrected text, respecting width and duration constraints.
    Enhanced with detailed debugging to identify segmentation issues.
    
    Args:
        words_dict (dict): Dictionary with corrected words and timing data
        max_width_pixels (int): Maximum width of a segment in pixels
        font_path (str): Path to the font file
        font_size (int): Font size for width calculation
        max_duration_seconds (float): Maximum duration of a segment in seconds
        video_width (int): Width of the video frame after rotation
        
    Returns:
        dict: Dictionary with segments containing the corrected text
    """
    from PIL import ImageFont, ImageDraw, Image
    import os
    import re
    from core.media_processer import parse_time_to_seconds
    
    # If video_width is provided, calculate margin and adjust max_width
    if video_width:
        margin_percent = 0.05  # 5% margin
        margin_pixels = int(video_width * margin_percent)
        max_width_pixels = min(max_width_pixels, video_width - (2 * margin_pixels))
    
    print(f"Creating segments with max width: {max_width_pixels} pixels, font size: {font_size} pixels")
    print(f"Font path: {font_path}")
    print(f"Max duration: {max_duration_seconds} seconds")
    
    # Load font for width calculation
    try:
        if font_path and os.path.exists(font_path):
            try:
                font = ImageFont.truetype(font_path, font_size)
                print(f"Using font: {font_path}")
            except Exception as e:
                print(f"Error loading font: {e}, using default")
                font = ImageFont.load_default()
        else:
            print(f"Font path not found or not specified: {font_path}, using default")
            font = ImageFont.load_default()
    except Exception as e:
        print(f"Error in font loading: {e}, using fallback approach")
        font = ImageFont.load_default()
    
    # Create a temporary image for text measurement
    temp_image = Image.new('RGB', (max_width_pixels * 2, 100))
    draw = ImageDraw.Draw(temp_image)
    
    # Function to measure text width
    def measure_text_width(text):
        try:
            if hasattr(draw, 'textlength'):
                # For newer PIL versions
                width = draw.textlength(text, font=font)
                return width
            elif hasattr(draw, 'textsize'):
                # For older PIL versions
                width, _ = draw.textsize(text, font=font)
                return width
            else:
                # Fallback
                width = len(text) * (font_size // 2)
                return width
        except Exception as e:
            print(f"Error measuring text width for '{text}': {e}")
            width = len(text) * (font_size // 2)
            return width
    
    # Function to check if a word is punctuation
    def is_punctuation(text):
        return re.match(r'^[^\w\s]$', text) is not None
    
    # Get all words from the dictionary
    words = words_dict.get('words', [])
    
    # Debug: Check if we have words to work with
    print(f"Words to segment: {len(words)}")
    if len(words) > 0:
        first_word = words[0]
        print(f"First word: '{first_word.get('text', '')}', timing: {first_word.get('start_time')} - {first_word.get('end_time')}")
        
        # Test measuring the first word
        test_width = measure_text_width(first_word.get('text', ''))
        print(f"First word width: {test_width} pixels")
        
        # Test measuring a space
        space_width = measure_text_width(' ')
        print(f"Space width: {space_width} pixels")
    
    # Create segments
    segments = []
    current_segment = {
        'text': '',
        'start_time': None,
        'end_time': None,
        'words': []
    }
    
    # Measure space width
    space_width = measure_text_width(' ')
    
    # Track the current width
    current_width = 0
    
    # Track how many segments we start
    segment_start_count = 0
    
    # Track segment split decisions
    width_splits = 0
    duration_splits = 0
    
    # Group words into segments
    for i, word in enumerate(words):
        if i < 5 or i % 25 == 0:  # Log the first 5 words and then every 25th word
            print(f"Processing word {i+1}/{len(words)}: '{word.get('text', '')}'")
            
        word_text = word.get('text', '')
        
        # Skip empty words
        if not word_text.strip():
            print(f"Skipping empty word at index {i}")
            continue
        
        # Measure this word
        word_width = measure_text_width(word_text)
        if i < 5:
            print(f"Word '{word_text}' width: {word_width} pixels")
        
        # Check if this is the first word in the segment
        if current_segment['start_time'] is None:
            # Start a new segment
            segment_start_count += 1
            print(f"Starting segment {segment_start_count} with word: '{word_text}'")
            
            current_segment['start_time'] = word.get('start_time')
            current_segment['text'] = word_text
            current_segment['words'] = [word]
            current_width = word_width
            continue
        
        # Calculate start and end times
        segment_start = current_segment['start_time']
        word_end = word.get('end_time')
        
        # Check for None values
        if segment_start is None or word_end is None:
            print(f"Warning: Missing timing data for word {i}: '{word_text}'")
            print(f"  segment_start: {segment_start}, word_end: {word_end}")
            
            # Add word anyway with a best-effort approach
            if is_punctuation(word_text):
                current_segment['text'] = current_segment['text'] + word_text
            else:
                current_segment['text'] = current_segment['text'] + ' ' + word_text
                
            current_segment['words'].append(word)
            current_width += word_width
            continue
        
        # Convert times to seconds
        try:
            if isinstance(segment_start, str):
                start_sec = parse_time_to_seconds(segment_start)
            else:
                start_sec = segment_start
                
            if isinstance(word_end, str):
                end_sec = parse_time_to_seconds(word_end)
            else:
                end_sec = word_end
            
            # Calculate duration
            duration = end_sec - start_sec
            
            if i < 5:
                print(f"Segment duration with word {i}: {duration} seconds")
        except Exception as e:
            print(f"Error calculating duration for word {i}: {e}")
            print(f"  segment_start: {segment_start}, word_end: {word_end}")
            
            # Add word anyway with a best-effort approach
            if is_punctuation(word_text):
                current_segment['text'] = current_segment['text'] + word_text
            else:
                current_segment['text'] = current_segment['text'] + ' ' + word_text
                
            current_segment['words'].append(word)
            
            # Use word width without space if it's punctuation
            if is_punctuation(word_text):
                current_width += word_width
            else:
                current_width += space_width + word_width
                
            continue
        
        # Calculate the new width
        # Add space before the word unless it's punctuation
        if is_punctuation(word_text):
            new_width = current_width + word_width
        else:
            new_width = current_width + space_width + word_width
        
        if i < 5:
            print(f"New width with word {i}: {new_width} pixels (max: {max_width_pixels})")
        
        # Check if adding this word would exceed limits
        width_exceeded = new_width > max_width_pixels
        duration_exceeded = duration > max_duration_seconds
        
        if (width_exceeded or duration_exceeded) and not is_punctuation(word_text):
            # Log the split decision
            if width_exceeded:
                width_splits += 1
                print(f"Width limit exceeded at word {i} ({new_width} > {max_width_pixels}) - splitting segment")
            if duration_exceeded:
                duration_splits += 1
                print(f"Duration limit exceeded at word {i} ({duration} > {max_duration_seconds}) - splitting segment")
            
            # Finish the current segment
            current_segment['end_time'] = current_segment['words'][-1].get('end_time')
            segments.append(current_segment)
            
            # Start a new segment with this word
            segment_start_count += 1
            print(f"Starting segment {segment_start_count} with word: '{word_text}'")
            
            current_segment = {
                'text': word_text,
                'start_time': word.get('start_time'),
                'end_time': None,
                'words': [word]
            }
            current_width = word_width
        else:
            # Add word to the current segment
            if is_punctuation(word_text):
                # Append punctuation without space
                current_segment['text'] = current_segment['text'] + word_text
            else:
                # Add space before regular words
                current_segment['text'] = current_segment['text'] + ' ' + word_text
                
            current_segment['words'].append(word)
            current_width = new_width
    
    # Add the last segment if it has content
    if current_segment['start_time'] is not None:
        current_segment['end_time'] = current_segment['words'][-1].get('end_time')
        segments.append(current_segment)
    
    # Format the segments
    result = {'segments': []}
    for i, segment in enumerate(segments):
        result['segments'].append({
            'index': i + 1,
            'start_time': segment['start_time'],
            'end_time': segment['end_time'],
            'text': segment['text'],
            'words': segment['words']
        })
    
    print(f"Created {len(result['segments'])} segments")
    print(f"Split decisions: {width_splits} by width, {duration_splits} by duration")
    
    # If no segments were created, but we had words, this indicates a problem
    if len(result['segments']) == 0 and len(words) > 0:
        print("WARNING: No segments were created despite having words. Creating a fallback segment.")
        
        # Create a single segment containing all words as a fallback
        all_words = words
        segment_text = ' '.join([w.get('text', '') for w in all_words])
        
        result['segments'] = [{
            'index': 1,
            'start_time': all_words[0].get('start_time'),
            'end_time': all_words[-1].get('end_time'),
            'text': segment_text,
            'words': all_words
        }]
        
        print(f"Created 1 fallback segment with {len(all_words)} words")
    
    return result



def generate_timing_data(words_dict):
    """
    Generate estimated timing data for words that are missing it.
    
    Args:
        words_dict (dict): Dictionary containing word data
        
    Returns:
        dict: Updated words dictionary with estimated timing
    """
    import copy
    
    # Make a deep copy to avoid modifying the original
    result = copy.deepcopy(words_dict)
    words = result.get('words', [])
    
    # Total duration for the entire transcript (in seconds)
    total_duration = 60.0  # Default 1 minute if no duration specified
    
    # Calculate estimated timing
    word_count = len(words)
    if word_count == 0:
        return result
    
    # Each word gets an equal portion of the total duration
    time_per_word = total_duration / word_count
    
    # Start at time 0
    current_time = 0.0
    
    # Assign timing to each word
    for word in words:
        # Assign start and end times
        word['start_time'] = current_time
        current_time += time_per_word
        word['end_time'] = current_time
    
    return result

def simple_word_level_correction(words_dict, corrected_text):
    """
    Apply corrections using a simple approach that preserves timing data.
    
    Args:
        words_dict (dict): Original words dictionary with timing data
        corrected_text (str): The corrected full transcript text
        
    Returns:
        dict: Updated words dictionary with corrected text
    """
    import copy
    import re
    
    # Make a deep copy of the original words
    corrected_words = copy.deepcopy(words_dict)
    original_words_list = words_dict.get('words', [])
    
    # Debug output
    print(f"Original words count: {len(original_words_list)}")
    if len(original_words_list) > 0:
        first_word = original_words_list[0]
        print(f"First original word: '{first_word.get('text', '')}', " 
              f"timing: {first_word.get('start_time')} - {first_word.get('end_time')}")
    
    # Split the texts into words
    original_text = " ".join([word.get('text', '') for word in original_words_list])
    
    print(f"Original text: {original_text[:100]}...")
    print(f"Corrected text: {corrected_text[:100]}...")
    
    # Split the corrected text into words
    corrected_words_text = re.findall(r'\S+', corrected_text)
    
    # Generate a new words list
    new_words = []
    
    # Use the original word timing but the corrected word text
    # If word counts are different, distribute timing proportionally
    if len(original_words_list) == 0:
        return corrected_words
    
    if len(corrected_words_text) == 0:
        return words_dict
    
    # Calculate the ratio for timing distribution
    ratio = len(original_words_list) / len(corrected_words_text)
    
    # Distribute timing
    for i, word_text in enumerate(corrected_words_text):
        # Calculate the corresponding index in the original words
        orig_index = min(int(i * ratio), len(original_words_list) - 1)
        
        # Create a new word entry
        original_word = original_words_list[orig_index]
        new_word = copy.deepcopy(original_word)
        new_word['text'] = word_text
        
        new_words.append(new_word)
    
    # Update the words dictionary
    corrected_words['words'] = new_words
    
    # Debug output
    print(f"Corrected words count: {len(new_words)}")
    if len(new_words) > 0:
        first_word = new_words[0]
        print(f"First corrected word: '{first_word.get('text', '')}', " 
              f"timing: {first_word.get('start_time')} - {first_word.get('end_time')}")
    
    return corrected_words

def create_corrected_segments(words_dict, max_width_pixels=700, font_path=None, 
                         font_size=40, max_duration_seconds=1.5, video_width=None):
    """
    Create word segments with corrected text, respecting width and duration constraints.
    Fixed version that correctly creates segments from words with timing data.
    
    Args:
        words_dict (dict): Dictionary with corrected words and timing data
        max_width_pixels (int): Maximum width of a segment in pixels
        font_path (str): Path to the font file
        font_size (int): Font size for width calculation
        max_duration_seconds (float): Maximum duration of a segment in seconds
        video_width (int): Width of the video frame after rotation
        
    Returns:
        dict: Dictionary with segments containing the corrected text
    """
    from PIL import ImageFont, ImageDraw, Image
    import os
    import re
    
    # If video_width is provided, calculate margin and adjust max_width
    if video_width:
        margin_percent = 0.05  # 5% margin
        margin_pixels = int(video_width * margin_percent)
        max_width_pixels = min(max_width_pixels, video_width - (2 * margin_pixels))
    
    print(f"Creating segments with max width: {max_width_pixels} pixels, font size: {font_size} pixels")
    print(f"Font path: {font_path}")
    print(f"Max duration: {max_duration_seconds} seconds")
    
    # Load font for width calculation
    try:
        if font_path and os.path.exists(font_path):
            try:
                font = ImageFont.truetype(font_path, font_size)
                print(f"Using font: {font_path}")
            except Exception as e:
                print(f"Error loading font: {e}, using default")
                font = ImageFont.load_default()
        else:
            print(f"Font path not found or not specified: {font_path}, using default")
            font = ImageFont.load_default()
    except Exception as e:
        print(f"Error in font loading: {e}, using fallback approach")
        font = ImageFont.load_default()
    
    # Create a temporary image for text measurement
    temp_image = Image.new('RGB', (max_width_pixels * 2, 100))
    draw = ImageDraw.Draw(temp_image)
    
    # Function to measure text width
    def measure_text_width(text):
        try:
            if hasattr(draw, 'textlength'):
                # For newer PIL versions
                width = draw.textlength(text, font=font)
                return width
            elif hasattr(draw, 'textsize'):
                # For older PIL versions
                width, _ = draw.textsize(text, font=font)
                return width
            else:
                # Fallback
                width = len(text) * (font_size // 2)
                return width
        except Exception as e:
            print(f"Error measuring text width for '{text}': {e}")
            width = len(text) * (font_size // 2)
            return width
    
    # Function to check if a word is punctuation
    def is_punctuation(text):
        return re.match(r'^[^\w\s]$', text) is not None
    
    # Get all words from the dictionary
    words = words_dict.get('words', [])
    
    # Debug: Check if we have words to work with
    print(f"Words to segment: {len(words)}")
    if len(words) > 0:
        first_word = words[0]
        print(f"First word: '{first_word.get('text', '')}', timing: {first_word.get('start_time')} - {first_word.get('end_time')}")
        
        # Test measuring the first word
        test_width = measure_text_width(first_word.get('text', ''))
        print(f"First word width: {test_width} pixels")
        
        # Test measuring a space
        space_width = measure_text_width(' ')
        print(f"Space width: {space_width} pixels")
    
    # Measure space width
    space_width = measure_text_width(' ')
    
    # FIXED APPROACH: Create segments with at most max_width_pixels width
    segments = []
    current_segment = None
    current_segment_width = 0
    
    for i, word in enumerate(words):
        word_text = word.get('text', '')
        
        # Skip empty words
        if not word_text.strip():
            continue
            
        # Measure this word
        word_width = measure_text_width(word_text)
        
        # Calculate new width with this word
        new_width = word_width
        if current_segment:
            if is_punctuation(word_text):
                new_width = current_segment_width + word_width
            else:
                new_width = current_segment_width + space_width + word_width
        
        # Check if we need to start a new segment
        start_new_segment = False
        
        if not current_segment:
            # If no current segment, always start a new one
            start_new_segment = True
        elif new_width > max_width_pixels and not is_punctuation(word_text):
            # If adding this word would exceed max width, start a new segment
            # (unless it's punctuation, which always stays with the previous word)
            start_new_segment = True
        
        if start_new_segment:
            # If we already had a segment, finalize it
            if current_segment:
                segments.append(current_segment)
            
            # Start a new segment
            current_segment = {
                'text': word_text,
                'start_time': word.get('start_time'),
                'end_time': word.get('end_time'),
                'words': [word]
            }
            current_segment_width = word_width
        else:
            # Add to the current segment
            if is_punctuation(word_text):
                # Add punctuation without a space
                current_segment['text'] += word_text
            else:
                # Add with a space
                current_segment['text'] += ' ' + word_text
                
            # Update end time
            current_segment['end_time'] = word.get('end_time')
            
            # Add to words list
            current_segment['words'].append(word)
            
            # Update width
            current_segment_width = new_width
    
    # Add the last segment if there is one
    if current_segment:
        segments.append(current_segment)
    
    # Format the segments
    result = {'segments': []}
    for i, segment in enumerate(segments):
        result['segments'].append({
            'index': i + 1,
            'start_time': segment['start_time'],
            'end_time': segment['end_time'],
            'text': segment['text'],
            'words': segment['words']
        })
    
    print(f"Created {len(result['segments'])} segments")
    
    # If no segments were created, but we had words, create a fallback
    if len(result['segments']) == 0 and len(words) > 0:
        print("WARNING: No segments were created despite having words. Creating a fallback segment.")
        
        # Create a single segment containing all words as a fallback
        all_words = words
        segment_text = ' '.join([w.get('text', '') for w in all_words])
        
        result['segments'] = [{
            'index': 1,
            'start_time': all_words[0].get('start_time'),
            'end_time': all_words[-1].get('end_time'),
            'text': segment_text,
            'words': all_words
        }]
        
        print(f"Created 1 fallback segment with {len(all_words)} words")
    
    return result