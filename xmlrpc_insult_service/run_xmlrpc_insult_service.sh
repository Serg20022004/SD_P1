#!/bin/bash

# Script to demonstrate running the XMLRPC InsultService

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_ROOT=$(realpath "$SCRIPT_DIR/../")
VENV_PATH="$PROJECT_ROOT/SD-env/bin/activate"
SERVICE_DIR="$SCRIPT_DIR" # Python scripts are in the same dir as this shell script

echo "Script Directory: $SCRIPT_DIR"
echo "Project Root: $PROJECT_ROOT"
echo "Virtual Env: $VENV_PATH"
echo "Service Dir (for Python scripts): $SERVICE_DIR"


echo "Starting XMLRPC InsultService demonstration..."
echo "Make sure no other instances are running on ports 8000, 9001, 9002..."

# Command to activate venv and run python script. Python scripts are in SERVICE_DIR.
ACTIVATE_CMD="source $VENV_PATH && cd $SERVICE_DIR &&" # cd to SERVICE_DIR before python

# 1. Start the InsultServer
echo "Starting InsultServer (XMLRPC)..."
gnome-terminal --title="XMLRPC InsultServer" --working-directory="$SERVICE_DIR" -- bash -c "$ACTIVATE_CMD python insult_server_xmlrpc.py; exec bash" &
sleep 3

# 2. Start Subscriber 1
echo "Starting Subscriber 1 (XMLRPC on port 9001)..."
gnome-terminal --title="XMLRPC Subscriber1 (9001)" --working-directory="$SERVICE_DIR" -- bash -c "$ACTIVATE_CMD python insult_subscriber_xmlrpc.py; exec bash" &
sleep 2

# 3. Start Subscriber 2 (Temporary script modification for different port)
TEMP_SUB2_SCRIPT_NAME="temp_subscriber_9002.py"
TEMP_SUB2_SCRIPT_PATH="$SERVICE_DIR/$TEMP_SUB2_SCRIPT_NAME" # Full path for cp/sed/rm
cp "$SERVICE_DIR/insult_subscriber_xmlrpc.py" "$TEMP_SUB2_SCRIPT_PATH"
# Adjust sed to use the full path to avoid issues if pwd changes
sed -i 's/subscriber_port = 9001/subscriber_port = 9002/g' "$TEMP_SUB2_SCRIPT_PATH"
sed -i 's/Subscriber XMLRPC Server listening on localhost:9001/Subscriber XMLRPC Server listening on localhost:9002/g' "$TEMP_SUB2_SCRIPT_PATH"
sed -i 's/my_subscriber_url = f"http:\/\/{subscriber_host}:9001\/RPC2"/my_subscriber_url = f"http:\/\/{subscriber_host}:9002\/RPC2"/g' "$TEMP_SUB2_SCRIPT_PATH"

echo "Starting Subscriber 2 (XMLRPC on port 9002)..."
gnome-terminal --title="XMLRPC Subscriber2 (9002)" --working-directory="$SERVICE_DIR" -- bash -c "$ACTIVATE_CMD python $TEMP_SUB2_SCRIPT_NAME; exec bash" &
sleep 2

# 4. Run the InsultClient
echo "Running InsultClient (XMLRPC)..."
gnome-terminal --title="XMLRPC InsultClient" --working-directory="$SERVICE_DIR" -- bash -c "$ACTIVATE_CMD python insult_client_xmlrpc.py; echo 'Client finished. Press Enter to close.'; read; exec bash"

echo "Demonstration initiated. Please observe the terminals."
echo "To clean up, close all opened 'gnome-terminal' windows or use Ctrl+C in them."
echo "Cleaning up temporary subscriber script..."
rm -f "$TEMP_SUB2_SCRIPT_PATH"
