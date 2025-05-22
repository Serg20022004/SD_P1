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


# 1. Start the FilterResultsCollector (to see results)
echo "Starting FilterResultsCollector (RabbitMQ)..."
gnome-terminal --title="RabbitMQ ResultsCollector" --working-directory="$SERVICE_DIR" -- bash -c "$ACTIVATE_CMD python filter_results_collector_rabbit.py; exec bash" &
sleep 2

# 2. Start Filter Worker 1
echo "Starting Filter Worker 1 (RabbitMQ)..."
gnome-terminal --title="RabbitMQ FilterWorker1" --working-directory="$SERVICE_DIR" -- bash -c "$ACTIVATE_CMD python filter_worker_rabbit.py; exec bash" &
sleep 2 # Give worker time to connect and declare queues

# 3. Start Filter Worker 2
echo "Starting Filter Worker 2 (RabbitMQ)..."
gnome-terminal --title="RabbitMQ FilterWorker2" --working-directory="$SERVICE_DIR" -- bash -c "$ACTIVATE_CMD python filter_worker_rabbit.py; exec bash" &
sleep 2

# 4. Run the FilterProducer (to send tasks)
echo "Running FilterProducer (RabbitMQ)..."
gnome-terminal --title="RabbitMQ FilterProducer" --working-directory="$SERVICE_DIR" -- bash -c "$ACTIVATE_CMD python filter_producer_rabbit.py; echo 'Producer finished. Press Enter to close.'; read; exec bash"

echo "Demonstration initiated. Please observe the terminals."
