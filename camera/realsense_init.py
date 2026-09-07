"""
RealSense カメラ初期化モジュール
"""

import pyrealsense2 as rs
try:
    from .config import CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_FPS
except ImportError:
    from config import CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_FPS

def create_pipeline():
    """
    RealSense パイプラインを作成・設定
    
    Returns:
        (pipeline, align): パイプラインとアライメントオブジェクト
    """
    pipeline = rs.pipeline()
    config = rs.config()
    
    # 深度ストリーム設定
    config.enable_stream(
        rs.stream.depth, 
        CAMERA_WIDTH, 
        CAMERA_HEIGHT, 
        rs.format.z16, 
        CAMERA_FPS
    )
    
    # カラーストリーム設定
    config.enable_stream(
        rs.stream.color, 
        CAMERA_WIDTH, 
        CAMERA_HEIGHT, 
        rs.format.bgr8, 
        CAMERA_FPS
    )
    
    # 深度とカラーを揃えるためのalign
    align = rs.align(rs.stream.color)
    
    return pipeline, config, align


def start_camera():
    """
    カメラを起動して準備完了したパイプラインを返す
    
    Returns:
        (pipeline, align): 起動済みパイプラインとアライメントオブジェクト
    """
    pipeline, config, align = create_pipeline()
    pipeline.start(config)
    return pipeline, align


def get_aligned_frames(pipeline, align):
    """
    アライン済みのフレームを取得
    
    Args:
        pipeline: RealSenseパイプライン
        align: アライメントオブジェクト
    
    Returns:
        (depth_frame, color_frame): 深度フレームとカラーフレーム
    """
    frames = pipeline.wait_for_frames()
    aligned_frames = align.process(frames)
    depth_frame = aligned_frames.get_depth_frame()
    color_frame = aligned_frames.get_color_frame()
    return depth_frame, color_frame
