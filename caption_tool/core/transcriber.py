"""
Audio transcription using OpenAI Whisper.
"""

import os
import tempfile
from typing import Dict, List, Any, Optional
import torch
import whisper
import moviepy as mp

from exceptions import TranscriptionError
from utils import ProgressTracker, format_srt_timestamp


class Transcriber:
    """Handles audio extraction and transcription using Whisper."""
    
    def __init__(self, model_name: str = "base", progress_tracker: Optional[ProgressTracker] = None):
        """
        Initialize transcriber.
        
        Args:
            model_name: Whisper model name (tiny, base, small, medium, large)
            progress_tracker: Optional progress tracker
        """
        self.model_name = model_name
        self.model = None
        self.progress_tracker = progress_tracker
    
    def _load_model(self) -> None:
        """Load Whisper model if not already loaded."""
        if self.model is None:
            if self.progress_tracker:
                self.progress_tracker.log(f"Loading Whisper model: {self.model_name}")
            
            self.model = whisper.load_model(self.model_name)
    
    def extract_audio(self, media_path: str, temp_dir: str) -> str:
        """
        Extract audio from media file.
        
        Args:
            media_path: Path to input media file
            temp_dir: Directory for temporary files
            
        Returns:
            Path to extracted audio file
            
        Raises:
            TranscriptionError: If audio extraction fails
        """
        try:
            file_ext = os.path.splitext(media_path)[1].lower()
            
            # If it's already an audio file, just return the path
            if file_ext in ['.mp3', '.wav', '.m4a', '.flac']:
                return media_path
            
            # Extract audio from video
            if self.progress_tracker:
                self.progress_tracker.log("Extracting audio from video...")
            
            video = mp.VideoFileClip(media_path)
            audio_path = os.path.join(temp_dir, "extracted_audio.wav")
            
            # Extract audio - simplified call without problematic parameters
            audio = video.audio
            
            # Try different parameter combinations based on MoviePy version
            try:
                # First try with no extra parameters (most compatible)
                audio.write_audiofile(audio_path)
            except TypeError:
                # If that fails, try with temp_audiofile parameter
                try:
                    audio.write_audiofile(audio_path, temp_audiofile=None)
                except TypeError:
                    # Final fallback - just the basic call
                    audio.write_audiofile(audio_path)
            
            # Clean up
            audio.close()
            video.close()
            
            return audio_path
            
        except Exception as e:
            raise TranscriptionError(f"Failed to extract audio: {e}")
    
    def transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe audio file using Whisper.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Transcription result with word-level timestamps
            
        Raises:
            TranscriptionError: If transcription fails
        """
        try:
            self._load_model()
            
            if self.progress_tracker:
                self.progress_tracker.log("Starting audio transcription...")
            
            # Transcribe with word-level timestamps
            result = self.model.transcribe(
                audio_path,
                word_timestamps=True,
                fp16=torch.cuda.is_available()
            )
            
            if self.progress_tracker:
                self.progress_tracker.log("Transcription complete")
            
            return result
            
        except Exception as e:
            raise TranscriptionError(f"Transcription failed: {e}")
    
    def create_word_timestamps(self, transcription_result: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract word-level timestamps from transcription result.
        
        Args:
            transcription_result: Raw Whisper transcription result
            
        Returns:
            Dictionary with word-level timing data
        """
        words_data = {'words': []}
        
        for segment in transcription_result.get('segments', []):
            for word in segment.get('words', []):
                word_text = word.get('word', '').strip()
                if word_text:  # Skip empty words
                    words_data['words'].append({
                        'text': word_text,
                        'start': format_srt_timestamp(max(0, word.get('start', 0))),
                        'end': format_srt_timestamp(word.get('end', 0))
                    })
        
        return words_data
    
    def process_media(self, media_path: str, temp_dir: str) -> tuple[str, Dict[str, List[Dict[str, Any]]]]:
        """
        Complete transcription pipeline: extract audio and transcribe.
        
        Args:
            media_path: Path to input media file
            temp_dir: Directory for temporary files
            
        Returns:
            Tuple of (full_transcript_text, word_timestamps_dict)
            
        Raises:
            TranscriptionError: If any step fails
        """
        # Extract audio
        audio_path = self.extract_audio(media_path, temp_dir)
        
        # Transcribe
        transcription_result = self.transcribe_audio(audio_path)
        
        # Extract word timestamps
        word_timestamps = self.create_word_timestamps(transcription_result)
        
        # Get full transcript text
        full_text = transcription_result.get('text', '').strip()
        
        return full_text, word_timestamps