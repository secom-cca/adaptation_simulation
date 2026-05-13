"""
物体検出モジュール
"""

import cv2
import numpy as np
try:
    from .config import HEIGHT_THRESHOLD_M, HEIGHT_MAX_THRESHOLD_M, MIN_CONTOUR_AREA
    from .coordinate import transform_point_to_normalized
except ImportError:    
    from config import HEIGHT_THRESHOLD_M, HEIGHT_MAX_THRESHOLD_M, MIN_CONTOUR_AREA
    from coordinate import transform_point_to_normalized


def detect_objects_2d(depth_frame, color_image, roi_points, base_depth_map, perspective_matrix,
                      min_height=None, max_height=None, min_area=None):
    """
    2D深度画像から物体を検出（傾き補正対応版）
    
    Args:
        depth_frame: RealSense深度フレーム
        color_image: カラー画像
        roi_points: ROIの4点座標
        base_depth_map: 各ピクセルの基準深度（平面フィッティング済み）
        perspective_matrix: 射影変換行列（マーカー基準座標用）
        min_height: 最小高さ閾値（m）
        max_height: 最大高さ閾値（m）
        min_area: 最小面積閾値（ピクセル^2）
    
    Returns:
        (objects, mask_combined)
        objects: list of {"id", "x", "y", "height", "cx_pixel", "cy_pixel", "contour"}
        mask_combined: 検出マスク画像
    """
    if min_height is None:
        min_height = HEIGHT_THRESHOLD_M
    if max_height is None:
        max_height = HEIGHT_MAX_THRESHOLD_M
    if min_area is None:
        min_area = MIN_CONTOUR_AREA
    
    depth_image = np.asanyarray(depth_frame.get_data())
    depth_scale = depth_frame.get_units()  # 深度値をメートルに変換する係数
    
    # 深度をメートルに変換
    depth_m = depth_image.astype(np.float32) * depth_scale
    
    # ROIマスクを作成
    mask_roi = np.zeros(depth_image.shape, dtype=np.uint8)
    roi_poly = roi_points.reshape((-1, 1, 2)).astype(np.int32)
    cv2.fillPoly(mask_roi, [roi_poly], 255)
    
    # 高さに基づくマスク（基準面より高い物体 = 深度が小さい）
    min_depth = base_depth_map - max_height  # 物体の上限
    max_depth = base_depth_map - min_height  # 物体の下限
    
    mask_height = ((depth_m > min_depth) & (depth_m < max_depth) & (depth_m > 0)).astype(np.uint8) * 255
    
    # ROIと高さマスクを組み合わせ
    mask_combined = cv2.bitwise_and(mask_roi, mask_height)
    
    # 輪郭検出
    contours, _ = cv2.findContours(mask_combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    objects = []
    for i, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        if area < min_area:
            continue
        
        # 重心を計算
        M = cv2.moments(contour)
        if M["m00"] == 0:
            continue
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        
        # その領域の深度から高さを計算（重心位置の基準深度を使用）
        base_depth_at_center = base_depth_map[cy, cx]
        contour_mask = np.zeros(depth_image.shape, dtype=np.uint8)
        cv2.drawContours(contour_mask, [contour], -1, 255, -1)
        contour_depths = depth_m[contour_mask > 0]
        valid_depths = contour_depths[(contour_depths > 0) & (contour_depths < base_depth_at_center)]
        
        if len(valid_depths) > 0:
            object_height = base_depth_at_center - np.min(valid_depths)
        else:
            object_height = 0.0
        
        # 射影変換でマーカー基準の正規化座標に変換
        x_norm, y_norm = transform_point_to_normalized(cx, cy, perspective_matrix)
        
        objects.append({
            "id": len(objects) + 1,
            "x": x_norm,
            "y": y_norm,
            "height": float(object_height),
            "cx_pixel": cx,
            "cy_pixel": cy,
            "contour": contour
        })
    
    return objects, mask_combined
