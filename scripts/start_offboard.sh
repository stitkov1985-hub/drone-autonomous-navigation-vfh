#!/bin/bash
# Wait for MAVROS FCU connection, then start OFFBOARD circle flight.
set -e
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

echo "Waiting for /mavros/state..."
until rostopic list 2>/dev/null | grep -q '/mavros/state'; do
    sleep 1
done

echo "Waiting for FCU connected=True..."
until rostopic echo -n 1 /mavros/state 2>/dev/null | grep -q "connected: True"; do
    sleep 1
done

echo "Starting circle flight (takeoff + waypoints)..."
python3 "$SCRIPT_DIR/../src/circle_flight.py"
