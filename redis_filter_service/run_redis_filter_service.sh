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


# 1. Start Filter Worker 1
echo "Starting Filter Worker 1 (Redis)..."
gnome-terminal --title="Redis FilterWorker1" --working-directory="$SERVICE_DIR" -- bash -c "$ACTIVATE_CMD python filter_worker_redis.py; exec bash" &
sleep 1

# 2. Start Filter Worker 2
echo "Starting Filter Worker 2 (Redis)..."
gnome-terminal --title="Redis FilterWorker2" --working-directory="$SERVICE_DIR" -- bash -c "$ACTIVATE_CMD python filter_worker_redis.py; exec bash" &
sleep 2 # Give workers time to connect

# 3. Run the FilterProducer (to send tasks)
echo "Running FilterProducer (Redis)..."
gnome-terminal --title="Redis FilterProducer" --working-directory="$SERVICE_DIR" -- bash -c "$ACTIVATE_CMD python filter_producer_redis.py; echo 'Producer finished. Press Enter to close.'; read; exec bash" &
sleep 3 # Allow tasks to be processed

# 4. Run the FilterResultsRetriever
echo "Running FilterResultsRetriever (Redis)..."
gnome-terminal --title="Redis ResultsRetriever" --working-directory="$SERVICE_DIR" -- bash -c "$ACTIVATE_CMD python filter_results_retriever_redis.py; echo 'Retriever finished. Press Enter to close.'; read; exec bash"

echo "Demonstration initiated. Please observe the terminals."
