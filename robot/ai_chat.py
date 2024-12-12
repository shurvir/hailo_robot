import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import tempfile
import os
import time
from google.cloud import speech

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

def transcribe_audio_bytes(audio_bytes, language_code="en-US"):
  """
  Transcribes audio bytes using Google Cloud Speech-to-Text.

  Args:
    audio_bytes: The audio bytes to transcribe.
    language_code: The language of the audio (e.g., "en-US", "es-ES").

  Returns:
    The transcribed text.
  """

  client = speech.SpeechClient()

  audio = speech.RecognitionAudio(content=audio_bytes)
  config = speech.RecognitionConfig(
      encoding=speech.RecognitionConfig.AudioEncoding.OGG_OPUS,

      sample_rate_hertz=48000,  # Adjust if necessary
      language_code=language_code,
  )

  response = client.recognize(config=config, audio=audio)

  transcription = ""
  for result in response.results:
    transcription += result.alternatives[0].transcript

  return transcription


class AIChat():
    
    def __init__(self):
        pass

    def send_message(self, message):
        pass

    def generate_content(self, prompt, mime_type, data):
        pass

    def generate_content_from_video(self, video_data, prompt):
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
        self._model = genai.GenerativeModel("gemini-2.0-flash-exp")

        # Define the chat context
        context = [
            {"role": "user", "parts": ["I want you to behave as though you are a robot arm with audio visual capabilities.",
                                       "I have connected you to a physical robotic arm so any instructions I tell you, are carried out by the physical arm."
                                       "Your text output is played into my living area via Speech to Text.",
                                       "Your name is Sharkie.",
                                       "Have a serious tone and don't make robot noises."]},
            {"role": "model", "parts": "Sure, I understand."},
        ]

        # Start a chat session with the context
        self._chat = self._model.start_chat(history=context)
    
    def send_message(self, message: str):
        """
        Sends a message to the chat and returns the response.

        Args:
            message (str): The message to send.

        Returns:
            str: The response from the chat.
        """
        response = self._chat.send_message(message)
        output_message = response.text
        return output_message
    
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
        response = self._model.generate_content([
            prompt,
            {
                "mime_type": mime_type,
                "data": data
            }
        ])

        return response.text
    
    def generate_content_from_video(self, video_data, prompt):
        """
        Generates content using the model.
        
        Args:
            video_data (bytes): The video data for the model.
            prompt (str): The prompt for the model.
        
        Returns:
            str: The response from the model.
        """
        video_file = self.upload_bytes_as_video_file(video_data, 'video.mp4')
        response = self._model.generate_content([video_file, prompt], request_options={"timeout": 1800})
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

