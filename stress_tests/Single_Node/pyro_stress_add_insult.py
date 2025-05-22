import Pyro4
import multiprocessing
import time
import random

# --- Test Configuration ---
PYRO_SERVICE_NAME = "example.insult.service" # Name in Pyro Name Server
TOTAL_REQUESTS = 10000
CONCURRENCY_LEVELS = [1, 2, 5, 10, 20]
SAMPLE_INSULTS = [f"Pyro insult {i} via stress test!" for i in range(100)]

# --- Worker Function ---
def pyro_add_insult_worker(num_requests_for_this_worker):
    pid = multiprocessing.current_process().pid
    try:
        # Each process gets its own proxy
        # Ensure Name Server is discoverable from where this script runs
        insult_server = Pyro4.Proxy(f"PYRONAME:{PYRO_SERVICE_NAME}")
        insult_server._pyroTimeout = 5 # Set a timeout for calls

        success_count = 0
        failure_count = 0
        
        for i in range(num_requests_for_this_worker):
            insult_to_send = random.choice(SAMPLE_INSULTS) + f" (req {i} by {pid})"
            try:
                # Assuming add_insult returns a string indicating success/failure
                response = insult_server.add_insult(insult_to_send)
                if "successfully" in response or "already exists" in response: # Adjust if server response changes
                    success_count += 1
                else:
                    failure_count +=1 # Count non-successful but non-exception responses as failures
            except Pyro4.errors.CommunicationError: # Specific Pyro communication error
                failure_count += 1
            except Exception: # Catch other Pyro errors or app-level errors
                failure_count += 1
        
        return {"success": success_count, "failure": failure_count}

    except Pyro4.errors.NamingError:
        return {"success": 0, "failure": num_requests_for_this_worker, "error": "NamingError"}
    except Exception as e:
        return {"success": 0, "failure": num_requests_for_this_worker, "error": str(type(e).__name__)}

# --- Main Test Execution ---
if __name__ == "__main__":
    print(f"Starting Pyro4 InsultService 'add_insult' stress test.")
    print(f"Target Service: PYRONAME:{PYRO_SERVICE_NAME}")
    print(f"Total Requests per concurrency level: {TOTAL_REQUESTS}")
    print("-" * 50)

    results_summary = []

    for concurrency in CONCURRENCY_LEVELS:
        print(f"\nTesting with {concurrency} concurrent processes...")
        
        base_req_per_worker = TOTAL_REQUESTS // concurrency
        remainder_reqs = TOTAL_REQUESTS % concurrency
        requests_per_worker_list = [base_req_per_worker] * concurrency
        for i in range(remainder_reqs):
            requests_per_worker_list[i] += 1
        
        start_time = time.perf_counter()
        with multiprocessing.Pool(processes=concurrency) as pool:
            worker_results = pool.map(pyro_add_insult_worker, requests_per_worker_list)
        end_time = time.perf_counter()
        total_time_taken = end_time - start_time

        total_successes = sum(r.get("success", 0) for r in worker_results)
        total_failures = sum(r.get("failure", 0) for r in worker_results)
        
        # Check for major errors reported by workers
        for r in worker_results:
            if "error" in r:
                print(f"  Worker reported error: {r['error']}")

        throughput = (total_successes / total_time_taken) if total_time_taken > 0 else float('inf')

        print(f"  Concurrency: {concurrency}")
        print(f"  Total Time Taken: {total_time_taken:.4f} seconds")
        print(f"  Total Successful Requests: {total_successes}")
        print(f"  Total Failed Requests: {total_failures}")
        print(f"  Throughput: {throughput:.2f} requests/sec")
        
        results_summary.append({
            "concurrency": concurrency, "time_taken": total_time_taken,
            "throughput": throughput, "successes": total_successes, "failures": total_failures
        })
        time.sleep(2)

    print("\n" + "=" * 50)
    print("Stress Test Summary (Pyro4 - Add Insult):")
    for res in results_summary:
        print(f"  Concurrency: {res['concurrency']:2d}, Time: {res['time_taken']:.2f}s, RPS: {res['throughput']:.2f}, Success: {res['successes']}, Fail: {res['failures']}")
    print("=" * 50)
