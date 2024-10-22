import google.generativeai as genai
import tempfile
import os
import time

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

class AIChat():
    
    def __init__(self):
        pass

    def send_message(self, message):
        pass

    def generate_content(self, prompt, mime_type, data):
        pass

    def generate_content(self, video_data, prompt):
        pass


class GeminiChat(AIChat):
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
    
    def generate_content(self, video_data, prompt):
        """
        Generates content using the model.
        
        Args:
            video_data (bytes): The video data for the model.
            prompt (str): The prompt for the model.
        
        Returns:
            str: The response from the model.
        """
        video_file = self.upload_bytes_as_video_file(video_data, 'video.mp4')
        response = self._model.generate_content([video_file, prompt], request_options={"timeout": 600})
        return response.text
    
    def upload_bytes_as_video_file(self, bytes_data, display_name):
        """Uploads bytes data as a file to Gemini.

        Args:
            bytes_data: The bytes data to upload.
            display_name: The display name for the uploaded file.

        Returns:
            The google.generativeai.File object representing the uploaded file.
        """
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(bytes_data)
            temp_file_path = temp_file.name

        # Now use the temporary file path to upload
        video_file = genai.upload_file(
            path=temp_file_path, 
            display_name=display_name, 
            resumable=True, 
            mime_type="video/mp4"
        )
        # Check upload status
        while video_file.state.name == "PROCESSING":
            print(".", end="")
            time.sleep(2)
            video_file = genai.get_file(video_file.name)

        if video_file.state.name == "FAILED":
            raise ValueError(video_file.state.name)

        return video_file

