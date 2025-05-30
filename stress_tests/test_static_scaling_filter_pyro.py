# test_static_scaling_filter_pyro.py
import multiprocessing
import subprocess
import time
import Pyro4
import os
import signal
import random 

# --- Configuration ---
PYTHON_EXECUTABLE = "python" # SET TO VENV PYTHON e.g., "/path/to/SD-env/bin/python"
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "."))

FILTER_DISPATCHER_SCRIPT = os.path.join(PROJECT_ROOT, "pyro_filter_service", "filter_dispatcher_pyro.py")
FILTER_WORKER_SCRIPT_PYRO = os.path.join(PROJECT_ROOT, "pyro_filter_service", "filter_worker_pyro.py")

PYRO_DISPATCHER_NAME = "example.filter.dispatcher"

TOTAL_REQUESTS = 5000
WORKER_COUNTS = [1, 2, 3]

SAMPLE_TEXTS_FOR_PYRO_FILTER = [
    "Pyro scaling: This is a stupid example text with some bad words like idiot.",
    "Pyro scaling: A perfectly clean and fine statement about a moron.",
    "Pyro scaling: What a LAME thing to say, you dummy!",
] * (TOTAL_REQUESTS // 3 + 1)


# --- Helper to run a Pyro server (dispatcher or worker) ---
def run_pyro_server_process(script_path, python_exec, title="Pyro Process"):
    # It's assumed the Name Server is already running independently.
    # Workers and Dispatcher will try to connect to it.
    print(f"  Starting {title} ({script_path})...")
    # For Pyro, often better to let them print their own output for debugging registration
    proc = subprocess.Popen([python_exec, script_path])
    time.sleep(3) # Give server/worker time to start and register
    if proc.poll() is not None: # Check if it exited immediately
        print(f"  ERROR: {title} at {script_path} exited prematurely. Check logs/Name Server.")
        return None
    return proc

# --- Helper to send tasks to Pyro Dispatcher ---
def pyro_producer_job(num_tasks, dispatcher_name, sample_texts):
    try:
        dispatcher = Pyro4.Proxy(f"PYRONAME:{dispatcher_name}")
        dispatcher._pyroTimeout = 20 # Longer timeout for dispatcher + worker chain

        for i in range(num_tasks):
            text_to_filter = random.choice(sample_texts) + f" task_{i}"
            try:
                # This call is synchronous from producer's POV; dispatcher handles worker call
                response = dispatcher.submit_text_for_filtering(text_to_filter)
            except Exception as e:
                print(f"Producer: Error submitting task to dispatcher: {e}")
                # If dispatcher is down, this job might fail many times.
        # print(f"Producer: Finished sending {num_tasks} tasks to dispatcher {dispatcher_name}.")
    except Pyro4.errors.NamingError:
        print(f"Producer Error: Could not find dispatcher '{dispatcher_name}'.")
    except Exception as e:
        print(f"Producer Error: {e}")


if __name__ == "__main__":
    venv_path_check = os.environ.get("VIRTUAL_ENV")
    if not venv_path_check:
        print("WARNING: Not running in a virtual environment.")
    elif PROJECT_ROOT not in venv_path_check :
         print(f"WARNING: Current VIRTUAL_ENV '{venv_path_check}' might not match project root '{PROJECT_ROOT}'.")


    print("Starting Static Scaling Performance Test for InsultFilter (Pyro4)")
    print(f"Total Requests to process per run: {TOTAL_REQUESTS}")
    print(f"Ensure Pyro Name Server is running (python -m Pyro4.naming)")
    print("-" * 70)

    overall_results_pyro = []
    dispatcher_process = None

    try:
        # Start Dispatcher ONCE for all worker count tests
        dispatcher_process = run_pyro_server_process(FILTER_DISPATCHER_SCRIPT, PYTHON_EXECUTABLE, "FilterDispatcher")
        if not dispatcher_process or dispatcher_process.poll() is not None:
            print("CRITICAL: FilterDispatcher failed to start. Aborting tests.")
            exit()
        print("FilterDispatcher started. Waiting for it to be available in Name Server...")
        time.sleep(5) # Extra time for NS registration visibility

        for num_workers in WORKER_COUNTS:
            print(f"\nTesting with {num_workers} Pyro worker(s)...")
            worker_procs_pyro = []
            
            try:
                print(f"  Starting {num_workers} worker process(es)...")
                for i in range(num_workers):
                    proc = run_pyro_server_process(FILTER_WORKER_SCRIPT_PYRO, PYTHON_EXECUTABLE, f"FilterWorker{i+1}")
                    if proc and proc.poll() is None:
                        worker_procs_pyro.append(proc)
                    else:
                        print(f"  ERROR: FilterWorker{i+1} failed to start.")
                
                if len(worker_procs_pyro) != num_workers:
                    print(f"  ERROR: Expected {num_workers} workers, but only {len(worker_procs_pyro)} started. Skipping this run.")
                    raise Exception("Worker startup failure") # Go to finally for cleanup
                
                print(f"  All {num_workers} workers presumed started. Waiting for registrations...")
                time.sleep(5 + num_workers * 2) # Allow workers time to register with dispatcher

                print(f"  Producer starting to send {TOTAL_REQUESTS} tasks...")
                test_start_time = time.perf_counter()
                
                # Run producer logic (could be a separate process for isolation)
                pyro_producer_job(TOTAL_REQUESTS, PYRO_DISPATCHER_NAME, SAMPLE_TEXTS_FOR_PYRO_FILTER)
                
                print(f"  Producer finished sending tasks. Now waiting for all results at dispatcher...")

                # Monitor results at the dispatcher
                dispatcher_monitor = Pyro4.Proxy(f"PYRONAME:{PYRO_DISPATCHER_NAME}")
                results_collected_count = 0
                max_wait_time_pyro = 60 + TOTAL_REQUESTS * 0.2 # Timeout
                wait_start_pyro = time.time()

                while results_collected_count < TOTAL_REQUESTS and (time.time() - wait_start_pyro) < max_wait_time_pyro:
                    try:
                        current_results = dispatcher_monitor.get_filtered_results()
                        results_collected_count = len(current_results)
                        if results_collected_count < TOTAL_REQUESTS:
                            time.sleep(0.5)
                        else:
                            break
                    except Exception as e_mon:
                        print(f"    Error polling dispatcher for results: {e_mon}")
                        time.sleep(1) # Wait and retry polling
                        break # Or assume failure for this iteration

                test_end_time = time.perf_counter()
                total_test_time_pyro = test_end_time - test_start_time

                if results_collected_count < TOTAL_REQUESTS:
                    print(f"  TIMEOUT or ERROR: Dispatcher only has {results_collected_count}/{TOTAL_REQUESTS} results after {max_wait_time_pyro:.0f}s.")
                    speedup_val_pyro = "N/A (Incomplete)"
                else:
                    print(f"  All {TOTAL_REQUESTS} tasks processed (results collected by dispatcher).")
                    print(f"  Total test time: {total_test_time_pyro:.4f} seconds")
                    if num_workers == 1:
                        T1_pyro = total_test_time_pyro
                        overall_results_pyro.append({"workers": num_workers, "time": T1_pyro, "speedup": 1.0})
                        print(f"    T1 (baseline for 1 worker): {T1_pyro:.4f}s")
                    else:
                        t1_entry_pyro = next((r for r in overall_results_pyro if r["workers"] == 1), None)
                        if t1_entry_pyro:
                            speedup_val_pyro = t1_entry_pyro["time"] / total_test_time_pyro if total_test_time_pyro > 0 else float('inf')
                            overall_results_pyro.append({"workers": num_workers, "time": total_test_time_pyro, "speedup": speedup_val_pyro})
                            print(f"    Speedup vs 1 worker: {speedup_val_pyro:.2f}x")
                        else:
                            overall_results_pyro.append({"workers": num_workers, "time": total_test_time_pyro, "speedup": "N/A (No T1)"})
            
            except Exception as e_iter:
                print(f"  Error during test iteration for {num_workers} workers: {e_iter}")
            finally:
                print(f"  Terminating {len(worker_procs_pyro)} worker process(es) for N={num_workers} run...")
                for proc in worker_procs_pyro:
                    try: 
                        proc.terminate()
                        proc.wait(timeout=5)
                    except: pass
                print(f"  Workers for N={num_workers} terminated.")
                # Clear dispatcher's results for next run
                try:
                    Pyro4.Proxy(f"PYRONAME:{PYRO_DISPATCHER_NAME}")._filtered_results = [] 
                    print("  Dispatcher results cleared (attempted).")
                except: pass
                time.sleep(2) # Pause

    except Exception as e_main_test:
        print(f"CRITICAL Error in main test execution: {e_main_test}")
        import traceback
        traceback.print_exc()
    finally:
        if dispatcher_process:
            print("Terminating FilterDispatcher server...")
            try:                
                dispatcher_process.terminate()
                dispatcher_process.wait(timeout=5)
            except: pass
            print("FilterDispatcher terminated.")

    print("\n" + "=" * 70)
    print("Static Scaling Test Summary (Pyro4 - InsultFilter):")
    print("Workers | Time (s) | Speedup (vs 1W)")
    print("--------|----------|----------------")
    for res in overall_results_pyro:
        speedup_str_pyro = f"{res['speedup']:.2f}x" if isinstance(res['speedup'], float) else res['speedup']
        print(f"{res['workers']:<7} | {res['time']:<8.2f} | {speedup_str_pyro}")
    print("=" * 70)
