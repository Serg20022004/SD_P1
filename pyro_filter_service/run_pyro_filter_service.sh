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

# 1. Start Pyro4 Name Server (if not already running)
echo "Checking/Starting Pyro4 Name Server (port 9090)..."
if ! ss -tuln | grep -q ':9090 '; then
    gnome-terminal --title="Pyro4 NameServer" --working-directory="$PROJECT_ROOT" -- bash -c "source $VENV_PATH && python -m Pyro4.naming; exec bash" &
    echo "Name Server started. Waiting for it to initialize..."
    sleep 5
else
    echo "Name Server (or something on port 9090) appears to be already running."
fi

# 2. Start the FilterDispatcher Server
echo "Starting FilterDispatcher Server (Pyro4)..."
gnome-terminal --title="Pyro4 FilterDispatcher" --working-directory="$SERVICE_DIR" -- bash -c "$ACTIVATE_CMD python filter_dispatcher_pyro.py; exec bash" &
sleep 3 # Give dispatcher time to register

# 3. Start Filter Worker 1
echo "Starting Filter Worker 1 (Pyro4)..."
gnome-terminal --title="Pyro4 FilterWorker1" --working-directory="$SERVICE_DIR" -- bash -c "$ACTIVATE_CMD python filter_worker_pyro.py; exec bash" &
sleep 2 # Give worker time to register

# 4. Start Filter Worker 2
echo "Starting Filter Worker 2 (Pyro4)..."
gnome-terminal --title="Pyro4 FilterWorker2" --working-directory="$SERVICE_DIR" -- bash -c "$ACTIVATE_CMD python filter_worker_pyro.py; exec bash" &
sleep 2

# 5. Run the FilterClient
echo "Running FilterClient (Pyro4)..."
gnome-terminal --title="Pyro4 FilterClient" --working-directory="$SERVICE_DIR" -- bash -c "$ACTIVATE_CMD python filter_client_pyro.py; echo 'Client finished. Press Enter to close.'; read; exec bash"

echo "Demonstration initiated. Please observe the terminals."
