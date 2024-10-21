import numpy as np
import sounddevice as sd
from piper.voice import PiperVoice
import asyncio

model_path = "/home/pi/Documents/en_US-lessac-medium.onnx"  # Replace with the actual path
voice = PiperVoice.load(model_path)

async def say(sentence: str):
    stream = sd.OutputStream(
        samplerate=voice.config.sample_rate,  # Match the model's sample rate
        channels=1,  # Mono audio
        dtype='int16'  # 16-bit integer data type
    )
    stream.start()

    for audio_bytes in voice.synthesize_stream_raw(sentence):
        int_data = np.frombuffer(audio_bytes, dtype=np.int16)
        stream.write(int_data)

    stream.stop()
    stream.close()

if __name__ == "__main__":
    asyncio.run(say("What you talking about... sucker"))