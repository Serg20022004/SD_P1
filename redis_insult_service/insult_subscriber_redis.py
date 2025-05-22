# insult_subscriber_redis.py
import redis
import signal # For graceful shutdown

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
BROADCAST_CHANNEL = 'insult_broadcast_channel'

# --- Graceful shutdown handling ---
# Global pubsub object to close it on shutdown
pubsub_client = None
shutdown_flag = False

def signal_handler(signum, frame):
    global shutdown_flag
    print("\nShutdown signal received, unsubscribing and exiting...")
    shutdown_flag = True
    if pubsub_client:
        try:
            pubsub_client.unsubscribe() # Unsubscribe from all channels
            # pubsub_client.close() # For older versions or if explicitly managing connection
            # In modern redis-py, the thread running listen() might need a different stop mechanism
            # Often, letting the loop break via shutdown_flag is enough, 
            # and the connection pool handles the rest.
            # If listen() blocks hard, setting a timeout on pubsub.listen() or using pubsub.get_message(timeout=...)
            # in a loop would be more robust for interruption.
        except Exception as e:
            print(f"Error during pubsub cleanup: {e}")


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def listen_for_insults():
    global pubsub_client # To allow signal_handler to access it
    print(f"Insult Subscriber started. Listening to channel '{BROADCAST_CHANNEL}'. Press Ctrl+C to stop.")
    
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
        pubsub_client = r.pubsub()
        pubsub_client.subscribe(BROADCAST_CHANNEL)
        
        print(f"Subscribed to '{BROADCAST_CHANNEL}'. Waiting for insults...")
        
        # listen() is a generator that blocks until a message arrives or an error.
        # To make it interruptible by shutdown_flag, we'd typically use get_message in a loop.
        # For simplicity aligned with the example `subscriber.py`, let's keep `listen()`
        # and rely on the fact that Ctrl+C will raise KeyboardInterrupt eventually,
        # or the signal handler might break out if listen() releases.
        # A more robust interrupt for listen() might involve pubsub.run_in_thread(sleep_time=0.1)
        # and then checking shutdown_flag in the main thread.
        
        # Simpler approach based on example:
        for message in pubsub_client.listen(): # This will block
            if shutdown_flag: # Check flag if listen() yields for any reason (e.g. unsubscribe)
                break
            if message and message['type'] == 'message':
                print(f"\n[SUBSCRIBER] >>> Received Insult: {message['data']}")
            elif message and message['type'] == 'subscribe':
                print(f"(Subscribed to channel: {message['channel'].decode() if isinstance(message['channel'], bytes) else message['channel']})")
            # Handle 'unsubscribe' if needed, or other message types

    except redis.exceptions.ConnectionError as e:
        if not shutdown_flag: # Avoid printing error if shutdown was intended
            print(f"Subscriber Error: Could not connect to Redis at {REDIS_HOST}:{REDIS_PORT} - {e}")
    except KeyboardInterrupt: # listen() can be interrupted by Ctrl+C
        print("\nSubscriber: KeyboardInterrupt caught, exiting.")
    except Exception as e:
        if not shutdown_flag:
            print(f"Subscriber: An unexpected error occurred: {e}")
    finally:
        print("Insult Subscriber is shutting down.")
        if pubsub_client:
            try:
                pubsub_client.unsubscribe()
                # pubsub_client.close() # As mentioned, often not strictly needed
            except Exception as e:
                print(f"Error during final pubsub cleanup: {e}")


if __name__ == "__main__":
    listen_for_insults()
