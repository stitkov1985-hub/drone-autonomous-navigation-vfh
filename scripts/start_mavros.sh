#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
echo $ROS_MASTER_URI
MODEL="uav_vision"

GEOID_DST="/usr/share/GeographicLib/geoids/egm96-5.pgm"
GEOID_SRC="$SCRIPT_DIR/../geoids/egm96-5.pgm"
if [ ! -r "$GEOID_DST" ]; then
    echo "GeographicLib geoid missing. Installing egm96-5.pgm..."
    sudo mkdir -p /usr/share/GeographicLib/geoids
    if [ -f "$GEOID_SRC" ]; then
        sudo cp "$GEOID_SRC" "$GEOID_DST"
        sudo chmod 644 "$GEOID_DST"
        echo "Copied geoid from $GEOID_SRC"
    else
        echo "ERROR: $GEOID_SRC not found. Cannot start MAVROS."
        echo "Mount the project at /app or copy geoids/egm96-5.pgm into the container."
        exit 1
    fi
fi

# Wait for the /clock topic to become available
while ! rostopic list | grep -q '/clock'; do
    sleep 1
done

roslaunch $SCRIPT_DIR/../launch/custom_mavros.launch \
            fcu_url:="udp://:14540@localhost:14557" \
            config_file:=$SCRIPT_DIR/../config/mavros_config.yaml \
            pluginlists_file:=$SCRIPT_DIR/../config/mavros_blacklist.yaml 