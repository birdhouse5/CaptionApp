import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import threading
import cv2
from PIL import Image, ImageTk
from datetime import datetime
import json
import logging
# Import transcript editor
from gui.transcript_editor import TranscriptEditor

# Import the necessary functions from media_processer.py
from core.media_processer import (
    extract_audio,
    transcribe_audio,
    create_word_timestamps,
    process_media_for_gui,
    create_word_segments_with_max_width,
    process_segment_dict,
    process_word_dict,
    parse_time_to_seconds,
    process_complete_video_with_audio_rotated_extended
)

# Import utilities
from gui.utils import (
    map_font_to_path,
    map_color_to_rgb,
    map_font_size_to_scale,
    get_available_fonts,
    get_supported_file_extensions,
    process_single_video_with_dicts_extended,
    reconcile_edited_text_with_timings
)





def draw_preview_caption(image, font_path, font_size, text_color, bg_color, position_ratio, blur_radius, word_spacing):
    """
    Draw preview caption text on an image using the specified settings.
    
    Args:
        image: The input PIL Image
        font_path: Path to the TTF font file
        font_size: Font size in pixels
        text_color: RGBA tuple for text color
        bg_color: RGBA tuple for background color
        position_ratio: Vertical position as a ratio (0.0 to 1.0)
        blur_radius: Radius for the text shadow blur
        word_spacing: Spacing between words in pixels
        
    Returns:
        PIL Image with caption text drawn on it
    """
    from PIL import Image, ImageFont, ImageDraw, ImageFilter
    import numpy as np
    import os
    
    # Create a copy of the image
    image = image.copy()
    
    # Get image dimensions
    width, height = image.size
    
    # Convert to RGBA if not already
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    # Load font
    try:
        if font_path and os.path.exists(font_path):
            font = ImageFont.truetype(font_path, font_size)
        else:
            # Use default font if specified font not available
            font = ImageFont.load_default()
    except Exception as e:
        print(f"Error loading font: {e}, using default")
        font = ImageFont.load_default()
    
    # Example text
    example_text = "Example Caption Text"
    
    # Split into words
    words = example_text.split()
    
    # Create a layer for the shadows
    shadow_layer = Image.new("RGBA", image.size, (255, 255, 255, 0))
    shadow_draw = ImageDraw.Draw(shadow_layer)
    
    # Create a layer for the text
    text_layer = Image.new("RGBA", image.size, (255, 255, 255, 0))
    draw_text = ImageDraw.Draw(text_layer)
    
    # If background color is not 'none', create a background layer
    if bg_color[3] > 0:  # If alpha > 0
        bg_layer = Image.new("RGBA", image.size, (255, 255, 255, 0))
        draw_bg = ImageDraw.Draw(bg_layer)
    else:
        bg_layer = None
    
    # Calculate text size for entire phrase to determine centering
    try:
        if hasattr(draw_text, 'textlength'):
            # For newer PIL versions
            text_width = sum(draw_text.textlength(word, font=font) for word in words) + word_spacing * (len(words) - 1)
        elif hasattr(draw_text, 'textsize'):
            # For older PIL versions
            word_sizes = [draw_text.textsize(word, font=font) for word in words]
            text_width = sum(w for w, h in word_sizes) + word_spacing * (len(words) - 1)
        else:
            # Fallback
            text_width = len(example_text) * (font_size // 2)
    except Exception as e:
        print(f"Error measuring text: {e}")
        text_width = len(example_text) * (font_size // 2)
    
    # Calculate vertical position based on ratio
    y_position = int(height * position_ratio)
    
    # Calculate starting x position to center the text
    start_x = (width - text_width) // 2
    current_x = start_x
    
    # Draw background rectangle if needed
    if bg_layer is not None:
        # Determine background rectangle size (add padding)
        padding = font_size // 2
        bg_rect = (
            start_x - padding,
            y_position - padding,
            start_x + text_width + padding,
            y_position + font_size + padding
        )
        draw_bg.rectangle(bg_rect, fill=bg_color)
    
    # Process each word
    for i, word in enumerate(words):
        # Calculate word width
        try:
            if hasattr(draw_text, 'textlength'):
                word_width = draw_text.textlength(word, font=font)
            elif hasattr(draw_text, 'textsize'):
                word_width, _ = draw_text.textsize(word, font=font)
            else:
                word_width = len(word) * (font_size // 2)
        except Exception as e:
            print(f"Error calculating word width: {e}")
            word_width = len(word) * (font_size // 2)
        
        # Position for this word
        word_position = (current_x, y_position)
        
        # Draw the word shadow
        shadow_draw.text(word_position, word, font=font, fill=(0, 0, 0, 255))
        
        # Draw the actual word
        draw_text.text(word_position, word, font=font, fill=text_color)
        
        # Update position for next word
        current_x += word_width + word_spacing
    
    # Apply Gaussian blur to the shadow
    blurred_shadow = shadow_layer.filter(ImageFilter.GaussianBlur(blur_radius))
    
    # Composite the layers
    if bg_layer is not None:
        # Image -> Background -> Shadow -> Text
        result = Image.alpha_composite(image, bg_layer)
    else:
        # Image -> Shadow -> Text
        result = image
    
    result = Image.alpha_composite(result, blurred_shadow)
    result = Image.alpha_composite(result, text_layer)
    
    return result

def draw_preview_caption_draggable(image, font_path, font_size, text_color, text_highlight_color, bg_highlight_color, bg_color, position_ratio, blur_radius, word_spacing, highlight_text=True, highlight_background=False, show_current_word_only=False):
    """
    Draw preview caption text on an image using the specified settings.
    This version supports both text highlighting and background highlighting with separate colors.
    It also supports showing only the current word.
    
    Args:
        image: The input PIL Image
        font_path: Path to the TTF font file
        font_size: Font size in pixels
        text_color: RGB tuple for normal text color
        text_highlight_color: RGB tuple for highlighted text color
        bg_highlight_color: RGB tuple for highlighted background color
        bg_color: RGB tuple for background color or None for transparent
        position_ratio: [x, y] position ratios (0.0 to 1.0)
        blur_radius: Radius for the text shadow blur
        word_spacing: Spacing between words in pixels
        highlight_text: Whether to highlight text with a different color (boolean)
        highlight_background: Whether to highlight word backgrounds (boolean)
        show_current_word_only: Whether to show only the highlighted word (boolean)
        
    Returns:
        PIL Image with caption text drawn on it
    """
    from PIL import Image, ImageFont, ImageDraw, ImageFilter
    import os
    
    # Create a copy of the image
    image = image.copy()
    
    # Get image dimensions
    width, height = image.size
    
    # Convert to RGBA if not already
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    # Load font
    try:
        if font_path and os.path.exists(font_path):
            font = ImageFont.truetype(font_path, font_size)
        else:
            font = ImageFont.load_default()
    except Exception as e:
        print(f"Error loading font: {e}, using default")
        font = ImageFont.load_default()
    
    # Example text
    example_text = "Example Caption Text"
    words = example_text.split()
    
    # Create layers
    shadow_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_layer)
    
    text_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw_text = ImageDraw.Draw(text_layer)
    
    # Background layer for the entire caption
    if bg_color is not None:
        bg_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw_bg = ImageDraw.Draw(bg_layer)
    else:
        bg_layer = None
    
    # Highlight background layer (only used when highlight_background is True)
    highlight_bg_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    highlight_bg_draw = ImageDraw.Draw(highlight_bg_layer)
    
    # Determine which word to highlight
    middle_word_index = len(words) // 2
    
    # In "current word only" mode, we only need to calculate the width of the highlighted word
    if show_current_word_only:
        # Just get the middle word that will be highlighted
        current_word = words[middle_word_index]
        
        # Calculate its width
        try:
            if hasattr(draw_text, 'textlength'):
                word_width = draw_text.textlength(current_word, font=font)
            elif hasattr(draw_text, 'textsize'):
                word_width, _ = draw_text.textsize(current_word, font=font)
            else:
                word_width = len(current_word) * (font_size // 2)
        except Exception as e:
            print(f"Error calculating word width: {e}")
            word_width = len(current_word) * (font_size // 2)
        
        # Get height
        if hasattr(font, 'getbbox'):
            text_height = font.getbbox('Aj')[3]  # Use characters with ascenders and descenders
        elif hasattr(font, 'getsize'):
            _, text_height = font.getsize('Aj')
        else:
            text_height = font_size + 4
            
        # Calculate position - centered for single word
        x_ratio, y_ratio = position_ratio
        x_position = int(width * x_ratio) - (word_width // 2)
        y_position = int(height * y_ratio) - (text_height // 2)
        
        # Calculate background bounds with padding
        h_padding = int(font_size * 0.5)  # Horizontal padding
        v_padding = int(font_size * 0.3)  # Vertical padding - smaller for better centering
        
        # Calculate background dimensions for the single word
        bg_left = x_position - h_padding
        bg_top = y_position - v_padding
        bg_right = x_position + word_width + h_padding
        bg_bottom = y_position + text_height + v_padding
    else:
        # For full caption mode, calculate the dimensions of the entire text
        try:
            # Calculate the total width
            if hasattr(draw_text, 'textlength'):
                text_width = sum(draw_text.textlength(word, font=font) for word in words) + word_spacing * (len(words) - 1)
            elif hasattr(draw_text, 'textsize'):
                word_sizes = [draw_text.textsize(word, font=font) for word in words]
                text_width = sum(w for w, h in word_sizes) + word_spacing * (len(words) - 1)
            else:
                text_width = len(example_text) * (font_size // 2)
                
            # Calculate text height - approximate if not available
            if hasattr(font, 'getbbox'):
                # For newer PIL versions
                text_height = font.getbbox('Aj')[3]  # Use characters with ascenders and descenders
            elif hasattr(font, 'getsize'):
                # For older PIL versions
                _, text_height = font.getsize('Aj')
            else:
                # Fallback if we can't get exact height
                text_height = font_size + 4
        except Exception as e:
            print(f"Error measuring text: {e}")
            text_width = len(example_text) * (font_size // 2)
            text_height = font_size + 4
        
        # Calculate position
        x_ratio, y_ratio = position_ratio
        x_position = int(width * x_ratio) - (text_width // 2)
        y_position = int(height * y_ratio) - (text_height // 2)  # Center vertically
        
        # Calculate background bounds with padding
        h_padding = int(font_size * 0.5)  # Horizontal padding
        v_padding = int(font_size * 0.3)  # Vertical padding - smaller for better centering
        
        # Calculate background dimensions for full caption
        bg_left = x_position - h_padding
        bg_top = y_position - v_padding
        bg_right = x_position + text_width + h_padding
        bg_bottom = y_position + text_height + v_padding
    
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
    
    # Ensure background stays within image bounds
    min_margin = int(width * 0.01)
    if bg_left < min_margin:
        # Shift background and text right
        offset = min_margin - bg_left
        bg_left += offset
        bg_right += offset
        x_position += offset
    
    if bg_right > width - min_margin:
        # Shift background and text left
        offset = bg_right - (width - min_margin)
        bg_left -= offset
        bg_right -= offset
        x_position -= offset
    
    if bg_top < min_margin:
        # Shift background and text down
        offset = min_margin - bg_top
        bg_top += offset
        bg_bottom += offset
        y_position += offset
    
    if bg_bottom > height - min_margin:
        # Shift background and text up
        offset = bg_bottom - (height - min_margin)
        bg_top -= offset
        bg_bottom -= offset
        y_position -= offset
    
    # Draw background if bg_layer exists (i.e., bg_color is not None)
    if bg_layer is not None:
        # Corner radius for rounded rectangle
        corner_radius = int(font_size * 0.3)  # Adjust for desired roundness
        
        # For preview, use semi-transparent color if the color is set
        # Make sure we have RGBA
        if len(bg_color) == 3:
            # Convert RGB to RGBA by adding alpha
            preview_bg_color = (bg_color[0], bg_color[1], bg_color[2], 180)
        else:
            preview_bg_color = bg_color
        
        # Draw the rounded rectangle background
        draw_rounded_rectangle(draw_bg, (bg_left, bg_top, bg_right, bg_bottom), corner_radius, preview_bg_color)
    
    # In "current word only" mode, only draw the highlighted word
    if show_current_word_only:
        # Get the word to display
        word = words[middle_word_index]
        
        # Position for this word
        word_position = (x_position, y_position)
        
        # Draw the shadow (always black)
        shadow_draw.text(word_position, word, font=font, fill=(0, 0, 0))
        
        # For background highlighting, draw the highlight background
        if highlight_background:
            # Calculate the background for this specific word
            word_width_for_bg = x_position + word_width
            
            word_bg_left = x_position - int(font_size * 0.2)
            word_bg_top = y_position - int(font_size * 0.2)
            word_bg_right = word_width_for_bg + int(font_size * 0.2)
            word_bg_bottom = y_position + text_height + int(font_size * 0.2)
            
            # Make sure we have RGBA format for background highlight color
            if bg_highlight_color is not None:
                if len(bg_highlight_color) == 3:
                    highlight_bg_color = (bg_highlight_color[0], bg_highlight_color[1], bg_highlight_color[2], 200)
                else:
                    highlight_bg_color = bg_highlight_color
                
                # Draw the highlight background with rounded corners
                draw_rounded_rectangle(
                    highlight_bg_draw,
                    (word_bg_left, word_bg_top, word_bg_right, word_bg_bottom),
                    int(font_size * 0.15),  # Smaller corner radius
                    highlight_bg_color
                )
        
        # Determine text color
        if highlight_text:
            # Use highlight color for the word
            text_color_to_use = text_highlight_color[:3] if text_highlight_color is not None else (255, 255, 0)
        else:
            # Use normal text color
            text_color_to_use = text_color[:3] if text_color is not None else (255, 255, 255)
        
        # Draw the word
        draw_text.text(word_position, word, font=font, fill=text_color_to_use)
    else:
        # For full caption mode, process each word
        current_x = x_position
        for i, word in enumerate(words):
            # Calculate word width
            try:
                if hasattr(draw_text, 'textlength'):
                    word_width = draw_text.textlength(word, font=font)
                elif hasattr(draw_text, 'textsize'):
                    word_width, _ = draw_text.textsize(word, font=font)
                else:
                    word_width = len(word) * (font_size // 2)
            except Exception as e:
                print(f"Error calculating word width: {e}")
                word_width = len(word) * (font_size // 2)
            
            # Position for this word
            word_position = (current_x, y_position)
            
            # Is this the highlighted word?
            is_highlighted = (i == middle_word_index)
            
            # Draw the shadow (always black)
            shadow_draw.text(word_position, word, font=font, fill=(0, 0, 0))
            
            # For background highlighting, draw the highlight background for the highlighted word
            if highlight_background and is_highlighted:
                # Calculate the background for this specific word
                word_bg_left = current_x - int(font_size * 0.2)
                word_bg_top = y_position - int(font_size * 0.2)
                word_bg_right = current_x + word_width + int(font_size * 0.2)
                word_bg_bottom = y_position + text_height + int(font_size * 0.2)
                
                # Make sure we have RGBA format for background highlight color
                if bg_highlight_color is not None:
                    if len(bg_highlight_color) == 3:
                        highlight_bg_color = (bg_highlight_color[0], bg_highlight_color[1], bg_highlight_color[2], 200)
                    else:
                        highlight_bg_color = bg_highlight_color
                    
                    # Draw the highlight background with rounded corners
                    draw_rounded_rectangle(
                        highlight_bg_draw,
                        (word_bg_left, word_bg_top, word_bg_right, word_bg_bottom),
                        int(font_size * 0.15),  # Smaller corner radius
                        highlight_bg_color
                    )
            
            # Determine which color to use for text
            if highlight_text and is_highlighted:
                # Use text highlight color for the highlighted word if text highlighting is enabled
                text_color_to_use = text_highlight_color[:3] if text_highlight_color is not None else (255, 255, 0)
            else:
                # Use normal text color for other words or if text highlighting is disabled
                text_color_to_use = text_color[:3] if text_color is not None else (255, 255, 255)
            
            # Draw the word
            draw_text.text(word_position, word, font=font, fill=text_color_to_use)
            
            # Update position for next word
            current_x += word_width + word_spacing
    
    # Apply blur to shadow
    blurred_shadow = shadow_layer.filter(ImageFilter.GaussianBlur(blur_radius))
    
    # Composite the layers
    result = image
    
    # Only composite with background if it exists
    if bg_layer is not None:
        result = Image.alpha_composite(result, bg_layer)
    
    # Add the highlight background (only visible when highlight_background is True)
    result = Image.alpha_composite(result, highlight_bg_layer)
        
    result = Image.alpha_composite(result, blurred_shadow)
    result = Image.alpha_composite(result, text_layer)
    
    return result

class TranscriptionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Transcription and Caption Tool")
        self.root.geometry("800x800")
        self.root.resizable(True, True)
        
        # Default parameters with updated values
        self.word_spacing = 25
        self.segment_spacing = 15
        self.blur_radius = 5
        self.max_duration_seconds = 3
        self.max_chars = 100
        
        # Highlighting options
        self.highlight_text = tk.BooleanVar(value=True)  # Default to text highlighting enabled
        self.highlight_background = tk.BooleanVar(value=False)  # Default to background highlighting disabled
        
        # New option for showing only current word
        self.show_current_word_only = tk.BooleanVar(value=False)  # Default to showing all words
        
        # Video preview
        self.video_frame = None
        self.video_preview_image = None
        self.original_frame = None  # Store the original frame without captions
        
        # Caption position (x, y ratios from 0.0 to 1.0)
        self.current_position = [0.5, 0.8]  # Default to horizontally centered, 80% down
        
        # Get available fonts
        self.available_fonts = get_available_fonts()
        
        # Create the main menu interface
        self.create_main_menu()
        
    def create_main_menu(self):
        # Clear any existing widgets
        for widget in self.root.winfo_children():
            widget.destroy()
            
        # Main title
        title_label = tk.Label(self.root, text="Select an Option", font=("Arial", 14, "bold"))
        title_label.pack(pady=20)
        
        # Button frame
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)
        
        
        # Create transcript button
        transcript_button = tk.Button(
            button_frame, 
            text="Create Transcript", 
            width=20, 
            height=2,
            command=self.open_transcript_window,
            state=tk.NORMAL  # Keep button enabled but change functionality
        )
        transcript_button.grid(row=0, column=0, padx=10)
        
        # Create captions button
        captions_button = tk.Button(
            button_frame, 
            text="Create Captions", 
            width=20, 
            height=2,
            command=self.open_captions_window,
            state=tk.NORMAL
        )
        captions_button.grid(row=0, column=1, padx=10)
        
        
    def open_transcript_window(self):
        # Clear main window
        for widget in self.root.winfo_children():
            widget.destroy()
            
        self.root.title("Create Transcript")
        
        # File path variable
        self.transcript_file_path = tk.StringVar()
        
        # Header
        header_label = tk.Label(self.root, text="Create Transcript", font=("Arial", 14, "bold"))
        header_label.pack(pady=20)
        
        # File path display
        path_frame = tk.Frame(self.root)
        path_frame.pack(fill=tk.X, padx=20)
        
        path_label = tk.Label(path_frame, text="File: ", width=5, anchor="w")
        path_label.grid(row=0, column=0, sticky="w")
        
        path_display = tk.Label(path_frame, textvariable=self.transcript_file_path, width=40, anchor="w", bg="#f0f0f0")
        path_display.grid(row=0, column=1, sticky="w")
        
        # Buttons frame
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=20)
        
        # Select file button
        select_button = tk.Button(
            button_frame, 
            text="Select File", 
            width=15,
            command=self.select_transcript_file
        )
        select_button.grid(row=0, column=0, padx=10)
        
        # Run button (initially disabled)
        self.run_transcript_button = tk.Button(
            button_frame, 
            text="Run", 
            width=15,
            state=tk.DISABLED,
            command=self.run_transcript
        )
        self.run_transcript_button.grid(row=0, column=1, padx=10)
        
        # Status label
        self.status_label = tk.Label(self.root, text="", fg="blue")
        self.status_label.pack(pady=10)
        
        # Back button
        back_button = tk.Button(
            self.root, 
            text="Back", 
            width=10,
            command=self.create_main_menu
        )
        back_button.pack(side=tk.BOTTOM, pady=10)
        
    def open_captions_window(self):
        # Clear main window
        for widget in self.root.winfo_children():
            widget.destroy()
            
        self.root.title("Create Captions")
        
        # Increase window size to accommodate options and preview
        self.root.geometry("800x800")
        
        # File path variable
        self.captions_file_path = tk.StringVar()
        
        # Option variables - default to first available font
        default_font = self.available_fonts[0]['name'] if self.available_fonts else "Default"
        self.font_var = tk.StringVar(value=default_font)
        self.font_size_var = tk.StringVar(value="large")
        self.text_color_var = tk.StringVar(value="Sand")
        self.bg_color_var = tk.StringVar(value="None")  # Default to transparent
        
        # Separate highlight colors for text and background
        self.text_highlight_color_var = tk.StringVar(value="Green")
        self.bg_highlight_color_var = tk.StringVar(value="Green")

        # Main container with left and right panes
        main_container = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left pane for controls
        left_pane = tk.Frame(main_container)
        main_container.add(left_pane, width=400)
        
        # Right pane for video preview
        right_pane = tk.Frame(main_container)
        main_container.add(right_pane, width=400)
        
        # Header
        header_label = tk.Label(left_pane, text="Create Captions", font=("Arial", 14, "bold"))
        header_label.pack(pady=10)
        
        # Main container for controls
        main_frame = tk.Frame(left_pane)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # File selection section
        file_section = tk.LabelFrame(main_frame, text="File Selection", padx=10, pady=10)
        file_section.pack(fill=tk.X, pady=5)
        
        # File path display
        path_frame = tk.Frame(file_section)
        path_frame.pack(fill=tk.X)
        
        path_label = tk.Label(path_frame, text="File: ", width=5, anchor="w")
        path_label.grid(row=0, column=0, sticky="w")
        
        path_display = tk.Label(path_frame, textvariable=self.captions_file_path, width=40, anchor="w", bg="#f0f0f0")
        path_display.grid(row=0, column=1, sticky="w")
        
        # Select file button
        select_button = tk.Button(
            file_section, 
            text="Select File", 
            width=15,
            command=lambda: self.select_captions_file()
        )
        select_button.pack(pady=10)
        
        # Options section
        options_section = tk.LabelFrame(main_frame, text="Caption Options", padx=10, pady=10)
        options_section.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Font options
        font_frame = tk.Frame(options_section)
        font_frame.pack(fill=tk.X, pady=5)
        
        font_label = tk.Label(font_frame, text="Font:", width=15, anchor="w")
        font_label.grid(row=0, column=0, sticky="w")
        
        # Create dropdown with available fonts
        font_names = [font['name'] for font in self.available_fonts]
        font_dropdown = ttk.Combobox(font_frame, textvariable=self.font_var, values=font_names, width=20)
        font_dropdown.grid(row=0, column=1, sticky="w")
        font_dropdown.bind("<<ComboboxSelected>>", self.update_caption_preview)
        
        # Font size options
        font_size_frame = tk.Frame(options_section)
        font_size_frame.pack(fill=tk.X, pady=5)
        
        font_size_label = tk.Label(font_size_frame, text="Font Size:", width=15, anchor="w")
        font_size_label.grid(row=0, column=0, sticky="w")
        
        font_size_dropdown = tk.OptionMenu(font_size_frame, self.font_size_var, "small", "medium", "large",
                                          command=self.update_caption_preview)
        font_size_dropdown.grid(row=0, column=1, sticky="w")
        
        # Text color options
        text_color_frame = tk.Frame(options_section)
        text_color_frame.pack(fill=tk.X, pady=5)

        text_color_label = tk.Label(text_color_frame, text="Text Color:", width=15, anchor="w")
        text_color_label.grid(row=0, column=0, sticky="w")

        # List of color options
        text_color_options = [
            'White', 'Black', 
            'Purple', 'Green', 'Orange',
            'Red', 'Pink', 'Light Blue', 'Dark Blue', 'Olive', 'Yellow', 'Sand'
        ]

        text_color_dropdown = ttk.Combobox(text_color_frame, textvariable=self.text_color_var, values=text_color_options, width=15)
        text_color_dropdown.grid(row=0, column=1, sticky="w")
        text_color_dropdown.bind("<<ComboboxSelected>>", self.update_caption_preview)

        # Background color options
        bg_color_frame = tk.Frame(options_section)
        bg_color_frame.pack(fill=tk.X, pady=5)

        bg_color_label = tk.Label(bg_color_frame, text="Background Color:", width=15, anchor="w")
        bg_color_label.grid(row=0, column=0, sticky="w")

        # Background color options should include "None" for transparent
        bg_color_options = ['None'] + text_color_options

        bg_color_dropdown = ttk.Combobox(bg_color_frame, textvariable=self.bg_color_var, values=bg_color_options, width=15)
        bg_color_dropdown.grid(row=0, column=1, sticky="w")
        bg_color_dropdown.bind("<<ComboboxSelected>>", self.update_caption_preview)
        
        # Caption Style section
        style_frame = tk.LabelFrame(options_section, text="Caption Style", padx=10, pady=5)
        style_frame.pack(fill=tk.X, pady=5)
        
        # Current word only option
        current_word_frame = tk.Frame(style_frame)
        current_word_frame.pack(fill=tk.X, pady=2)
        
        current_word_label = tk.Label(current_word_frame, text="Show Current Word Only:", width=15, anchor="w")
        current_word_label.grid(row=0, column=0, sticky="w")
        
        current_word_checkbox = tk.Checkbutton(current_word_frame, variable=self.show_current_word_only,
                                             command=self.update_caption_preview)
        current_word_checkbox.grid(row=0, column=1, sticky="w")
        
        # Highlight Options section
        highlight_frame = tk.LabelFrame(options_section, text="Highlight Options", padx=10, pady=5)
        highlight_frame.pack(fill=tk.X, pady=5)
        
        # Text highlighting checkbox
        text_highlight_frame = tk.Frame(highlight_frame)
        text_highlight_frame.pack(fill=tk.X, pady=2)
        
        text_highlight_label = tk.Label(text_highlight_frame, text="Highlight Text:", width=15, anchor="w")
        text_highlight_label.grid(row=0, column=0, sticky="w")
        
        text_highlight_checkbox = tk.Checkbutton(text_highlight_frame, variable=self.highlight_text,
                                                command=self.update_caption_preview)
        text_highlight_checkbox.grid(row=0, column=1, sticky="w")
        
        # Text highlight color
        text_highlight_color_frame = tk.Frame(highlight_frame)
        text_highlight_color_frame.pack(fill=tk.X, pady=2)
        
        text_highlight_color_label = tk.Label(text_highlight_color_frame, text="Text Highlight Color:", width=15, anchor="w")
        text_highlight_color_label.grid(row=0, column=0, sticky="w")
        
        text_highlight_color_dropdown = ttk.Combobox(text_highlight_color_frame, textvariable=self.text_highlight_color_var, 
                                                   values=text_color_options, width=15)
        text_highlight_color_dropdown.grid(row=0, column=1, sticky="w")
        text_highlight_color_dropdown.bind("<<ComboboxSelected>>", self.update_caption_preview)
        
        # Background highlighting checkbox
        bg_highlight_frame = tk.Frame(highlight_frame)
        bg_highlight_frame.pack(fill=tk.X, pady=2)
        
        bg_highlight_label = tk.Label(bg_highlight_frame, text="Highlight BG:", width=15, anchor="w")
        bg_highlight_label.grid(row=0, column=0, sticky="w")
        
        bg_highlight_checkbox = tk.Checkbutton(bg_highlight_frame, variable=self.highlight_background,
                                              command=self.update_caption_preview)
        bg_highlight_checkbox.grid(row=0, column=1, sticky="w")
        
        # Background highlight color
        bg_highlight_color_frame = tk.Frame(highlight_frame)
        bg_highlight_color_frame.pack(fill=tk.X, pady=2)
        
        bg_highlight_color_label = tk.Label(bg_highlight_color_frame, text="BG Highlight Color:", width=15, anchor="w")
        bg_highlight_color_label.grid(row=0, column=0, sticky="w")
        
        bg_highlight_color_dropdown = ttk.Combobox(bg_highlight_color_frame, textvariable=self.bg_highlight_color_var, 
                                                 values=text_color_options, width=15)
        bg_highlight_color_dropdown.grid(row=0, column=1, sticky="w")
        bg_highlight_color_dropdown.bind("<<ComboboxSelected>>", self.update_caption_preview)
        
        # Status label
        self.status_label = tk.Label(main_frame, text="", fg="blue")
        self.status_label.pack(pady=5)
        
        # Button section
        button_section = tk.Frame(main_frame)
        button_section.pack(fill=tk.X, pady=10)

        # Run button - initially disabled
        self.run_captions_button = tk.Button(
            button_section, 
            text="Run", 
            width=15,
            state=tk.DISABLED,
            command=self.run_captions
        )
        self.run_captions_button.pack(side=tk.LEFT, padx=10)

        # Back button
        back_button = tk.Button(
            button_section, 
            text="Back", 
            width=15,
            command=self.create_main_menu
        )
        back_button.pack(side=tk.RIGHT, padx=10)
        
        # Setup the video preview area in the right pane
        preview_label = tk.Label(right_pane, text="Video Preview", font=("Arial", 12, "bold"))
        preview_label.pack(pady=5)
        
        # Frame to display video preview
        self.video_frame = tk.Label(right_pane, bg="black", width=400, height=300)
        self.video_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create a label to show when no video is selected
        self.no_video_label = tk.Label(
            self.video_frame, 
            text="No video selected", 
            fg="white", 
            bg="black", 
            font=("Arial", 14)
        )
        self.no_video_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    def update_caption_preview(self, *args):
        """
        Update the caption preview on the video frame based on current settings.
        This is called whenever caption settings change.
        """
        # If no video is loaded, don't try to update captions
        if not hasattr(self, 'original_frame') or self.original_frame is None:
            return
        
        try:
            # Get current caption settings
            font_path = map_font_to_path(self.font_var.get())
            font_size = int(self.original_frame.height * map_font_size_to_scale(self.font_size_var.get()))
            text_color = map_color_to_rgb(self.text_color_var.get())
            
            # Determine background color - use None if "None" is selected
            if self.bg_color_var.get() == "None":
                bg_color = None
            else:
                bg_color = map_color_to_rgb(self.bg_color_var.get())
            
            # Update the preview using the current settings
            self.update_video_preview()
            
        except Exception as e:
            print(f"Error updating caption preview: {e}")
            import traceback
            traceback.print_exc()

    def update_ui_state(self):
        """Update the UI elements based on the current highlight mode and background setting."""
        highlight_mode = self.highlight_mode.get()
        
        if highlight_mode == "text":
            # For text highlighting mode
            self.highlight_color_label.config(text="Highlight Color:")
            self.highlight_color_dropdown.config(state="normal")
            
            # Allow background to be toggled
            self.bg_enable_checkbox.config(state="normal")
            
            # Update background color dropdown state
            bg_enabled = self.enable_background.get()
            if bg_enabled:
                self.bg_color_dropdown.config(state="normal")
                self.bg_color_label.config(state="normal")
            else:
                self.bg_color_dropdown.config(state="disabled")
                self.bg_color_label.config(state="disabled")
                
        elif highlight_mode == "background":
            # For background highlighting mode
            self.highlight_color_label.config(text="Highlight BG Color:")
            self.highlight_color_dropdown.config(state="normal")
            
            # Force background to be enabled and checkbox disabled
            self.enable_background.set(True)
            self.bg_enable_checkbox.config(state="disabled")
            
            # Enable background color setting
            self.bg_color_dropdown.config(state="normal")
            self.bg_color_label.config(state="normal")
        
        # Update the preview with the new settings
        self.update_caption_preview()
    
    def extract_first_frame(self, video_path):
            """
            Extract the first frame from a video and return it as a PIL Image.
            """
            try:
                # Open the video file
                cap = cv2.VideoCapture(video_path)
                
                # Check if video opened successfully
                if not cap.isOpened():
                    print(f"Error: Could not open video {video_path}")
                    return None
                
                # Read the first frame
                ret, frame = cap.read()
                
                # Release the video capture object
                cap.release()
                
                if not ret:
                    print("Error: Could not read frame from video")
                    return None
                
                # Rotate frame 90 degrees clockwise to match the processing rotation
                frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                
                # Convert the frame from BGR (OpenCV format) to RGB (PIL format)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Create a PIL Image
                pil_image = Image.fromarray(frame_rgb)
                
                return pil_image
                
            except Exception as e:
                print(f"Error extracting first frame: {e}")
                return None
        
    def update_video_preview(self, video_path=None):
        """
        Update the video preview area with the first frame of the selected video.
        If video_path is None, just redraw current frame with captions.
        """
        # First, check if video_frame exists
        if not hasattr(self, 'video_frame') or self.video_frame is None:
            return
            
        # If we're loading a new video
        if video_path is not None:
            # Clear previous preview
            if hasattr(self, 'video_preview_image') and self.video_preview_image:
                self.video_preview_image = None
            
            # Remove "No video selected" label
            if hasattr(self, 'no_video_label'):
                self.no_video_label.place_forget()
            
            try:
                # Extract first frame
                frame = self.extract_first_frame(video_path)
                
                if frame is None:
                    # If frame extraction failed, show error message
                    self.video_frame.config(text="Error loading video preview")
                    return
                
                # Store the original frame without captions
                self.original_frame = frame.copy()
                
            except Exception as e:
                print(f"Error updating video preview: {e}")
                import traceback
                traceback.print_exc()
                
                # Show error message
                self.video_frame.config(text=f"Error: {str(e)}")
                return
        
        # If we don't have an original frame yet, nothing to show
        if not hasattr(self, 'original_frame') or self.original_frame is None:
            return
        
        try:
            # Get frame dimensions - use default values if widget isn't drawn yet
            frame_width = self.video_frame.winfo_width()
            frame_height = self.video_frame.winfo_height()
            
            # Make sure we have valid dimensions (if widget hasn't been drawn yet)
            if frame_width <= 1:
                frame_width = 400
            if frame_height <= 1:
                frame_height = 300
                
            # Get the original image dimensions
            original_width, original_height = self.original_frame.size
                
            # Calculate the scaling factor to fit the frame in the preview area
            width_ratio = frame_width / original_width
            height_ratio = frame_height / original_height
            scale_factor = min(width_ratio, height_ratio)
            
            # Calculate new dimensions
            new_width = int(original_width * scale_factor)
            new_height = int(original_height * scale_factor)
            
            # Store the preview dimensions for drag coordinate conversion
            self.preview_dimensions = {
                'original': (original_width, original_height),
                'preview': (new_width, new_height),
                'scale_factor': scale_factor
            }
            
            # Get current caption settings
            font_path = map_font_to_path(self.font_var.get())
            font_size = int(self.original_frame.height * map_font_size_to_scale(self.font_size_var.get()))
            text_color = map_color_to_rgb(self.text_color_var.get())
            
            # Get separate highlight colors
            text_highlight_color = map_color_to_rgb(self.text_highlight_color_var.get())
            bg_highlight_color = map_color_to_rgb(self.bg_highlight_color_var.get())
            
            # Determine background color - use None if "None" is selected
            if self.bg_color_var.get() == "None":
                bg_color = None
            else:
                bg_color = map_color_to_rgb(self.bg_color_var.get())
            
            position_ratio = self.current_position  # Use stored position for dragging
            
            # Use fixed values instead of UI variables
            blur_radius = self.blur_radius
            word_spacing = self.word_spacing
            
            # Get highlight options
            highlight_text = self.highlight_text.get()
            highlight_background = self.highlight_background.get()
            
            # Get current word only option
            show_current_word_only = self.show_current_word_only.get()
            
            # Create a copy of the original frame
            captioned_frame = self.original_frame.copy()
            
            # Apply caption to the frame with the current highlighting options
            captioned_frame = draw_preview_caption_draggable(
                captioned_frame,
                font_path,
                font_size,
                text_color,
                text_highlight_color,  # Pass the text highlight color
                bg_highlight_color,    # Pass the background highlight color
                bg_color,
                position_ratio,
                blur_radius,
                word_spacing,
                highlight_text,
                highlight_background,
                show_current_word_only  # Pass the show current word only option
            )
            
            # Resize the frame
            resized_frame = captioned_frame.resize((new_width, new_height), Image.LANCZOS)
            
            # Convert PIL image to Tkinter PhotoImage
            self.video_preview_image = ImageTk.PhotoImage(resized_frame)
            
            # Update the preview frame
            self.video_frame.config(image=self.video_preview_image)
            
            # Setup the drag and drop functionality if not already set up
            if not hasattr(self, 'drag_enabled') or not self.drag_enabled:
                self.setup_drag_functionality()
                
        except Exception as e:
            print(f"Error updating caption preview: {e}")
            import traceback
            traceback.print_exc()

    def select_transcript_file(self):
        # Open file dialog
        file_path = filedialog.askopenfilename(
            title="Select Audio/Video File",
            filetypes=[("Media Files", "*.mp3 *.mp4 *.wav *.m4a *.flac"), ("All Files", "*.*")]
        )
        
        if file_path:
            # Check if file format is valid
            _, file_extension = os.path.splitext(file_path)
            file_extension = file_extension.lower()  # Convert to lowercase
            
            if file_extension not in ['.mp3', '.mp4', '.wav', '.m4a', '.flac']:
                messagebox.showerror("Invalid Format", f"File format {file_extension} is not supported. Please select a supported audio/video file.")
                return
            
            # Set file path and enable run button
            self.transcript_file_path.set(file_path)
            self.run_transcript_button.config(state=tk.NORMAL)

    def select_captions_file(self):
        # Open file dialog with explicit file types
        file_path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[
                ("MP4 files", "*.mp4"),
                ("MOV files", "*.mov"),
                ("AVI files", "*.avi"),
                ("MKV files", "*.mkv"),
                ("All Video Files", "*.mp4 *.mov *.avi *.mkv"),
                ("All Files", "*.*")
            ]
        )
        
        # Debug print
        print(f"Selected file: {file_path}")
        
        if file_path:
            # Check if file format is valid
            _, file_extension = os.path.splitext(file_path)
            file_extension = file_extension.lower()  # Convert to lowercase
            
            print(f"File extension: {file_extension}")
            
            if file_extension not in ['.mp4', '.mov', '.avi', '.mkv']:
                messagebox.showerror("Invalid Format", f"File format {file_extension} is not supported. Please select a supported video file format.")
                return
            
            # Set file path and enable run button - check if run_captions_button exists first
            self.captions_file_path.set(file_path)
            
            # Find and enable the run button if it exists
            if hasattr(self, 'run_captions_button'):
                self.run_captions_button['state'] = tk.NORMAL
            
            # Make sure video_frame is initialized before updating preview
            if hasattr(self, 'video_frame') and self.video_frame is not None:
                # Update video preview
                self.update_video_preview(file_path)
            else:
                print("Warning: video_frame not initialized, skipping preview update")
                # You could add a delayed call to update the preview after a short time:
                self.root.after(100, lambda: self.update_video_preview(file_path))

    def run_transcript(self):
        """
        Process audio/video file to generate transcript only.
        This runs in a separate thread to keep UI responsive.
        """
        self.status_label.config(text="Processing... Please wait.")
        self.run_transcript_button.config(state=tk.DISABLED)
        
        # Start processing in a separate thread
        threading.Thread(target=self._process_transcript, daemon=True).start()

    def _process_transcript(self):
        """
        Background thread for transcript processing.
        """
        try:
            input_path = self.transcript_file_path.get()
            
            # Update status
            self.root.after(0, lambda: self.status_label.config(text="Processing... This may take a while."))
            
            # Create output directory if needed
            output_dir = os.path.join(os.path.dirname(input_path), "output")
            os.makedirs(output_dir, exist_ok=True)
            
            # Extract audio from media file
            print("Extracting audio...")
            audio_path = extract_audio(input_path)
            
            # Transcribe audio
            print("Transcribing audio...")
            transcription = transcribe_audio(audio_path)
            
            # Create word timestamps
            print("Processing word timestamps...")
            words = create_word_timestamps(transcription)
            
            # Create transcript output path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.basename(input_path)
            name, ext = os.path.splitext(filename)
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
                import json
                json.dump(words, f, indent=2)
                
            print(f"Transcript saved to: {output_path}")
            print(f"Word timestamps saved to: {words_json_path}")
            
            # Show success message
            self.root.after(0, lambda: self.status_label.config(text=f"Transcript saved to {output_path}"))
            self.root.after(0, lambda: messagebox.showinfo("Success", f"Transcription complete!\nSaved to: {output_path}"))
            self.root.after(0, lambda: self.run_transcript_button.config(state=tk.NORMAL))
            
        except Exception as e:
            # Show error message
            error_msg = f"Error: {str(e)}"
            self.root.after(0, lambda: self.status_label.config(text=error_msg))
            self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
            self.root.after(0, lambda: self.run_transcript_button.config(state=tk.NORMAL))

# Add to app_window.py

    # Add to app_window.py

    def run_captions(self):
        """
        Process video file to generate captions with automatic correction.
        This runs in a separate thread to keep UI responsive.
        """
        self.status_label.config(text="Processing... Please wait.")
        self.run_captions_button.config(state=tk.DISABLED)
        
        # Start processing in a separate thread
        threading.Thread(target=self._process_captions_with_auto_correction, daemon=True).start()
    
    
    def _process_captions_with_auto_correction(self):
        """
        Process the captions with automatic grammar correction using the simplified approach.
        This runs in a background thread.
        """
        try:
            input_path = self.captions_file_path.get()
            
            # Update status
            self.root.after(0, lambda: self.status_label.config(text="Transcribing audio... This may take a while."))
            
            # Create output directory if needed
            output_dir = os.path.join(os.path.dirname(input_path), "output")
            os.makedirs(output_dir, exist_ok=True)
            
            # Step 1: Extract audio and transcribe
            audio_path = extract_audio(input_path)
            transcription = transcribe_audio(audio_path)
            
            # Create word timestamps
            words = create_word_timestamps(transcription)
            
            # Get video dimensions to calculate maximum caption width
            cap = cv2.VideoCapture(input_path)
            orig_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            orig_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            
            # After 90-degree clockwise rotation:
            rotated_width = orig_height
            rotated_height = orig_width
            
            # Calculate maximum caption width (80% of rotated width)
            max_caption_width_pixels = int(rotated_width * 0.8)
            
            # Estimate font size
            font_path = map_font_to_path(self.font_var.get())
            font_scale = map_font_size_to_scale(self.font_size_var.get())
            estimated_font_size = int(rotated_height * font_scale)
            
            # Update status for correction phase
            self.root.after(0, lambda: self.status_label.config(text="Applying automatic grammar correction..."))
            
            # Check if required libraries are installed
            correction_available = True
            try:
                from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline
                import nltk
            except ImportError:
                correction_available = False
                self.root.after(0, lambda: messagebox.showwarning("Missing Libraries", 
                                                            "Grammar correction requires additional libraries. "
                                                            "Continuing with original transcript.\n\n"
                                                            "To enable correction, run:\n"
                                                            "pip install transformers torch nltk"))
            
            # Apply grammar correction if available
            if correction_available:
                try:
                    from gui.utils import apply_spelling_correction
                    corrected_words = apply_spelling_correction(input_path, words)
                except Exception as e:
                    print(f"Error in grammar correction: {e}")
                    import traceback
                    traceback.print_exc()
                    
                    # Fall back to original words
                    corrected_words = words
                    self.root.after(0, lambda: messagebox.showwarning("Correction Error", 
                                                                f"Error during grammar correction: {str(e)}\n"
                                                                "Continuing with original transcript."))
            else:
                # Use original words if correction not available
                corrected_words = words
            
            # Create segments from the corrected words
            from gui.utils import create_corrected_segments
            segments = create_corrected_segments(
                corrected_words,
                max_width_pixels=max_caption_width_pixels,
                font_path=font_path,
                font_size=estimated_font_size,
                max_duration_seconds=self.max_duration_seconds,
                video_width=rotated_width
            )
            
            # Store the data for later use
            self.transcription_data = {
                'input_path': input_path,
                'words': words,
                'corrected_words': corrected_words,
                'segments': segments
            }
            
            # Update status for caption generation
            self.root.after(0, lambda: self.status_label.config(text="Generating captions..."))
            
            # Get caption settings
            font_path = map_font_to_path(self.font_var.get())
            text_color = map_color_to_rgb(self.text_color_var.get())
            text_highlight_color = map_color_to_rgb(self.text_highlight_color_var.get())
            bg_highlight_color = map_color_to_rgb(self.bg_highlight_color_var.get())
            font_scale = map_font_size_to_scale(self.font_size_var.get())
            
            # Determine background color
            if self.bg_color_var.get() == "None":
                bg_color = None
            else:
                bg_color = map_color_to_rgb(self.bg_color_var.get())
            
            # Get position ratio
            position_ratio = (self.current_position[0], self.current_position[1])
            
            # Get other settings
            word_spacing = self.word_spacing
            segment_spacing = self.segment_spacing
            blur_radius = self.blur_radius
            highlight_text = self.highlight_text.get()
            highlight_background = self.highlight_background.get()
            show_current_word_only = self.show_current_word_only.get()
            
            # Create output filename based on current date/time
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.basename(input_path)
            name, ext = os.path.splitext(filename)
            output_path = os.path.join(output_dir, f"{name}_{timestamp}_captioned{ext}")
            
            # Save the corrected data to JSON files for reference
            import json
            
            if correction_available and words != corrected_words:
                # Save the corrected words
                corrected_words_path = os.path.join(output_dir, f"{name}_{timestamp}_corrected_words.json")
                with open(corrected_words_path, 'w', encoding='utf-8') as f:
                    json.dump(corrected_words, f, indent=2)
                    
            # Save the segments
            segments_json_path = os.path.join(output_dir, f"{name}_{timestamp}_segments.json")
            with open(segments_json_path, 'w', encoding='utf-8') as f:
                json.dump(segments, f, indent=2)
            
            # Process video with captions
            from core.media_processer import process_segment_dict, process_complete_video_with_audio_rotated_extended
            
            # Convert segments for video processing
            processed_segments = []
            for segment in segments['segments']:
                # Convert times to seconds
                start_time = segment['start_time']
                end_time = segment['end_time']
                
                if isinstance(start_time, str):
                    from core.media_processer import parse_time_to_seconds
                    start_time_sec = parse_time_to_seconds(start_time)
                else:
                    start_time_sec = start_time
                    
                if isinstance(end_time, str):
                    from core.media_processer import parse_time_to_seconds
                    end_time_sec = parse_time_to_seconds(end_time)
                else:
                    end_time_sec = end_time
                
                # Create processed segment
                processed_segment = {
                    'text': segment['text'],
                    'start_time': start_time_sec,
                    'end_time': end_time_sec,
                    'words': []
                }
                
                # Add words with proper timing
                for word in segment['words']:
                    word_start = word['start_time']
                    word_end = word['end_time']
                    
                    if isinstance(word_start, str):
                        word_start_sec = parse_time_to_seconds(word_start)
                    else:
                        word_start_sec = word_start
                        
                    if isinstance(word_end, str):
                        word_end_sec = parse_time_to_seconds(word_end)
                    else:
                        word_end_sec = word_end
                    
                    processed_segment['words'].append({
                        'text': word['text'],
                        'start_time': word_start_sec,
                        'end_time': word_end_sec
                    })
                
                processed_segments.append(processed_segment)
            
            # Process the video
            process_complete_video_with_audio_rotated_extended(
                input_path, output_path, processed_segments, font_path, 
                normal_color=text_color, 
                text_highlight_color=text_highlight_color, 
                bg_highlight_color=bg_highlight_color, 
                font_scale=font_scale, 
                position_ratio=position_ratio,
                blur_radius=blur_radius, 
                word_spacing=word_spacing, 
                segment_spacing=segment_spacing, 
                bg_color=bg_color,
                highlight_text=highlight_text, 
                highlight_background=highlight_background, 
                show_current_word_only=show_current_word_only
            )
            
            # Create success message
            if correction_available and words != corrected_words:
                success_msg = "Automatic transcript correction and captioning complete!"
            else:
                success_msg = "Captioning complete (without grammar correction)!"
            
            # Show success message
            self.root.after(0, lambda: self.status_label.config(text=f"Captioned video saved to {output_path}"))
            self.root.after(0, lambda: messagebox.showinfo("Success", 
                                                        f"{success_msg}\n\nSaved to: {output_path}"))
            self.root.after(0, lambda: self.run_captions_button.config(state=tk.NORMAL))
            
        except Exception as e:
            # Show error message
            error_msg = f"Error: {str(e)}"
            self.root.after(0, lambda: self.status_label.config(text=error_msg))
            self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
            self.root.after(0, lambda: self.run_captions_button.config(state=tk.NORMAL))

    # Create a function to handle requirements installation
    def install_requirements():
        """
        Install required packages for automatic transcript correction.
        Returns True if successful, False otherwise.
        """
        try:
            import subprocess
            import sys
            
            # Check if transformers is already installed
            try:
                import transformers
                print("Transformers library already installed.")
                return True
            except ImportError:
                pass
            
            print("Installing required packages...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", 
                                "transformers", "torch", "difflib"])
            
            # Verify installation
            import transformers
            print("Packages installed successfully!")
            return True
            
        except Exception as e:
            print(f"Error installing packages: {e}")
            return False


    def _process_transcription(self):
        """
        Process the transcription in a background thread.
        After transcription is complete, show the transcript editor.
        """
        try:
            input_path = self.captions_file_path.get()
            
            # Update status
            self.root.after(0, lambda: self.status_label.config(text="Transcribing audio... This may take a while."))
            
            # Create output directory if needed
            output_dir = os.path.join(os.path.dirname(input_path), "output")
            os.makedirs(output_dir, exist_ok=True)
            
            # Extract audio from media file
            audio_path = extract_audio(input_path)
            
            # Transcribe audio
            transcription = transcribe_audio(audio_path)
            
            # Create word timestamps
            words = create_word_timestamps(transcription)
            
            # Get video dimensions to calculate maximum caption width
            cap = cv2.VideoCapture(input_path)
            orig_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            orig_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            
            # After 90-degree clockwise rotation:
            rotated_width = orig_height
            rotated_height = orig_width
            
            # Calculate maximum caption width (80% of rotated width)
            max_caption_width_pixels = int(rotated_width * 0.8)
            
            # Estimate font size
            font_path = map_font_to_path(self.font_var.get())
            font_scale = map_font_size_to_scale(self.font_size_var.get())
            estimated_font_size = int(rotated_height * font_scale)
            
            # Create word segments
            segments = create_word_segments_with_max_width(
                words,
                max_width_pixels=max_caption_width_pixels,
                font_path=font_path,
                font_size=estimated_font_size,
                max_duration_seconds=self.max_duration_seconds
            )
            
            # Store the data for later use
            self.transcription_data = {
                'input_path': input_path,
                'words': words,
                'segments': segments
            }
            
            # Show the transcript editor in the main thread
            self.root.after(0, lambda: self.show_transcript_editor())
            
        except Exception as e:
            # Show error message
            error_msg = f"Error: {str(e)}"
            self.root.after(0, lambda: self.status_label.config(text=error_msg))
            self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
            self.root.after(0, lambda: self.run_captions_button.config(state=tk.NORMAL))

    def _process_captions(self):
        """
        Background thread for captions processing.
        This function properly applies captions without transcript editing.
        """
        try:
            input_path = self.captions_file_path.get()
            
            # Update status
            self.root.after(0, lambda: self.status_label.config(text="Processing... This may take a while."))
            
            # Get font and color settings
            font_path = map_font_to_path(self.font_var.get())
            text_color = map_color_to_rgb(self.text_color_var.get())
            
            # Get separate highlight colors
            text_highlight_color = map_color_to_rgb(self.text_highlight_color_var.get())
            bg_highlight_color = map_color_to_rgb(self.bg_highlight_color_var.get())
            
            font_scale = map_font_size_to_scale(self.font_size_var.get())
            
            # Determine background color - use None if "None" is selected
            if self.bg_color_var.get() == "None":
                bg_color = None
            else:
                bg_color = map_color_to_rgb(self.bg_color_var.get())
            
            # Use both horizontal and vertical position from current_position
            position_ratio = (self.current_position[0], self.current_position[1])
            
            # Use fixed values for advanced settings
            word_spacing = self.word_spacing
            segment_spacing = self.segment_spacing
            blur_radius = self.blur_radius
            
            # Get highlight options
            highlight_text = self.highlight_text.get()
            highlight_background = self.highlight_background.get()
            
            # Get current word only option
            show_current_word_only = self.show_current_word_only.get()
            
            # Check if we have transcription data from an earlier process
            if hasattr(self, 'transcription_data') and self.transcription_data:
                # Use the transcription data we already have
                from gui.utils import process_single_video_with_dicts_extended
                
                # Create output filename based on current date/time
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.basename(input_path)
                name, ext = os.path.splitext(filename)
                output_dir = os.path.join(os.path.dirname(input_path), "output")
                output_path = os.path.join(output_dir, f"{name}_{timestamp}_captioned{ext}")
                
                # Create output directory if it doesn't exist
                os.makedirs(output_dir, exist_ok=True)
                
                # Process using the existing transcription data
                process_single_video_with_dicts_extended(
                    input_path, self.transcription_data['segments'], self.transcription_data['words'], output_path,
                    font_path, text_color, text_highlight_color, bg_highlight_color, font_scale,
                    position_ratio, blur_radius, word_spacing, segment_spacing, bg_color,
                    highlight_text, highlight_background, show_current_word_only
                )
            else:
                # Process the media file for captions from scratch - pass all parameters
                output_path = process_media_for_gui(
                    transcribe_only=False,
                    path=input_path,
                    font_path=font_path,
                    text_color=text_color,
                    text_highlight_color=text_highlight_color,  # Pass separate text highlight color
                    bg_highlight_color=bg_highlight_color,      # Pass separate background highlight color
                    word_spacing=word_spacing,
                    segment_spacing=segment_spacing,
                    font_scale=font_scale,
                    position_ratio=position_ratio,
                    blur_radius=blur_radius,
                    max_duration_seconds=self.max_duration_seconds,
                    max_chars=self.max_chars,
                    bg_color=bg_color,
                    highlight_text=highlight_text,
                    highlight_background=highlight_background,
                    show_current_word_only=show_current_word_only  # Pass the show current word only option
                )
            
            # Show success message
            self.root.after(0, lambda: self.status_label.config(text=f"Captioned video saved to {output_path}"))
            self.root.after(0, lambda: messagebox.showinfo("Success", f"Captioning complete!\nSaved to: {output_path}"))
            self.root.after(0, lambda: self.run_captions_button.config(state=tk.NORMAL))
        
        except Exception as e:
            # Show error message
            error_msg = f"Error: {str(e)}"
            self.root.after(0, lambda: self.status_label.config(text=error_msg))
            self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
            self.root.after(0, lambda: self.run_captions_button.config(state=tk.NORMAL))



    def show_transcript_editor(self):
        """
        Display the transcript editor window for users to edit the transcription.
        """
        # Update status
        self.status_label.config(text="Edit the transcript before generating captions.")
        
        # Import the TranscriptEditor class
        from gui.transcript_editor import TranscriptEditor
        
        # Create the transcript editor with callbacks
        self.editor = TranscriptEditor(
            self.root,
            self.transcription_data['segments'],
            self.transcription_data['words'],
            self.on_transcript_edited,
            self.on_transcript_edit_canceled
        )

    def on_transcript_edited(self, edited_segments, original_words):
        """
        Called when the user completes editing the transcript.
        Proceed with caption generation using the edited transcript.
        
        Args:
            edited_segments: The segments dictionary with edited text
            original_words: The original words dictionary
        """
        # Store the edited segments separately to avoid confusion
        self.transcription_data['edited_segments'] = edited_segments
        
        # Print some debug info
        print("Edited transcript saved. Sample segments:")
        for i, segment in enumerate(edited_segments.get('segments', [])[:3]):
            print(f"Segment {i+1}: {segment.get('text', 'N/A')}")
        
        # Create a new status label if the previous one is gone
        try:
            # Try to update the existing status label
            self.status_label.config(text="Generating captions with edited transcript...")
        except (tk.TclError, AttributeError):
            # If the label is gone, create a new one
            # First make sure the root window exists and is ready
            if not hasattr(self, 'root') or not self.root.winfo_exists():
                print("Error: Root window doesn't exist or was destroyed")
                return
                
            # Recreate the main window structure
            for widget in self.root.winfo_children():
                widget.destroy()
                
            # Create a simple frame for status updates
            temp_frame = tk.Frame(self.root)
            temp_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            # Create a new status label
            self.status_label = tk.Label(temp_frame, text="Generating captions with edited transcript...")
            self.status_label.pack(pady=10)
        
        # Start caption generation in a separate thread
        threading.Thread(target=self._process_captions_with_edited_transcript, daemon=True).start()

    def on_transcript_edit_canceled(self):
        """
        Called when the user cancels transcript editing.
        Return to the caption options screen.
        """
        # Update status
        self.status_label.config(text="Transcript editing canceled.")
        
        # Re-enable the run button
        self.run_captions_button.config(state=tk.NORMAL)
        
        # Return to the caption options screen
        self.open_captions_window()

    def _process_captions_with_edited_transcript(self):
        """
        Process the captions using the edited transcript.
        This runs in a background thread.
        """
        try:
            # Get data from stored transcription
            input_path = self.transcription_data['input_path']
            edited_segments = self.transcription_data['edited_segments']  # This is the edited transcript
            original_words = self.transcription_data['words']
            
            # Print some debug info
            print("\nProcessing captions with edited transcript...")
            print(f"Number of segments in edited transcript: {len(edited_segments.get('segments', []))}")
            if edited_segments.get('segments'):
                print(f"First segment text: {edited_segments['segments'][0]['text']}")

            # Get caption settings
            font_path = map_font_to_path(self.font_var.get())
            text_color = map_color_to_rgb(self.text_color_var.get())
            text_highlight_color = map_color_to_rgb(self.text_highlight_color_var.get())
            bg_highlight_color = map_color_to_rgb(self.bg_highlight_color_var.get())
            font_scale = map_font_size_to_scale(self.font_size_var.get())
            
            # Determine background color
            if self.bg_color_var.get() == "None":
                bg_color = None
            else:
                bg_color = map_color_to_rgb(self.bg_color_var.get())
            
            # Get position ratio
            position_ratio = (self.current_position[0], self.current_position[1])
            
            # Get other settings
            word_spacing = self.word_spacing
            segment_spacing = self.segment_spacing
            blur_radius = self.blur_radius
            highlight_text = self.highlight_text.get()
            highlight_background = self.highlight_background.get()
            show_current_word_only = self.show_current_word_only.get()
            
            # Define max character and duration constraints
            max_chars = 30  # Maximum characters per segment
            max_duration_seconds = 1.5  # Maximum seconds per segment
            
            # Create output filename based on current date/time
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.basename(input_path)
            name, ext = os.path.splitext(filename)
            output_dir = os.path.join(os.path.dirname(input_path), "output")
            output_path = os.path.join(output_dir, f"{name}_{timestamp}_captioned{ext}")
            
            # Create output directory if needed
            os.makedirs(output_dir, exist_ok=True)
            
            # Save the edited segments to a JSON file for reference
            segments_json_path = os.path.join(output_dir, f"{name}_{timestamp}_edited_segments.json")
            with open(segments_json_path, 'w', encoding='utf-8') as f:
                import json
                json.dump(edited_segments, f, indent=2)
            
            # Process video with captions - Use our new utility function with segment optimization
            from gui.utils import process_edited_transcript_video
            process_edited_transcript_video(
                input_path, edited_segments, original_words, output_path,
                font_path, text_color, text_highlight_color, bg_highlight_color, font_scale,
                position_ratio, blur_radius, word_spacing, segment_spacing, bg_color,
                highlight_text, highlight_background, show_current_word_only,
                max_chars=max_chars, max_duration_seconds=max_duration_seconds
            )
            
            # Schedule UI update on the main thread
            self.root.after(0, lambda: self.update_ui_success(output_path))
                
        except Exception as e:
            # Show error message - safely update UI
            error_msg = f"Error: {str(e)}"
            self.root.after(0, lambda: self.show_ui_error(error_msg))
        
    def update_ui_success(self, path):
        """
        Update the UI after successful caption generation.
        
        Args:
            path (str): Path to the saved captioned video
        """
        try:
            if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                self.status_label.config(text=f"Captioned video saved to {path}")
            messagebox.showinfo("Success", f"Captioning complete!\nSaved to: {path}")
            self.create_main_menu()  # Return to main menu
        except (tk.TclError, AttributeError) as e:
            print(f"UI update error: {e}")
            # Still try to show the message box if possible
            try:
                messagebox.showinfo("Success", f"Captioning complete!\nSaved to: {path}")
                self.create_main_menu()  # Return to main menu
            except:
                pass

    def show_ui_error(self, error_msg):
        """
        Display an error message in the UI.
        
        Args:
            error_msg (str): The error message to display
        """
        try:
            if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                self.status_label.config(text=error_msg)
            messagebox.showerror("Error", error_msg)
            if hasattr(self, 'run_captions_button') and self.run_captions_button.winfo_exists():
                self.run_captions_button.config(state=tk.NORMAL)
        except (tk.TclError, AttributeError):
            # Just try to show the error message box
            try:
                messagebox.showerror("Error", error_msg)
            except:
                print(f"Critical UI error: {error_msg}")

    def setup_drag_functionality(self):
        """
        Set up event bindings for drag-and-drop functionality of the caption text.
        """
        # Variables to track dragging state
        self.dragging = False
        self.last_x = 0
        self.last_y = 0
        
        # Bind mouse events to the video frame
        self.video_frame.bind("<ButtonPress-1>", self.start_drag)
        self.video_frame.bind("<B1-Motion>", self.on_drag)
        self.video_frame.bind("<ButtonRelease-1>", self.stop_drag)
        
        # Flag to prevent re-binding
        self.drag_enabled = True


    def start_drag(self, event):
        """
        Start caption dragging operation when the mouse button is pressed.
        """
        self.dragging = True
        self.last_x = event.x
        self.last_y = event.y


    def on_drag(self, event):
        """
        Handle caption dragging when the mouse is moved with button pressed.
        """
        if not self.dragging:
            return
        
        # Calculate the change in position
        dx = event.x - self.last_x
        dy = event.y - self.last_y
        
        # Update last position
        self.last_x = event.x
        self.last_y = event.y
        
        # Convert pixel change to ratio change using the scale factor
        if not hasattr(self, 'preview_dimensions'):
            return
        
        orig_width, orig_height = self.preview_dimensions['original']
        scale_factor = self.preview_dimensions['scale_factor']
        
        # Calculate ratio change
        dx_ratio = dx / (orig_width * scale_factor)
        dy_ratio = dy / (orig_height * scale_factor)
        
        # Update position
        self.current_position[0] += dx_ratio
        self.current_position[1] += dy_ratio
        
        # Clamp position to stay within image bounds (with smaller margin)
        margin = 0.01  # Reduced from 0.05 to 0.01
        self.current_position[0] = max(margin, min(1.0 - margin, self.current_position[0]))
        self.current_position[1] = max(margin, min(1.0 - margin, self.current_position[1]))
        
        # Update the preview
        self.update_video_preview()


    def stop_drag(self, event):
        """
        End caption dragging operation when the mouse button is released.
        """
        self.dragging = False

    def test_color_mapping(self):
        """Test color mapping functionality"""
        # Import utilities
        from gui.utils import map_color_to_rgb
        
        print("\n==== Testing Color Mapping ====")
        # Test all available color options
        test_colors = [
            'None', 'White', 'Black', 'Purple', 'Green', 
            'Orange', 'Red', 'Pink', 'Light Blue', 'Dark Blue', 
            'Olive', 'Yellow', 'Sand'
        ]
        
        for color_name in test_colors:
            color_value = map_color_to_rgb(color_name)
            print(f"Color '{color_name}' maps to {color_value}")
        
        # Also test the current selected colors
        print("\n==== Current Color Settings ====")
        print(f"Text color: {self.text_color_var.get()} -> {map_color_to_rgb(self.text_color_var.get())}")
        print(f"Highlight color: {self.highlight_color_var.get()} -> {map_color_to_rgb(self.highlight_color_var.get())}")
        print(f"Background color: {self.bg_color_var.get()} -> {map_color_to_rgb(self.bg_color_var.get())}")
        print("================================")
        
        # Show a message
        from tkinter import messagebox
        messagebox.showinfo("Color Test", "Color test completed. Check console for results.")

if __name__ == "__main__":
    root = tk.Tk()
    app = TranscriptionApp(root)
    root.mainloop()