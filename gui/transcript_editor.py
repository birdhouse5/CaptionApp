import tkinter as tk
from tkinter import messagebox

class TranscriptEditor:
    def __init__(self, root, segments, words, on_complete_callback, on_cancel_callback):
        """
        Initialize the transcript editor.
        
        Args:
            root: The Tkinter root or parent window
            segments: Dictionary containing segment data
            words: Dictionary containing word data
            on_complete_callback: Function to call when editing is complete
            on_cancel_callback: Function to call when editing is cancelled
        """
        self.root = root
        self.original_segments = segments
        self.original_words = words
        self.edited_segments = self._copy_segments(segments)
        self.on_complete_callback = on_complete_callback
        self.on_cancel_callback = on_cancel_callback
        
        # Current segment index
        self.current_segment_idx = 0
        
        # Create the UI
        self._create_ui()
        
        # Display the first segment
        self._display_current_segment()
    
    def _copy_segments(self, segments):
        """Create a deep copy of the segments dictionary for editing."""
        import copy
        return copy.deepcopy(segments)
    
    def _create_ui(self):
        """Create the transcript editor UI."""
        # Clear any existing widgets
        for widget in self.root.winfo_children():
            widget.destroy()
            
        # Set window title
        self.root.title("Edit Transcript")
        
        # Main container
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        header_label = tk.Label(main_frame, text="Edit Transcript", font=("Arial", 14, "bold"))
        header_label.pack(pady=10)
        
        # Instructions
        instructions = "Edit each segment text and navigate using the buttons below."
        instructions_label = tk.Label(main_frame, text=instructions, wraplength=600)
        instructions_label.pack(pady=5)
        
        # Segment info frame
        segment_info_frame = tk.Frame(main_frame)
        segment_info_frame.pack(fill=tk.X, pady=5)
        
        # Segment number and time display
        self.segment_info_label = tk.Label(segment_info_frame, text="Segment 1 of 1")
        self.segment_info_label.pack(side=tk.LEFT, padx=5)
        
        self.segment_time_label = tk.Label(segment_info_frame, text="00:00:00 - 00:00:00")
        self.segment_time_label.pack(side=tk.RIGHT, padx=5)
        
        # Text editor frame with border
        editor_frame = tk.Frame(main_frame, bd=2, relief=tk.SUNKEN)
        editor_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Text editor with scrollbar
        self.text_editor = tk.Text(editor_frame, wrap=tk.WORD, height=10, font=("Arial", 12))
        self.text_editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(editor_frame, command=self.text_editor.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_editor.config(yscrollcommand=scrollbar.set)
        
        # Navigation buttons frame
        nav_frame = tk.Frame(main_frame)
        nav_frame.pack(fill=tk.X, pady=10)
        
        # Previous segment button
        self.prev_button = tk.Button(nav_frame, text="← Previous", width=15, command=self._prev_segment)
        self.prev_button.pack(side=tk.LEFT, padx=5)
        
        # Next segment button
        self.next_button = tk.Button(nav_frame, text="Next →", width=15, command=self._next_segment)
        self.next_button.pack(side=tk.RIGHT, padx=5)
        
        # Segment counter display
        self.counter_label = tk.Label(nav_frame, text="")
        self.counter_label.pack(side=tk.TOP, padx=5)
        
        # Bottom buttons frame
        bottom_frame = tk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=10)
        
        # Cancel button
        cancel_button = tk.Button(bottom_frame, text="Cancel", width=15, command=self._on_cancel)
        cancel_button.pack(side=tk.LEFT, padx=5)
        
        # Complete button
        complete_button = tk.Button(bottom_frame, text="Complete Editing", width=15, command=self._on_complete)
        complete_button.pack(side=tk.RIGHT, padx=5)
    
    def _display_current_segment(self):
        """Display the current segment in the editor."""
        # Get total segment count
        total_segments = len(self.edited_segments["segments"])
        
        if total_segments == 0:
            # No segments to edit
            self.text_editor.delete("1.0", tk.END)
            self.text_editor.insert(tk.END, "No segments found in the transcript.")
            self.segment_info_label.config(text="No segments")
            self.segment_time_label.config(text="--:--:-- - --:--:--")
            self.counter_label.config(text="0/0")
            self.prev_button.config(state=tk.DISABLED)
            self.next_button.config(state=tk.DISABLED)
            return
        
        # Get current segment
        segment = self.edited_segments["segments"][self.current_segment_idx]
        
        # Update segment text
        self.text_editor.delete("1.0", tk.END)
        self.text_editor.insert(tk.END, segment["text"])
        
        # Update segment info
        self.segment_info_label.config(text=f"Segment {self.current_segment_idx + 1}")
        self.segment_time_label.config(text=f"{segment['start_time']} - {segment['end_time']}")
        
        # Update counter label
        self.counter_label.config(text=f"{self.current_segment_idx + 1}/{total_segments}")
        
        # Update navigation buttons
        self.prev_button.config(state=tk.NORMAL if self.current_segment_idx > 0 else tk.DISABLED)
        self.next_button.config(state=tk.NORMAL if self.current_segment_idx < total_segments - 1 else tk.DISABLED)
    
    def _save_current_segment(self):
        """Save the edited text for the current segment."""
        if self.edited_segments and "segments" in self.edited_segments and self.edited_segments["segments"]:
            # Get the edited text
            edited_text = self.text_editor.get("1.0", "end-1c")  # end-1c removes the trailing newline
            
            # Update the segment text
            self.edited_segments["segments"][self.current_segment_idx]["text"] = edited_text
    
    def _prev_segment(self):
        """Navigate to the previous segment."""
        if self.current_segment_idx > 0:
            # Save current edits
            self._save_current_segment()
            
            # Go to previous segment
            self.current_segment_idx -= 1
            self._display_current_segment()
    
    def _next_segment(self):
        """Navigate to the next segment."""
        if self.current_segment_idx < len(self.edited_segments["segments"]) - 1:
            # Save current edits
            self._save_current_segment()
            
            # Go to next segment
            self.current_segment_idx += 1
            self._display_current_segment()
    
    def _on_complete(self):
        """Handle completion of editing."""
        # Save the current segment
        self._save_current_segment()
        
        # Call the completion callback with edited segments and original words
        if self.on_complete_callback:
            self.on_complete_callback(self.edited_segments, self.original_words)
    
    def _on_cancel(self):
        """Cancel editing and return to previous screen."""
        if self.on_cancel_callback:
            self.on_cancel_callback()