#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

pkill gz
pkill gzclient
pkill gzserver
pkill gazebo
pkill roslaunch
pkill roscore
pkill -f "xterm -T mavros"
pkill -f "xterm -T gazebo"
pkill -f "xterm -T gz"
$SCRIPT_DIR/kill_px4.sh
docker stop $(docker ps -q -a --filter "ancestor=px4_ros")

