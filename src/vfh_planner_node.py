#!/usr/bin/env python3
import math
import rospy
import numpy as np
from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import LaserScan

def angle_wrap(angle):
    return (angle + math.pi) % (2.0 * math.pi) - math.pi

class VFH2DOmniPlannerNode:
    def __init__(self):
        rospy.init_node("vfh_planner_node", anonymous=True)

        self.input_pose = None
        self.current_pose = None
        self.scan = None
        self.rate = rospy.Rate(20)

        # Настройки VFH алгоритма
        self.num_sectors = 72          # 72 бина по 5 градусов
        
        # КАРДИНАЛЬНО УСИЛЕННЫЕ НАСТРОЙКИ ДЛЯ МОЩНОГО УХОДА В СТОРОНУ:
        self.block_distance = 2.5      # Замечаем препятствие заранее (за 2.5 метра)
        self.dist_threshold = 3.5      # ДАЕМ БОЛЬШЕ ХОДА: Выносим точку уклонения на 3.5 метра вбок!
        self.target_altitude = 2.0     # Высота полета 2.0 метра

        self.is_avoiding = False

        # Подписчики
        self.input_sub = rospy.Subscriber("/vfh/input_pose", PoseStamped, self.input_cb)
        self.pose_sub = rospy.Subscriber("/mavros/local_position/pose", PoseStamped, self.pose_cb)
        self.scan_sub = rospy.Subscriber("/laser/scan", LaserScan, self.scan_cb)

        # Топик управления
        self.final_pos_pub = rospy.Publisher("/mavros/setpoint_position/local", PoseStamped, queue_size=10)

        rospy.loginfo("=== Узел VFH: Активирован сверхширокий силовой облет препятствий ===")

    def input_cb(self, msg):
        self.input_pose = msg

    def pose_cb(self, msg):
        self.current_pose = msg

    def scan_cb(self, msg):
        self.scan = msg

    def angular_distance(self, angle1, angle2):
        difference = angle2 - angle1
        difference = (difference + math.pi) % (2.0 * math.pi) - math.pi
        return abs(difference)

    def build_global_histogram(self, curr_yaw):
        """ Строит глобальную гистограмму с агрессивным расширением зоны безопасности """
        bins = np.zeros(self.num_sectors, dtype=np.int32)
        if self.scan is None or not self.scan.ranges:
            return bins

        sector_width = (2.0 * math.pi) / self.num_sectors

        # Увеличенный радиус виртуальной "подушки безопасности" дрона (в метрах)
        # Чем он больше, тем шире конус секторов, которые заблокирует препятствие
        robot_radius_with_safety = 0.7  

        for i, dist in enumerate(self.scan.ranges):
            if math.isinf(dist) or math.isnan(dist) or dist < 0.15:
                continue

            local_ang = self.scan.angle_min + i * self.scan.angle_increment
            global_ang = angle_wrap(curr_yaw + local_ang)

            sector = int(math.floor((global_ang + math.pi) / sector_width)) % self.num_sectors

            if dist <= self.block_distance:
                bins[sector] = 1
                
                # Агрессивное динамическое расширение секторов (Sector Blowing)
                alpha = math.asin(min(1.0, robot_radius_with_safety / dist))
                num_sectors_to_blow = int(math.ceil(alpha / sector_width))
                
                # Принудительно закрываем огромный сектор вокруг препятствия, чтобы дрон даже не думал срезать
                for offset in range(-num_sectors_to_blow, num_sectors_to_blow + 1):
                    bins[(sector + offset) % self.num_sectors] = 1

        return bins

    def find_best_global_direction(self, global_target_yaw, bins):
        sector_width = (2.0 * math.pi) / self.num_sectors
        best_sector = -1
        min_cost = float('inf')

        for index in range(self.num_sectors):
            if bins[index] == 0:
                global_sector_angle = (index * sector_width) + (sector_width / 2.0) - math.pi
                current_cost = self.angular_distance(global_target_yaw, global_sector_angle)

                if current_cost < min_cost:
                    min_cost = current_cost
                    best_sector = index

        return best_sector

    def run(self):
        while not rospy.is_shutdown():
            if self.input_pose is None or self.current_pose is None:
                self.rate.sleep()
                continue
            if self.input_pose.header.frame_id == "stop":
                # Передаем жесткую целевую координату финиша вместо плывущей текущей
                output_pose.pose.position.x = target_x
                output_pose.pose.position.y = target_y
                output_pose.pose.position.z = self.target_altitude
                output_pose.pose.orientation = self.current_pose.pose.orientation
                
                self.final_pos_pub.publish(output_pose)
                self.rate.sleep()
                continue


            target_x = self.input_pose.pose.position.x
            target_y = self.input_pose.pose.position.y

            curr_x = self.current_pose.pose.position.x
            curr_y = self.current_pose.pose.position.y

            qx = self.current_pose.pose.orientation.x
            qy = self.current_pose.pose.orientation.y
            qz = self.current_pose.pose.orientation.z
            qw = self.current_pose.pose.orientation.w
            
            siny_cosp = 2.0 * (qw * qz + qx * qy)
            cosy_cosp = 1.0 - 2.0 * (qy * qy + qz * qz)
            curr_yaw = math.atan2(siny_cosp, cosy_cosp)

            global_target_yaw = math.atan2(target_y - curr_y, target_x - curr_x)

            bins = self.build_global_histogram(curr_yaw)
            best_sector_id = self.find_best_global_direction(global_target_yaw, bins)

            output_pose = PoseStamped()
            output_pose.header.stamp = rospy.Time.now()
            output_pose.header.frame_id = self.input_pose.header.frame_id

            any_obstacles_near = np.any(bins == 1)

            # 1. РЕЖИМ СИЛОВОГО ОБХОДА ПРЕПЯТСТВИЯ
            if best_sector_id != -1 and (any_obstacles_near or self.is_avoiding):
                self.is_avoiding = True  
                
                sector_width = (2.0 * math.pi) / self.num_sectors
                chosen_global_angle = (best_sector_id * sector_width) + (sector_width / 2.0) - math.pi

                # Строим уставку с мощным выносом (3.5 метра вбок), выталкивая дрон по широкой траектории
                output_pose.pose.position.x = curr_x + self.dist_threshold * math.cos(chosen_global_angle)
                output_pose.pose.position.y = curr_y + self.dist_threshold * math.sin(chosen_global_angle)
                output_pose.pose.position.z = self.target_altitude
                output_pose.pose.orientation = self.current_pose.pose.orientation

                if not any_obstacles_near:
                    self.is_avoiding = False

                rospy.loginfo_throttle(1.5, "VFH_360: Силовой широкий маневр уклонения в сторону.")
            
            # 2. РЕЖИМ МЕДЛЕННОГО И ПЛАВНОГО ВОЗВРАТА НА ОСНОВНОЙ МАРШРУТ
            else:
                self.is_avoiding = False
                
                dist_to_global_target = math.hypot(target_x - curr_x, target_y - curr_y)
                
                # Маленький шаг вперед (0.25м), чтобы он возвращался ОЧЕНЬ медленно и аккуратно,
                # давая лидару время просканировать пространство на пути возврата
                step_back = 0.25  
                
                if dist_to_global_target > step_back:
                    output_pose.pose.position.x = curr_x + step_back * math.cos(global_target_yaw)
                    output_pose.pose.position.y = curr_y + step_back * math.sin(global_target_yaw)
                else:
                    output_pose.pose.position.x = target_x
                    output_pose.pose.position.y = target_y
                    
                output_pose.pose.position.z = self.target_altitude
                output_pose.pose.orientation = self.input_pose.pose.orientation

            self.final_pos_pub.publish(output_pose)
            self.rate.sleep()

if __name__ == "__main__":
    try:
        node = VFH2DOmniPlannerNode()
        node.run()
    except rospy.ROSInterruptException:
        pass