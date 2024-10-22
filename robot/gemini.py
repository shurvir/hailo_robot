import google.generativeai as genai
import os

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

class GeminiChat():
    """
    Represents a Gemini chat.
    
    Attributes:
        _model (genai.GenerativeModel): The model to use for the chat.
        _chat (genai.ChatSession): The chat session.
    
    """
    _model: genai.GenerativeModel
    _chat: genai.ChatSession

    def __init__(self):
        """
        Initializes a new instance of the GeminiChat class.
        """
        genai.configure(api_key=GEMINI_API_KEY)
        self._model = genai.GenerativeModel("gemini-1.5-flash")
        self._chat = self._model.start_chat()
    
    def send_message(self, message: str):
        """
        Sends a message to the chat and returns the response.

        Args:
            message (str): The message to send.

        Returns:
            str: The response from the chat.
        """
        return self._chat.send_message(message).text
    
    def generate_content(self, prompt, mime_type, data):
        """
        Generates content using the model.
        
        Args:
            prompt (str): The prompt for the model.
            mime_type (str): The mime type for the model.
            data (bytes): The data for the model.
        
        Returns:
            str: The response from the model.
        """
        return self._model.generate_content([
            prompt,
            {
                "mime_type": mime_type,
                "data": data
            }
        ]).text

