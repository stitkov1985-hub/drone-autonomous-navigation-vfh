#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Set default GPU usage
USE_GPU=0

# Help message
usage() {
  echo "Usage: $0 [-u <use_gpu>] [-c image_name]"
  echo "Options:"
  echo "  -c image_name     Specify the name of docker image."
  echo "  -u <use_gpu>  Set GPU usage (0 - disable, 1 - enable, default: 0)"
  echo "  -h             Display this help message"
  exit 1
}

# Default values
image_name=""


# Process command-line arguments
while getopts "u:c:h" opt; do
  case $opt in
    u)
      USE_GPU=$OPTARG
      ;;
    c)
      image_name=$OPTARG
      ;;
    h)
      usage
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      usage
      ;;
  esac
done

# Set runtime and GPU flags based on the USE_GPU variable
if [[ $USE_GPU -eq 0 ]]; then
  RUNTIME_FLAG=""
else
  RUNTIME_FLAG="--runtime=nvidia --gpus all"
fi

# Container run
CONTAINER_ID=$(docker run -it --rm -d --privileged \
    --network=host  \
    --name px4_simulation \
    --user=$(id -u $USER):$(id -g $USER) \
    --env="DISPLAY" \
    --env="LIBGL_ALWAYS_SOFTWARE=0" \
    --volume="/tmp/.X11-unix:/tmp/.X11-unix:rw" \
    --volume="$SCRIPT_DIR/..":/app \
    $RUNTIME_FLAG \
    $image_name )

# Run gazebo
docker exec -it $CONTAINER_ID /bin/bash -c "source /opt/ros/noetic/setup.bash && \
                                            source /PX4-Autopilot/Tools/setup_gazebo.bash \
                                            /PX4-Autopilot /PX4-Autopilot/build/px4_sitl_default && \
                                            export ROS_PACKAGE_PATH=/opt/ros/noetic/share:/PX4-Autopilot:/PX4-Autopilot/Tools/sitl_gazebo && \
                                            export GAZEBO_MODEL_PATH=/app/sim/models:/PX4-Autopilot/Tools/sitl_gazebo/models
                                            /app/scripts/start_sim.sh"

echo "STOP DOCKER CONTAINER!"
docker stop $CONTAINER_ID
