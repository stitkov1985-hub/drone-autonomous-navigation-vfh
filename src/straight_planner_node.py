#!/usr/bin/env python3
import math
import rospy
from geometry_msgs.msg import PoseStamped
from mavros_msgs.msg import State, ParamValue
from mavros_msgs.srv import CommandBool, SetMode, ParamSet

def angle_wrap(angle):
    return (angle + math.pi) % (2.0 * math.pi) - math.pi

class StraightPointsPlanner:
    def __init__(self):
        rospy.init_node("straight_planner_node", anonymous=True)

        self.current_state = State()
        self.local_pose = None
        self.rate = rospy.Rate(20)

        # Подписчики MAVROS
        self.state_sub = rospy.Subscriber("/mavros/state", State, self.state_cb)
        self.pose_sub = rospy.Subscriber("/mavros/local_position/pose", PoseStamped, self.pose_cb)

        # Публикуем во входной топик VFH (вместо прямой отправки в автопилот)
        self.vfh_input_pub = rospy.Publisher("/vfh/input_pose", PoseStamped, queue_size=10)

        # Сервисы управления PX4
        self.arming_client = rospy.ServiceProxy('/mavros/cmd/arming', CommandBool)
        self.set_mode_client = rospy.ServiceProxy('/mavros/set_mode', SetMode)
        self.param_set_client = rospy.ServiceProxy('/mavros/param/set', ParamSet)

        # Маршрут: полет по квадрату вокруг препятствий
        self.waypoints = [[62.0, 0.0]]
        self.current_wp_idx = 0
        
        self.target_altitude = 2.0
        self.takeoff_speed = 0.02
        self.current_yaw = 0.0
        
        self.sub_phase = "FLY"
        self.takeoff_complete = False
        self.current_set_alt = 0.0

    def state_cb(self, msg):
        self.current_state = msg

    def pose_cb(self, msg):
        self.local_pose = msg

    def set_param(self, name, value, is_real=False):
        try:
            val = ParamValue()
            if is_real:
                val.integer = 0
                val.real = float(value)
            else:
                val.integer = int(value)
                val.real = 0.0
            self.param_set_client(param_id=name, value=val)
        except Exception:
            pass

    def disable_failsafes(self):
        # Отключаем обязательный пульт управления и проверки систем для Docker-симуляции
        self.set_param("COM_RC_IN_MODE", 1)
        self.set_param("NAV_DLL_ACT", 0)
        self.set_param("COM_RCL_EXCEPT", 4)
        self.set_param("COM_ARM_WO_GPS", 1)
        self.set_param("CBRK_SUPPLY_CHK", 894281)
        self.set_param("COM_BAT_ACT", 0)
        self.set_param("NAV_RCL_ACT", 0)
        
        # НАСТРОЙКИ ДИНАМИКИ ДЛЯ УСТОЙЧИВОГО ОБЛЕТА ПРЕПЯТСТВИЙ VFH
        self.set_param("MPC_XY_VEL_MAX", 0.35, is_real=True)  # Ограничение предельной скорости БЛА
        self.set_param("MPC_XY_CRUISE", 0.12, is_real=True)   # Крейсерская скорость полета на вейпоинт
        self.set_param("MPC_TILTMAX_AIR", 10.0, is_real=True) # Ограничение угла крена для снижения заносов

    def start(self):
        rospy.loginfo("Ожидание подключения к PX4/MAVROS...")
        while not rospy.is_shutdown() and not self.current_state.connected:
            self.rate.sleep()

        self.disable_failsafes()
        last_req = rospy.Time.now()

        # Инициализационный поток пустых уставок для включения режима OFFBOARD
        for _ in range(100):
            if rospy.is_shutdown(): return
            cmd_p = PoseStamped()
            cmd_p.header.stamp = rospy.Time.now()
            cmd_p.header.frame_id = "map"
            cmd_p.pose.position.z = 0.0
            cmd_p.pose.orientation.w = 1.0
            self.vfh_input_pub.publish(cmd_p)
            self.rate.sleep()

        rospy.loginfo("=== Запуск полетного цикла OFFBOARD ===")
        while not rospy.is_shutdown():
            # Автоматический перевод PX4 в OFFBOARD режим
            if self.current_state.mode != "OFFBOARD":
                if (rospy.Time.now() - last_req) > rospy.Duration(3.0):
                    try:
                        self.set_mode_client(base_mode=0, custom_mode="OFFBOARD")
                    except Exception: pass
                    last_req = rospy.Time.now()
            else:
                # Автоматический запуск моторов (Arming)
                if not self.current_state.armed:
                    if (rospy.Time.now() - last_req) > rospy.Duration(3.0):
                        try:
                            self.arming_client(True)
                        except Exception: pass
                        last_req = rospy.Time.now()

            cmd_p = PoseStamped()
            cmd_p.header.stamp = rospy.Time.now()
            cmd_p.header.frame_id = "map"

            # ФАЗА 1: Вертикальный взлет
            if not self.takeoff_complete:
                if self.current_set_alt < self.target_altitude:
                    self.current_set_alt += self.takeoff_speed
                else:
                    if self.local_pose is not None and self.local_pose.pose.position.z > (self.target_altitude - 0.15):
                        self.takeoff_complete = True
                        rospy.loginfo("Взлет завершен. Переход к полетной траектории.")
                
                if self.local_pose is not None:
                    cmd_p.pose.position.x = self.local_pose.pose.position.x
                    cmd_p.pose.position.y = self.local_pose.pose.position.y
                else:
                    cmd_p.pose.position.x = 0.0
                    cmd_p.pose.position.y = 0.0
                
                cmd_p.pose.position.z = self.current_set_alt
                cmd_p.pose.orientation.w = 1.0

            # ФАЗА 2: Движение по вейпоинтам квадрата
            elif self.takeoff_complete and self.local_pose is not None:
                curr_x = self.local_pose.pose.position.x
                curr_y = self.local_pose.pose.position.y

                wp_x = self.waypoints[self.current_wp_idx][0]
                wp_y = self.waypoints[self.current_wp_idx][1]

                dist_to_wp = math.hypot(wp_x - curr_x, wp_y - curr_y)

                # Расчет угла на следующую целевую точку
                target_yaw = math.atan2(wp_y - curr_y, wp_x - curr_x)

                if self.sub_phase == "FLY":
                    cmd_p.pose.position.x = wp_x
                    cmd_p.pose.position.y = wp_y
                    
                    # ИСПРАВЛЕНО: Принудительно вращаем нос дрона по направлению полета, чтобы лидар всегда смотрел вперед
                    self.current_yaw = target_yaw

                    # Проверка достижения путевой точки с учетом радиуса уклонения VFH
                    if dist_to_wp < 0.4:
                        if self.current_wp_idx < len(self.waypoints) - 1:
                            self.current_wp_idx += 1
                            self.sub_phase = "ROTATING"
                            rospy.loginfo(f"--- Достигнута путевая точка! Смена индекса на: {self.current_wp_idx} ---")
                        else:
                            # Точка последняя — фазу не меняем, индекс не сбрасываем, 
                            # а просто шлем сигнал фиксации в ВФН
                            cmd_p.header.frame_id = "stop"
                            rospy.loginfo_throttle(5.0, "=== Финальная точка достигнута. Сигнал STOP зафиксирован ===")

                        
                elif self.sub_phase == "ROTATING":
                    # Во время вращения удерживаем текущую позицию БЛА
                    cmd_p.pose.position.x = curr_x
                    cmd_p.pose.position.y = curr_y

                    yaw_error = angle_wrap(target_yaw - self.current_yaw)
                    
                    if abs(yaw_error) < 0.15:
                        cmd_p.header.frame_id = "stop"
                        self.sub_phase = "FLY"
                        rospy.loginfo("Разворот на точку завершен. Летим по прямой.")

                    # Плавная угловая интерполяция поворота
                    self.current_yaw += math.copysign(min(abs(yaw_error), 0.04), yaw_error)

                cmd_p.pose.position.z = self.target_altitude
                cmd_p.pose.orientation.z = math.sin(self.current_yaw / 2.0)
                cmd_p.pose.orientation.w = math.cos(self.current_yaw / 2.0)

            # Передаем уставку в ноду планировщика VFH
            self.vfh_input_pub.publish(cmd_p)
            self.rate.sleep()

if __name__ == "__main__":
    try:
        planner = StraightPointsPlanner()
        planner.start()
    except rospy.ROSInterruptException:
        pass