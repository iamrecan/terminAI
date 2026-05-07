import asyncio
import os
import time
import speech_recognition as sr
import pygame
import tempfile
import warnings
from .elevenlabs_integration import ElevenLabsIntegration
import whisper
import threading
import queue
from datetime import datetime

# Suppress Whisper warnings
warnings.filterwarnings("ignore", category=UserWarning)

class VoiceAssistant:
    def __init__(self, llm_router=None):
        """Initialize voice assistant.

        llm_router: optional pre-built LLMRouter from the agent (avoids creating a second one)
        """
        os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
        self._pygame_ready = False
        self._llm_router = llm_router       # injected from TerminalAgent
        self._conv_history: list[dict] = [] # conversation context for voice chat
        
        self.recognizer = sr.Recognizer()
        self.conversation_active = False
        self.listening = False
        self.command_queue = queue.Queue()
        self.service_stats = {
            'google': {'success': 0, 'failed': 0, 'total_time': 0},
            'whisper': {'success': 0, 'failed': 0, 'total_time': 0},
            'elevenlabs': {'success': 0, 'failed': 0, 'total_time': 0},
            'system_voice': {'success': 0, 'failed': 0, 'total_time': 0}
        }
        
        # Initialize microphone only once
        try:
            print("Initializing voice recognition system...")
            self.microphone = sr.Microphone()
            self.microphone_available = True
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
                self.recognizer.dynamic_energy_threshold = True
                self.recognizer.energy_threshold = 4000
            print("Voice recognition system ready.")
        except (OSError, AttributeError) as e:
            self.microphone_available = False
            print("Warning: Voice recognition system not available")
            
        # Initialize Whisper only if needed
        self._whisper_model = None
        
        # LLM is accessed via the router in agent.py; voice handles audio only
        self.model = None
        self.chat = None
            
        self.elevenlabs = ElevenLabsIntegration()
        
        # Language settings
        self.language = None  # Default to None for auto-detection
        
    @property
    def whisper_model(self):
        """Lazy load whisper model when needed."""
        if self._whisper_model is None:
            self._whisper_model = whisper.load_model("base")
        return self._whisper_model
        
    def detect_language(self, text):
        """Detect language from recognized text using heuristics."""
        turkish_chars = set("ğüşıöçĞÜŞİÖÇ")
        turkish_words = {"merhaba", "nasılsın", "evet", "hayır", "tamam", "teşekkür", "günaydın"}
        low = text.lower()
        if any(c in turkish_chars for c in text) or any(w in low for w in turkish_words):
            return "tr"
        return "en"
            
    def set_language(self, lang):
        """Set the assistant's language."""
        if lang in ["en", "tr"]:
            self.language = lang
            # Reset chat with new language context
            if self.model:
                context = (
                    "You are a friendly voice assistant. Follow these rules strictly:\n"
                    "1. Keep responses EXTREMELY short - maximum 10-15 words\n"
                    "2. Use casual, everyday language\n"
                    "3. Never explain or apologize\n"
                    "4. Never add greetings or pleasantries\n"
                    f"5. Always respond in {'English' if lang == 'en' else 'Turkish'}\n"
                    "6. Never ask follow-up questions\n"
                    "Examples:\n"
                    "- User: 'What's the weather?' → 'It's sunny and warm today'\n"
                    "- User: 'Tell me about AI' → 'AI helps computers think and learn'\n"
                    "- User: 'How are you?' → 'Doing great!'\n"
                    "- User: 'What can you do?' → 'I can chat, help with tasks, and answer questions'"
                )
                self.chat = self.model.start_chat(history=[])
                self.chat.send_message(context)
            print(f"Language set to: {'English' if lang == 'en' else 'Turkish'}")
        else:
            print("Unsupported language. Using English.")
            self.language = "en"
            
    def listen(self):
        """Record audio from microphone and convert to text"""
        if not self.microphone_available:
            print("Error: Voice recognition system not available")
            return None
            
        try:
            with self.microphone as source:
                print("\nListening...")
                start_time = time.time()
                
                try:
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                    audio_duration = time.time() - start_time
                    print(f"Audio captured in {audio_duration:.2f}s")
                except sr.WaitTimeoutError:
                    return None
                    
                # Try Google Speech Recognition first
                try:
                    google_start = time.time()
                    text = self.recognizer.recognize_google(audio)
                    google_time = time.time() - google_start
                    self.service_stats['google']['success'] += 1
                    self.service_stats['google']['total_time'] += google_time
                    print(f"Google Speech Recognition: {google_time:.2f}s")
                    print(f"You said: {text}")
                    
                    # Auto-detect language from first utterance if not set
                    if not hasattr(self, 'language') or self.language is None:
                        detected_lang = self.detect_language(text)
                        self.set_language(detected_lang)
                        
                    return text.lower().strip()
                except sr.UnknownValueError:
                    print("\nTrying Whisper...")
                    self.service_stats['google']['failed'] += 1
                except sr.RequestError:
                    print("\nUsing Whisper...")
                    self.service_stats['google']['failed'] += 1
                    
                # Try Whisper as a fallback
                try:
                    whisper_start = time.time()
                    audio_data = audio.get_wav_data()
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                        temp_wav.write(audio_data)
                        temp_wav.flush()
                        result = self.whisper_model.transcribe(temp_wav.name)
                        os.remove(temp_wav.name)
                        text = result["text"].strip()
                        whisper_time = time.time() - whisper_start
                        self.service_stats['whisper']['success'] += 1
                        self.service_stats['whisper']['total_time'] += whisper_time
                        print(f"Whisper Recognition: {whisper_time:.2f}s")
                        print(f"You said: {text}")
                        
                        # Auto-detect language if not set
                        if not hasattr(self, 'language') or self.language is None:
                            self.set_language(result.get("language", "en"))
                            
                        return text.lower().strip()
                except Exception as e:
                    print(f"Error in speech recognition: {str(e)}")
                    self.service_stats['whisper']['failed'] += 1
                    return None
                    
        except Exception as e:
            print(f"Error in listen: {str(e)}")
            return None
            
    def _ensure_pygame(self):
        if not self._pygame_ready:
            pygame.mixer.init()
            self._pygame_ready = True

    def speak(self, text):
        """Convert text to speech and play it."""
        try:
            # Try ElevenLabs first
            elevenlabs_start = time.time()
            audio_file = self.elevenlabs.text_to_speech(text)
            if audio_file:
                self._ensure_pygame()
                pygame.mixer.music.load(audio_file)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                pygame.mixer.music.unload()
                os.remove(audio_file)
                elevenlabs_time = time.time() - elevenlabs_start
                self.service_stats['elevenlabs']['success'] += 1
                self.service_stats['elevenlabs']['total_time'] += elevenlabs_time
                print(f"ElevenLabs synthesis: {elevenlabs_time:.2f}s")
                return True
                
            # Use system voice as fallback
            print("Using system voice...")
            system_start = time.time()
            voice = "Alex" if self.language == "en" else "Yelda"
            os.system(f'say -v {voice} "{text}"')
            system_time = time.time() - system_start
            self.service_stats['system_voice']['success'] += 1
            self.service_stats['system_voice']['total_time'] += system_time
            print(f"System voice synthesis: {system_time:.2f}s")
            return True
            
        except Exception as e:
            print(f"Error in speak: {str(e)}")
            if 'elevenlabs' in str(e):
                self.service_stats['elevenlabs']['failed'] += 1
            else:
                self.service_stats['system_voice']['failed'] += 1
            return False
            
    def get_response(self, text):
        """Generate a short voice response using the LLM router."""
        exit_commands_en = ['exit', 'quit', 'bye', 'goodbye', 'stop']
        exit_commands_tr = ['çık', 'çıkış', 'güle güle', 'hoşça kal', 'dur']
        lang = getattr(self, 'language', 'en') or 'en'

        text = text.lower().strip()
        if any(cmd in text for cmd in (exit_commands_en if lang == "en" else exit_commands_tr)):
            return None

        try:
            if self._llm_router is None:
                from ..core.providers import LLMRouter
                self._llm_router = LLMRouter()

            lang_instruction = "English" if lang == "en" else "Turkish"
            system_msg = (
                f"You are a voice assistant. Reply in {lang_instruction}. "
                "Maximum 15 words. Direct answers only, no greetings or filler."
            )
            from ..core.providers.base_provider import Message
            messages = [Message(role="system", content=system_msg)]
            for turn in self._conv_history[-6:]:  # last 3 exchanges
                messages.append(Message(role=turn["role"], content=turn["content"]))
            messages.append(Message(role="user", content=text))

            reply = asyncio.run(
                self._llm_router.chat(messages, task_type="quick_answer")
            ).strip()
            words = reply.split()
            reply = ' '.join(words[:15]) + ('...' if len(words) > 15 else '')

            self._conv_history.append({"role": "user", "content": text})
            self._conv_history.append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            print(f"Error getting AI response: {e}")
            return "Sorry, something went wrong." if lang == "en" else "Üzgünüm, bir hata oluştu."
            
    def is_command(self, text):
        """Check if the input is a command."""
        commands = {
            'en': {
                'exit': ['exit', 'quit', 'bye', 'goodbye', 'stop'],
                'switch_lang': ['switch language', 'change language'],
                'help': ['help', 'commands', 'what can you do'],
                'clear': ['clear', 'clear chat', 'reset chat']
            },
            'tr': {
                'exit': ['çık', 'çıkış', 'güle güle', 'hoşça kal', 'dur', 'kapat'],
                'switch_lang': ['dil değiştir', 'dili değiştir'],
                'help': ['yardım', 'komutlar', 'neler yapabilirsin'],
                'clear': ['temizle', 'sohbeti temizle', 'sohbeti sıfırla']
            }
        }
        
        text = text.lower().strip()
        current_commands = commands[self.language]
        
        for cmd_type, cmd_list in current_commands.items():
            if any(cmd in text for cmd in cmd_list):
                return cmd_type
        return None

    def handle_command(self, command_type):
        """Handle system commands during conversation."""
        if command_type == 'exit':
            return None
        elif command_type == 'switch_lang':
            new_lang = 'tr' if self.language == 'en' else 'en'
            self.set_language(new_lang)
            return "Language switched!" if new_lang == 'en' else "Dil değiştirildi!"
        elif command_type == 'help':
            if self.language == 'en':
                return "Available commands: exit, switch language, help, clear chat"
            else:
                return "Mevcut komutlar: çıkış, dil değiştir, yardım, temizle"
        elif command_type == 'clear':
            if self.model:
                self.chat = self.model.start_chat(history=[])
            return "Chat cleared!" if self.language == 'en' else "Sohbet temizlendi!"
        return None

    def command_listener(self):
        """Listen for commands in a separate thread."""
        while self.conversation_active:
            try:
                cmd = input().strip().lower()
                self.command_queue.put(cmd)
                if cmd in ['exit', 'quit', 'stop', 'çık', 'çıkış', 'dur']:
                    break
            except Exception:
                continue

    def start_listening(self):
        """Start voice recognition mode."""
        if not self.microphone_available:
            print("Error: Voice recognition system not available")
            return False
            
        self.listening = True
        return True
        
    def stop_listening(self):
        """Stop voice recognition mode."""
        self.listening = False

    def start_conversation(self):
        """Start interactive conversation mode."""
        if not self.microphone_available:
            print("Error: Cannot start conversation - voice recognition system not available")
            return
            
        print("\nConversation mode activated in background.")
        print("Language will be detected automatically from your speech.")
        print("You can continue using agent commands while conversing.")
        print("Type 'stop conversation' to end.")
        
        self.conversation_active = True
        
        try:
            while self.conversation_active:
                text = self.listen()
                if text and self.conversation_active:
                    response = self.get_response(text)
                    if response:
                        print(f"\nAssistant: {response}")
                        self.speak(response)
                    
        except KeyboardInterrupt:
            print("\nStopping conversation...")
        finally:
            self.conversation_active = False
            if self._pygame_ready:
                pygame.mixer.quit()
                self._pygame_ready = False

    def start(self):
        """Start voice command mode."""
        if not self.microphone_available:
            print("Error: Cannot start voice assistant - voice recognition system not available")
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

    def print_stats(self):
        """Print service statistics."""
        print("\nService Statistics:")
        for service, stats in self.service_stats.items():
            total = stats['success'] + stats['failed']
            if total > 0:
                avg_time = stats['total_time'] / stats['success'] if stats['success'] > 0 else 0
                success_rate = (stats['success'] / total) * 100 if total > 0 else 0
                print(f"\n{service.upper()}:")
                print(f"Success Rate: {success_rate:.1f}%")
                print(f"Average Time: {avg_time:.2f}s")
                print(f"Total Calls: {total}")