import os
import requests
import tempfile
import subprocess
from dotenv import load_dotenv

class ElevenLabsIntegration:
    def __init__(self):
        """Initialize ElevenLabs integration."""
        env_path = os.path.join(os.path.dirname(__file__), "../../../config/.env")
        load_dotenv(env_path)
        
        self.api_key = os.getenv('ELEVENLABS_API_KEY')
        if not self.api_key:
            print("Warning: ELEVENLABS_API_KEY not found in .env file")
            
        self.base_url = "https://api.elevenlabs.io/v1"
        self.voice_id = "21m00Tcm4TlvDq8ikWAM"  # Default voice ID
        
    def text_to_speech(self, text):
        """Convert text to speech using ElevenLabs API or system voice as fallback."""
        if not text:
            return None
            
        try:
            # Try ElevenLabs first if API key is available
            if self.api_key:
                try:
                    # Generate speech using ElevenLabs
                    headers = {
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "xi-api-key": self.api_key
                    }
                    
                    response = requests.post(
                        f"{self.base_url}/text-to-speech/{self.voice_id}/stream",
                        headers=headers,
                        json={
                            "text": text,
                            "model_id": "eleven_monolingual_v1",
                            "voice_settings": {
                                "stability": 0.5,
                                "similarity_boost": 0.5
                            }
                        }
                    )
                    
                    if response.status_code == 200:
                        # Save audio to temporary file
                        temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
                        temp_file.write(response.content)
                        temp_file.close()
                        return temp_file.name
                    else:
                        print(f"ElevenLabs error: {response.status_code}, {response.text}")
                        raise Exception("ElevenLabs API error")
                        
                except Exception as e:
                    print(f"ElevenLabs failed, falling back to system voice: {str(e)}")
            
            # Use system voice as fallback (macOS)
            if os.uname().sysname == 'Darwin':
                subprocess.run(['say', text])
                return None
                
            print("No text-to-speech service available")
            return None
                
        except Exception as e:
            print(f"Error in text-to-speech: {str(e)}")
            return None
