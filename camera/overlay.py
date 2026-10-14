"""RealSense検出結果の描画ユーティリティ。"""

import cv2
import numpy as np


def draw_detected_objects(image, objects, roi_points):
    """検出した物体、座標、高さをカメラ画像へ描画する。"""
    display = image.copy()
    cv2.polylines(
        display,
        [roi_points.reshape((-1, 1, 2)).astype(int)],
        True,
        (0, 255, 0),
        2,
    )

    for obj in objects:
        cv2.drawContours(display, [obj["contour"]], -1, (255, 0, 0), 2)
        cx = obj["cx_pixel"]
        cy = obj["cy_pixel"]
        cv2.circle(display, (cx, cy), 5, (0, 0, 255), -1)
        cv2.putText(
            display,
            f"#{obj['id']} ({obj['x']:.2f},{obj['y']:.2f})",
            (cx + 10, cy - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (0, 0, 255),
            1,
        )
        cv2.putText(
            display,
            f"h={obj['height'] * 100:.1f}cm",
            (cx + 10, cy + 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (0, 0, 255),
            1,
        )

    return display


def draw_height_map(depth_frame, base_depth_map, mask, max_height):
    """テーブル面との差分から高さマップを生成する。"""
    depth_image = np.asanyarray(depth_frame.get_data())
    depth_m = depth_image.astype(np.float32) * depth_frame.get_units()
    height_from_table = base_depth_map - depth_m
    height_normalized = np.clip(height_from_table / max_height, 0, 1)
    height_8bit = (height_normalized * 255).astype(np.uint8)
    height_colormap = cv2.applyColorMap(height_8bit, cv2.COLORMAP_JET)
    height_colormap[mask > 0] = [0, 0, 0]
    return height_colormap
