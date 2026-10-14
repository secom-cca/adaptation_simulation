"""Intel RealSenseを使った物体検出・入力ブリッジ。"""

from .aruco_detector import (
    check_marker_positions,
    create_aruco_detector,
    detect_marker_bounds_2d,
)
from .config import CAMERA_CONFIG
from .coordinate import (
    compute_base_depth_map,
    compute_perspective_transform,
    transform_point_to_normalized,
    transform_point_to_pixel,
)
from .object_detector import detect_objects_2d
from .overlay import draw_detected_objects, draw_height_map
from .realsense_init import get_aligned_frames, start_camera

__all__ = [
    "CAMERA_CONFIG",
    "start_camera",
    "get_aligned_frames",
    "create_aruco_detector",
    "detect_marker_bounds_2d",
    "check_marker_positions",
    "detect_objects_2d",
    "compute_perspective_transform",
    "transform_point_to_normalized",
    "transform_point_to_pixel",
    "compute_base_depth_map",
    "draw_detected_objects",
    "draw_height_map",
]
