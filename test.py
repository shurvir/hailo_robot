import argparse
import sys
import os
from typing import Dict, List
import cv2

import numpy as np
import supervision as sv

from hailo_platform import (
    HEF,
    VDevice,
    HailoSchedulingAlgorithm,
)

# Assuming this is your Hailo inference class, modified for synchronous inference
from utils_sync import HailoAsyncInference

from picamera2 import Picamera2, Preview


def initialize_arg_parser() -> argparse.ArgumentParser:
    """Initialize argument parser for the script."""
    parser = argparse.ArgumentParser(
        description="Detection Example - Tracker with ByteTrack and Supervision"
    )
    parser.add_argument(
        "-n", "--net", help="Path for the HEF model.", default="/home/pi/Documents/hailo_robot/yolov5m_wo_spp.hef"
    )
    parser.add_argument(
        "-l", "--labels", default="/home/pi/Documents/hailo_robot/coco.txt", help="Path to a text file containing labels."
    )
    parser.add_argument(
        "-s", "--score_thresh", type=float, default=0.5, help="Score threshold - between 0 and 1."
    )
    return parser


def preprocess_frame(frame: np.ndarray, model_h: int, model_w: int) -> np.ndarray:
    """Preprocess the frame to match the model's input size and padding."""
    resized_frame = cv2.resize(frame, (model_w, model_h))

    # Calculate padding
    padding_bottom = model_h - resized_frame.shape[0]
    padding_right = model_w - resized_frame.shape[1]

    # Apply padding
    padded_frame = cv2.copyMakeBorder(
        resized_frame,
        0, padding_bottom, 0, padding_right,
        cv2.BORDER_CONSTANT,
        value=0
    )

    return padded_frame


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
        for _, (class_id, tracker_id) in enumerate(
            zip(sv_detections.class_id, sv_detections.tracker_id)
        )
    ]

    # Annotate objects with bounding boxes
    annotated_frame: np.ndarray = box_annotator.annotate(
        scene=frame.copy(), detections=sv_detections
    )
    # Annotate objects with labels
    annotated_labeled_frame: np.ndarray = label_annotator.annotate(
        scene=annotated_frame, detections=sv_detections, labels=labels
    )
    return annotated_labeled_frame


def main() -> None:
    """Main function to run the detection with tracker."""
    # Parse command-line arguments
    args = initialize_arg_parser().parse_args()

    # Initialize Hailo inference (modified for synchronous inference)
    hailo_inference = HailoAsyncInference(
        hef_path=args.net,
    )
    model_h, model_w, _ = hailo_inference.get_input_shape()

    # Initialize components for video processing
    box_annotator = sv.RoundBoxAnnotator()
    label_annotator = sv.LabelAnnotator()
    tracker = sv.ByteTrack()

    # Load class names from the labels file
    with open(args.labels, "r", encoding="utf-8") as f:
        class_names: List[str] = f.read().splitlines()

    # Initialize picamera2
    picam2 = Picamera2()
    picam2.start_preview(Preview.QTGL)
    preview_config = picam2.create_preview_configuration()
    capture_config = picam2.create_still_configuration()
    picam2.configure(preview_config)
    picam2.start()

    # Continuously capture and process frames
    while True:
        image = picam2.capture_array()

        # Preprocess the frame
        preprocessed_frame = preprocess_frame(image, model_h, model_w)

        # Perform inference
        results = hailo_inference.run(preprocessed_frame)

        # Extract detections
        detections = extract_detections(
            results,
            picam2.stream_configuration("main")["size"][1],
            picam2.stream_configuration("main")["size"][0],
            args.score_thresh
        )

        # Annotate frame if detections are found
        if detections["num_detections"] > 0:
            # Postprocess and annotate the frame
            annotated_frame = postprocess_detections(
                image, detections, class_names, tracker, box_annotator, label_annotator
            )
        else:
            annotated_frame = image

        # Display the annotated frame (using your preferred method)
        # Example using pygame:
        import pygame
        pygame.init()
        screen = pygame.display.set_mode(annotated_frame.shape[1::-1])
        pygame_surface = pygame.surfarray.make_surface(annotated_frame)
        screen.blit(pygame_surface, (0, 0))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_q:
                sys.exit()

if __name__ == "__main__":
    main()