# filter_worker_redis.py
import redis
import time
import re
import signal
import os # For worker ID
import json # For storing structured results
import random

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
TASK_QUEUE_NAME = 'filter_work_queue'     # Queue to get tasks from
RESULTS_LIST_NAME = 'filtered_texts_results' # List to store results

KNOWN_INSULTS = {"stupid", "idiot", "dummy", "moron", "lame", "darn", "heck"} # Lowercased

# --- Shutdown ---
shutdown_flag = False
def signal_handler(signum, frame):
    global shutdown_flag
    print(f"\nWorker {os.getpid()}: Shutdown signal received, stopping...")
    shutdown_flag = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def filter_text_logic(original_text, known_insults_set):
    """The actual filtering logic."""
    words = re.split(r'(\W+)', original_text) # Splits the sentences into individual words for procecssing
    censored_words = []
    for word in words:
        if word.lower() in known_insults_set:
            censored_words.append("CENSORED")
        else:
            censored_words.append(word)
    return "".join(censored_words)

def main():
    worker_id = os.getpid() # Get process ID for unique worker identification
    print(f"Filter Worker {worker_id}: Starting...")
    
    try:
        # Using decode_responses=True for receiving strings
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
        print(f"Worker {worker_id}: Connected to Redis. Waiting for tasks on '{TASK_QUEUE_NAME}'.")
    except redis.exceptions.ConnectionError as e:
        print(f"Worker {worker_id}: Error connecting to Redis: {e}. Exiting.")
        return

    while not shutdown_flag:
        try:
            # BLPOP from task queue (Blocking Left Pop)
            # Returns a tuple: (queue_name, task_data) or None if timeout occurs
            # timeout=0 means block indefinitely. Use a small timeout to check shutdown_flag.
            task_tuple = r.blpop(TASK_QUEUE_NAME, timeout=1) 

            if task_tuple:
                queue_name, original_text = task_tuple
                print(f"\nWorker {worker_id}: Received task from '{queue_name}': '{original_text[:50]}...'")
                
                # Simulate some processing time
                time.sleep(random.uniform(0.5, 2.0)) 
                
                filtered_text = filter_text_logic(original_text, KNOWN_INSULTS)
                print(f"Worker {worker_id}: Filtered result: '{filtered_text[:50]}...'")

                # Store structured result in the results list
                result_data = {
                    "original": original_text,
                    "filtered": filtered_text,
                    "worker_id": worker_id,
                    "timestamp": time.time()
                }
                # Use rpush to add to the results list. Encode to JSON string.
                r.rpush(RESULTS_LIST_NAME, json.dumps(result_data))
                print(f"Worker {worker_id}: Stored result to '{RESULTS_LIST_NAME}'.")
            # else:
                # print(f"Worker {worker_id}: No task received (timeout).") # Can be noisy
                
        except redis.exceptions.ConnectionError as e:
            print(f"Worker {worker_id}: Redis connection error: {e}. Retrying in 5s...")
            time.sleep(5)
            # Re-establish connection (simplified)
            try:
                r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
                print(f"Worker {worker_id}: Reconnected to Redis.")
            except redis.exceptions.ConnectionError:
                print(f"Worker {worker_id}: Failed to reconnect. Will try again.")
        except Exception as e:
            if not shutdown_flag: # Avoid error message if we are shutting down
                print(f"Worker {worker_id}: An unexpected error occurred: {e}")
                time.sleep(1) # Brief pause before continuing loop

    print(f"Filter Worker {worker_id}: Exiting.")

if __name__ == "__main__":
    main()
