import cv2
import json
import numpy as np
import matplotlib.pyplot as plt
import open3d as o3d
import pyrealsense2 as rs
import socket
import time


# === 設定値 ===
height_threshold = 0.05 # m

# === ArUco辞書の定義 ===
aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
parameters = cv2.aruco.DetectorParameters()

# === RealSense初期設定 ===
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
pipeline.start(config)

# === 初期化 ===
pc = rs.pointcloud()
pcd = o3d.geometry.PointCloud()
last_update_time = time.time()
plt.ion()  # インタラクティブモードON（非ブロッキング）
# fig = plt.figure(figsize=(6, 6))


# === 接続先 === 
HOST = '127.0.0.1'
PORT = 5000
client_socket = None
backend_available = False
try:
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))
    backend_available = True
    print("[INFO] バックエンドと接続に成功しました。")
except (ConnectionRefusedError, socket.error) as e:
    print(f"[WARN] バックエンドへの接続に失敗しました。送信はスキップされます。 ({e})")

def send_object_positions(objects):
    if not backend_available:
        return  # バックエンドが使えない場合はスキップ

    try:
        data = json.dumps({"objects": objects})
        client_socket.sendall(data.encode('utf-8'))
        print("[SENT]", data)
    except Exception as e:
        print("[SEND ERROR]", e)

def get_filtered_objects(
        object_cloud, 
        table_z, 
        marker_bounds_x_min, 
        marker_bounds_x_max, 
        marker_bounds_y_min, 
        marker_bounds_y_max, 
        height_threshold=height_threshold, 
        voxel_size=0.001
        ):
    # ダウンサンプリング & 高さフィルタ
    # print(f"[DEBUG] 基の点群座標: {object_cloud.points}")
    downsampled = object_cloud.voxel_down_sample(voxel_size)
    #downsampled = object_cloud
    points = np.asarray(downsampled.points)
    print(f"[DEBUG] 基の点群座標: {points}")

    within_marker = points[
    (points[:, 0] >= marker_bounds_x_min) & (points[:, 0] <= marker_bounds_x_max) &
    (points[:, 1] >= marker_bounds_y_min) & (points[:, 1] <= marker_bounds_y_max)
    ]

    # print(f"[DEBUG] 領域内の点群座標: {within_marker}")

    high_points = within_marker[within_marker[:, 2] < table_z - height_threshold]
    print(f"[DEBUG] テーブルまでの距離: {table_z:.4}")
    print(f"[DEBUG] 閾値としての距離: {(table_z - height_threshold):.4}")
    print(f"[DEBUG] マーカー範囲内 & 閾値以上の点群数：{len(high_points)}")
    
    if len(high_points) == 0:
        return None, None, None

    object_z = np.max(high_points[:, 2])
    height = object_z - table_z

    filtered_cloud = o3d.geometry.PointCloud()
    filtered_cloud.points = o3d.utility.Vector3dVector(high_points)
    return filtered_cloud, high_points, height

def align_point_cloud_to_table(pcd, plane_normal):
    # ===平面法線をZ軸（[0, 0, 1]）に合わせる回転行列を作成 ===
    z_axis = np.array([0.0, 0.0, 1.0])
    normal = plane_normal / np.linalg.norm(plane_normal)
    v = np.cross(normal, z_axis)
    c = np.dot(normal, z_axis)
    
    if np.linalg.norm(v) < 1e-6:
        R = np.eye(3)  # 回転不要
    else:
        s = np.linalg.norm(v)
        kmat = np.array([[    0, -v[2],  v[1]],
                         [ v[2],     0, -v[0]],
                         [-v[1],  v[0],    0]])
        R = np.eye(3) + kmat + (kmat @ kmat) * ((1 - c) / (s**2))
    
    # 回転行列で点群を回転
    pcd.rotate(R, center=(0, 0, 0))
    return R

# === 座標の正規化の処理 ===
def normalize_coordinates(x, y, 
                          x_min, x_max, 
                          y_min, y_max):
    x_norm = (x - x_min) / (x_max - x_min)
    y_norm = (y - y_min) / (y_max - y_min)
    return x_norm, y_norm

# === 四隅のマーカー座標の初期化 ===
def detect_marker_bounds(pipeline, aruco_dict, parameters, intrinsics):
    print("[INFO] マーカー座標を初期化中...")

    while True:
        frames = pipeline.wait_for_frames()
        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()
        color_image = np.asanyarray(color_frame.get_data())

        # マーカー検出
        corners, ids, _ = cv2.aruco.detectMarkers(color_image, aruco_dict, parameters=parameters)
        if ids is None or len(corners) < 4:
            print(f"[WARN] マーカーが検出されません。検出数：{len(corners) if corners else 0}、再試行中...")
            continue

        # マーカーの3D座標取得
        marker_xyz_array = []
        for corner in corners:
            cx = int(np.mean(corner[0][:, 0]))
            cy = int(np.mean(corner[0][:, 1]))
            depth = depth_frame.get_distance(cx, cy)
            x, y, z = rs.rs2_deproject_pixel_to_point(intrinsics, [cx, cy], depth)
            marker_xyz_array.append([x, y, z])
        marker_xyz_array = np.array(marker_xyz_array)

        # 点群を生成
        pc = rs.pointcloud()
        pc.map_to(color_frame)
        points = pc.calculate(depth_frame)
        vtx = np.asanyarray(points.get_vertices()).view(np.float32).reshape(-1, 3)
        pcd.points = o3d.utility.Vector3dVector(vtx)

        # 平面検出（机）
        plane_model, inliers = pcd.segment_plane(distance_threshold=0.01, ransac_n=3, num_iterations=1000)
        if plane_model is None or len(plane_model) != 4:
            print("[ERROR] 平面検出に失敗しました。再試行...")
            continue

        a, b, c, d = plane_model
        normal = np.array([a, b, c])

        # 回転補正
        R = align_point_cloud_to_table(pcd, normal)
        marker_xyz_array_rotated = np.dot(marker_xyz_array, R.T)

        print("[INFO] マーカー座標取得＆回転補正完了")
        return marker_xyz_array_rotated


class LivePointCloudVisualizer:
    def __init__(self):
        self.vis = o3d.visualization.Visualizer()
        self.vis.create_window(window_name="Live PointCloud", width=960, height=540)
        self.added = False

    def update(self, filtered_cloud, marker_xyz_array,
               marker_x_min=None, marker_x_max=None, 
               marker_y_min=None, marker_y_max=None):
        geometries = []

        # 点群（緑）
        filtered_cloud.paint_uniform_color([0.1, 0.7, 0.1])
        geometries.append(filtered_cloud)

        # バウンディングボックス（青）
        if None not in [marker_x_min, marker_x_max, marker_y_min, marker_y_max]:
            marker_min = np.array([marker_x_min, marker_y_min, np.min(marker_xyz_array[:, 2])])
            marker_max = np.array([marker_x_max, marker_y_max, np.max(marker_xyz_array[:, 2])])
        else:
            # fallback: マーカー全体のAABBで表示
            marker_min = marker_xyz_array.min(axis=0)
            marker_max = marker_xyz_array.max(axis=0)

        aabb = o3d.geometry.AxisAlignedBoundingBox(marker_min, marker_max)
        aabb.color = (0, 0, 1)
        geometries.append(aabb)

        # 表示更新
        if not self.added:
            for g in geometries:
                self.vis.add_geometry(g)
            self.added = True
        else:
            self.vis.clear_geometries()
            for g in geometries:
                self.vis.add_geometry(g)

        self.vis.poll_events()
        self.vis.update_renderer()

    def close(self):
        self.vis.destroy_window()


try:
    visualizer = LivePointCloudVisualizer()
    # === カメラフレーム取得 === 
    frames = pipeline.wait_for_frames()
    depth_frame = frames.get_depth_frame()
    color_frame = frames.get_color_frame()
    color_image = np.asanyarray(color_frame.get_data())
    intrinsics = depth_frame.profile.as_video_stream_profile().intrinsics
    
    # 一度だけマーカー検出して範囲取得
    marker_xyz_array_rotated = detect_marker_bounds(pipeline, aruco_dict, parameters, intrinsics)
    plane_model, inliers = pcd.segment_plane(distance_threshold=0.01, ransac_n=3, num_iterations=1000)
    for i, coord in enumerate(marker_xyz_array_rotated):
                x, y, z = coord
                print(f"  マーカー {i + 1}: [{x:.3f}, {y:.3f}, {z:.3f}]")
    marker_bounds_x_min = np.min(marker_xyz_array_rotated[:, 0])
    marker_bounds_x_max = np.max(marker_xyz_array_rotated[:, 0])
    marker_bounds_y_min = np.min(marker_xyz_array_rotated[:, 1])
    marker_bounds_y_max = np.max(marker_xyz_array_rotated[:, 1])
    
    while True:
        frames = pipeline.wait_for_frames()
        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()
        color_image = np.asanyarray(color_frame.get_data())
        intrinsics = depth_frame.profile.as_video_stream_profile().intrinsics
        if not depth_frame or not color_frame:
            continue

        cv2.imshow('RealSense', color_image)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        # === 点群処理（5秒ごと）=== 
        current_time = time.time()
        if current_time - last_update_time >= 5:
            print("=================================================================")
            pc.map_to(color_frame)
            points = pc.calculate(depth_frame)
            vtx = np.asanyarray(points.get_vertices()).view(np.float32).reshape(-1, 3)
            print("[DEBUG] vtx shape:", vtx.shape)
            print("[DEBUG] 非ゼロの点数:", np.sum(np.linalg.norm(vtx, axis=1) > 0))
            pcd.points = o3d.utility.Vector3dVector(vtx)

            # === 平面検出（机）=== 
            plane_model, inliers = pcd.segment_plane(distance_threshold=0.01, ransac_n=3, num_iterations=1000)
            if plane_model is None or len(plane_model) != 4:
                print("[ERROR] 平面検出に失敗しました。")
                last_update_time = current_time
                continue

            a, b, c, d = plane_model
            normal = np.array([a, b, c])
            angle_deg = np.degrees(np.arccos(np.clip(np.dot(normal / np.linalg.norm(normal), [0, 0, 1]), -1.0, 1.0)))
            if angle_deg >= 30:
                print("\n[ERROR] 検出された平面が机とみなせません（角度が大きすぎます）")
                last_update_time = current_time
                continue

            # === 点群を机に対して回転補正 ===
            R = align_point_cloud_to_table(pcd, normal)
            
            # === 点群分離 === 
            plane_cloud = pcd.select_by_index(inliers)
            object_cloud = pcd.select_by_index(inliers, invert=True)
            table_z = np.median(np.asarray(plane_cloud.points)[:, 2])
            if len(object_cloud.points) == 0:
                print("[WARN] object_cloud が空です。スキップします。")
                last_update_time = current_time
                continue
            print("[DEBUG] plane_cloud 点数:", len(plane_cloud.points))
            print("[DEBUG] object_cloud 点数:", len(object_cloud.points))
            # print(f"[DEBUG] 基の点群座標: {object_cloud}")

            # === height_threshold以上の高さの物体のみ抽出 === 
            filtered_cloud, high_points, height = get_filtered_objects(
                object_cloud, 
                table_z, 
                marker_bounds_x_min=marker_bounds_x_min, 
                marker_bounds_x_max=marker_bounds_x_max,
                marker_bounds_y_min=marker_bounds_y_min, 
                marker_bounds_y_max=marker_bounds_y_max
            )
            print(f"[DEBUG] 基の点群データ： {plane_cloud}, 処理点群データ： {filtered_cloud}")

            if filtered_cloud is None or len(filtered_cloud.points) == 0:
                print(f"[DEBUG] 高さが{height_threshold*100}cm以上の物体は検出されませんでした。")
                last_update_time = current_time
                continue
            else:

                # === クラスタリングによる物体検知（点群から物体への変換） === 
                with o3d.utility.VerbosityContextManager(o3d.utility.VerbosityLevel.Error):
                    labels = np.array(filtered_cloud.cluster_dbscan(eps=0.02, min_points=10, print_progress=False))
                    max_label = labels.max()
                    print(f"[DEBUG] 検出された物体数: {max_label + 1}")
                    
                    # === 物体の座標データ格納 === 
                    object_positions_2d = []
                    for i in range(max_label + 1):
                        cluster_indices = np.where(labels == i)[0]
                        cluster_points = np.asarray(filtered_cloud.points)[cluster_indices]
                        cluster_center = cluster_points.mean(axis=0)
                        x, y = cluster_center[0], cluster_center[1]

                        # === 正規化の処理 ===
                        x_norm, y_norm = normalize_coordinates(
                            x, y,
                            marker_bounds_x_min, marker_bounds_x_max,
                            marker_bounds_y_min, marker_bounds_y_max
                        )
                        print(f"[INFO] 物体 {i + 1}: 正規化座標 x={x_norm:.3f}, y={y_norm:.3f}")
                        object_positions_2d.append({
                                "id": i + 1,
                                "x": float(cluster_center[0]),
                                "y": float(cluster_center[1])
                            })
                    
                    
                    # === JSON形式でバックエンドに出力 === 
                    send_object_positions(object_positions_2d)
                    
                    # === 点群画像の表示 === 
                    if filtered_cloud is not None:
                        visualizer.update(
                            filtered_cloud, marker_xyz_array_rotated,
                            marker_x_min=marker_bounds_x_min, 
                            marker_x_max=marker_bounds_x_max, 
                            marker_y_min=marker_bounds_y_min, 
                            marker_y_max=marker_bounds_y_max
                        )
                    
                    # === 物体2D座標のプロット === 
                    # plot_object_positions(object_positions_2d, xlim=(-0.3, 0.3), ylim=(-0.2, 0.4))

                        
                    # === 物体の識別を可視化する === 
                    # colors = plt.get_cmap("tab20")(labels / (max_label if max_label > 0 else 1))
                    # colors[labels < 0] = 0
                    # filtered_cloud.colors = o3d.utility.Vector3dVector(colors[:, :3])
                    # o3d.visualization.draw_geometries([filtered_cloud])
            
                # === XY投影 === 
                cv2.waitKey(1)


            last_update_time = current_time

finally:
    pipeline.stop()
    cv2.destroyAllWindows()
