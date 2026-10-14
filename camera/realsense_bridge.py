#!/usr/bin/env python3
"""
RealSense 軽量ブリッジ

検出したオブジェクトを政策値へ変換し、ローカルのWebSocketリレー経由で
React UIへ送信する。
"""

import json
import time
import csv
import os
import cv2
import numpy as np
try:
    from .config import (
        TIME_INTERVAL,
        MARKER_CHECK_INTERVAL,
        DRIFT_THRESHOLD,
        CAMERA_HEIGHT,
        CAMERA_WIDTH,
    )
    from .realsense_init import start_camera, get_aligned_frames
    from .aruco_detector import create_aruco_detector, detect_marker_bounds_2d, check_marker_positions
    from .object_detector import detect_objects_2d
    from .coordinate import compute_base_depth_map, compute_perspective_transform
    from .overlay import draw_detected_objects
except ImportError:
    from config import (
        TIME_INTERVAL,
        MARKER_CHECK_INTERVAL,
        DRIFT_THRESHOLD,
        CAMERA_HEIGHT,
        CAMERA_WIDTH,
    )
    from realsense_init import start_camera, get_aligned_frames
    from aruco_detector import create_aruco_detector, detect_marker_bounds_2d, check_marker_positions
    from object_detector import detect_objects_2d
    from coordinate import compute_base_depth_map, compute_perspective_transform
    from overlay import draw_detected_objects

# --- React UI向けWebSocketリレー ---
WS_URI = "ws://localhost:3001"

#高さの閾値と単位
height_threshold = 0.00
height_unit = 0.01


def load_parameter_zones():
    """backend/data/parameter_zones.csv からゾーン定義を読み込む。"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.abspath(os.path.join(current_dir, "..", "backend", "data", "parameter_zones.csv"))
    zones = {}

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                param = row.get("param")
                if not param:
                    continue
                zones[param] = {
                    "x_min": float(row.get("x_min", 0.0)),
                    "x_max": float(row.get("x_max", 1.0)),
                    "y_min": float(row.get("y_min", 0.0)),
                    "y_max": float(row.get("y_max", 1.0)),
                    "mid": float(row["mid"]) if row.get("mid") not in (None, "") else None,
                    "max": float(row["max"]) if row.get("max") not in (None, "") else None,
                }
    except Exception as e:
        print(f"[WARN] parameter_zones.csv の読み込みに失敗: {e}")

    return zones


def count_objects_per_zone(object_positions_normalized, parameter_zones):
    """各ゾーン内の集計値を返す。

    変更点: `simulate_trigger` はこれまで通り個数カウントを返し、
    その他のパラメータは各物体の `height` を合算した連続値を返します。
    これによりゾーンの影響量を高さに比例させた連続値として扱えます。
    """
    counts = {}
    for param, bounds in parameter_zones.items():
        if param == "simulate_trigger":
            counts[param] = sum(
                bounds["x_min"] <= obj["x_norm"] <= bounds["x_max"]
                and bounds["y_min"] <= obj["y_norm"] <= bounds["y_max"]
                for obj in object_positions_normalized
            )
        else:
            total_point = 0.0
            for obj in object_positions_normalized:
                if bounds["x_min"] <= obj["x_norm"] <= bounds["x_max"] and bounds["y_min"] <= obj["y_norm"] <= bounds["y_max"]:
                    try:
                        h = float(obj.get("height", 0.0))
                    except Exception:
                        h = 0.0
                    total_point += min(int(max(0.0, h - height_threshold) / height_unit),5)  # 高さに基づく影響量を計算（例: 0.03m以上で影響開始、0.01mごとに1ポイント、最大5ポイント）
            counts[param] = float(total_point)
    return counts


def decide_parameter_values_normalized(object_positions_normalized, parameter_zones):
    """
    `count_objects_per_zone()` と同じ条件でゾーン内を判定し、
    各物体の高さを点数化したものを使う。
    """
    param_values = {}
    for param, bounds in parameter_zones.items():
        if param == "simulate_trigger":
            continue
        total_point = 0.0
        for obj in object_positions_normalized:
            if bounds["x_min"] <= obj["x_norm"] <= bounds["x_max"] and bounds["y_min"] <= obj["y_norm"] <= bounds["y_max"]:
                try:
                    h = float(obj.get("height", 0.0))
                except Exception:
                    h = 0.0
                total_point += min(int(max(0.0, h - height_threshold) / height_unit), 5)

        param_values[param] = min(total_point, 10)

        """
        これまでの段階的な閾値方式は廃止し、物体の高さに基づく連続値方式に変更した。
        if total_point >= 6:
            param_values[param] = bounds.get("max", 0)
        elif total_point >= 1:
            param_values[param] = bounds.get("mid", 0)
        else:
            param_values[param] = 0
        """

    return param_values


def connect_ws_client():
    """同期 WebSocket クライアントを生成。失敗時は None。"""
    try:
        from websockets.sync.client import connect
        ws = connect(WS_URI)
        print(f"[INFO] WebSocket に接続しました: {WS_URI}")
        return ws
    except Exception as e:
        print(f"[WARN] WebSocket 接続失敗: {e}")
        return None


def ws_send_json(ws_client, payload):
    """JSON 送信し、失敗時は接続を閉じて None を返す。"""
    if not ws_client:
        return None
    try:
        ws_client.send(json.dumps(payload))
        return ws_client
    except Exception as e:
        print(f"[WARN] WebSocket 送信失敗: {e}")
        try:
            ws_client.close()
        except Exception:
            pass
        return None


def run_realsense_bridge():
    pipeline, align = start_camera()
    aruco_dict, parameters, _ = create_aruco_detector()
    parameter_zones = load_parameter_zones()

    turn_counter = 0
    last_trigger_count = 0
    last_sent_counts = {}

    # 同期WebSocketクライアント（制御データ送信用）
    ws_client = connect_ws_client()

    last_update_time = time.time()
    last_marker_check_time = time.time()

    try:
        # 初期マーカー検出 -> ROI, depth map, perspective
        roi_points, marker_depths, marker_positions = detect_marker_bounds_2d(pipeline, align, aruco_dict, parameters)
        base_depth_map = compute_base_depth_map(roi_points, marker_depths, (CAMERA_HEIGHT, CAMERA_WIDTH))
        perspective_matrix = compute_perspective_transform(roi_points)
        inverse_perspective_matrix = np.linalg.inv(perspective_matrix)

        while True:
            depth_frame, color_frame = get_aligned_frames(pipeline, align)
            if not depth_frame or not color_frame:
                continue

            color_image = np.asanyarray(color_frame.get_data())

            # 表示（簡易）
            display_image = color_image.copy()
            cv2.polylines(display_image, [roi_points.reshape((-1, 1, 2)).astype(np.int32)], True, (0, 255, 0), 2)
            cv2.imshow('RealSense (Q to quit)', display_image)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            current_time = time.time()

            # マーカー再チェック
            if current_time - last_marker_check_time >= MARKER_CHECK_INTERVAL:
                new_roi, new_depths, drift, _ = check_marker_positions(color_image, depth_frame, aruco_dict, parameters, roi_points, DRIFT_THRESHOLD)
                if new_roi is not None and drift:
                    roi_points = new_roi
                    base_depth_map = compute_base_depth_map(new_roi, new_depths, (CAMERA_HEIGHT, CAMERA_WIDTH))
                    perspective_matrix = compute_perspective_transform(new_roi)
                    inverse_perspective_matrix = np.linalg.inv(perspective_matrix)
                last_marker_check_time = current_time

            # 定期更新と送信
            if current_time - last_update_time >= TIME_INTERVAL:
                objects, mask = detect_objects_2d(depth_frame, color_image, roi_points, base_depth_map, perspective_matrix)

                object_positions_normalized = []
                for obj in objects:
                    object_positions_normalized.append({
                        'id': int(obj.get('id', 0)),
                        'x_norm': float(obj.get('x', 0.0)),
                        'y_norm': float(obj.get('y', 0.0)),
                        'height': float(obj.get('height', 0.0)),
                    })

                if not ws_client:
                    ws_client = connect_ws_client()

                # --- realsense.py 由来: ゾーン集計 & 制御送信 ---
                if parameter_zones: #and object_positions_normalized:
                    counts = count_objects_per_zone(object_positions_normalized, parameter_zones)
                    current_trigger_count = int(counts.get("simulate_trigger", 0))

                    # 新規トリガー増加時のみ simulate_trigger を送る
                    if current_trigger_count > last_trigger_count:
                        turn_counter += 1
                        ws_client = ws_send_json(ws_client, {"simulate_trigger": True})
                        last_trigger_count = current_trigger_count
                        last_sent_counts = counts.copy()
                    elif turn_counter in [1, 2, 3]:
                        # ターン中は増減差分を送る
                        diff_data = {}
                        for param, value in counts.items():
                            if param == "simulate_trigger":
                                continue
                            prev = last_sent_counts.get(param, 0)
                            delta = int(value - prev)
                            if delta > 0:
                                diff_data[param] = int(min(delta, 10))
                            elif delta <= 0 and prev > 0:
                                diff_data[param] = 0

                        if diff_data:
                            ws_client = ws_send_json(ws_client, diff_data)
                            last_sent_counts = counts.copy()

                    param_update = decide_parameter_values_normalized(object_positions_normalized, parameter_zones)
                    if param_update:
                        ws_client = ws_send_json(ws_client, param_update)

                # --- ローカル表示: 輪郭と簡易オーバーレイ ---
                contour_display = draw_detected_objects(color_image, objects, roi_points)
                cv2.imshow('Detected Objects (bridge)', contour_display)

                last_update_time = current_time

    finally:
        if ws_client:
            try:
                ws_client.close()
            except:
                pass
        pipeline.stop()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    run_realsense_bridge()
