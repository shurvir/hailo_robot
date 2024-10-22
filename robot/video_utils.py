import numpy as np
import cv2
import io
import tempfile
import os

def create_mp4_from_images(images, fps=4):
  """Creates an MP4 video from a list of NumPy array images and returns it as a BytesIO Blob.

  Args:
      images: A list of NumPy array images (e.g., from OpenCV).
      fps: Frames per second for the video (default: 24).

  Returns:
      io.BytesIO: The MP4 video data as a BytesIO Blob.
  """
  try:
    height, width, _ = images[0].shape
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')

    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
        temp_filename = temp_file.name

        # Create a VideoWriter object to write to the temporary file
        video_writer = cv2.VideoWriter(temp_filename, fourcc, fps, (width, height), isColor=True)

        for image in images:
            video_writer.write(image)

        video_writer.release()

    # Read the video data from the temporary file into a BytesIO object
    video_blob = io.BytesIO()
    with open(temp_filename, 'rb') as f:
        video_blob.write(f.read())

    # Remove the temporary file
    os.remove(temp_filename)

    video_blob.seek(0)  # Reset buffer position to the beginning
    return video_blob

  except Exception as e:
    print(f"An error occurred: {e}")
    return None

if __name__ == "__main__":
    # Example usage:
    num_images = 30
    images = [
        np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        for _ in range(num_images)
    ]

    video_blob = create_mp4_from_images(images)

    # Now you can use video_blob (e.g., send it over a network, save it to a database, etc.)
    if video_blob:
        with open('/home/pi/Desktop/my_video.mp4', 'wb') as f:
            f.write(video_blob.getbuffer())