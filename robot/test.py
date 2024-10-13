import os
import cv2
import numpy as np
import queue
from utils import HailoAsyncInference
from typing import Dict, List, Tuple
import threading
from scipy.io import loadmat

def load_PETA_metadata():
    dataset = dict()
    dataset['att_name'] = []

    # load PETA.MAT
    data = loadmat('/home/pi/Documents/hailo_robot/settings/PETA.mat')
    for idx in range(105):
        dataset['att_name'].append(data['peta'][0][0][1][idx,0][0])

    return dataset['att_name']

def preprocess_frame(frame: np.ndarray, model_h: int, model_w: int
) -> np.ndarray:
    """Preprocess the frame to match the model's input size."""
    resized_frame = cv2.resize(frame, (model_w, model_h))
    return resized_frame

# Path to the .hef file
hef_file = "/home/pi/Documents/hailo_robot/models/person_attr_resnet_v1_18.hef"

input_queue: queue.Queue = queue.Queue()
output_queue: queue.Queue = queue.Queue()

hailo_inference = HailoAsyncInference(
    hef_path=hef_file,
    input_queue=input_queue,
    output_queue=output_queue,
)
model_h, model_w, _ = hailo_inference.get_input_shape()

# Start the asynchronous inference in a separate thread
inference_thread: threading.Thread = threading.Thread(target=hailo_inference.run)
inference_thread.start()

image = cv2.imread("/home/pi/Documents/hailo_robot/test_data/images/image_png_5.png")

# Preprocess the frame
preprocessed_frame: np.ndarray = preprocess_frame(image, model_h, model_w)

# Put the frame into the input queue for inference
input_queue.put([preprocessed_frame])

# Get the inference result from the output queue
#results: List[np.ndarray]
_, results = output_queue.get()

petr_attributes = load_PETA_metadata()

print(petr_attributes)
print(results)

# Print the results
#for result in results:
#    print(f'{}')

# Signal the inference thread to stop and wait for it to finish
input_queue.put(None)
inference_thread.join()
 