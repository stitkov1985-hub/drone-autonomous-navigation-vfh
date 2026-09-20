#!/bin/bash

# Определение рабочей директории скрипта
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE}" )" &> /dev/null && pwd )
echo $ROS_MASTER_URI
MODEL="uav_vision"

# Запуск MAVROS в отдельном внешнем терминале Xterm (исправили имя скрипта)
xterm -e "$SCRIPT_DIR/start_mavros.sh ; exec /bin/bash" &

# Отключаем онлайн-базу моделей внутри самого контейнера, чтобы не висло
export GAZEBO_MODEL_DATABASE_URI=""

# ПРИНУДИТЕЛЬНОЕ ОТКЛЮЧЕНИЕ БЛОКИРОВОК БАТАРЕИ И ПУЛЬТА В АВТОПИЛОТЕ PX4
export PX4_SIM_PARAMS="BAT_CRIT_THR=0.00,BAT_LOW_THR=0.00,COM_BAT_ACT=0,COM_RCL_EXCEPT=4"

# Запуск основного симулятора ROS/Gazebo с оригинальным миром
roslaunch $SCRIPT_DIR/../launch/uav_simulator.launch \
    sdf:=$SCRIPT_DIR/../sim/models/$MODEL/$MODEL.sdf \
    world:=$SCRIPT_DIR/../sim/worlds/aruco_world.world \

