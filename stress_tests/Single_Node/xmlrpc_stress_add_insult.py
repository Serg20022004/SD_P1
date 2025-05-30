import xmlrpc.client
import multiprocessing
import time
import random # For generating varied insults if needed

# --- Test Configuration ---
XMLRPC_SERVER_URL = "http://127.0.0.1:8000/RPC2" # From InsultService XMLRPC server
TOTAL_REQUESTS = 10000  # Total insults to add
CONCURRENCY_LEVELS = [1, 2, 5, 10, 20] # Number of parallel client processes
SAMPLE_INSULTS = [f"Test insult {i} from a stress test!" for i in range(100)] # Create varied data

# --- Worker Function (executed by each process) ---
def xmlrpc_add_insult_worker(num_requests_for_this_worker):
    """
    Connects to the XMLRPC server and sends a specified number of add_insult requests.
    Each worker process will call this function.
    """
    pid = multiprocessing.current_process().pid
    try:
        # Each process creates its own ServerProxy
        server_proxy = xmlrpc.client.ServerProxy(XMLRPC_SERVER_URL, allow_none=True)
        
        success_count = 0
        failure_count = 0
        
        for i in range(num_requests_for_this_worker):
            # Select a sample insult to send
            insult_to_send = random.choice(SAMPLE_INSULTS) + f" (req {i} by {pid})"
            try:
                response = server_proxy.add_insult(insult_to_send)
                success_count += 1
            except Exception as e:
                failure_count += 1
        
        return {"success": success_count, "failure": failure_count}

    except Exception as e:
        return {"success": 0, "failure": num_requests_for_this_worker, "error": str(e)}

# --- Main Test Execution ---
if __name__ == "__main__":
    # Ensure the target server is running before starting this test.
    # e.g., python xmlrpc_insult_service/insult_server_xmlrpc.py

    print(f"Starting XMLRPC InsultService 'add_insult' stress test.")
    print(f"Target Server: {XMLRPC_SERVER_URL}")
    print(f"Total Requests to send per concurrency level: {TOTAL_REQUESTS}")
    print("-" * 50)

    results_summary = []

    for concurrency in CONCURRENCY_LEVELS:
        print(f"\nTesting with {concurrency} concurrent processes...")

        if TOTAL_REQUESTS % concurrency != 0:
            print(f"Warning: TOTAL_REQUESTS ({TOTAL_REQUESTS}) not perfectly divisible by concurrency ({concurrency}). Adjusting.")
        
        # Distribute requests among workers
        # Each item in requests_per_worker_list is the number of requests for one worker
        base_req_per_worker = TOTAL_REQUESTS // concurrency
        remainder_reqs = TOTAL_REQUESTS % concurrency
        requests_per_worker_list = [base_req_per_worker] * concurrency
        for i in range(remainder_reqs):
            requests_per_worker_list[i] += 1
        
        # print(f"  Requests distribution: {requests_per_worker_list}")

        start_time = time.perf_counter()

        with multiprocessing.Pool(processes=concurrency) as pool:
            # `map` will block until all results are back
            # Each worker function receives one element from `requests_per_worker_list`
            worker_results = pool.map(xmlrpc_add_insult_worker, requests_per_worker_list)

        end_time = time.perf_counter()
        total_time_taken = end_time - start_time

        total_successes = sum(r.get("success", 0) for r in worker_results)
        total_failures = sum(r.get("failure", 0) for r in worker_results)
        
        if total_time_taken > 0:
            throughput = total_successes / total_time_taken # RPS based on successful requests
        else:
            throughput = float('inf') # Avoid division by zero if time is too short

        print(f"  Concurrency: {concurrency}")
        print(f"  Total Time Taken: {total_time_taken:.4f} seconds")
        print(f"  Total Successful Requests: {total_successes}")
        print(f"  Total Failed Requests: {total_failures}")
        print(f"  Throughput: {throughput:.2f} requests/sec")
        
        results_summary.append({
            "concurrency": concurrency,
            "time_taken": total_time_taken,
            "throughput": throughput,
            "successes": total_successes,
            "failures": total_failures
        })
        
        # Small pause before next concurrency level
        time.sleep(2) 

    print("\n" + "=" * 50)
    print("Stress Test Summary:")
    for res in results_summary:
        print(f"  Concurrency: {res['concurrency']:2d}, Time: {res['time_taken']:.2f}s, RPS: {res['throughput']:.2f}, Success: {res['successes']}, Fail: {res['failures']}")
    print("=" * 50)

