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

# 1. Start the Insult Broadcaster
echo "Starting Insult Broadcaster (Redis)..."
gnome-terminal --title="Redis InsultBroadcaster" --working-directory="$SERVICE_DIR" -- bash -c "$ACTIVATE_CMD python insult_broadcaster_redis.py; exec bash" &
sleep 2

# 2. Start Subscriber 1
echo "Starting Subscriber 1 (Redis)..."
gnome-terminal --title="Redis Subscriber1" --working-directory="$SERVICE_DIR" -- bash -c "$ACTIVATE_CMD python insult_subscriber_redis.py; exec bash" &
sleep 1

# 3. Start Subscriber 2
echo "Starting Subscriber 2 (Redis)..."
gnome-terminal --title="Redis Subscriber2" --working-directory="$SERVICE_DIR" -- bash -c "$ACTIVATE_CMD python insult_subscriber_redis.py; exec bash" &
sleep 2

# 4. Run the Insult Adder (to add some insults)
echo "Running Insult Adder (Redis)..."
gnome-terminal --title="Redis InsultAdder" --working-directory="$SERVICE_DIR" -- bash -c "$ACTIVATE_CMD python insult_adder_redis.py; echo 'Adder finished. Press Enter to close.'; read; exec bash" &
# Wait for adder to finish and insults to be potentially broadcasted
sleep 3 

# 5. Run the Insult Getter (to view insults)
echo "Running Insult Getter (Redis)..."
gnome-terminal --title="Redis InsultGetter" --working-directory="$SERVICE_DIR" -- bash -c "$ACTIVATE_CMD python insult_getter_redis.py; echo 'Getter finished. Press Enter to close.'; read; exec bash"

echo "Demonstration initiated. Please observe the terminals."
