"""
Camera パッケージ
RealSense カメラを用いた物体検出とArUcoマーカーキャリブレーション
"""

from .config import CAMERA_CONFIG
from .realsense_init import start_camera, get_aligned_frames
from .aruco_detector import (
    create_aruco_detector,
    detect_marker_bounds_2d,
    check_marker_positions
)
from .object_detector import detect_objects_2d
from .coordinate import (
    compute_perspective_transform,
    transform_point_to_normalized,
    transform_point_to_pixel,
    compute_base_depth_map
)
from .overlay import draw_game_overlay, draw_detected_objects, draw_height_map
from .main import run_camera_loop, main

__all__ = [
    # 設定
    "CAMERA_CONFIG",
    
    # カメラ初期化
    "start_camera",
    "get_aligned_frames",
    
    # ArUco検出
    "create_aruco_detector",
    "detect_marker_bounds_2d",
    "check_marker_positions",
    
    # 物体検出
    "detect_objects_2d",
    
    # 座標変換
    "compute_perspective_transform",
    "transform_point_to_normalized",
    "transform_point_to_pixel",
    "compute_base_depth_map",
    
    # 描画
    "draw_game_overlay",
    "draw_detected_objects",
    "draw_height_map",
    
    # メイン
    "run_camera_loop",
    "main",
]
