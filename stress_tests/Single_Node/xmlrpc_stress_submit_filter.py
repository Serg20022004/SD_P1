import xmlrpc.client
import multiprocessing
import time
import random

# --- Test Configuration ---
XMLRPC_FILTER_SERVER_URL = "http://127.0.0.1:8001/RPC2"
TOTAL_REQUESTS = 10000 
CONCURRENCY_LEVELS = [1, 2, 5, 10, 20] 
SAMPLE_TEXTS = [
    "This is a stupid example text with some bad words like idiot.",
    "A perfectly clean and fine statement about a moron.",
    "What a LAME thing to say, you dummy!",
    "This darn computer is so dense and heck is bad and more idiot stuff is not good.",
    "The quick brown fox jumps over the lazy dog."
] * 20 

# --- Worker Function ---
def xmlrpc_submit_filter_worker(num_requests_for_this_worker):
    pid = multiprocessing.current_process().pid
    try:
        server_proxy = xmlrpc.client.ServerProxy(XMLRPC_FILTER_SERVER_URL, allow_none=True)
        success_count = 0
        failure_count = 0
        
        for _ in range(num_requests_for_this_worker):
            text_to_filter = random.choice(SAMPLE_TEXTS) + f" (process {pid})"
            try:
                response = server_proxy.submit_text_for_filtering(text_to_filter)
                # Assuming a simple string response indicating submission
                if isinstance(response, str) and "submitted successfully" in response:
                    success_count += 1
                else:
                    failure_count += 1
            except Exception:
                failure_count += 1
        
        return {"success": success_count, "failure": failure_count}
    except Exception:
        return {"success": 0, "failure": num_requests_for_this_worker, "error": "WorkerConnectionOrSetupError"}

# --- Main Test Execution ---
if __name__ == "__main__":
    print(f"Starting XMLRPC InsultFilter 'submit_text' stress test.")
    print(f"Target Server: {XMLRPC_FILTER_SERVER_URL}")
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
            worker_results = pool.map(xmlrpc_submit_filter_worker, requests_per_worker_list)
        end_time = time.perf_counter()
        total_time_taken = end_time - start_time

        total_successes = sum(r.get("success", 0) for r in worker_results)
        total_failures = sum(r.get("failure", 0) for r in worker_results)
        
        for r in worker_results:
            if "error" in r:
                print(f"  Worker reported error: {r['error']}")

        throughput = (total_successes / total_time_taken) if total_time_taken > 0 else float('inf')

        print(f"  Concurrency: {concurrency}")
        print(f"  Total Time Taken: {total_time_taken:.4f} seconds")
        print(f"  Total Successful Submissions: {total_successes}")
        print(f"  Total Failed Submissions: {total_failures}")
        print(f"  Throughput: {throughput:.2f} submissions/sec")
        
        results_summary.append({
            "concurrency": concurrency, "time_taken": total_time_taken,
            "throughput": throughput, "successes": total_successes, "failures": total_failures
        })
        time.sleep(2)

    print("\n" + "=" * 50)
    print("Stress Test Summary (XMLRPC - Submit Filter Text):")
    for res in results_summary:
        print(f"  Concurrency: {res['concurrency']:2d}, Time: {res['time_taken']:.2f}s, RPS: {res['throughput']:.2f}, Success: {res['successes']}, Fail: {res['failures']}")
    print("=" * 50)
