import os
import requests
import tempfile
from dotenv import load_dotenv


class ElevenLabsIntegration:
    def __init__(self):
        env_path = os.path.join(os.path.dirname(__file__), "../../../config/.env")
        load_dotenv(env_path)
        self.api_key = os.getenv('ELEVENLABS_API_KEY')
        self._disabled = False  # set True after first auth failure
        self.base_url = "https://api.elevenlabs.io/v1"
        self.voice_id = "21m00Tcm4TlvDq8ikWAM"

    def text_to_speech(self, text):
        if not text or not self.api_key or self._disabled:
            return None
        try:
            resp = requests.post(
                f"{self.base_url}/text-to-speech/{self.voice_id}/stream",
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "xi-api-key": self.api_key,
                },
                json={
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.5},
                },
                timeout=10,
            )
            if resp.status_code == 200:
                tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
                tmp.write(resp.content)
                tmp.close()
                return tmp.name
            elif resp.status_code in (401, 403):
                # Invalid key — disable permanently this session, warn once
                self._disabled = True
                print("ElevenLabs disabled (invalid API key). Using system voice.")
            else:
                print(f"ElevenLabs error {resp.status_code}")
        except Exception as e:
            print(f"ElevenLabs error: {e}")
        return None
