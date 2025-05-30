# insult_processor_rabbit.py
import pika
import time
import random
import threading
import signal
import sys 

RABBITMQ_HOST = 'localhost'
ADD_INSULT_QUEUE_NAME = 'add_insult_queue' # For receiving new insults
BROADCAST_EXCHANGE_NAME = 'insult_broadcast_exchange' # Fanout for broadcasting

# In-memory store for unique insults
_insults_set = set()
_insults_lock = threading.Lock() # To protect _insults_set

_broadcaster_active = True
_consumer_channel = None # Make it accessible for shutdown

def add_insult_callback(ch, method, properties, body):
    """Called when a new insult is received on ADD_INSULT_QUEUE_NAME."""
    insult_text = body.decode()
    with _insults_lock:
        if insult_text not in _insults_set:
            _insults_set.add(insult_text)
            print(f"[Processor] Added insult: '{insult_text}'. Total: {len(_insults_set)}")
        else:
            print(f"[Processor] Insult '{insult_text}' already exists.")
    ch.basic_ack(delivery_tag=method.delivery_tag)

def start_consuming_new_insults():
    """Connects and starts consuming messages to add insults."""
    global _consumer_channel
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        _consumer_channel = connection.channel()
        _consumer_channel.queue_declare(queue=ADD_INSULT_QUEUE_NAME, durable=True)
        _consumer_channel.basic_qos(prefetch_count=1)
        _consumer_channel.basic_consume(queue=ADD_INSULT_QUEUE_NAME, on_message_callback=add_insult_callback)
        
        print(f"[Processor] Waiting for insults on queue '{ADD_INSULT_QUEUE_NAME}'.")
        _consumer_channel.start_consuming() # Blocking call
    except pika.exceptions.AMQPConnectionError as e:
        print(f"[Processor Consumer] AMQP Connection Error: {e}. Retrying in 5s...")
        time.sleep(5)
        start_consuming_new_insults() # Simple retry
    except Exception as e:
        print(f"[Processor Consumer] Unexpected error: {e}")
    finally:
        if _consumer_channel and _consumer_channel.is_open:
            _consumer_channel.close()
        if connection and connection.is_open:
            connection.close()
        print("[Processor Consumer] Connection closed.")


def periodic_broadcaster():
    """Periodically fetches a random insult and publishes it to a fanout exchange."""
    global _broadcaster_active
    connection = None
    channel = None

    while _broadcaster_active:
        try:
            if not connection or connection.is_closed:
                connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
                channel = connection.channel()
                channel.exchange_declare(exchange=BROADCAST_EXCHANGE_NAME, exchange_type='fanout')
                print(f"[Broadcaster] Connected and exchange '{BROADCAST_EXCHANGE_NAME}' declared.")

            insult_to_send = None
            with _insults_lock:
                if _insults_set:
                    insult_to_send = random.choice(list(_insults_set))
            
            if insult_to_send and channel and channel.is_open:
                channel.basic_publish(
                    exchange=BROADCAST_EXCHANGE_NAME,
                    routing_key='', # Ignored for fanout
                    body=insult_to_send,
                    properties=pika.BasicProperties(delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE)
                )
                print(f"[Broadcaster] Sent: '{insult_to_send}'")
            # else:
                # print("[Broadcaster] No insults to send or channel not ready.")
            
            # Sleep for 5 seconds, but check _broadcaster_active more often
            for _ in range(50): # 50 * 0.1s = 5s
                if not _broadcaster_active:
                    break
                time.sleep(0.1)

        except pika.exceptions.AMQPConnectionError as e:
            print(f"[Broadcaster] AMQP Connection Error: {e}. Retrying in 5s...")
            if channel and channel.is_open: channel.close()
            if connection and connection.is_open: connection.close()
            connection, channel = None, None # Reset for re-connection
            time.sleep(5)
        except Exception as e:
            print(f"[Broadcaster] Unexpected error: {e}. Retrying in 5s...")
            if channel and channel.is_open: channel.close()
            if connection and connection.is_open: connection.close()
            connection, channel = None, None
            time.sleep(5)
            
    if channel and channel.is_open: channel.close()
    if connection and connection.is_open: connection.close()
    print("[Broadcaster] Stopped and connection closed.")


def signal_shutdown(signum, frame):
    global _broadcaster_active, _consumer_channel
    print("\n[Processor] Shutdown signal received...")
    _broadcaster_active = False # Signal broadcaster thread to stop
    
    if _consumer_channel and _consumer_channel.is_open:
        print("[Processor] Attempting to stop insult consumer...")
        _consumer_channel.stop_consuming() # This should make start_consuming() return
    # The consumer thread will then clean up its own connection in its finally block.
    # The broadcaster thread will exit its loop and clean up its connection.
    # sys.exit(0) # Might be too abrupt if threads need cleanup. Let them exit.

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_shutdown)
    signal.signal(signal.SIGTERM, signal_shutdown)

    print("[Processor] Starting Insult Processor...")

    # Start the broadcaster in a separate thread
    broadcaster_thread = threading.Thread(target=periodic_broadcaster, daemon=True)
    broadcaster_thread.start()

    # Start the consumer for new insults in the main thread (it's blocking)
    # This will keep the main script alive.
    start_consuming_new_insults()
    
    # Wait for broadcaster thread to finish if it hasn't already
    if broadcaster_thread.is_alive():
        print("[Processor] Main consumer loop exited, waiting for broadcaster thread...")
        broadcaster_thread.join(timeout=5) # Wait for up to 5s

    print("[Processor] Shutdown complete.")
