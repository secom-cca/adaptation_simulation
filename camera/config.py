"""
カメラシステム設定
"""

# === 物体検出閾値 ===
HEIGHT_THRESHOLD_M = 0.03       # テーブルからの最小高さ (m) - これより低いものは無視
HEIGHT_MAX_THRESHOLD_M = 0.30   # テーブルからの最大高さ (m) - これより高いものは無視
MIN_CONTOUR_AREA = 30           # 検出する物体の最小面積 (ピクセル^2)

# === フレームレート ===
CAMERA_FPS = 15                 # カメラのフレームレート
DETECTION_FPS = 15              # 物体検出のフレームレート
TIME_INTERVAL = 1 / DETECTION_FPS

# === カメラ解像度 ===
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

# === ArUco マーカー設定 ===
ARUCO_DICT_TYPE = "DICT_4X4_50"
MARKER_ORDER = [0, 1, 3, 2]     # マーカーIDと配置順序（時計回り: 左上→右上→右下→左下）

# === マーカーチェック設定 ===
MARKER_CHECK_INTERVAL = 1.0     # マーカー確認間隔（秒）
DRIFT_THRESHOLD = 10            # ずれ閾値（ピクセル）

# 設定を辞書形式でエクスポート
CAMERA_CONFIG = {
    "height_threshold_m": HEIGHT_THRESHOLD_M,
    "height_max_threshold_m": HEIGHT_MAX_THRESHOLD_M,
    "min_contour_area": MIN_CONTOUR_AREA,
    "camera_fps": CAMERA_FPS,
    "detection_fps": DETECTION_FPS,
    "time_interval": TIME_INTERVAL,
    "camera_width": CAMERA_WIDTH,
    "camera_height": CAMERA_HEIGHT,
    "aruco_dict_type": ARUCO_DICT_TYPE,
    "marker_order": MARKER_ORDER,
    "marker_check_interval": MARKER_CHECK_INTERVAL,
    "drift_threshold": DRIFT_THRESHOLD,
}
