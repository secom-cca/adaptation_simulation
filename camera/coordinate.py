"""
座標変換モジュール
- 射影変換（ピクセル座標 ⇔ 正規化座標）
- 基準深度マップ計算
"""

import cv2
import numpy as np


def compute_perspective_transform(roi_points):
    """
    4点のマーカー座標から射影変換行列を計算
    変換後の座標は (0,0) 〜 (1,1) に正規化される
    
    Args:
        roi_points: マーカー4点の座標 (順序: 左上, 右上, 右下, 左下)
    
    Returns:
        射影変換行列 (3x3)
    """
    src_points = roi_points.astype(np.float32)
    
    # 変換先: 正規化された正方形 (0,0) 〜 (1,1)
    # スケールを1000倍にして計算精度を上げる
    dst_points = np.array([
        [0, 0],       # 左上
        [1000, 0],    # 右上
        [1000, 1000], # 右下
        [0, 1000]     # 左下
    ], dtype=np.float32)
    
    M = cv2.getPerspectiveTransform(src_points, dst_points)
    return M


def transform_point_to_normalized(cx, cy, perspective_matrix):
    """
    ピクセル座標をマーカー基準の正規化座標に変換
    
    Args:
        cx, cy: ピクセル座標
        perspective_matrix: 射影変換行列
    
    Returns:
        (x_norm, y_norm): 0-1に正規化された座標
    """
    point = np.array([[[cx, cy]]], dtype=np.float32)
    transformed = cv2.perspectiveTransform(point, perspective_matrix)
    x_norm = transformed[0][0][0] / 1000.0
    y_norm = transformed[0][0][1] / 1000.0
    
    # クリップ
    x_norm = np.clip(x_norm, 0.0, 1.0)
    y_norm = np.clip(y_norm, 0.0, 1.0)
    
    return float(x_norm), float(y_norm)


def transform_point_to_pixel(x_norm, y_norm, inverse_perspective_matrix):
    """
    正規化座標(0-1)をピクセル座標に変換
    
    Args:
        x_norm, y_norm: 正規化座標 (0-1)
        inverse_perspective_matrix: 逆射影変換行列
    
    Returns:
        (px, py): ピクセル座標
    """
    point = np.array([[[x_norm * 1000.0, y_norm * 1000.0]]], dtype=np.float32)
    transformed = cv2.perspectiveTransform(point, inverse_perspective_matrix)
    px = int(transformed[0][0][0])
    py = int(transformed[0][0][1])
    return px, py


def compute_base_depth_map(roi_points, marker_depths, image_shape):
    """
    4点のマーカーから平面をフィッティングし、
    各ピクセルの基準深度マップを生成
    
    Args:
        roi_points: マーカー4点の座標
        marker_depths: マーカーごとの深度（MARKER_ORDER順）
        image_shape: (height, width)
    
    Returns:
        base_depth_map: 各ピクセルの基準深度
    """
    # 4点の(x, y, depth)から平面方程式 ax + by + c = depth を計算
    points = []
    for i, (x, y) in enumerate(roi_points):
        points.append([x, y, 1, marker_depths[i]])
    
    # 最小二乗法で平面係数を求める
    A = np.array([[p[0], p[1], 1] for p in points])
    b = np.array([p[3] for p in points])
    coeffs, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
    
    # 全ピクセルの基準深度を計算
    h, w = image_shape
    y_coords, x_coords = np.mgrid[0:h, 0:w]
    base_depth_map = coeffs[0] * x_coords + coeffs[1] * y_coords + coeffs[2]
    
    return base_depth_map.astype(np.float32)
