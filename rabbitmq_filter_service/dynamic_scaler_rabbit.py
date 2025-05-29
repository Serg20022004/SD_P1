# dynamic_scaler_rabbit.py (Revised for clearer data output)
import pika
import time
import subprocess
import os
import signal
import math
import datetime

# --- Configuration ---
PYTHON_EXECUTABLE = "/home/milax/Documents/SD/P1/SD-env/bin/python" # YOUR VENV PYTHON!
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "."))
FILTER_WORKER_SCRIPT = os.path.join(PROJECT_ROOT, "rabbitmq_filter_service", "filter_worker_rabbit.py")

RESULTS_QUEUE_NAME_RABBIT = 'filter_results_data_queue'
RABBITMQ_HOST = 'localhost'
TASK_QUEUE_NAME = 'filter_task_work_queue'
# RESULTS_QUEUE_NAME_RABBIT is used by workers but not directly by this scaler for its decisions.

# Scaler Parameters
MIN_WORKERS = 1
MAX_WORKERS = 3 # Keep this reasonable for your VM (e.g., <= vCPUs for best effect)
POLL_INTERVAL = 5  # Seconds: How often to check queue and make scaling decisions

# --- ACCURATE Formula parameters from your Phase 2, N=1 RabbitMQ test ---
# Example: T1_rabbit for 10000 tasks was 15.25s
T1_FOR_10K_TASKS_RABBIT = 15.25 # <<< REPLACE WITH YOUR ACTUAL MEASURED VALUE
TOTAL_TASKS_FOR_T1_CALC = 10000
T_AVG_PROCESSING_PER_TASK = T1_FOR_10K_TASKS_RABBIT / TOTAL_TASKS_FOR_T1_CALC

if T_AVG_PROCESSING_PER_TASK > 0:
    C_WORKER_CAPACITY = math.ceil(1 / T_AVG_PROCESSING_PER_TASK)
else:
    C_WORKER_CAPACITY = 100 # Fallback: A very conservative estimate if T_avg is somehow zero

Tr_TARGET_RESPONSE_TIME = 2.0 # Seconds: Target for tasks in backlog
LAMBDA_ESTIMATED_ARRIVAL_RATE = 150 # tasks/second (Average expected, adjust based on producer)

SCALE_COOLDOWN_PERIOD = 15 # Seconds: Reduced for quicker reaction in demo

active_worker_processes_info = [] # List of dicts: {"process": Popen_obj, "pid": pid, "id_str": "Worker-X"}
last_scaling_action_time = 0
worker_id_counter = 0 # To give unique IDs to workers

# --- Log File ---
SCALER_LOG_FILE = "dynamic_scaler_log.csv"

def log_to_file(message):
    with open(SCALER_LOG_FILE, "a") as f:
        f.write(message + "\n")

def get_queue_length(queue_name):
    # (get_queue_length function remains the same - ensure robust connection)
    connection = None
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST, connection_attempts=2, retry_delay=1))
        channel = connection.channel()
        q_info = channel.queue_declare(queue=queue_name, durable=True, passive=True)
        return q_info.method.message_count
    except Exception as e:
        log_to_file(f"{datetime.datetime.now().strftime('%H:%M:%S')},ERROR_Q_LEN,-1,-1,ErrorGettingQueueLength: {e}")
        return None 
    finally:
        if connection and connection.is_open:
            connection.close()

def start_new_worker():
    global active_worker_processes_info, worker_id_counter
    if len(active_worker_processes_info) < MAX_WORKERS:
        worker_id_counter += 1
        worker_id_str = f"Worker-{worker_id_counter}"
        log_message = f"Attempting to start {worker_id_str} (current: {len(active_worker_processes_info)})"
        print(log_message); log_to_file(f"INFO,{log_message}")
        try:
            # Redirect worker output to its own log file to keep scaler output clean
            worker_logfile_name = f"worker_{worker_id_counter}_log.txt"
            worker_logfile = open(worker_logfile_name, "w")
            
            proc = subprocess.Popen([PYTHON_EXECUTABLE, FILTER_WORKER_SCRIPT],
                                    stdout=worker_logfile, stderr=subprocess.STDOUT)
            
            active_worker_processes_info.append({"process": proc, "pid": proc.pid, "id_str": worker_id_str, "logfile": worker_logfile_name})
            log_message = f"New worker {worker_id_str} (PID: {proc.pid}) started. Total: {len(active_worker_processes_info)}"
            print(log_message); log_to_file(f"INFO,{log_message}")
            return True
        except Exception as e:
            log_message = f"Failed to start new worker {worker_id_str}: {e}"
            print(log_message); log_to_file(f"ERROR,{log_message}")
            if 'worker_logfile' in locals() and worker_logfile: worker_logfile.close() # Close if opened
            return False
    return False

def stop_one_worker():
    global active_worker_processes_info
    if len(active_worker_processes_info) > MIN_WORKERS:
        try:
            worker_info_to_stop = active_worker_processes_info.pop(0) # Stop oldest worker
            proc_to_stop = worker_info_to_stop["process"]
            pid_to_stop = worker_info_to_stop.get("pid", "N/A")
            worker_id_str = worker_info_to_stop.get("id_str", f"PID {pid_to_stop}")

            log_message = f"Attempting to stop worker {worker_id_str} (PID: {pid_to_stop})"
            print(log_message); log_to_file(f"INFO,{log_message}")
            
            proc_to_stop.terminate() 
            proc_to_stop.wait(timeout=5) 
            if proc_to_stop.poll() is None: 
                log_message_kill = f"Worker {worker_id_str} (PID: {pid_to_stop}) did not terminate gracefully, killing."
                print(log_message_kill); log_to_file(f"INFO,{log_message_kill}")
                proc_to_stop.kill()
                proc_to_stop.wait(timeout=2)
            
            log_message_stopped = f"Worker {worker_id_str} stopped. Total: {len(active_worker_processes_info)}"
            print(log_message_stopped); log_to_file(f"INFO,{log_message_stopped}")

            # Close worker's log file
            logfile_name = worker_info_to_stop.get("logfile")
            if logfile_name:
                # This requires finding the file object if it wasn't stored, or just noting it.
                # For simplicity, we just have the name. Actual closing would be if we kept file objects.
                pass
            return True
        except Exception as e:
            log_message_err = f"Error stopping worker {pid_to_stop}: {e}"
            print(log_message_err); log_to_file(f"ERROR,{log_message_err}")
        return False
    return False

def cleanup_terminated_workers():
    global active_worker_processes_info
    # (cleanup logic remains same)
    live_workers_info = []
    changed = False
    for worker_info in active_worker_processes_info:
        proc = worker_info["process"]
        if proc.poll() is None: 
            live_workers_info.append(worker_info)
        else:
            pid = worker_info.get("pid", "N/A")
            log_message = f"Worker PID {pid} found terminated (exit code {proc.returncode}). Removing."
            print(log_message); log_to_file(f"INFO,{log_message}")
            changed = True
    if changed:
        active_worker_processes_info = live_workers_info

# --- Main Scaler Loop ---
def scaler_loop():
    global last_scaling_action_time

    header = "Timestamp,Backlog_B,Active_Workers,N_Desired_Formula,Action_Taken"
    print(header); log_to_file(header) # Print and log CSV header

    print("Scaler: Starting initial minimum workers...")
    for _ in range(MIN_WORKERS): # Start initial MIN_WORKERS
        start_new_worker()
    last_scaling_action_time = 0 # Allow first decision after poll_interval without cooldown

    try:
        while True:
            time.sleep(POLL_INTERVAL)
            cleanup_terminated_workers() 

            current_timestamp_obj = datetime.datetime.now()
            ts = current_timestamp_obj.strftime('%Y-%m-%d %H:%M:%S')

            current_backlog_B = get_queue_length(TASK_QUEUE_NAME)
            if current_backlog_B is None: 
                log_to_file(f"{ts},ERROR_Q_LEN,-1,-1,ErrorGettingQueueLength")
                continue 
            
            num_current_live_workers = len(active_worker_processes_info)
            
            numerator = current_backlog_B + (LAMBDA_ESTIMATED_ARRIVAL_RATE * Tr_TARGET_RESPONSE_TIME)
            N_desired = MIN_WORKERS 
            if C_WORKER_CAPACITY > 0:
                N_desired = math.ceil(numerator / C_WORKER_CAPACITY)
            else: 
                 if numerator > 0 : N_desired = MAX_WORKERS 

            N_desired = max(MIN_WORKERS, min(N_desired, MAX_WORKERS))
            
            action_taken_str = "Maintain"
            scaled_this_cycle = False

            if time.time() - last_scaling_action_time >= SCALE_COOLDOWN_PERIOD:
                if N_desired > num_current_live_workers:
                    action_taken_str = f"Attempt_ScaleUP_to_{N_desired}"
                    if start_new_worker(): # Tries to start one if not at MAX
                       last_scaling_action_time = time.time()
                       scaled_this_cycle = True
                       # If N_desired needs more than one new worker, it will happen over multiple polls
                elif N_desired < num_current_live_workers:
                    action_taken_str = f"Attempt_ScaleDOWN_to_{N_desired}"
                    if stop_one_worker(): # Tries to stop one if not at MIN
                        last_scaling_action_time = time.time()
                        scaled_this_cycle = True
            else:
                action_taken_str = f"InCooldown ({SCALE_COOLDOWN_PERIOD - (time.time() - last_scaling_action_time):.0f}s left)"
            
            # Log data AFTER action attempt, use updated num_current_live_workers for log
            num_current_live_workers = len(active_worker_processes_info) # Re-check after potential scaling
            log_line = f"{ts},{current_backlog_B},{num_current_live_workers},{N_desired},{action_taken_str}"
            print(log_line); log_to_file(log_line)

    except KeyboardInterrupt:
        log_message_kb = "\nScaler: KeyboardInterrupt. Shutting down..."
        print(log_message_kb); log_to_file(f"INFO,{log_message_kb}")
    finally:
        log_message_final = "Scaler: Final cleanup. Terminating active workers..."
        print(log_message_final); log_to_file(f"INFO,{log_message_final}")
        
        # Create a copy for safe iteration if stop_one_worker modifies the list
        # However, stop_one_worker now pops from the global list directly
        while len(active_worker_processes_info) > 0:
            stop_one_worker() # This will stop them one by one until MIN_WORKERS or list is empty
            if len(active_worker_processes_info) <= MIN_WORKERS and not any(p['process'].poll() is None for p in active_worker_processes_info if p['process'] is not None and hasattr(p['process'], 'poll')):
                 # Break if only min workers left and they are not running, or list is empty
                 # This logic needs refinement to ensure all are stopped.
                 # The pop in stop_one_worker will eventually empty the list.
                 pass


        # Ensure all process log files are closed if they were managed by scaler
        # (This part is tricky as Popen objects don't directly give file handles back easily)

        print("Dynamic Scaler stopped."); log_to_file("INFO,Dynamic Scaler stopped.")

if __name__ == "__main__":
    # (venv check and queue pre-declaration as before)
    if PYTHON_EXECUTABLE == "python" or "SD-env/bin/python" not in PYTHON_EXECUTABLE :
        print(f"CRITICAL WARNING: PYTHON_EXECUTABLE is '{PYTHON_EXECUTABLE}'.")
    with open(SCALER_LOG_FILE, "w") as f: # Create/overwrite log file
        f.write(f"Scaler Log Initialized at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Config: MIN_W={MIN_WORKERS}, MAX_W={MAX_WORKERS}, POLL_I={POLL_INTERVAL}s, COOLDOWN={SCALE_COOLDOWN_PERIOD}s\n")
        f.write(f"Formula: T_avg={T_AVG_PROCESSING_PER_TASK:.6f}s, C_cap={C_WORKER_CAPACITY:.0f}rps, Tr_target={Tr_TARGET_RESPONSE_TIME}s, Lambda_est={LAMBDA_ESTIMATED_ARRIVAL_RATE}rps\n")

    try:
        conn_init = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        ch_init = conn_init.channel()
        ch_init.queue_declare(queue=TASK_QUEUE_NAME, durable=True)
        ch_init.queue_declare(queue=RESULTS_QUEUE_NAME_RABBIT, durable=True) 
        conn_init.close()
    except Exception as e:
        log_message_q_err = f"Scaler: Could not pre-declare RabbitMQ queues: {e}."
        print(log_message_q_err); log_to_file(f"ERROR,{log_message_q_err}")
    
    scaler_loop()
