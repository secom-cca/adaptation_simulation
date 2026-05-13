"""
ArUco マーカー検出モジュール
"""

import cv2
import numpy as np
try:
    from .config import MARKER_ORDER  # 既存のドットあり
except ImportError:
    from config import MARKER_ORDER   # ドットなし（Macで直接動かす用）


def create_aruco_detector():
    """
    ArUco検出器を作成
    
    Returns:
        (aruco_dict, parameters, detector)
    """
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    parameters = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
    return aruco_dict, parameters, detector


def detect_marker_bounds_2d(pipeline, align, aruco_dict, parameters, required_marker_ids=None):
    """
    マーカーを検出し、ROI（ピクセル座標）とテーブル深度を返す
    
    Args:
        pipeline: RealSenseパイプライン
        align: アライメントオブジェクト
        aruco_dict: ArUco辞書
        parameters: ArUco検出パラメータ
        required_marker_ids: 必要なマーカーIDセット（デフォルトはMARKER_ORDER）
    
    Returns:
        roi_corners: マーカー4点のピクセル座標 (順序: 左上, 右上, 右下, 左下)
        table_depth: マーカーごとの深度配列
        marker_pixel_positions: {marker_id: (cx, cy)} の辞書
    """
    if required_marker_ids is None:
        required_marker_ids = set(MARKER_ORDER)
    
    print("[INFO] マーカー座標を初期化中 (4個のマーカーが必要です)...")
    print(f"[INFO] 必要なマーカーID: {sorted(required_marker_ids)}")
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
    
    while True:
        frames = pipeline.wait_for_frames()
        aligned_frames = align.process(frames)
        depth_frame = aligned_frames.get_depth_frame()
        color_frame = aligned_frames.get_color_frame()
        
        if not depth_frame or not color_frame:
            continue
            
        color_image = np.asanyarray(color_frame.get_data())
        corners, ids, _ = detector.detectMarkers(color_image)
        
        # カメラ映像を表示（マーカー検出状況も描画）
        display_image = color_image.copy()
        detected_ids = set(ids.flatten()) if ids is not None else set()
        missing_ids = required_marker_ids - detected_ids
        
        # 検出されたマーカーを描画
        if ids is not None and len(corners) > 0:
            cv2.aruco.drawDetectedMarkers(display_image, corners, ids)
        
        # ステータス表示
        status_text = f"Detected: {sorted(detected_ids)} | Missing: {sorted(missing_ids)}"
        cv2.putText(display_image, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, 
                    (0, 255, 0) if len(missing_ids) == 0 else (0, 0, 255), 2)
        cv2.imshow('RealSense - Marker Detection (Q to quit)', display_image)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            raise KeyboardInterrupt("ユーザーによる中断")
        
        if len(missing_ids) > 0:
            print(f"[WARN] マーカーが足りません。検出: {sorted(detected_ids)}, 未検出: {sorted(missing_ids)}")
            continue
        
        # マーカーの中心座標と深度を取得
        marker_positions = {}
        marker_depths = {}
        for i, marker_id in enumerate(ids.flatten()):
            corner = corners[i]
            cx = int(np.mean(corner[0][:, 0]))
            cy = int(np.mean(corner[0][:, 1]))
            depth = depth_frame.get_distance(cx, cy)
            marker_positions[marker_id] = (cx, cy)
            if depth > 0:
                marker_depths[marker_id] = depth
        
        # 全マーカーの深度が取得できたか確認
        if len(marker_depths) != len(MARKER_ORDER):
            print("[WARN] 一部マーカーの深度が取得できません。")
            continue
        
        # ROIのピクセル座標を取得（時計回りの順序で）
        all_points = np.array([marker_positions[mid] for mid in MARKER_ORDER])
        
        # MARKER_ORDER順に深度配列を作成
        depths_ordered = np.array([marker_depths[mid] for mid in MARKER_ORDER])
        
        print(f"[INFO] マーカー深度: {depths_ordered}")
        print("[INFO] 初期化完了。計測を開始します。")
        cv2.destroyWindow('RealSense - Marker Detection (Q to quit)')
        
        return all_points, depths_ordered, marker_positions


def check_marker_positions(color_image, depth_frame, aruco_dict, parameters, current_roi_points, 
                           drift_threshold=10, required_marker_ids=None):
    """
    マーカー位置を確認し、ドリフト（ずれ）を検出する軽量版関数
    
    Args:
        color_image: カラー画像
        depth_frame: 深度フレーム
        aruco_dict: ArUco辞書
        parameters: ArUco検出パラメータ
        current_roi_points: 現在のROI座標 (4点)
        drift_threshold: ずれの閾値（ピクセル）
        required_marker_ids: 必要なマーカーID（デフォルト: MARKER_ORDER）
    
    Returns:
        (new_roi_points, new_marker_depths, drift_detected, max_drift)
    """
    if required_marker_ids is None:
        required_marker_ids = set(MARKER_ORDER)
    
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
    corners, ids, _ = detector.detectMarkers(color_image)
    
    # マーカーが足りない場合
    if ids is None:
        return None, None, False, 0
    
    detected_ids = set(ids.flatten())
    if not required_marker_ids.issubset(detected_ids):
        missing = required_marker_ids - detected_ids
        print(f"[WARN] マーカー確認: 一部検出できません ({sorted(missing)})")
        return None, None, False, 0
    
    # マーカー位置と深度を取得
    marker_positions = {}
    marker_depths = {}
    for i, marker_id in enumerate(ids.flatten()):
        if marker_id in required_marker_ids:
            corner = corners[i]
            cx = int(np.mean(corner[0][:, 0]))
            cy = int(np.mean(corner[0][:, 1]))
            marker_positions[marker_id] = (cx, cy)
            depth = depth_frame.get_distance(cx, cy)
            if depth > 0:
                marker_depths[marker_id] = depth
    
    # 全マーカーの深度が取得できたか確認
    if len(marker_depths) != len(MARKER_ORDER):
        return None, None, False, 0
    
    # 新しいROI座標と深度配列を作成
    new_roi_points = np.array([marker_positions[mid] for mid in MARKER_ORDER])
    new_depths = np.array([marker_depths[mid] for mid in MARKER_ORDER])
    
    # ドリフト計算
    drifts = np.linalg.norm(new_roi_points - current_roi_points, axis=1)
    max_drift = np.max(drifts)
    drift_detected = max_drift > drift_threshold
    
    if drift_detected:
        print(f"[WARN] マーカーずれ検出: 最大 {max_drift:.1f}px (閾値: {drift_threshold}px)")
    
    return new_roi_points, new_depths, drift_detected, max_drift
