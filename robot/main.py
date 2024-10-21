#!/usr/bin/env python3
"""Example module for Hailo Detection + ByteTrack + Supervision."""

import argparse
from typing import Dict, List, Tuple
import camera_processor
import time
import telegram
import threading
import queue

def initialize_arg_parser() -> argparse.ArgumentParser:
    """Initialize argument parser for the script."""
    parser = argparse.ArgumentParser(
        description="Detection Example - Tracker with ByteTrack and Supervision"
    )
    parser.add_argument(
        "-n", "--net", help="Path for the HEF model.", default="../models/yolov10b.hef"
    )
    parser.add_argument(
        "-l", "--labels", default="../settings/coco.txt", help="Path to a text file containing labels."
    )
    parser.add_argument(
        "-s", "--score_thresh", type=float, default=0.5, help="Score threshold - between 0 and 1."
    )
    return parser

def main() -> None:
    """Main function to run the video processing."""
    # Parse command-line arguments
    args = initialize_arg_parser().parse_args()

    camera_queue: queue.Queue = queue.Queue()
    telegram.camera_queue = camera_queue
    camera_processor.camera_queue = camera_queue

    # Start the telegram listener
    telegram_thread: threading.Thread = threading.Thread(target=telegram.bot.infinity_polling)
    telegram_thread.start()

    # Start the camera listener
    camera_thread: threading.Thread = threading.Thread(target=camera_processor.run, args=(args.net, args.score_thresh))
    camera_thread.start()

    telegram.bot.stop_polling()
    telegram_thread.join()
    camera_thread.join()

if __name__ == "__main__":
    main()