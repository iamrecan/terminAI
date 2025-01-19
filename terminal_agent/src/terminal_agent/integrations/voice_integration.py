import os
import time
import speech_recognition as sr
import pygame
import tempfile
import warnings
import google.generativeai as genai
from dotenv import load_dotenv
from .elevenlabs_integration import ElevenLabsIntegration
import whisper
import wave

# Suppress Whisper warnings
warnings.filterwarnings("ignore", category=UserWarning)

class VoiceAssistant:
    def __init__(self):
        """Initialize voice assistant."""
        env_path = os.path.join(os.path.dirname(__file__), "../../../config/.env")
        load_dotenv(env_path)
        
        self.recognizer = sr.Recognizer()
        try:
            self.microphone = sr.Microphone()
            self.microphone_available = True
            
            # Adjust microphone settings
            with self.microphone as source:
                print("Initializing microphone...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                self.recognizer.dynamic_energy_threshold = True
                self.recognizer.energy_threshold = 4000
                
        except (OSError, AttributeError) as e:
            self.microphone_available = False
            print("Warning: Microphone not available")
            
        # Initialize Whisper only if needed
        self._whisper_model = None
        
        # Initialize Google AI
        google_api_key = os.getenv('GOOGLE_API_KEY')
        if not google_api_key:
            print("Warning: GOOGLE_API_KEY not found in .env file")
        else:
            genai.configure(api_key=google_api_key)
            
        # Initialize text generation model
        try:
            self.model = genai.GenerativeModel('gemini-pro')
            self.chat = self.model.start_chat(history=[])
        except Exception as e:
            print(f"Warning: Could not initialize Google AI model: {str(e)}")
            self.model = None
            self.chat = None
            
        pygame.mixer.init()
        self.elevenlabs = ElevenLabsIntegration()
        
        # Language settings
        self.language = "en"  # Default to English
        
    @property
    def whisper_model(self):
        """Lazy load whisper model when needed."""
        if self._whisper_model is None:
            self._whisper_model = whisper.load_model("base")
        return self._whisper_model
        
    def set_language(self, lang):
        """Set the assistant's language."""
        if lang in ["en", "tr"]:
            self.language = lang
            # Reset chat with new language context
            if self.model:
                context = ("You are a helpful AI assistant. Keep your responses natural and conversational. "
                          f"Always respond in {'English' if lang == 'en' else 'Turkish'}. "
                          "If the user asks to exit, respond with a goodbye message.")
                self.chat = self.model.start_chat(history=[])
                self.chat.send_message(context)
            print(f"Language set to: {'English' if lang == 'en' else 'Turkish'}")
        else:
            print("Unsupported language. Using English.")
            self.language = "en"
            
    def listen(self):
        """Record audio from microphone and convert to text"""
        if not self.microphone_available:
            print("Error: Microphone not available")
            return None
            
        try:
            with self.microphone as source:
                print("\nListening... (Press Ctrl+C to exit)")
                
                try:
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                except sr.WaitTimeoutError:
                    print("No speech detected, listening again...")
                    return None
                    
                # Try Google Speech Recognition first
                try:
                    print("\nProcessing with Google Speech Recognition...")
                    text = self.recognizer.recognize_google(audio, language="en-US" if self.language == "en" else "tr-TR")
                    print(f"You said: {text}")
                    return text.lower().strip()
                except sr.UnknownValueError:
                    print("\nGoogle could not understand audio, trying Whisper...")
                except sr.RequestError:
                    print("\nGoogle service unavailable, trying Whisper...")
                    
                # Try Whisper as a fallback
                try:
                    print("Processing with Whisper...")
                    audio_data = audio.get_wav_data()
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                        temp_wav.write(audio_data)
                        temp_wav.flush()
                        result = self.whisper_model.transcribe(temp_wav.name, language=self.language)
                        os.remove(temp_wav.name)
                        text = result["text"].strip()
                        print(f"You said: {text}")
                        return text.lower().strip()
                except Exception as e:
                    print(f"Error in speech recognition: {str(e)}")
                    return None
                    
        except Exception as e:
            print(f"Error in listen: {str(e)}")
            return None
            
    def speak(self, text):
        """Convert text to speech and play it."""
        try:
            # Try ElevenLabs first
            audio_file = self.elevenlabs.text_to_speech(text)
            if audio_file:
                pygame.mixer.music.load(audio_file)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                pygame.mixer.music.unload()
                os.remove(audio_file)
                return True
                
            # Use system voice as fallback
            print("Using system voice...")
            voice = "Alex" if self.language == "en" else "Yelda"
            os.system(f'say -v {voice} "{text}"')
            return True
            
        except Exception as e:
            print(f"Error in speak: {str(e)}")
            return False
            
    def get_response(self, text):
        """Generate response using Google AI."""
        # Check for exit commands in both languages
        exit_commands_en = ['exit', 'quit', 'bye', 'goodbye', 'stop']
        exit_commands_tr = ['çık', 'çıkış', 'güle güle', 'hoşça kal', 'dur']
        
        if any(cmd in text.lower() for cmd in (exit_commands_en if self.language == "en" else exit_commands_tr)):
            return None  # Signal to stop conversation
            
        try:
            if self.chat:
                response = self.chat.send_message(text)
                return response.text
            else:
                # Fallback responses if AI is not available
                if self.language == "en":
                    return "I apologize, but I'm having trouble connecting to my AI service. Please try again later."
                else:
                    return "Üzgünüm, AI servisine bağlanmakta sorun yaşıyorum. Lütfen daha sonra tekrar deneyin."
                    
        except Exception as e:
            print(f"Error getting AI response: {str(e)}")
            if self.language == "en":
                return "I'm sorry, I encountered an error. Could you please try again?"
            else:
                return "Üzgünüm, bir hata oluştu. Tekrar deneyebilir misiniz?"
            
    def start(self):
        """Start voice command mode."""
        if not self.microphone_available:
            print("Error: Cannot start voice assistant - microphone not available")
            return
            
        print("\nVoice Assistant activated. Say 'exit' or press Ctrl+C to quit.")
        
        try:
            while True:
                text = self.listen()
                if text:
                    if any(word in text for word in ['exit', 'quit', 'bye', 'goodbye', 'stop']):
                        print("\nGoodbye!")
                        break
                    print(f"Command received: {text}")
        except KeyboardInterrupt:
            print("\nStopping voice assistant...")
        finally:
            pygame.mixer.quit()
            
    def start_conversation(self):
        """Start interactive conversation mode."""
        if not self.microphone_available:
            print("Error: Cannot start conversation - microphone not available")
            return
            
        # Ask for language preference
        print("\nSelect language / Dil seçin:")
        print("1. English")
        print("2. Türkçe")
        
        try:
            choice = input("Enter 1 or 2: ").strip()
            self.set_language("en" if choice == "1" else "tr")
        except Exception:
            print("Invalid choice. Using English.")
            self.set_language("en")
            
        print("\nConversation mode activated.")
        print("Say 'exit', 'quit', 'stop', or 'bye' to end." if self.language == "en" else 
              "Çıkmak için 'çık', 'çıkış', 'dur' veya 'hoşça kal' deyin.")
        
        try:
            while True:
                text = self.listen()
                if text:
                    response = self.get_response(text)
                    if response is None:  # Exit command detected
                        final_msg = "Goodbye! Take care!" if self.language == "en" else "Görüşmek üzere!"
                        print(f"\nAssistant: {final_msg}")
                        self.speak(final_msg)
                        break
                        
                    print(f"\nAssistant: {response}")
                    self.speak(response)
                    
        except KeyboardInterrupt:
            print("\nStopping conversation...")
        finally:
            pygame.mixer.quit()
