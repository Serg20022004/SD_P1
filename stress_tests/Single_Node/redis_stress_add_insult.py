import redis
import multiprocessing
import time
import random

# --- Test Configuration ---
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
INSULTS_SET_KEY = 'insults_set' # Key used by InsultService (broadcaster)
TOTAL_REQUESTS = 10000
CONCURRENCY_LEVELS = [1, 2, 5, 10, 20, 50] # Can often handle more
SAMPLE_INSULTS = [f"Redis insult {i} stress test!" for i in range(100)]

# --- Worker Function ---
def redis_add_insult_worker(num_requests_for_this_worker):
    pid = multiprocessing.current_process().pid
    try:
        # Each process creates its own Redis connection
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
        r.ping() # Check connection

        success_count = 0 # SADD returns 1 if new, 0 if exists; both are "successful" operations
        failure_count = 0
        
        for i in range(num_requests_for_this_worker):
            insult_to_send = random.choice(SAMPLE_INSULTS) + f" (req {i} by {pid})"
            try:
                r.sadd(INSULTS_SET_KEY, insult_to_send)
                success_count += 1 
            except redis.exceptions.RedisError:
                failure_count += 1
        
        return {"success": success_count, "failure": failure_count}

    except redis.exceptions.ConnectionError:
        return {"success": 0, "failure": num_requests_for_this_worker, "error": "ConnectionError"}
    except Exception as e:
        return {"success": 0, "failure": num_requests_for_this_worker, "error": str(type(e).__name__)}

# --- Main Test Execution ---
if __name__ == "__main__":
    print(f"Starting Redis InsultService 'add_insult' (direct SADD) stress test.")
    print(f"Target Redis: {REDIS_HOST}:{REDIS_PORT}, Key: {INSULTS_SET_KEY}")
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
            worker_results = pool.map(redis_add_insult_worker, requests_per_worker_list)
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
        print(f"  Total Successful Operations: {total_successes}")
        print(f"  Total Failed Operations: {total_failures}")
        print(f"  Throughput: {throughput:.2f} ops/sec")
        
        results_summary.append({
            "concurrency": concurrency, "time_taken": total_time_taken,
            "throughput": throughput, "successes": total_successes, "failures": total_failures
        })
        time.sleep(2)

    print("\n" + "=" * 50)
    print("Stress Test Summary (Redis - Add Insult):")
    for res in results_summary:
        print(f"  Concurrency: {res['concurrency']:2d}, Time: {res['time_taken']:.2f}s, RPS: {res['throughput']:.2f}, Success: {res['successes']}, Fail: {res['failures']}")
    print("=" * 50)
