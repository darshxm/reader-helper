"""
Gemini API worker thread for handling asynchronous AI requests.
"""

from PyQt6.QtCore import QThread, pyqtSignal
from google.genai import types
from utils import MODEL


class GeminiWorker(QThread):
    """Background worker for Gemini API calls with streaming."""
    chunk_received = pyqtSignal(str)
    finished_response = pyqtSignal(str)  # Emit full response for history
    error_occurred = pyqtSignal(str)
    
    def __init__(self, client, message: str, model: str = MODEL,
                 uploaded_file=None, conversation_history: list = None,
                 system_instruction: str = "", image_bytes: bytes = None):
        super().__init__()
        self.client = client
        self.message = message
        self.model = model
        self.uploaded_file = uploaded_file  # File reference from Files API
        self.conversation_history = conversation_history or []
        self.system_instruction = system_instruction
        self.image_bytes = image_bytes  # Image from selection
        self._is_cancelled = False
    
    def cancel(self):
        self._is_cancelled = True
    
    def run(self):
        try:
            # Build contents with uploaded file reference and conversation history
            contents = []
            
            # Add uploaded file reference (not raw bytes - much more efficient!)
            if self.uploaded_file:
                contents.append(self.uploaded_file)
            
            # Add conversation history for context (excluding current message)
            history_text = ""
            for msg in self.conversation_history[:-1]:  # Exclude current message
                role = "User" if msg["role"] == "user" else "Assistant"
                history_text += f"{role}: {msg['content']}\n\n"
            
            if history_text:
                contents.append(f"Previous conversation:\n{history_text}")
            
            # Add selected image if present
            if self.image_bytes:
                contents.append({
                    "mime_type": "image/png",
                    "data": self.image_bytes
                })
            
            # Add current message
            contents.append(f"Current question: {self.message}")
            
            # Make the API call with streaming
            response = self.client.models.generate_content_stream(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction
                ) if self.system_instruction else None
            )
            
            full_response = ""
            for chunk in response:
                if self._is_cancelled:
                    break
                if chunk.text:
                    full_response += chunk.text
                    self.chunk_received.emit(chunk.text)
            
            self.finished_response.emit(full_response)
        except Exception as e:
            self.error_occurred.emit(str(e))
