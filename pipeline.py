import os
import subprocess
import requests
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import pickle

# Load environment variables
load_dotenv()

class VideoStoryPipeline:
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY')
        self.elevenlabs_voice_id = os.getenv('ELEVENLABS_VOICE_ID', 'default_voice_id')
        self.google_credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
        self.token_path = 'token.pickle'
        
        # Google Drive API setup
        self.SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
        self.drive_service = None
        
    def authenticate_google_drive(self):
        """Authenticate with Google Drive API"""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.google_credentials_path, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        self.drive_service = build('drive', 'v3', credentials=creds)
        return True
    
    def read_prompt_from_file(self, file_path):
        """Read story prompt from text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read().strip()
        except FileNotFoundError:
            raise Exception(f"Prompt file not found: {file_path}")
    
    def generate_story(self, prompt, word_count=500):
        """Generate story using OpenAI API"""
        headers = {
            'Authorization': f'Bearer {self.openai_api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': 'gpt-4',
            'messages': [
                {
                    'role': 'system',
                    'content': f'You are a creative storyteller. Write a compelling story of approximately {word_count} words based on the given prompt.'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'max_tokens': word_count * 2,  # Buffer for token-to-word conversion
            'temperature': 0.8
        }
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            story = response.json()['choices'][0]['message']['content']
            print(f"Generated story ({len(story.split())} words)")
            return story
        else:
            raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")
    
    def text_to_speech_elevenlabs(self, text, output_path="narration.mp3"):
        """Convert text to speech using ElevenLabs API"""
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.elevenlabs_voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.elevenlabs_api_key
        }
        
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }
        
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print(f"Audio saved as {output_path}")
            return output_path
        else:
            raise Exception(f"ElevenLabs API error: {response.status_code} - {response.text}")
    
    def download_from_google_drive(self, file_id, output_path):
        """Download file from Google Drive using file ID"""
        if not self.drive_service:
            self.authenticate_google_drive()
        
        request = self.drive_service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print(f"Download progress: {int(status.progress() * 100)}%")
        
        with open(output_path, 'wb') as f:
            f.write(fh.getvalue())
        
        print(f"Downloaded {output_path}")
        return output_path
    
    def combine_with_ffmpeg(self, video_path, narration_path, music_path, output_path="final_video.mp4"):
        """Combine video, narration, and background music using FFmpeg"""
        
        # FFmpeg command to combine video with narration and background music
        # This command:
        # - Takes the video file as main input
        # - Adds narration audio
        # - Adds background music at lower volume
        # - Mixes the audio streams
        cmd = [
            'ffmpeg',
            '-i', video_path,           # Video input
            '-i', narration_path,       # Narration audio input
            '-i', music_path,           # Background music input
            '-filter_complex',
            '[1:a]volume=1.0[narration];'    # Narration at full volume
            '[2:a]volume=0.3[music];'        # Background music at 30% volume
            '[narration][music]amix=inputs=2:duration=shortest[audio_out]',  # Mix audio
            '-map', '0:v',              # Use video from first input
            '-map', '[audio_out]',      # Use mixed audio
            '-c:v', 'copy',             # Copy video codec (no re-encoding)
            '-c:a', 'aac',              # Encode audio as AAC
            '-shortest',                # End when shortest stream ends
            '-y',                       # Overwrite output file
            output_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"Video successfully created: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            raise Exception(f"FFmpeg error: {e.stderr}")
    
    def run_pipeline(self, prompt_file, video_file_id, music_file_id, target_word_count=500):
        """Run the complete pipeline"""
        print("Starting video story pipeline...")
        
        try:
            # Step 1: Read prompt
            print("1. Reading prompt from file...")
            prompt = self.read_prompt_from_file(prompt_file)
            
            # Step 2: Generate story
            print("2. Generating story...")
            story = self.generate_story(prompt, target_word_count)
            
            # Step 3: Convert to speech
            print("3. Converting story to speech...")
            narration_file = self.text_to_speech_elevenlabs(story, "narration.mp3")
            
            # Step 4: Authenticate and download video
            print("4. Downloading video from Google Drive...")
            self.authenticate_google_drive()
            video_file = self.download_from_google_drive(video_file_id, "video.mp4")
            
            # Step 5: Download background music
            print("5. Downloading background music from Google Drive...")
            music_file = self.download_from_google_drive(music_file_id, "background_music.mp3")
            
            # Step 6: Combine everything
            print("6. Combining video, narration, and music...")
            final_video = self.combine_with_ffmpeg(
                video_file, 
                narration_file, 
                music_file, 
                "final_story_video.mp4"
            )
            
            print(f"✅ Pipeline completed successfully! Final video: {final_video}")
            return final_video
            
        except Exception as e:
            print(f"❌ Pipeline failed: {str(e)}")
            raise

# Example usage
if __name__ == "__main__":
    # Initialize pipeline
    pipeline = VideoStoryPipeline()
    
    # Configuration
    prompt_file = "story_prompt.txt"  # Your prompt file
    video_file_id = "your_google_drive_video_file_id"  # Google Drive file ID for video
    music_file_id = "your_google_drive_music_file_id"  # Google Drive file ID for music
    word_count = 500  # Target word count for story
    
    # Run pipeline
    try:
        final_video = pipeline.run_pipeline(
            prompt_file=prompt_file,
            video_file_id=video_file_id,
            music_file_id=music_file_id,
            target_word_count=word_count
        )
        print(f"🎬 Your story video is ready: {final_video}")
    except Exception as e:
        print(f"Error: {e}")