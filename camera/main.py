#!/usr/bin/env python3
"""
RealSense カメラ メインループ
ArUcoマーカーを用いたキャリブレーションと物体検出を実行
"""

import cv2
import numpy as np
import time
import datetime
import os
import sys
import importlib.util
import subprocess
import socket
import json

from .config import (
    TIME_INTERVAL,
    MARKER_CHECK_INTERVAL,
    DRIFT_THRESHOLD,
    CAMERA_HEIGHT,
    CAMERA_WIDTH
)
from .realsense_init import start_camera, get_aligned_frames
from .aruco_detector import create_aruco_detector, detect_marker_bounds_2d, check_marker_positions
from .object_detector import detect_objects_2d
from .coordinate import compute_base_depth_map, compute_perspective_transform
from .overlay import draw_game_overlay, draw_detected_objects

def load_simulation():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.abspath(os.path.join(current_dir, "..", "backend"))
    if backend_dir not in sys.path:
        sys.path.append(backend_dir)
    try:
        sim_path = os.path.join(backend_dir, "gaku_simulation.py")
        spec = importlib.util.spec_from_file_location("gaku_simulation", sim_path)
        sim_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sim_module)
        return sim_module.run_simulation
    except Exception as e:
        print(f"[WARN] シミュレーション読み込み失敗: {e}")
        return None

def get_ngrok_url():
    """ngrok のローカル API から公開 URL を取得する"""
    import urllib.request
    import json
    import time
    
    # 起動直後は API が準備できていない場合があるので数回リトライ
    for _ in range(5):
        try:
            with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels") as response:
                data = json.loads(response.read().decode())
                # 最初に見つかった https トンネルの URL を返す
                for tunnel in data.get("tunnels", []):
                    if tunnel["proto"] == "https":
                        return tunnel["public_url"]
        except:
            time.sleep(1)
    return None

def start_bridge_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        is_free = s.connect_ex(('127.0.0.1', 8765)) != 0
    if is_free:
        print("[INFO] Bridge Server を起動中...")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.abspath(os.path.join(current_dir, "..", "backend"))
        server_script = os.path.join(backend_dir, "bridge_server.py")
        log_file_path = os.path.join(backend_dir, "bridge_server.log")
        
        # ログをファイルに書き出しながらバックグラウンド起動
        f = open(log_file_path, "a", encoding="utf-8")
        subprocess.Popen([sys.executable, server_script], 
                         stdout=f, 
                         stderr=f,
                         cwd=backend_dir)
            
        print(f"[INFO] Server を開始しました (ログ: {log_file_path})")
    else:
        print("[INFO] Bridge Server はすでに動作しています (Port 8765)")

def start_ngrok():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            is_ngrok_running = s.connect_ex(('127.0.0.1', 4040)) == 0
    except:
        is_ngrok_running = False

    if not is_ngrok_running:
        print("[INFO] ngrok を起動中...")
        domain = "unquixotic-hypermetrical-matilde.ngrok-free.dev"
        try:
            subprocess.Popen(["ngrok", "http", "8765", f"--domain={domain}"], 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL)
            print(f"[INFO] ngrok を開始しました")
        except Exception as e:
            print(f"[ERROR] ngrok 起動失敗: {e}")
    else:
        print("[INFO] ngrok はすでに動作しています (Port 4040)")

def run_camera_loop():
    run_simulation = load_simulation()
    pipeline, align = start_camera()
    aruco_dict, parameters, _ = create_aruco_detector()
    last_update_time = time.time()
    last_marker_check_time = time.time()
    
    # WebSocket 送信用のクライアント（同期版）
    # 映像は送らず、軽量な数値データのみ送る
    ws_client = None
    try:
        from websockets.sync.client import connect
        ws_client = connect("ws://127.0.0.1:8765/stream")
    except Exception as e:
        print(f"[WARN] サーバーへの接続に失敗しました (スマホ同期は無効): {e}")

    try:
        roi_points, marker_depths, marker_positions = detect_marker_bounds_2d(pipeline, align, aruco_dict, parameters)
        base_depth_map = compute_base_depth_map(roi_points, marker_depths, (CAMERA_HEIGHT, CAMERA_WIDTH))
        perspective_matrix = compute_perspective_transform(roi_points)
        inverse_perspective_matrix = np.linalg.inv(perspective_matrix)
        
        while True:
            depth_frame, color_frame = get_aligned_frames(pipeline, align)
            if not depth_frame or not color_frame: continue
            
            color_image = np.asanyarray(color_frame.get_data())
            display_image = color_image.copy()
            cv2.polylines(display_image, [roi_points.reshape((-1, 1, 2)).astype(np.int32)], True, (0, 255, 0), 2)
            cv2.imshow('RealSense (Q to quit)', display_image)
            
            if cv2.waitKey(1) & 0xFF == ord('q'): break
            
            current_time = time.time()
            if current_time - last_marker_check_time >= MARKER_CHECK_INTERVAL:
                new_roi, new_depths, drift, _ = check_marker_positions(color_image, depth_frame, aruco_dict, parameters, roi_points, DRIFT_THRESHOLD)
                if new_roi is not None and drift:
                    roi_points, base_depth_map = new_roi, compute_base_depth_map(new_roi, new_depths, (CAMERA_HEIGHT, CAMERA_WIDTH))
                    perspective_matrix = compute_perspective_transform(new_roi)
                    inverse_perspective_matrix = np.linalg.inv(perspective_matrix)
                last_marker_check_time = current_time
            
            if current_time - last_update_time >= TIME_INTERVAL:
                objects, _ = detect_objects_2d(depth_frame, color_image, roi_points, base_depth_map, perspective_matrix)
                sim_result = run_simulation({"timestamp": datetime.datetime.now().isoformat(), "objects": objects}) if run_simulation else None
                
                # --- スマホに詳細なデータを送信 ---
                if ws_client:
                    try:
                        if sim_result:
                            # gaku_simulation.py はシミュレーション結果を dict で返す
                            # その中の "game_state" に詳細データ (enemies, towers等) が含まれている
                            payload = {
                                "score": float(sim_result.get("score", 0)),
                                "base_hp": float(sim_result.get("base_hp", 100)),
                                "game_over": sim_result.get("game_over", False),
                                "details": sim_result.get("game_state", {}),
                                "timestamp": sim_result.get("timestamp")
                            }
                            ws_client.send(json.dumps(payload))
                    except Exception as e:
                        print(f"[WARN] サーバーへの送信失敗: {e}")
                        ws_client = None 
                else:
                    try:
                        from websockets.sync.client import connect
                        ws_client = connect("ws://127.0.0.1:8765/stream", timeout=0.1)
                        print("[INFO] サーバーに再接続しました")
                    except:
                        pass
                
                contour_display = draw_detected_objects(color_image, objects, roi_points)
                contour_display = draw_game_overlay(contour_display, sim_result, inverse_perspective_matrix)
                cv2.imshow('Detected Objects', contour_display)
                last_update_time = current_time
    finally:
        if ws_client: ws_client.close()
        pipeline.stop()
        cv2.destroyAllWindows()

def main():
    print("[INFO] 🎮 システム起動中...")
    start_bridge_server()
    start_ngrok()
    
    public_url = get_ngrok_url()
    print("\n" + "="*60)
    print("🚀  SYSTEM READY")
    print("📱  スマホで URL を開いてください")
    if public_url:
        print(f"    {public_url}")
    else:
        print("    (ngrok 起動待ちです。ブラウザで http://localhost:4040 を開き")
        print("     Status -> Tunnels にある URL を確認して開いてください)")
    print("="*60 + "\n")
    
    run_camera_loop()

if __name__ == "__main__":
    main()
