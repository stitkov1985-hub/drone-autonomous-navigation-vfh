#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )


function check_package_installed() {
    if dpkg-query -W -f='${Status}' "$1" 2>/dev/null | grep -q "ok installed"; then
        echo "$1 is installed."
        return 1 # package is installed, return true
    else
        echo "$1 is not installed."
        return 0 # package is not installed, return false
    fi
}

declare -A ros_version=( ["focal"]="noetic" ["bionic"]="melodic" ["xenial"]="kinetic")

if check_package_installed ros-${ros_version[$(lsb_release -sc)]}-mavros; then
    sudo apt install -y ros-${ros_version[$(lsb_release -sc)]}-mavros
fi

# GeographicLib datasets are required by MAVROS even if mavros was already installed.
if [ ! -r /usr/share/GeographicLib/geoids/egm96-5.pgm ]; then
    wget -O /tmp/install_geographiclib_datasets.sh \
        https://raw.githubusercontent.com/mavlink/mavros/master/mavros/scripts/install_geographiclib_datasets.sh
    sudo bash /tmp/install_geographiclib_datasets.sh
    rm -f /tmp/install_geographiclib_datasets.sh
fi

if check_package_installed ros-${ros_version[$(lsb_release -sc)]}-mavros-extras; then
    sudo apt install ros-${ros_version[$(lsb_release -sc)]}-mavros-extras -y
fi

if check_package_installed ros-${ros_version[$(lsb_release -sc)]}-mavros-extras; then
    sudo apt install ros-${ros_version[$(lsb_release -sc)]}-mavros-extras -y
fi

if check_package_installed ros-${ros_version[$(lsb_release -sc)]}-cv-bridge; then
    sudo apt install ros-${ros_version[$(lsb_release -sc)]}-cv-bridge -y
fi

if check_package_installed ros-${ros_version[$(lsb_release -sc)]}-image-transport; then
    sudo apt install ros-${ros_version[$(lsb_release -sc)]}-image-transport -y
fi
#     ## link opencv (check for your system)
#     sudo ln -s /usr/include/opencv4/opencv2/ /usr/include/opencv
