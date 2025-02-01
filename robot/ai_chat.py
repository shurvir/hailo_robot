from google import genai
from google.genai import types
from ollama import chat
import tempfile
import os
import time
from google.cloud import speech

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
DEEP_SEEK_API_KEY = os.environ.get('DEEP_SEEK_API_KEY')

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

    def get_bbox_coordinates(self, prompt, mime_type, data):
        pass

class DeepSeekChat(AIChat):

    _history: None
    _model:str = 'deepseek-r1:1.5b'
    
    def __init__(self):
        
        system_instruction="""
        I want you to behave as though you are a robot arm with audio visual capabilities.
        I have connected you to a physical robotic arm so any instructions I tell you, are carried out by the physical arm.
        Your text output is played into my living area via Speech to Text.
        Your name is Sharkie.
        Have a serious tone and don't make robot noises.
        """
        messages = [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": "Hello"},
                ]
        
        chat(
            self._model,
            messages=messages,
                stream=False
        )

        self._history = messages

    def send_message(self, message):
        messages = self._history
        messages.append({"role": "user", "content": message})
        response = chat(
            self._model,
            messages=messages,
            stream=False
        )
        messages += [
            {'role': 'assistant', 'content': response.message.content},
        ]
        self._history = messages

        return response.message.content

    def generate_content(self, prompt, mime_type, data):
        pass

    def generate_content_from_video(self, video_data, prompt):
        pass

    def get_bbox_coordinates(self, prompt, mime_type, data):
        pass


class GeminiChat(AIChat):
    """
    Represents a Gemini chat.
    
    Attributes:
        _model (genai.GenerativeModel): The model to use for the chat.
        _chat (genai.ChatSession): The chat session.
    
    """
    _client: genai.Client
    _chat = None
    _model_name: str

    def __init__(self):
        """
        Initializes a new instance of the GeminiChat class.
        """
        self._client = genai.Client(api_key=GEMINI_API_KEY)
        self._model_name = "gemini-2.0-flash-exp"

        system_instruction="""
        I want you to behave as though you are a robot arm with audio visual capabilities.
        I have connected you to a physical robotic arm so any instructions I tell you, are carried out by the physical arm.
        Your text output is played into my living area via Speech to Text.
        Your name is Sharkie.
        Have a serious tone and don't make robot noises.
        """
        self._chat = self._client.chats.create(
            model=self._model_name,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.5,
            ),
        )
    
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
    
    def generate_content(self, prompt, data):
        """
        Generates content using the model.
        
        Args:
            prompt (str): The prompt for the model.
            mime_type (str): The mime type for the model.
            data (bytes): The data for the model.
        
        Returns:
            str: The response from the model.
        """
        response = self._client.models.generate_content(
            model=self._model_name,
            contents=[
                data,
                prompt
            ]
        )

        return response.text
    
    def get_bbox_coordinates(self, prompt, data):
        """
        Generates bounding box coordinates using the model.

        Args:
            prompt (str): The prompt for the model.
            data (bytes): The data for the model.

        Returns:
            str: The response from the model.
        """
        bounding_box_system_instructions = """
        Return bounding boxes as a JSON array with labels. Never return masks or code fencing. Limit to 25 objects.
        If an object is present multiple times, name them according to their unique characteristic (colors, size, position, unique characteristics, etc..).
        """
        response = self._client.models.generate_content(
            model=self._model_name,
            contents=[prompt, data],
            config = types.GenerateContentConfig(
                system_instruction=bounding_box_system_instructions,
                temperature=0.5
            )
        )

        return response.text
    
    def generate_content_from_video(self, video_data, prompt, mime_type="video/mp4", video_file=None):
        """
        Generates content using the model.
        
        Args:
            video_data (bytes): The video data for the model.
            prompt (str): The prompt for the model.
        
        Returns:
            str: The response from the model.
        """
        if video_file is None:
            video_file = self.upload_bytes_as_video_file(video_data)
        response = self._client.models.generate_content(
            model=self._model_name,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_uri(
                            file_uri=video_file.uri,
                            mime_type=video_file.mime_type),
                        ]),
                prompt,
            ]
        )
        return response.text
    
    def upload_bytes_as_video_file(self, bytes_data):
        """Uploads bytes data as a file to Gemini.

        Args:
            bytes_data: The bytes data to upload.
            display_name: The display name for the uploaded file.

        Returns:
            The google.generativeai.File object representing the uploaded file.
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
            temp_file.write(bytes_data)
            temp_file_path = temp_file.name

        # Now use the temporary file path to upload
        video_file = self._client.files.upload(path=temp_file_path)
        os.remove(temp_file_path)

        # Check upload status
        while video_file.state == "PROCESSING":
            print('Waiting for video to be processed.')
            time.sleep(10)
            video_file = self._client.files.get(name=video_file.name)

        if video_file.state == "FAILED":
            raise ValueError(video_file.state.name)

        return video_file