import numpy as np
import cv2
import io
import tempfile
import os
from PIL import Image
from typing import Dict, List, Tuple
import math

def get_robot_coordinates_from_bbox(bbox: np.ndarray) -> Tuple[int, int]:
    """
    Converts a bounding box to robot coordinates.

    Args:
        bbox: 
    """
    adjusted_x_image = 640 - (bbox[2] + bbox[0])/2.0
    adjusted_y_image = (bbox[3] + bbox[1])/2.0

    print(f'adjusted_x: {adjusted_x_image}, adjusted_y: {adjusted_y_image}')
    robot_x = (1 / math.cos(math.radians((1280 - adjusted_y_image)*9/256)))*275
    robot_y = (adjusted_x_image/640.0)*350
    print(f'robot_x: {robot_x}, robot_y: {robot_y}')
    robot_z = -75

    return (robot_x, robot_y, robot_z)

def draw_square_on_image(image: np.ndarray, bbox: tuple) -> np.ndarray:
    """
    Draws a square on an image given the bounding box coordinates.

    Args:
        image: A NumPy array representing the image.
        bbox: A tuple containing the (x1, y1, x2, y2) coordinates 
              of the top-left and bottom-right corners of the bounding box.

    Returns:
        A NumPy array representing the image with the square drawn.
    """

    x1, y1, x2, y2 = bbox
    cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)  # Green color, thickness 2
    return image

def save_temp_image(image: np.ndarray):
    """
    Saves an image to a temporary file.

    Args:
        image: A NumPy array representing the image.
    """
    cv2.imwrite('/home/pi/Documents/hailo_robot/test_data/images/temp.png', image)

def convert_array_image(image_array, format):
    """
    Converts a NumPy array image to a BytesIO object.

    Args:
        image_array: A NumPy array representing the image.
        format: The format of the image (e.g., 'PNG' or 'JPEG').

    Returns:
        io.BytesIO: A BytesIO object containing the image data.
        PIL.Image: The PIL Image object.
    
    """
    img_rgb = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB) 
    img = Image.fromarray(img_rgb)
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format=format)  # 'PNG' or 'JPEG'
    img_byte_arr.seek(0)
    return img_byte_arr, img

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