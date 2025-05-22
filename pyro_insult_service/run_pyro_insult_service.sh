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

# 1. Start Pyro4 Name Server (if not already running in a dedicated terminal)
# It's best to run this manually in its own terminal and keep it running.
# This script will try to start one if it can, but it might conflict.
echo "Checking/Starting Pyro4 Name Server (port 9090)..."
# Check if port 9090 is in use
if ! ss -tuln | grep -q ':9090 '; then
    gnome-terminal --title="Pyro4 NameServer" --working-directory="$PROJECT_ROOT" -- bash -c "source $VENV_PATH && python -m Pyro4.naming; exec bash" &
    echo "Name Server started. Waiting for it to initialize..."
    sleep 5
else
    echo "Name Server (or something on port 9090) appears to be already running."
fi

# 2. Start the InsultServer (Pyro4)
echo "Starting InsultServer (Pyro4)..."
gnome-terminal --title="Pyro4 InsultServer" --working-directory="$SERVICE_DIR" -- bash -c "$ACTIVATE_CMD python insult_server_pyro.py; exec bash" &
sleep 3 # Give server time to register with Name Server

# 3. Start Subscriber 1
echo "Starting Subscriber 1 (Pyro4)..."
gnome-terminal --title="Pyro4 Subscriber1" --working-directory="$SERVICE_DIR" -- bash -c "$ACTIVATE_CMD python insult_subscriber_pyro.py; exec bash" &
sleep 2

# 4. Start Subscriber 2
echo "Starting Subscriber 2 (Pyro4)..."
gnome-terminal --title="Pyro4 Subscriber2" --working-directory="$SERVICE_DIR" -- bash -c "$ACTIVATE_CMD python insult_subscriber_pyro.py; exec bash" &
sleep 2 # Pyro subscribers find their own ports for their daemons

# 5. Run the InsultClient
echo "Running InsultClient (Pyro4)..."
gnome-terminal --title="Pyro4 InsultClient" --working-directory="$SERVICE_DIR" -- bash -c "$ACTIVATE_CMD python insult_client_pyro.py; echo 'Client finished. Press Enter to close.'; read; exec bash"

echo "Demonstration initiated. Please observe the terminals."
