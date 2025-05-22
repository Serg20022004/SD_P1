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

# 1. Start the Insult Processor (Manager & Broadcaster)
echo "Starting Insult Processor (RabbitMQ)..."
gnome-terminal --title="RabbitMQ InsultProcessor" --working-directory="$SERVICE_DIR" -- bash -c "$ACTIVATE_CMD python insult_processor_rabbit.py; exec bash" &
sleep 4 # Give it time to connect and declare queues/exchanges

# 2. Start Subscriber 1
echo "Starting Subscriber 1 (RabbitMQ)..."
gnome-terminal --title="RabbitMQ Subscriber1" --working-directory="$SERVICE_DIR" -- bash -c "$ACTIVATE_CMD python insult_subscriber_rabbit.py; exec bash" &
sleep 2

# 3. Start Subscriber 2
echo "Starting Subscriber 2 (RabbitMQ)..."
gnome-terminal --title="RabbitMQ Subscriber2" --working-directory="$SERVICE_DIR" -- bash -c "$ACTIVATE_CMD python insult_subscriber_rabbit.py; exec bash" &
sleep 2

# 4. Run the Insult Adder Client
echo "Running Insult Adder Client (RabbitMQ)..."
gnome-terminal --title="RabbitMQ InsultAdder" --working-directory="$SERVICE_DIR" -- bash -c "$ACTIVATE_CMD python insult_adder_client_rabbit.py; echo 'Adder finished. Press Enter to close.'; read; exec bash"

echo "Demonstration initiated. Please observe the terminals."
