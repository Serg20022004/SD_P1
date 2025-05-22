# test_static_scaling_filter_redis.py
import multiprocessing
import subprocess
import time
import redis
import json # For results, though tasks are plain text
import os
import signal
import random

# --- Configuration ---
PYTHON_EXECUTABLE = "python" # SET TO YOUR VENV PYTHON
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "."))

FILTER_WORKER_SCRIPT_REDIS = os.path.join(PROJECT_ROOT, "redis_filter_service", "filter_worker_redis.py")

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
TASK_QUEUE_NAME_REDIS = 'filter_work_queue'
RESULTS_LIST_NAME_REDIS = 'filtered_texts_results'

TOTAL_REQUESTS = 10000 # Keeping it high for Redis
WORKER_COUNTS = [1, 2, 3] # Test with 1, 2, and 3 workers

SAMPLE_TEXTS_FOR_REDIS_FILTER = [
    "Redis scaling test: stupid text example.",
    "Redis scaling test: another LAME example from a moron.",
    "Redis scaling test: this is a heck of a clean text, not dense at all."
] * (TOTAL_REQUESTS // 3 + 1)


# --- Helper Functions ---
def clear_redis_data():
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
        r.delete(TASK_QUEUE_NAME_REDIS)
        r.delete(RESULTS_LIST_NAME_REDIS)
        print("  Redis task and result lists cleared.")
    except Exception as e:
        print(f"  Error clearing Redis lists: {e}")

def redis_producer_job(num_tasks, task_queue_name, sample_texts):
    try:
        r_prod = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
        for i in range(num_tasks):
            text_content = random.choice(sample_texts) + f" task_{i}"
            r_prod.rpush(task_queue_name, text_content)
        # print(f"  Producer: Sent {num_tasks} tasks to Redis queue '{task_queue_name}'.")
    except Exception as e:
        print(f"  Producer (Redis) error: {e}")

def run_worker_process(worker_script_path, python_exec, title_prefix="Worker"):
    print(f"  Starting {title_prefix} ({worker_script_path})...")
    proc = subprocess.Popen([python_exec, worker_script_path])
    time.sleep(1) # Give worker a moment to connect to Redis
    if proc.poll() is not None:
        print(f"  ERROR: {title_prefix} at {worker_script_path} exited prematurely.")
        return None
    return proc

# --- Main Test Execution ---
if __name__ == "__main__":
    venv_path_check = os.environ.get("VIRTUAL_ENV")
    if not venv_path_check:
        print("WARNING: Not running in a virtual environment.")
    elif PROJECT_ROOT not in venv_path_check :
         print(f"WARNING: Current VIRTUAL_ENV '{venv_path_check}' might not match project root '{PROJECT_ROOT}'.")

    print("Starting Static Scaling Performance Test for InsultFilter (Redis)")
    print(f"Total Requests to process per run: {TOTAL_REQUESTS}")
    print(f"Redis Worker script: {FILTER_WORKER_SCRIPT_REDIS}")
    print("Ensure Redis server is running.")
    print("-" * 70)

    overall_results_redis = []
    T1_redis = None # To store time for 1 worker

    for num_workers in WORKER_COUNTS:
        print(f"\nTesting with {num_workers} Redis worker(s)...")
        clear_redis_data() # Clear queues before each N-worker test
        worker_procs_redis = []
        
        try:
            print(f"  Starting {num_workers} Redis worker process(es)...")
            for i in range(num_workers):
                proc = run_worker_process(FILTER_WORKER_SCRIPT_REDIS, PYTHON_EXECUTABLE, f"RedisWorker{i+1}")
                if proc: worker_procs_redis.append(proc)
            
            if len(worker_procs_redis) != num_workers:
                raise Exception(f"Failed to start all {num_workers} Redis workers.")

            time.sleep(2 + num_workers * 0.5) # More time for workers to be ready

            print(f"  Producer starting to send {TOTAL_REQUESTS} tasks to Redis queue...")
            test_start_time = time.perf_counter()
            
            # Run producer logic
            redis_producer_job(TOTAL_REQUESTS, TASK_QUEUE_NAME_REDIS, SAMPLE_TEXTS_FOR_REDIS_FILTER)
            
            print(f"  Producer finished sending tasks. Now waiting for all results...")

            # Monitor results list in Redis
            r_monitor = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
            results_collected_count = 0
            # Adjust max_wait_time based on expected processing speed. Redis is fast.
            max_wait_time_redis = 30 + (TOTAL_REQUESTS / (num_workers * 100 if num_workers > 0 else 1)) # Heuristic
            wait_start_redis = time.time()

            while results_collected_count < TOTAL_REQUESTS and (time.time() - wait_start_redis) < max_wait_time_redis:
                results_collected_count = r_monitor.llen(RESULTS_LIST_NAME_REDIS)
                if results_collected_count < TOTAL_REQUESTS:
                    time.sleep(0.1) # Poll frequently
                else:
                    break
            
            test_end_time = time.perf_counter()
            total_test_time_redis = test_end_time - test_start_time

            if results_collected_count < TOTAL_REQUESTS:
                print(f"  TIMEOUT or ERROR: Only {results_collected_count}/{TOTAL_REQUESTS} results found in Redis list after {max_wait_time_redis:.0f}s.")
                speedup_val_redis = "N/A (Incomplete)"
            else:
                print(f"  All {TOTAL_REQUESTS} tasks processed and results stored in Redis.")
                print(f"  Total test time: {total_test_time_redis:.4f} seconds")
                if num_workers == 1:
                    T1_redis = total_test_time_redis
                    overall_results_redis.append({"workers": num_workers, "time": T1_redis, "speedup": 1.0})
                    print(f"    T1 (baseline for 1 Redis worker): {T1_redis:.4f}s")
                else:
                    if T1_redis is not None:
                        speedup_val_redis = T1_redis / total_test_time_redis if total_test_time_redis > 0 else float('inf')
                        overall_results_redis.append({"workers": num_workers, "time": total_test_time_redis, "speedup": speedup_val_redis})
                        print(f"    Speedup vs 1 Redis worker: {speedup_val_redis:.2f}x")
                    else:
                        overall_results_redis.append({"workers": num_workers, "time": total_test_time_redis, "speedup": "N/A (No T1)"})
        
        except Exception as e_iter_redis:
            print(f"  Error during test iteration for {num_workers} Redis workers: {e_iter_redis}")
            import traceback
            traceback.print_exc()
        finally:
            print(f"  Terminating {len(worker_procs_redis)} Redis worker process(es) for N={num_workers} run...")
            for proc in worker_procs_redis:
                try: 
                    proc.terminate() 
                    proc.wait(timeout=5)
                except: pass # Ignore errors during cleanup
            print(f"  Redis workers for N={num_workers} terminated.")
            time.sleep(1)

    print("\n" + "=" * 70)
    print("Static Scaling Test Summary (Redis - InsultFilter):")
    print("Workers | Time (s) | Speedup (vs 1W)")
    print("--------|----------|----------------")
    for res in overall_results_redis:
        speedup_str_redis = f"{res['speedup']:.2f}x" if isinstance(res['speedup'], float) else res['speedup']
        print(f"{res['workers']:<7} | {res['time']:<8.2f} | {speedup_str_redis}")
    print("=" * 70)
