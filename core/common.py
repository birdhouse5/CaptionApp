# core/common.py
def parse_time_to_seconds(time_str):
    """
    Convert a time string to seconds.
    Format: HH:MM:SS,mmm
    """
    time_parts = time_str.split(',')
    time_base = time_parts[0]
    milliseconds = int(time_parts[1]) if len(time_parts) > 1 else 0
    
    hours, minutes, seconds = map(int, time_base.split(':'))
    total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
    return total_seconds

def reconcile_edited_text_with_timings(edited_segments, original_words):
    """
    Reconcile edited segment text with original word timings.
    
    This function attempts to match words in the edited text with words in the original
    transcription to preserve timing information as much as possible.
    """
    import re
    from difflib import SequenceMatcher
    import copy
    
    # Make a deep copy of the segments to avoid modifying the original
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
                
                # Check type of prev_end and convert if necessary
                if isinstance(prev_end, str):
                    # Convert string time (like "00:00:10,500") to seconds (float)
                    from core.common import parse_time_to_seconds
                    prev_end_seconds = parse_time_to_seconds(prev_end)
                else:
                    prev_end_seconds = prev_end
                    
                # Estimate a reasonable duration (e.g., 0.3 seconds)
                estimated_duration = 0.3
                
                # Calculate new times
                new_start_time = prev_end_seconds
                new_end_time = new_start_time + estimated_duration
                
                # Convert back to string format if needed
                if isinstance(prev_end, str):
                    from core.media_processer import format_srt_timestamp
                    new_start_time = format_srt_timestamp(new_start_time)
                    new_end_time = format_srt_timestamp(new_end_time)
                
                matched_words.append({
                    'text': edited_word,
                    'start_time': new_start_time,
                    'end_time': new_end_time
                })
            else:
                # If this is the first word with no match, use the segment start time
                segment_start = segment.get('start_time', 0)
                
                # Check type of segment_start and convert if necessary
                if isinstance(segment_start, str):
                    # Convert string time to seconds
                    from core.common import parse_time_to_seconds
                    segment_start_seconds = parse_time_to_seconds(segment_start)
                else:
                    segment_start_seconds = segment_start
                    
                estimated_duration = 0.3
                
                # Calculate new times
                new_start_time = segment_start_seconds
                new_end_time = new_start_time + estimated_duration
                
                # Convert back to string format if needed
                if isinstance(segment_start, str):
                    from core.media_processer import format_srt_timestamp
                    new_start_time = format_srt_timestamp(new_start_time)
                    new_end_time = format_srt_timestamp(new_end_time)
                
                matched_words.append({
                    'text': edited_word,
                    'start_time': new_start_time,
                    'end_time': new_end_time
                })
        
        # Update the segment with matched words
        segment['words'] = matched_words
        
        # Adjust segment start and end times based on matched words
        if matched_words:
            segment['start_time'] = matched_words[0]['start_time']
            segment['end_time'] = matched_words[-1]['end_time']
    
    return updated_segments