#!/usr/bin/env python3
"""Example module for Hailo Detection + ByteTrack + Supervision."""

import argparse
import camera_processor
import controller
import telegram
import threading
import queue

def initialize_arg_parser() -> argparse.ArgumentParser:
    """Initialize argument parser for the script."""
    parser = argparse.ArgumentParser(
        description="Detection Example - Tracker with ByteTrack and Supervision"
    )
    parser.add_argument(
        "-n", "--net", help="Path for the HEF model.", default="/home/pi/Documents/hailo_robot/models/yolox_l_leaky.hef"
    )
    parser.add_argument(
        "-l", "--labels", default="/home/pi/Documents/hailo_robot/settings", help="Path to a text file containing labels."
    )
    parser.add_argument(
        "-s", "--score_thresh", type=float, default=0.5, help="Score threshold - between 0 and 1."
    )
    return parser

def main() -> None:
    """Main function to run the video processing."""
    # Parse command-line arguments
    args = initialize_arg_parser().parse_args()

    camera_queue: queue.Queue = queue.LifoQueue(maxsize=180)
    camera_processor.camera_queue = camera_queue
    controller.camera_queue = camera_queue


    # Start the telegram listener
    telegram_thread: threading.Thread = threading.Thread(target=telegram.telegram_bot.infinity_polling)
    telegram_thread.start()

    # Start the camera listener
    camera_thread: threading.Thread = threading.Thread(target=camera_processor.run, args=(args.net, args.score_thresh))
    camera_thread.start()

    telegram.telegram_bot.stop_polling()
    telegram_thread.join()
    camera_thread.join()

if __name__ == "__main__":
    main()