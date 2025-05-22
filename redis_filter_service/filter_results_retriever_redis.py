# filter_results_retriever_redis.py
import redis
import json
import time

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
RESULTS_LIST_NAME = 'filtered_texts_results'

def main():
    try:
        # Using decode_responses=True to get strings from Redis
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
        print(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
    except redis.exceptions.ConnectionError as e:
        print(f"Error: Could not connect to Redis: {e}")
        return

    try:
        # LRANGE results_list_name 0 -1  (gets all elements)
        print(f"\n--- Retrieving All Filtered Results from '{RESULTS_LIST_NAME}' ---")
        raw_results = r.lrange(RESULTS_LIST_NAME, 0, -1)

        if not raw_results:
            print("No filtered results found in the list.")
            return

        print(f"Found {len(raw_results)} results:")
        for i, raw_item in enumerate(raw_results):
            try:
                item = json.loads(raw_item) # Decode JSON string back to dictionary
                print(f"\nResult {i+1}:")
                print(f"  Original : '{item.get('original', 'N/A')}'")
                print(f"  Filtered : '{item.get('filtered', 'N/A')}'")
                print(f"  Worker ID: {item.get('worker_id', 'N/A')}")
                print(f"  Timestamp: {time.ctime(item.get('timestamp', 0))}")
            except json.JSONDecodeError:
                print(f"  Could not decode result item: {raw_item}")
            except Exception as e:
                print(f"  Error processing result item '{raw_item}': {e}")
                
    except Exception as e:
        print(f"An error occurred while retrieving results: {e}")

if __name__ == "__main__":
    main()
