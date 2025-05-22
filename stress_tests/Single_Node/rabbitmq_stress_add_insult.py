import pika
import multiprocessing
import time
import random

# --- Test Configuration ---
RABBITMQ_HOST = 'localhost'
ADD_INSULT_QUEUE_NAME = 'add_insult_queue' # Queue listened to by insult_processor_rabbit.py
TOTAL_REQUESTS = 10000
CONCURRENCY_LEVELS = [1, 2, 5, 10, 20, 50]
SAMPLE_INSULTS = [f"RabbitMQ insult {i} for stress test!" for i in range(100)]

# --- Worker Function ---
def rabbitmq_add_insult_worker(num_requests_for_this_worker):
    pid = multiprocessing.current_process().pid
    connection = None
    try:
        # Each process creates its own connection and channel
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        channel = connection.channel()
        # Producer should declare the queue to ensure it exists; durable to match processor.
        channel.queue_declare(queue=ADD_INSULT_QUEUE_NAME, durable=True)

        success_count = 0
        failure_count = 0
        
        for i in range(num_requests_for_this_worker):
            insult_to_send = random.choice(SAMPLE_INSULTS) + f" (req {i} by {pid})"
            try:
                channel.basic_publish(
                    exchange='', # Default exchange
                    routing_key=ADD_INSULT_QUEUE_NAME,
                    body=insult_to_send,
                    properties=pika.BasicProperties(
                        delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE,
                    )
                )
                success_count += 1
            except pika.exceptions.AMQPConnectionError: # More specific error
                failure_count += 1
                # Attempt to reconnect (simplified for stress test worker)
                try:
                    if connection and connection.is_open: connection.close()
                    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
                    channel = connection.channel()
                    channel.queue_declare(queue=ADD_INSULT_QUEUE_NAME, durable=True)
                except: # If reconnect fails, continue failing this worker's requests
                    pass 
            except Exception:
                failure_count += 1
        
        return {"success": success_count, "failure": failure_count}

    except pika.exceptions.AMQPConnectionError:
        return {"success": 0, "failure": num_requests_for_this_worker, "error": "AMQPConnectionError"}
    except Exception as e:
        return {"success": 0, "failure": num_requests_for_this_worker, "error": str(type(e).__name__)}
    finally:
        if connection and connection.is_open:
            connection.close()

# --- Main Test Execution ---
if __name__ == "__main__":
    print(f"Starting RabbitMQ InsultService 'add_insult' (publish to queue) stress test.")
    print(f"Target RabbitMQ: {RABBITMQ_HOST}, Queue: {ADD_INSULT_QUEUE_NAME}")
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
            worker_results = pool.map(rabbitmq_add_insult_worker, requests_per_worker_list)
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
        print(f"  Total Successful Messages Sent: {total_successes}")
        print(f"  Total Failed Messages: {total_failures}")
        print(f"  Throughput: {throughput:.2f} messages/sec")
        
        results_summary.append({
            "concurrency": concurrency, "time_taken": total_time_taken,
            "throughput": throughput, "successes": total_successes, "failures": total_failures
        })
        time.sleep(2)

    print("\n" + "=" * 50)
    print("Stress Test Summary (RabbitMQ - Add Insult):")
    for res in results_summary:
        print(f"  Concurrency: {res['concurrency']:2d}, Time: {res['time_taken']:.2f}s, RPS: {res['throughput']:.2f}, Success: {res['successes']}, Fail: {res['failures']}")
    print("=" * 50)
