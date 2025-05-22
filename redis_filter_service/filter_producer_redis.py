# filter_producer_redis.py
import redis
import time
import sys

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
TASK_QUEUE_NAME = 'filter_work_queue'

def main():
    try:
        # Using decode_responses=True, so send/receive strings directly
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
        print(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
    except redis.exceptions.ConnectionError as e:
        print(f"Error: Could not connect to Redis: {e}")
        return

    texts_to_send = [
        "This is a stupid example text with some bad words like idiot.",
        "A perfectly clean and fine statement.",
        "What a LAME thing to say, you moron!",
        "This darn computer is so dense and heck is bad."
    ]

    if len(sys.argv) > 1:
        texts_to_send = sys.argv[1:]
        print(f"Sending texts from command line arguments...")
    else:
        print(f"Sending default texts to filter queue '{TASK_QUEUE_NAME}'...")

    for text_content in texts_to_send:
        try:
            r.rpush(TASK_QUEUE_NAME, text_content) # RPUSH the text string
            print(f"  [x] Sent task: '{text_content[:50]}...'")
            time.sleep(0.5) 
        except Exception as e:
            print(f"    Error sending task '{text_content[:50]}...': {e}")
            
    print("\nAll tasks sent.")

if __name__ == "__main__":
    main()
