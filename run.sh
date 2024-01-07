#!/bin/bash

# Check for root privileges
if [ "$(id -u)" != "0" ]; then
    echo "Warning: Some operations (like checking service status) require root privileges."
    echo "You are not running as root. Continuing without those operations."
fi

# Use the current directory as default if no argument is provided
DIR=${1:-.}

# Check if the directory exists
if [ ! -d "$DIR" ]; then
    echo "Directory does not exist"
    exit 1
fi

# Check if main.py file exists in the directory
if [ ! -f "$DIR/main.py" ]; then
    echo "main.py does not exist in the directory"
    exit 1
fi

# Check if the venv directory exists
if [ ! -d "$DIR/venv" ]; then
    echo "venv does not exist in the directory"
    exit 1
fi

# Full path to the directory
DIR_PATH=$(realpath $DIR)

# Get the directory name without the path for the service name
DIR_NAME=$(basename $DIR_PATH)

# Check and display service status/logs if running as root
if [ "$(id -u)" -eq 0 ]; then
    if systemctl is-active --quiet "$DIR_NAME.service"; then
        echo "Service '$DIR_NAME.service' is running. Displaying logs:"
        journalctl -u "$DIR_NAME.service" -n 100
    else
        echo "Service '$DIR_NAME.service' is not running. Starting..."
        systemctl start "$DIR_NAME.service"&
        echo "Started"
        systemctl status "$DIR_NAME.service" | cat &


    fi

else
  # Execute the Python script
  echo "Running the Python script in $DIR_PATH/main.py"
  $DIR_PATH/venv/bin/python3 $DIR_PATH/main.py

fi