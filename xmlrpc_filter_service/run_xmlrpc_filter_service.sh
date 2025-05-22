#!/bin/bash

# Get the directory where this script itself is located
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Assume the project root is one level above the SCRIPT_DIR
PROJECT_ROOT=$(realpath "$SCRIPT_DIR/../") 

VENV_PATH="$PROJECT_ROOT/SD-env/bin/activate"
# SERVICE_DIR will be the same as SCRIPT_DIR in these specific scripts
# as Python scripts are expected to be in the same folder as this shell script.
SERVICE_DIR="$SCRIPT_DIR" 

echo "Script Directory: $SCRIPT_DIR"
echo "Project Root: $PROJECT_ROOT"
echo "Virtual Env: $VENV_PATH"
echo "Service Dir (for Python scripts): $SERVICE_DIR"

# Command to activate venv and then run python script from SERVICE_DIR.
ACTIVATE_CMD="source $VENV_PATH && cd $SERVICE_DIR &&"

# 1. Start the FilterServer
echo "Starting FilterServer (XMLRPC)..."
gnome-terminal --title="XMLRPC FilterServer" --working-directory="$SERVICE_DIR" -- bash -c "$ACTIVATE_CMD python filter_server_xmlrpc.py; exec bash" &
sleep 3 # Give server time to start

# 2. Run the FilterClient
echo "Running FilterClient (XMLRPC)..."
gnome-terminal --title="XMLRPC FilterClient" --working-directory="$SERVICE_DIR" -- bash -c "$ACTIVATE_CMD python filter_client_xmlrpc.py; echo 'Client finished. Press Enter to close.'; read; exec bash"

echo "Demonstration initiated. Please observe the terminals."
