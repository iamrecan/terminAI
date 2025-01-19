import google.generativeai as genai
import os
from dotenv import load_dotenv

class AIAssistant:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("GOOGLE_AI_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_AI_KEY not found in .env file")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        
        # Default conversation context
        self.conversation_context = """You are a friendly and helpful voice assistant. 
        Keep your responses brief, conversational, and natural - as if you're speaking, not writing.
        Use simple language and short sentences. Feel free to use casual expressions.
        Respond in a way that sounds natural when spoken aloud.
        If you don't know something, just say so casually.
        Keep responses under 3 sentences when possible."""
        
    def ask(self, question):
        """
        Ask a question to the AI model and get a response
        """
        try:
            # For structured prompts (asking for JSON), use a different context
            if "JSON" in question and "{" in question:
                prompt = f"""You are a helpful assistant that provides structured data.
                Always respond with valid JSON only, no other text.
                If you cannot provide valid JSON, respond with {{"error": "reason for error"}}
                
                Human: {question}
                Assistant:"""
            else:
                prompt = f"{self.conversation_context}\nHuman: {question}\nAssistant:"
                
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"Sorry, I ran into a problem: {str(e)}"
            
    def chat(self, message, history=None):
        """
        Have a natural conversation with the AI
        """
        try:
            if history is None:
                # Start a new chat session
                chat = self.model.start_chat(history=[])
                # Set the context for conversational responses
                chat.send_message(self.conversation_context)
            else:
                # Continue existing chat
                chat = history
                
            response = chat.send_message(message)
            return response.text, chat
        except Exception as e:
            return f"Oops, something went wrong: {str(e)}", history
