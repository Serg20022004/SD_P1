# test_static_scaling_filter_rabbitmq.py
import multiprocessing
import subprocess
import time
import pika
import json
import os
import signal
import random

# --- Configuration ---
# !!! IMPORTANT: SET THIS TO THE PYTHON EXECUTABLE IN YOUR VIRTUAL ENVIRONMENT !!!
PYTHON_EXECUTABLE = "python" # CHANGE THIS IF NEEDED

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "."))
FILTER_WORKER_SCRIPT_RABBIT = os.path.join(PROJECT_ROOT, "rabbitmq_filter_service", "filter_worker_rabbit.py")

RABBITMQ_HOST = 'localhost'
TASK_QUEUE_NAME_RABBIT = 'filter_task_work_queue'
RESULTS_QUEUE_NAME_RABBIT = 'filter_results_data_queue'

TOTAL_REQUESTS = 10000 # Keep high if worker processing is fast
WORKER_COUNTS = [1, 2, 3]

SAMPLE_TEXTS_FOR_RABBIT_FILTER = [
    "RabbitMQ scaling test: stupid text example.",
    "RabbitMQ scaling test: another LAME example from a moron.",
    "RabbitMQ scaling test: this is a heck of a clean text, not dense at all."
] * (TOTAL_REQUESTS // 3 + 1)


# --- Helper Functions ---
def clear_rabbitmq_data_robust():
    # (clear_rabbitmq_data_robust remains mostly the same, ensure queues declared durable)
    connection = None
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        channel = connection.channel()
        
        queues_to_clear = [TASK_QUEUE_NAME_RABBIT, RESULTS_QUEUE_NAME_RABBIT]
        for q_name in queues_to_clear:
            try:
                channel.queue_purge(queue=q_name)
            except pika.exceptions.ChannelClosedByBroker as e: # Queue might not exist
                if e.reply_code == 404: # Not Found
                    pass # It's fine if it doesn't exist, we'll declare it next
                else:
                    raise # Other channel error
            # Declare to ensure it exists and is durable
            channel.queue_declare(queue=q_name, durable=True)
        print("  RabbitMQ task and result queues cleared and declared.")
    except Exception as e:
        print(f"  Error clearing/declaring RabbitMQ queues: {e}")
    finally:
        if connection and connection.is_open:
            connection.close()


def rabbitmq_producer_job_direct(num_tasks, task_queue_name, sample_texts):
    # (producer logic remains the same)
    connection_prod = None
    try:
        connection_prod = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        channel_prod = connection_prod.channel()
        channel_prod.queue_declare(queue=task_queue_name, durable=True) 

        for i in range(num_tasks):
            text_content = random.choice(sample_texts) + f" task_{i}_pid{os.getpid()}"
            channel_prod.basic_publish(
                exchange='', routing_key=task_queue_name, body=text_content,
                properties=pika.BasicProperties(delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE)
            )
        print(f"  Producer: Sent {num_tasks} tasks to RabbitMQ queue '{task_queue_name}'.")
    except Exception as e:
        print(f"  Producer (RabbitMQ) error: {e}")
    finally:
        if connection_prod and connection_prod.is_open:
            connection_prod.close()


def run_worker_process_rb(worker_script_path, python_exec, title_prefix="Worker"):
    # (Worker starter same as Redis test)
    print(f"  Starting {title_prefix} using: {python_exec} {worker_script_path}")
    # proc = subprocess.Popen([python_exec, worker_script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc = subprocess.Popen([python_exec, worker_script_path]) # Let worker print to this console
    time.sleep(2) # RabbitMQ workers need time to connect, declare, start consuming
    if proc.poll() is not None:
        print(f"  ERROR: {title_prefix} at {worker_script_path} exited prematurely.")
        stdout, stderr = proc.communicate()
        print(f"    Worker STDOUT: {stdout.decode(errors='ignore')}")
        print(f"    Worker STDERR: {stderr.decode(errors='ignore')}")
        return None
    print(f"  {title_prefix} (PID: {proc.pid}) presumed started.")
    return proc

def consume_all_results_from_rabbit(num_expected, queue_name, timeout_per_message=0.5, overall_timeout=60):
    """Consumes up to num_expected messages from a queue or until overall_timeout."""
    results = []
    conn_results = None
    start_overall_wait = time.time()
    try:
        conn_results = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        ch_results = conn_results.channel()
        ch_results.queue_declare(queue=queue_name, durable=True) # Ensure it exists

        while len(results) < num_expected:
            if time.time() - start_overall_wait > overall_timeout:
                print(f"  Results consumer: Overall timeout ({overall_timeout}s) reached.")
                break
            
            method_frame, properties, body = ch_results.basic_get(queue=queue_name, auto_ack=True)
            if method_frame:
                results.append(body) # Store raw body, or parse JSON if needed
            else:
                # Queue is empty, wait a bit if we still expect more messages
                if len(results) < num_expected:
                    time.sleep(timeout_per_message) 
                else: # Should not happen if len(results) < num_expected is true
                    break 
        # print(f"  Results consumer: Consumed {len(results)} results from '{queue_name}'.")
    except Exception as e:
        print(f"  Results consumer error for '{queue_name}': {e}")
    finally:
        if conn_results and conn_results.is_open:
            conn_results.close()
    return results


# --- Main Test Execution ---
if __name__ == "__main__":
    # (venv check same as Redis script)
    if PYTHON_EXECUTABLE == "python":
        print("WARNING: PYTHON_EXECUTABLE is 'python'. Ensure this resolves to your venv Python.")

    print("Starting Static Scaling Performance Test for InsultFilter (RabbitMQ)")
    print(f"Total Requests to process per run: {TOTAL_REQUESTS}")
    print(f"RabbitMQ Worker script: {FILTER_WORKER_SCRIPT_RABBIT}")
    print("Ensure RabbitMQ server is running.")
    print("-" * 70)

    overall_results_rabbit = []
    T1_rabbit = None

    for num_workers in WORKER_COUNTS:
        print(f"\n>>> Testing with {num_workers} RabbitMQ worker(s)...")
        clear_rabbitmq_data_robust()
        worker_procs_rabbit = []
        
        try:
            print(f"  Starting {num_workers} RabbitMQ worker process(es)...")
            for i in range(num_workers):
                proc = run_worker_process_rb(FILTER_WORKER_SCRIPT_RABBIT, PYTHON_EXECUTABLE, f"RabbitWorker{i+1}")
                if proc: worker_procs_rabbit.append(proc)
            
            if len(worker_procs_rabbit) != num_workers:
                raise Exception(f"Failed to start all {num_workers} RabbitMQ workers.")

            print(f"  All {num_workers} workers launched. Waiting for them to stabilize (e.g., 5-7s)...")
            time.sleep(5 + num_workers * 1.5) 

            print(f"  Producer starting to send {TOTAL_REQUESTS} tasks to RabbitMQ queue...")
            test_start_time = time.perf_counter()
            
            # Run producer in a separate process so it doesn't block timing
            producer_proc = multiprocessing.Process(target=rabbitmq_producer_job_direct,
                                                    args=(TOTAL_REQUESTS, TASK_QUEUE_NAME_RABBIT, SAMPLE_TEXTS_FOR_RABBIT_FILTER))
            producer_proc.start()
            producer_proc.join(timeout=60) # Wait for producer

            if producer_proc.is_alive():
                print("  ERROR: Producer timed out. Terminating.")
                producer_proc.terminate()
                raise Exception("Producer failed to send all tasks.")
            print(f"  Producer finished sending tasks. Now waiting for all results to be collected from '{RESULTS_QUEUE_NAME_RABBIT}'...")

            # Now, consume results directly in the main test script
            # Adjust overall timeout based on expected processing time.
            # If TOTAL_REQUESTS = 10000, and each worker does ~50RPS, 3 workers ~150RPS
            # Time = 10000 / 150 = ~66s. Add buffer.
            results_collection_timeout = 60 + (TOTAL_REQUESTS / (num_workers * 5 if num_workers > 0 else 1)) # Heuristic for results collection
            
            collected_results = consume_all_results_from_rabbit(
                TOTAL_REQUESTS, 
                RESULTS_QUEUE_NAME_RABBIT,
                timeout_per_message=0.2, # How long to wait if queue is empty but not all results are in
                overall_timeout=results_collection_timeout
            )
            
            test_end_time = time.perf_counter()
            total_test_time_rabbit = test_end_time - test_start_time
            
            num_results_actually_collected = len(collected_results)

            if num_results_actually_collected < TOTAL_REQUESTS:
                print(f"  TIMEOUT or ERROR: Only {num_results_actually_collected}/{TOTAL_REQUESTS} results collected after {total_test_time_rabbit:.0f}s.")
                print(f"    Task queue message count: (check RabbitMQ Management UI or use pika to get count)")
                # Check task queue if possible
                try:
                    conn_check = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
                    ch_check = conn_check.channel()
                    q_info = ch_check.queue_declare(queue=TASK_QUEUE_NAME_RABBIT, passive=True)
                    print(f"    Current tasks in '{TASK_QUEUE_NAME_RABBIT}': {q_info.method.message_count}")
                    conn_check.close()
                except Exception as e_qc:
                    print(f"    Could not check task queue count: {e_qc}")

                speedup_val_rabbit = "N/A (Incomplete)"
            else:
                print(f"  All {TOTAL_REQUESTS} tasks processed and results collected.")
                print(f"  Total test time: {total_test_time_rabbit:.4f} seconds")
                if num_workers == 1:
                    T1_rabbit = total_test_time_rabbit
                    overall_results_rabbit.append({"workers": num_workers, "time": T1_rabbit, "speedup": 1.0})
                    print(f"    T1 (baseline for 1 RabbitMQ worker): {T1_rabbit:.4f}s")
                else:
                    if T1_rabbit is not None:
                        speedup_val_rabbit = T1_rabbit / total_test_time_rabbit if total_test_time_rabbit > 0 else float('inf')
                        overall_results_rabbit.append({"workers": num_workers, "time": total_test_time_rabbit, "speedup": speedup_val_rabbit})
                        print(f"    Speedup vs 1 RabbitMQ worker: {speedup_val_rabbit:.2f}x")
                    else:
                        overall_results_rabbit.append({"workers": num_workers, "time": total_test_time_rabbit, "speedup": "N/A (No T1)"})
        
        except Exception as e_iter_rabbit:
            print(f"  Error during test iteration for {num_workers} RabbitMQ workers: {e_iter_rabbit}")
            import traceback
            traceback.print_exc()
        finally:
            print(f"  Terminating {len(worker_procs_rabbit)} RabbitMQ worker process(es) for N={num_workers} run...")
            for proc in worker_procs_rabbit:
                if proc and proc.poll() is None: # Check if progress still running
               	    print(f"    Terminating worker PID: {proc.pid}...")
                    try: 
                        # proc.send_signal(signal.SIGINT)
                        # time.sleep(1)
                        # if proc.poll() is None:
                        proc.terminate() 
                        proc.wait(timeout=5)
                        if proc.poll() is None: # If still running after SIGTERM and wait
                             print(f"    Worker PID: {proc.pid} did not stop with SIGTERM, sending SIGKILL...")
                             proc.kill()
                             proc.wait(timeout=2) # Wait for kill
                        # else:
                        #    print(f"    Worker PID: {proc.pid} terminated with code {proc.returncode}.")
                    except subprocess.TimeoutExpired:
                        print(f"    Worker PID: {proc.pid} did not terminate/wait in time after SIGTERM, killing.")
                        proc.kill() # Force kill if terminate + wait times out
                        proc.wait(timeout=2)
                    except Exception as e_term_rb: 
                        print(f"    Error during complex termination of worker {proc.pid}: {e_term_rb}")
                        try:
                            if proc.poll() is None: proc.kill() # Last resort
                        except: pass
                # else:
                    # print(f"    Worker process was already terminated or not valid.")
            print(f"  RabbitMQ workers for N={num_workers} terminated (or were already).")
            time.sleep(1)

    print("\n" + "=" * 70)
    print("Static Scaling Test Summary (RabbitMQ - InsultFilter):")
    # ... (summary printing remains same) ...
    print("Workers | Time (s) | Speedup (vs 1W)")
    print("--------|----------|----------------")
    for res in overall_results_rabbit:
        speedup_str_rabbit = f"{res['speedup']:.2f}x" if isinstance(res['speedup'], float) else res['speedup']
        print(f"{res['workers']:<7} | {res['time']:<8.2f} | {speedup_str_rabbit}")
    print("=" * 70)
