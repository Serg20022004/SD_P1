# dynamic_scaler_rabbit.py
import pika
import time
import subprocess
import os
import signal
import math

# --- Configuration ---
PYTHON_EXECUTABLE = "/home/milax/Documents/SD/P1/SD-env/bin/python" # VENV PYTHON 
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".")) 
FILTER_WORKER_SCRIPT = os.path.join(PROJECT_ROOT, "rabbitmq_filter_service", "filter_worker_rabbit.py")

RABBITMQ_HOST = 'localhost'
TASK_QUEUE_NAME = 'filter_task_work_queue'

# Scaler Parameters
MIN_WORKERS = 1
MAX_WORKERS = 5 # Max workers to allow (less than the vCPU count to avoid thrashing)
POLL_INTERVAL = 5  # Seconds: How often to check queue and make scaling decisions

# Formula parameters
# T_avg_processing_per_task: Avg time for 1 worker to process 1 task.
# From RabbitMQ N=1 static test: T1_rabbit = 15.25s for TOTAL_REQUESTS = 10000
# So, T_avg_processing_per_task = 15.25 / 10000 = 0.001525 seconds/task
T_AVG_PROCESSING_PER_TASK = 0.001525 # Seconds

# C_worker_capacity: Capacity of a single worker (tasks/second)
# C_worker_capacity = 1 / T_AVG_PROCESSING_PER_TASK if T_AVG_PROCESSING_PER_TASK > 0 else float('inf')
# Example: If T = 0.01s (10ms), C = 100 tasks/sec.
# Let's re-evaluate C based on actual filtering. If filtering is <1ms, C could be 1000+.
# For now, let's use a placeholder value and refine based on your T1 without artificial sleep.
# If T1_rabbit (10000 tasks) = 15s (no artificial sleep), then worker did ~666 RPS. So C ~ 600-700.
C_WORKER_CAPACITY = 600 # Placeholder: tasks per second per worker (ADJUST THIS BASED ON YOUR T1)

# Tr_target_response_time: Target time for a task to be in the queue before processing.
Tr_TARGET_RESPONSE_TIME = 2 # Seconds (e.g., aim for tasks not to wait more than 2s)

# Lambda_arrival_rate: Task arrival rate (tasks/second).
# This is harder to measure dynamically in a simple script.
# For a simpler scaler, we can focus on Backlog (B) primarily or use a fixed estimate for Lambda.
# If producer sends 100 tasks/sec, LAMBDA_ESTIMATED_ARRIVAL_RATE = 100.
# For now, let's make a version that primarily reacts to backlog B,
# but can incorporate Lambda if we can estimate it.
LAMBDA_ESTIMATED_ARRIVAL_RATE = 50 # Placeholder: tasks/second (producer's average rate)

# Thresholds for simpler scaling (if not using full formula)
QUEUE_THRESHOLD_SCALE_UP = 500   # If queue has more than this, consider scaling up
QUEUE_THRESHOLD_SCALE_DOWN = 50 # If queue has less than this for a while, consider scaling down
SCALE_COOLDOWN_PERIOD = 30      # Seconds: Wait this long after a scaling action

active_worker_processes = [] # List to store Popen objects of worker processes
last_scaling_action_time = 0

def get_queue_length(queue_name):
    connection = None
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        channel = connection.channel()
        # Passive declare to get info without modifying queue if it exists
        q_info = channel.queue_declare(queue=queue_name, durable=True, passive=True)
        return q_info.method.message_count
    except Exception as e:
        print(f"Scaler: Error getting queue length for '{queue_name}': {e}")
        return None # Indicate error
    finally:
        if connection and connection.is_open:
            connection.close()

def start_new_worker():
    global active_worker_processes
    if len(active_worker_processes) < MAX_WORKERS:
        print(f"Scaler: Starting a new worker (current: {len(active_worker_processes)}, max: {MAX_WORKERS})...")
        try:
            # Ensure worker output is visible for debugging, or redirect later
            proc = subprocess.Popen([PYTHON_EXECUTABLE, FILTER_WORKER_SCRIPT])
            active_worker_processes.append(proc)
            print(f"Scaler: New worker started (PID: {proc.pid}). Total workers: {len(active_worker_processes)}")
        except Exception as e:
            print(f"Scaler: Failed to start new worker: {e}")
    else:
        print(f"Scaler: Max worker limit ({MAX_WORKERS}) reached. Cannot scale up further.")


def stop_one_worker():
    global active_worker_processes
    if len(active_worker_processes) > MIN_WORKERS:
        try:
            worker_to_stop = active_worker_processes.pop() # Remove last worker from list
            print(f"Scaler: Stopping worker (PID: {worker_to_stop.pid})...")
            worker_to_stop.terminate() # Send SIGTERM, worker should handle for graceful shutdown
            worker_to_stop.wait(timeout=5) # Wait for it
            if worker_to_stop.poll() is None: # If still running
                print(f"Scaler: Worker {worker_to_stop.pid} did not terminate gracefully, killing.")
                worker_to_stop.kill()
            print(f"Scaler: Worker stopped. Total workers: {len(active_worker_processes)}")
        except subprocess.TimeoutExpired:
            print(f"Scaler: Worker {worker_to_stop.pid} did not terminate in time after SIGTERM, attempting kill.")
            if worker_to_stop.poll() is None: worker_to_stop.kill()
        except Exception as e:
            print(f"Scaler: Error stopping worker: {e}")
            # Add it back if stopping failed, or handle more gracefully
            # active_worker_processes.append(worker_to_stop) 
    else:
        print(f"Scaler: Min worker limit ({MIN_WORKERS}) reached. Cannot scale down further.")


def cleanup_terminated_workers():
    """Removes any worker processes that have already terminated."""
    global active_worker_processes
    live_workers = []
    for proc in active_worker_processes:
        if proc.poll() is None: # If still running
            live_workers.append(proc)
        else:
            print(f"Scaler: Worker PID {proc.pid} found terminated (exit code {proc.returncode}). Removing from list.")
    active_worker_processes = live_workers


# --- Main Scaler Loop ---
def scaler_loop():
    global last_scaling_action_time
    print("Dynamic Scaler for RabbitMQ InsultFilter started.")
    print(f"Config: MIN_W={MIN_WORKERS}, MAX_W={MAX_WORKERS}, POLL_I={POLL_INTERVAL}s")
    print(f"Formula params: T_avg={T_AVG_PROCESSING_PER_TASK:.4f}s, C_cap={C_WORKER_CAPACITY:.0f}rps, Tr_target={Tr_TARGET_RESPONSE_TIME}s, Lambda_est={LAMBDA_ESTIMATED_ARRIVAL_RATE}rps")

    # Initial worker setup
    for _ in range(MIN_WORKERS):
        start_new_worker()
    last_scaling_action_time = time.time()


    try:
        while True:
            time.sleep(POLL_INTERVAL)
            cleanup_terminated_workers() # Check for crashed workers

            current_backlog_B = get_queue_length(TASK_QUEUE_NAME)
            if current_backlog_B is None: # Error getting queue length
                print("Scaler: Cannot get queue length, skipping scaling decision.")
                continue
            
            num_current_live_workers = len(active_worker_processes)
            print(f"\nScaler: Poll at {time.strftime('%H:%M:%S')}")
            print(f"  Current Backlog (B): {current_backlog_B} tasks in '{TASK_QUEUE_NAME}'")
            print(f"  Current Active Workers: {num_current_live_workers}")

            # Dynamic scaling formula: N = ceil( (B + (λ * Tr)) / C )
            # For lambda, if we don't measure it dynamically, we use estimated or a simpler logic
            # Simplified: If B is high, N needs to be B/C for immediate processing + some for ongoing lambda
            # N_desired_for_backlog = math.ceil(current_backlog_B / (C_WORKER_CAPACITY * Tr_TARGET_RESPONSE_TIME)) if C_WORKER_CAPACITY > 0 and Tr_TARGET_RESPONSE_TIME > 0 else num_current_live_workers
            
            # Using the formula from P1 spec: N = [B + (λ * Tr)] / C
            # Let's use a fixed estimated lambda for now.
            # A more advanced scaler would try to estimate lambda.
            numerator = current_backlog_B + (LAMBDA_ESTIMATED_ARRIVAL_RATE * Tr_TARGET_RESPONSE_TIME)
            N_desired = MIN_WORKERS # Default to min
            if C_WORKER_CAPACITY > 0:
                N_desired = math.ceil(numerator / C_WORKER_CAPACITY)
            else: # Avoid division by zero if C is 0 (should not happen if T_avg is > 0)
                 if numerator > 0 : N_desired = MAX_WORKERS # If there's work and no capacity, max out

            # Clamp N_desired between MIN_WORKERS and MAX_WORKERS
            N_desired = max(MIN_WORKERS, min(N_desired, MAX_WORKERS))
            print(f"  Formula desired workers (N_desired): {N_desired}")

            # Cooldown logic
            if time.time() - last_scaling_action_time < SCALE_COOLDOWN_PERIOD:
                print(f"  Scaler in cooldown. Waiting for {SCALE_COOLDOWN_PERIOD - (time.time() - last_scaling_action_time):.0f}s more.")
                continue # Skip scaling action if in cooldown

            # Scaling decision
            if N_desired > num_current_live_workers:
                print(f"  Decision: Scale UP from {num_current_live_workers} to {N_desired} workers.")
                for _ in range(N_desired - num_current_live_workers):
                    if len(active_worker_processes) < MAX_WORKERS:
                        start_new_worker()
                    else: break # Reached max
                last_scaling_action_time = time.time()
            elif N_desired < num_current_live_workers:
                print(f"  Decision: Scale DOWN from {num_current_live_workers} to {N_desired} workers.")
                for _ in range(num_current_live_workers - N_desired):
                    if len(active_worker_processes) > MIN_WORKERS:
                        stop_one_worker()
                    else: break # Reached min
                last_scaling_action_time = time.time()
            else:
                print(f"  Decision: Maintain {num_current_live_workers} workers. No scaling action needed.")

    except KeyboardInterrupt:
        print("\nScaler: KeyboardInterrupt received. Shutting down all workers...")
    finally:
        print("Scaler: Final cleanup. Terminating all active workers...")
        # Create a copy for iteration as stop_one_worker modifies the list
        for _ in range(len(active_worker_processes)): 
            if active_worker_processes: # Check if list is not empty
                 stop_one_worker() # This will try to stop MIN_WORKERS eventually
            else: break
        print("Dynamic Scaler stopped.")

if __name__ == "__main__":
    if "SD-env/bin/python" not in PYTHON_EXECUTABLE : # Basic check
        print(f"CRITICAL WARNING: PYTHON_EXECUTABLE ('{PYTHON_EXECUTABLE}') may not be your venv Python.")
        print(f"         Set it to the full path: e.g., '{os.path.join(PROJECT_ROOT, 'SD-env', 'bin', 'python')}'")
        # exit() # Optionally exit if not configured correctly

    # Ensure RabbitMQ queues are declared before starting
    # This is usually handled by workers/producers, but good to do here too.
    try:
        conn_init = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        ch_init = conn_init.channel()
        ch_init.queue_declare(queue=TASK_QUEUE_NAME, durable=True)
        ch_init.queue_declare(queue=RESULTS_QUEUE_NAME_RABBIT, durable=True) # Assuming this is used by workers
        conn_init.close()
    except Exception as e:
        print(f"Scaler: Could not pre-declare RabbitMQ queues: {e}. Workers might fail if queues don't exist.")

    scaler_loop()
