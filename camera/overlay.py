"""
ゲームオーバーレイ描画モジュール
"""

import cv2
from .coordinate import transform_point_to_pixel


def draw_game_overlay(image, sim_result, inverse_perspective_matrix):
    """
    gaku_simulation の返り値を OpenCV 画面へオーバーレイ描画
    
    Args:
        image: 描画先画像
        sim_result: シミュレーション結果辞書
        inverse_perspective_matrix: 逆射影変換行列
    
    Returns:
        オーバーレイ描画済み画像
    """
    if sim_result is None:
        return image

    game_state = sim_result.get("game_state", {})
    enemies = game_state.get("enemies", [])
    bullets = game_state.get("bullets", [])
    path = game_state.get("path", [])

    # 経路描画
    if len(path) >= 2:
        path_pixels = [transform_point_to_pixel(p[0], p[1], inverse_perspective_matrix) for p in path]
        for i in range(len(path_pixels) - 1):
            cv2.line(image, path_pixels[i], path_pixels[i + 1], (0, 255, 255), 2)

    # 敵描画
    for enemy in enemies:
        ex, ey = transform_point_to_pixel(enemy["x"], enemy["y"], inverse_perspective_matrix)
        cv2.circle(image, (ex, ey), 8, (0, 0, 255), -1)
        hp_text = f"{enemy['hp']:.0f}/{enemy['max_hp']:.0f}"
        cv2.putText(image, hp_text, (ex + 10, ey - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

    # 弾道描画
    for bullet in bullets:
        start = bullet.get("start", None)
        end = bullet.get("end", None)
        if start is None or end is None:
            continue
        sx, sy = transform_point_to_pixel(start[0], start[1], inverse_perspective_matrix)
        ex, ey = transform_point_to_pixel(end[0], end[1], inverse_perspective_matrix)
        cv2.line(image, (sx, sy), (ex, ey), (0, 255, 0), 2)

    # スコア/拠点HP/ウェーブ表示
    score = sim_result.get("score", 0)
    base_hp = sim_result.get("base_hp", 0)
    game_over = sim_result.get("game_over", False)
    wave_info = game_state.get("wave", {})
    
    # ウェーブ情報
    wave_number = wave_info.get("wave_number", 1)
    wave_state = wave_info.get("state", "")
    enemies_spawned = wave_info.get("enemies_spawned", 0)
    enemies_total = wave_info.get("enemies_total", 0)
    prep_remaining = wave_info.get("preparation_remaining", 0)

    # 背景ボックス
    cv2.rectangle(image, (8, 8), (280, 110), (0, 0, 0), -1)
    
    # スコアとHP
    cv2.putText(image, f"Score: {int(score)}", (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(image, f"Base HP: {int(base_hp)}", (16, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # ウェーブ情報
    if wave_state == "waiting":
        prep_sec = prep_remaining / 15  # 15fps想定
        wave_text = f"Wave {wave_number} - Ready in {prep_sec:.1f}s"
        cv2.putText(image, wave_text, (16, 84), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    elif wave_state in ("spawning", "fighting"):
        wave_text = f"Wave {wave_number} - {enemies_spawned}/{enemies_total}"
        cv2.putText(image, wave_text, (16, 84), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    elif wave_state == "completed":
        cv2.putText(image, f"Wave {wave_number} CLEAR!", (16, 84), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    
    if game_over:
        cv2.putText(image, "GAME OVER", (16, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3)

    return image


def draw_detected_objects(image, objects, roi_points):
    """
    検出された物体を画像に描画
    
    Args:
        image: 描画先画像
        objects: 検出された物体リスト
        roi_points: ROI座標
    
    Returns:
        描画済み画像
    """
    display = image.copy()
    
    # ROIを緑で描画
    cv2.polylines(display, [roi_points.reshape((-1, 1, 2)).astype(int)], True, (0, 255, 0), 2)
    
    for obj in objects:
        # 輪郭を青で描画
        cv2.drawContours(display, [obj["contour"]], -1, (255, 0, 0), 2)
        # 重心を赤丸で描画
        cx = obj["cx_pixel"]
        cy = obj["cy_pixel"]
        cv2.circle(display, (cx, cy), 5, (0, 0, 255), -1)
        # ID、座標、高さを表示
        cv2.putText(display, f"#{obj['id']} ({obj['x']:.2f},{obj['y']:.2f})", 
                   (cx + 10, cy - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        cv2.putText(display, f"h={obj['height']*100:.1f}cm", 
                   (cx + 10, cy + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
    
    return display


def draw_height_map(depth_frame, base_depth_map, mask, max_height):
    """
    高さマップを生成して描画
    
    Args:
        depth_frame: 深度フレーム
        base_depth_map: 基準深度マップ
        mask: 検出マスク
        max_height: 最大高さ（m）
    
    Returns:
        高さマップのカラー画像
    """
    import numpy as np
    
    depth_image = np.asanyarray(depth_frame.get_data())
    depth_scale = depth_frame.get_units()
    depth_m = depth_image.astype(np.float32) * depth_scale
    
    height_from_table = base_depth_map - depth_m
    height_normalized = np.clip(height_from_table / max_height, 0, 1)
    height_8bit = (height_normalized * 255).astype(np.uint8)
    height_colormap = cv2.applyColorMap(height_8bit, cv2.COLORMAP_JET)
    height_colormap[mask > 0] = [0, 0, 0]  # 検出部分を黒
    
    return height_colormap
