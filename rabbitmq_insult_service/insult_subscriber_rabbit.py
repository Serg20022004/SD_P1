# insult_subscriber_rabbit.py
import pika
import sys
import signal

RABBITMQ_HOST = 'localhost'
BROADCAST_EXCHANGE_NAME = 'insult_broadcast_exchange' # Must match processor's exchange

# Globals for signal handler
connection = None
channel = None
consumer_tag = None # To specifically cancel this consumer

def signal_shutdown(signum, frame):
    global connection, channel, consumer_tag
    print("\n[Subscriber] Shutdown signal received...")
    if channel and channel.is_open and consumer_tag:
        try:
            print(f"[Subscriber] Attempting to cancel consumer (tag: {consumer_tag})...")
            channel.basic_cancel(consumer_tag=consumer_tag)
            # This should ideally make start_consuming() return
        except Exception as e:
            print(f"[Subscriber] Error cancelling consumer: {e}")
            
    # Closing connection will also typically stop consuming if basic_cancel didn't
    # or if start_consuming was interrupted.
    if connection and connection.is_open:
        print("[Subscriber] Closing connection...")
        try:
            connection.close() # This should also make start_consuming() return if it hasn't already.
        except Exception as e:
            print(f"[Subscriber] Error closing connection: {e}")
    print("[Subscriber] Exiting.")
    # sys.exit(0) # Let main's finally block execute if possible

def on_message_callback(ch, method, properties, body):
    insult_message = body.decode()
    print(f"\n[SUBSCRIBER] >>> Received Insult: {insult_message}")
    # No ack needed if auto_ack=True (which is default for fanout examples usually)

def main():
    global connection, channel, consumer_tag # Allow signal handler to access
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        channel = connection.channel()

        channel.exchange_declare(exchange=BROADCAST_EXCHANGE_NAME, exchange_type='fanout')

        # result.method.queue contains the generated queue name
        result = channel.queue_declare(queue='', exclusive=True) 
        queue_name = result.method.queue

        channel.queue_bind(exchange=BROADCAST_EXCHANGE_NAME, queue=queue_name)
        print(f"[Subscriber] Bound queue '{queue_name}' to exchange '{BROADCAST_EXCHANGE_NAME}'.")
        print('[Subscriber] Waiting for insult broadcasts. To exit press CTRL+C')

        # Store the consumer tag to be able to cancel it specifically
        consumer_tag = channel.basic_consume(
            queue=queue_name, 
            on_message_callback=on_message_callback, 
            auto_ack=True
        )
        channel.start_consuming() # Blocking call

    except pika.exceptions.AMQPConnectionError as e:
        print(f"[Subscriber] AMQP Connection Error: {e}")
    except KeyboardInterrupt:
        print("\n[Subscriber] KeyboardInterrupt received.")
    except Exception as e:
        print(f"[Subscriber] Unexpected error: {e}")
    finally:
        print("[Subscriber] Cleaning up and exiting...")
        # Signal handler should ideally have handled most of this if Ctrl+C was used
        # This is a fallback
        if channel and channel.is_open:
            try:
                if consumer_tag and channel.is_consuming: # Check if it's still consuming
                    channel.basic_cancel(consumer_tag)
            except Exception: pass # Ignore errors on cleanup
        if connection and connection.is_open:
            try:
                connection.close()
            except Exception: pass # Ignore errors on cleanup
        print("[Subscriber] Finished cleanup.")


if __name__ == '__main__':
    main()
