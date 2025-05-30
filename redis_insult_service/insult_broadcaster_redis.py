# insult_broadcaster_redis.py
import redis
import time
import random
import signal

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
INSULTS_SET_KEY = 'insults_set'
BROADCAST_CHANNEL = 'insult_broadcast_channel'

# --- Graceful shutdown handling ---
shutdown_flag = False
def signal_handler(signum, frame):
    global shutdown_flag
    print("\nShutdown signal received, stopping broadcaster...")
    shutdown_flag = True

signal.signal(signal.SIGINT, signal_handler)  # Handle Ctrl+C
signal.signal(signal.SIGTERM, signal_handler) # Handle kill

def broadcast_insults():
    print(f"Insult Broadcaster started. Publishing to channel '{BROADCAST_CHANNEL}'. Press Ctrl+C to stop.")
    r_publisher = None # Initialize to None
    try:
        # Connection for reading insults
        r_reader = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
        # Connection for publishing messages
        r_publisher = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

        while not shutdown_flag:
            insult_to_send = None
            try:
                # SRANDMEMBER picks a random element from the set.
                # If the set is empty, it returns None.
                insult_to_send = r_reader.srandmember(INSULTS_SET_KEY)
            except redis.exceptions.RedisError as e:
                print(f"Broadcaster: Error reading from Redis set '{INSULTS_SET_KEY}': {e}")
                time.sleep(5) # Wait before retrying on Redis error
                continue # Skip this broadcast iteration

            if insult_to_send:
                try:
                    # Publish the insult to the channel
                    # PUBLISH returns the number of clients that received the message
                    num_clients = r_publisher.publish(BROADCAST_CHANNEL, insult_to_send)
                    print(f"Broadcasted: '{insult_to_send}' (to {num_clients} subscribers on channel '{BROADCAST_CHANNEL}')")
                except redis.exceptions.RedisError as e:
                     print(f"Broadcaster: Error publishing to Redis channel '{BROADCAST_CHANNEL}': {e}")

            # Wait for 5 seconds before the next broadcast
            # Check shutdown_flag more frequently for responsiveness
            for _ in range(50): # 50 * 0.1s = 5s
                if shutdown_flag:
                    break
                time.sleep(0.1)
        
    except redis.exceptions.ConnectionError as e:
        print(f"Broadcaster Error: Could not connect to Redis at {REDIS_HOST}:{REDIS_PORT} - {e}")
    except Exception as e:
        print(f"Broadcaster: An unexpected error occurred: {e}")
    finally:
        print("Insult Broadcaster is shutting down.")


if __name__ == "__main__":
    broadcast_insults()
