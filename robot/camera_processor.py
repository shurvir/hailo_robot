import supervision as sv
import numpy as np
import cv2
import queue
from typing import Dict, List, Tuple
import threading
from utils import HailoAsyncInference
import sys
import math

# Import picamera2 libraries
from picamera2 import Picamera2

def is_debugging():
  """Checks if the Python script is running in debug mode."""
  return sys.gettrace() is not None

camera_queue = None
class_names: List[str] = []

def preprocess_frame(frame: np.ndarray, model_h: int, model_w: int
) -> np.ndarray:
    """Preprocess the frame to match the model's input size."""
    resized_frame = cv2.resize(frame, (model_w, model_h))
    return resized_frame


def extract_detections(
    hailo_output: List[np.ndarray], h: int, w: int, threshold: float = 0.5
) -> Dict[str, np.ndarray]:
    """Extract detections from the HailoRT-postprocess output."""
    xyxy: List[np.ndarray] = []
    confidence: List[float] = []
    class_id: List[int] = []
    num_detections: int = 0

    for i, detections in enumerate(hailo_output):
        if len(detections) == 0:
            continue
        for detection in detections:
            bbox, score = detection[:4], detection[4]

            if score < threshold:
                continue

            # Convert bbox to xyxy absolute pixel values
            bbox[0], bbox[1], bbox[2], bbox[3] = (
                bbox[1] * w,
                bbox[0] * h,
                bbox[3] * w,
                bbox[2] * h,
            )

            xyxy.append(bbox)
            confidence.append(score)
            class_id.append(i)
            num_detections += 1

    return {
        "xyxy": np.array(xyxy),
        "confidence": np.array(confidence),
        "class_id": np.array(class_id),
        "num_detections": num_detections,
    }


def postprocess_detections(
    frame: np.ndarray,
    detections: Dict[str, np.ndarray],
    class_names: List[str],
    tracker: sv.ByteTrack,
    box_annotator: sv.RoundBoxAnnotator,
    label_annotator: sv.LabelAnnotator,
) -> np.ndarray:
    """Postprocess the detections by annotating the frame with bounding boxes and labels."""
    sv_detections = sv.Detections(
        xyxy=detections["xyxy"],
        confidence=detections["confidence"],
        class_id=detections["class_id"],
    )

    # Update detections with tracking information
    sv_detections = tracker.update_with_detections(sv_detections)

    # Generate tracked labels for annotated objects
    labels: List[str] = [
        f"#{tracker_id} {class_names[class_id]}"
        for class_id, tracker_id in zip(sv_detections.class_id, sv_detections.tracker_id)
    ]

    # Annotate objects with bounding boxes
    annotated_frame: np.ndarray = box_annotator.annotate(
        scene=frame.copy(), detections=sv_detections
    )
    # Annotate objects with labels
    annotated_labeled_frame: np.ndarray = label_annotator.annotate(
        scene=annotated_frame, detections=sv_detections, labels=labels
    )
    return annotated_labeled_frame, sv_detections

def get_coordinates_of_object(object_name: str, detection_results: sv.Detections) -> Tuple[int, int] | None:
    """
    Gets the coordinates of the top-left corner of the bounding box for the first detected object 
    with the given name and confidence above 0.5.

    Args:
        object_name: The name of the object to find.
        detection_results: The detection results containing bounding boxes and class IDs.

    Returns:
        A tuple containing the x and y coordinates of the top-left corner of the bounding box, 
        or None if the object is not found.
    """
    try:
        class_id = class_names.index(object_name)
    except ValueError:
        return None

    for box, detection_class_id, confidence in zip(
        detection_results.xyxy, detection_results.class_id, detection_results.confidence
    ):
        if detection_class_id == class_id and confidence > 0.5:
            adjusted_x_image = 640 - (box[2] + box[0])/2.0
            adjusted_y_image = (box[3] + box[1])/2.0

            robot_x = (1 / math.cos(math.radians((1280 - adjusted_y_image)*9/128)))*225
            robot_y = (adjusted_x_image/640.0)*225
            robot_z = 0

            return (robot_x, robot_y, robot_z)

    return None
    
def run(hef_path: str, score_thresh: float = 0.5):
    input_queue: queue.Queue = queue.Queue()
    output_queue: queue.Queue = queue.Queue()

    hailo_inference = HailoAsyncInference(
        hef_path=hef_path,
        input_queue=input_queue,
        output_queue=output_queue,
    )
    model_h, model_w, _ = hailo_inference.get_input_shape()

    # Initialize components for video processing
    box_annotator = sv.RoundBoxAnnotator()
    label_annotator = sv.LabelAnnotator()
    tracker = sv.ByteTrack()

    # Load class names from the labels file
    with open('/home/pi/Documents/hailo_robot/settings/coco.txt', "r", encoding="utf-8") as f:
        global class_names
        class_names = f.read().splitlines()

    # Start the asynchronous inference in a separate thread
    inference_thread: threading.Thread = threading.Thread(target=hailo_inference.run)
    inference_thread.start()

    # Initialize picamera2
    picam2 = Picamera2()
    picam2.configure(picam2.create_preview_configuration(main={"format": 'RGB888', "size": (1280, 1280)}))
    
    picam2.start()
    
    # Continuously capture frames
    while True:
        image = picam2.capture_array()

        # flip image
        image = cv2.flip(image, 0)
        image = cv2.flip(image, 1)

        # Preprocess the frame
        preprocessed_frame: np.ndarray = preprocess_frame(image, model_h, model_w)

        # Put the frame into the input queue for inference
        input_queue.put([preprocessed_frame])

        # Get the inference result from the output queue
        results: List[np.ndarray]
        _, results = output_queue.get()


        # Extract detections from the inference results
        detections: Dict[str, np.ndarray] = extract_detections(
            results[0], picam2.stream_configuration("main")["size"][1], picam2.stream_configuration("main")["size"][0], score_thresh
        )

        # Check if any detections were found
        if detections["num_detections"] > 0: 
            # Postprocess the detections and annotate the frame
            annotated_labeled_frame, sv_detections = postprocess_detections(
                image, detections, class_names, tracker, box_annotator, label_annotator
            )
            
            get_coordinates_of_object('teddy bear', sv_detections)

            # Display the resulting frame
            if not is_debugging():
                cv2.imshow(f'preview', annotated_labeled_frame)
            if camera_queue is not None:
                # Add to the queue
                if camera_queue.full():
                    camera_queue.get()
                camera_queue.put({'image': annotated_labeled_frame, 
                                  'detections': sv_detections})
        else:
            if not is_debugging():
                cv2.imshow(f'preview', image)

        # Break the loop if the 'q' key is pressed
        if not is_debugging():
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    # Signal the inference thread to stop and wait for it to finish
    input_queue.put(None)
    inference_thread.join()

    # Cleanup
    if not is_debugging():
        cv2.destroyAllWindows()
    picam2.stop()