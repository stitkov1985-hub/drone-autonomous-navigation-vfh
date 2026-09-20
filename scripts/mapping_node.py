#!/usr/bin/env python3
import rospy
import numpy as np
import math
import os
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import PoseStamped
from visualization_msgs.msg import Marker
from geometry_msgs.msg import Point

class DroneMapper:
    def __init__(self):
        rospy.init_node('drone_mapping_node', anonymous=True)

        self.grid_step = 0.5 
        self.map_file_path = "/app/src/voxel_map_database.txt"
        
        # Хранилище карты препятствий (только то, что нашел лидар)
        self.global_map = set()
        
        # Хранилище пройденного маршрута дрона
        self.drone_path = set()

        # Параметры фильтрации ROR от WorkAI
        self.hit_counter = {}
        self.neighbor_radius = 1.0
        self.min_neighbors = 3
        self.min_hits_to_confirm = 3

        # Координаты и ориентация БЛА
        self.drone_x = 0.0; self.drone_y = 0.0; self.drone_z = 0.0
        self.qx = 0.0; self.qy = 0.0; self.qz = 0.0; self.qw = 1.0
        self.has_pose = False

        self.load_map_from_file()

        rospy.Subscriber('/mavros/vision_pose/pose', PoseStamped, self.pose_callback)
        rospy.Subscriber('/mavros/local_position/pose', PoseStamped, self.pose_callback)
        rospy.Subscriber('/laser/scan', LaserScan, self.laser_callback)
        
        # Два разных издателя для RViz
        self.marker_pub = rospy.Publisher('/visualization_marker', Marker, queue_size=10)
        self.path_pub = rospy.Publisher('/drone_path_marker', Marker, queue_size=10)
        
        rospy.loginfo("Узел картографии запущен. Препятствия и трек разделены.")

    def pose_callback(self, msg):
        self.drone_x = msg.pose.position.x
        self.drone_y = msg.pose.position.y
        self.drone_z = msg.pose.position.z
        self.qx = msg.pose.orientation.x
        self.qy = msg.pose.orientation.y
        self.qz = msg.pose.orientation.z
        self.qw = msg.pose.orientation.w
        self.has_pose = True
        
        # Записываем позицию дрона отдельно в маршрут (округляем для плавности)
        vx = round(self.drone_x / 0.2) * 0.2
        vy = round(self.drone_y / 0.2) * 0.2
        vz = round(self.drone_z / 0.2) * 0.2
        self.drone_path.add((vx, vy, vz))
        self.publish_path_rviz()

    def get_rotation_matrix(self):
        r00 = 1 - 2 * (self.qy**2 + self.qz**2)
        r01 = 2 * (self.qx * self.qy - self.qz * self.qw)
        r02 = 2 * (self.qx * self.qz + self.qy * self.qw)
        r10 = 2 * (self.qx * self.qy + self.qz * self.qw)
        r11 = 1 - 2 * (self.qx**2 + self.qz**2)
        r12 = 2 * (self.qy * self.qz - self.qx * self.qw)
        r20 = 2 * (self.qx * self.qz - self.qy * self.qw)
        r21 = 2 * (self.qy * self.qz + self.qx * self.qw)
        r22 = 1 - 2 * (self.qx**2 + self.qy**2)
        return np.array([[r00, r01, r02], [r10, r11, r12], [r20, r21, r22]])

    def laser_callback(self, msg):
        if not self.has_pose:
            return

        R = self.get_rotation_matrix()
        map_updated = False

        floor_z = 0.5
        max_range = 3.0
        candidate_points = []

        for i, r in enumerate(msg.ranges):
            if r < msg.range_min or r > max_range or math.isnan(r) or math.isinf(r):
                continue

            angle = msg.angle_min + i * msg.angle_increment
            point_sensor = np.array([r * math.cos(angle), r * math.sin(angle), 0.0])
            point_map = R.dot(point_sensor) + np.array([self.drone_x, self.drone_y, self.drone_z])
            
            if point_map[2] < floor_z:
                continue

            candidate_points.append(point_map)

        if not candidate_points:
            return

        candidate_points = np.array(candidate_points)
        filtered_points = []
        radius_sq = self.neighbor_radius * self.neighbor_radius

        for p in candidate_points:
            diff = candidate_points - p
            dist_sq = np.sum(diff * diff, axis=1)
            neighbor_count = int(np.sum((dist_sq > 0.0) & (dist_sq <= radius_sq)))

            if neighbor_count >= self.min_neighbors:
                filtered_points.append(p)

        if not filtered_points:
            return

        for point_map in filtered_points:
            vx = round(point_map[0] / self.grid_step) * self.grid_step
            vy = round(point_map[1] / self.grid_step) * self.grid_step
            vz = round(point_map[2] / self.grid_step) * self.grid_step

            voxel = (vx, vy, vz)
            self.hit_counter[voxel] = self.hit_counter.get(voxel, 0) + 1

            if self.hit_counter[voxel] >= self.min_hits_to_confirm:
                if voxel not in self.global_map:
                    self.global_map.add(voxel)
                    map_updated = True

        if map_updated and len(self.global_map) > 0:
            self.publish_voxels_rviz()

    def publish_voxels_rviz(self):
        # ТОЛЬКО ПРЕПЯТСТВИЯ: Зеленые кубы
        marker = Marker()
        marker.header.frame_id = "map"
        marker.header.stamp = rospy.Time.now()
        marker.ns = "drone_voxels"
        marker.id = 0
        marker.type = Marker.CUBE_LIST
        marker.action = Marker.ADD
        marker.scale.x = marker.scale.y = marker.scale.z = self.grid_step
        marker.color.r = 0.0; marker.color.g = 1.0; marker.color.b = 0.0; marker.color.a = 0.8

        for voxel in self.global_map:
            p = Point()
            p.x = voxel[0]; p.y = voxel[1]; p.z = voxel[2]
            marker.points.append(p)
        self.marker_pub.publish(marker)

    def publish_path_rviz(self):
        # ТОЛЬКО МАРШРУТ ПОЛЕТА: Красные сферы
        marker = Marker()
        marker.header.frame_id = "map"
        marker.header.stamp = rospy.Time.now()
        marker.ns = "drone_path"
        marker.id = 1
        marker.type = Marker.SPHERE_LIST
        marker.action = Marker.ADD
        # Маленький диаметр сфер маршрута (15 сантиметров), чтобы не мешать карте
        marker.scale.x = marker.scale.y = marker.scale.z = 0.15
        marker.color.r = 1.0; marker.color.g = 0.0; marker.color.b = 0.0; marker.color.a = 0.9

        for pt in self.drone_path:
            p = Point()
            p.x = pt[0]; p.y = pt[1]; p.z = pt[2]
            marker.points.append(p)
        self.path_pub.publish(marker)

    def save_map_to_file(self):
        try:
            os.makedirs(os.path.dirname(self.map_file_path), exist_ok=True)
            with open(self.map_file_path, 'w') as f:
                for voxel in self.global_map:
                    f.write(f"{voxel[0]} {voxel[1]} {voxel[2]}\n")
            rospy.loginfo(f"Карта успешно сериализована в файл: {self.map_file_path}")
        except Exception as e:
            rospy.logerr(f"Ошибка сохранения карты в файл: {e}")

    def load_map_from_file(self):
        if not os.path.exists(self.map_file_path):
            return
        try:
            with open(self.map_file_path, 'r') as f:
                for line in f:
                    coords = line.strip().split()
                    if len(coords) == 3:
                        self.global_map.add((float(coords[0]), float(coords[1]), float(coords[2])))
            rospy.loginfo(f"Карта успешно загружена. Найдено {len(self.global_map)} вокселей.")
        except Exception as e:
            rospy.logerr(f"Ошибка при чтении файла карты: {e}")

if __name__ == '__main__':
    mapper = DroneMapper()
    try:
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
    finally:
        mapper.save_map_to_file()
