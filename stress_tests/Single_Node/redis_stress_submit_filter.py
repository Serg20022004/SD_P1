import redis
import multiprocessing
import time
import random

# --- Test Configuration ---
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
TASK_QUEUE_NAME = 'filter_work_queue'
TOTAL_REQUESTS = 10000 
CONCURRENCY_LEVELS = [1, 2, 5, 10, 20] 
SAMPLE_TEXTS = [
    "Redis filter: This is a stupid example text with some bad words like idiot.",
    "Redis filter: A perfectly clean and fine statement about a moron.",
    "Redis filter: What a LAME thing to say, you dummy!",
    "Redis filter: This darn computer is so dense and heck is bad and more idiot stuff."
] * 20 # Adjust multiplier for more unique texts

# --- Worker Function (redis_submit_filter_worker) ---
def redis_submit_filter_worker(num_requests_for_this_worker):
    pid = multiprocessing.current_process().pid
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
        r.ping()

        success_count = 0
        failure_count = 0
        
        for _ in range(num_requests_for_this_worker):
            text_to_filter = random.choice(SAMPLE_TEXTS) + f" (process {pid})"
            try:
                r.rpush(TASK_QUEUE_NAME, text_to_filter)
                success_count += 1
            except redis.exceptions.RedisError:
                failure_count += 1
        
        return {"success": success_count, "failure": failure_count}

    except redis.exceptions.ConnectionError:
        return {"success": 0, "failure": num_requests_for_this_worker, "error": "ConnectionError"}
    except Exception:
        return {"success": 0, "failure": num_requests_for_this_worker, "error": "WorkerSetupError"}

# --- Main Test Execution ---
if __name__ == "__main__":
    print(f"Starting Redis InsultFilter 'submit_text' (RPUSH to queue) stress test.")
    print(f"Target Redis: {REDIS_HOST}:{REDIS_PORT}, Queue: {TASK_QUEUE_NAME}")
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
            worker_results = pool.map(redis_submit_filter_worker, requests_per_worker_list)
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
        print(f"  Total Tasks Submitted: {total_successes}")
        print(f"  Total Failed Submissions: {total_failures}")
        print(f"  Throughput: {throughput:.2f} tasks/sec")
        
        results_summary.append({
            "concurrency": concurrency, "time_taken": total_time_taken,
            "throughput": throughput, "successes": total_successes, "failures": total_failures
        })
        time.sleep(1) 

    print("\n" + "=" * 50)
    print("Stress Test Summary (Redis - Submit Filter Task):")
    for res in results_summary:
        print(f"  Concurrency: {res['concurrency']:2d}, Time: {res['time_taken']:.2f}s, RPS: {res['throughput']:.2f}, Success: {res['successes']}, Fail: {res['failures']}")
    print("=" * 50)
