# filter_producer_rabbit.py
import pika
import sys
import time

RABBITMQ_HOST = 'localhost'
TASK_QUEUE_NAME = 'filter_task_work_queue'

def main():
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        channel = connection.channel()

        # Declare a durable queue for tasks
        # The worker will also declare this queue to ensure it exists.
        channel.queue_declare(queue=TASK_QUEUE_NAME, durable=True)
        print(f"Producer: Connected to RabbitMQ and queue '{TASK_QUEUE_NAME}' is ready.")

    except pika.exceptions.AMQPConnectionError as e:
        print(f"Producer Error: Could not connect to RabbitMQ: {e}")
        return
    except Exception as e:
        print(f"Producer Error: An unexpected error occurred during setup: {e}")
        return

    default_texts = [
        "This is a stupid example text with some bad words like idiot.",
        "A perfectly clean and fine statement.",
        "What a LAME thing to say, you moron!",
        "This darn computer is so dense and heck is bad and more idiot stuff."
    ]
    
    texts_to_send = default_texts
    if len(sys.argv) > 1:
        texts_to_send = sys.argv[1:]
        print(f"Producer: Sending texts from command line arguments to queue '{TASK_QUEUE_NAME}'...")
    else:
        print(f"Producer: Sending default texts to queue '{TASK_QUEUE_NAME}'...")

    for i, text_content in enumerate(texts_to_send):
        try:
            channel.basic_publish(
                exchange='', # Default exchange
                routing_key=TASK_QUEUE_NAME, # Name of the queue
                body=text_content,
                properties=pika.BasicProperties(
                    delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE, # Make message persistent
                )
            )
            print(f"  [x] Sent task ({i+1}): '{text_content[:50]}...'")
            time.sleep(0.2) # Small delay
        except Exception as e:
            print(f"    Producer Error sending task '{text_content[:50]}...': {e}")
            # Attempt to re-establish connection if it dropped
            try:
                if not connection or connection.is_closed:
                    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
                    channel = connection.channel()
                    channel.queue_declare(queue=TASK_QUEUE_NAME, durable=True)
                    print("Producer: Reconnected to RabbitMQ.")
            except Exception as recon_e:
                print(f"Producer: Failed to reconnect: {recon_e}. Skipping message.")
                break # Exit loop if reconnect fails

    try:
        if connection and connection.is_open:
            connection.close()
            print("Producer: All tasks sent and connection closed.")
    except Exception as e:
        print(f"Producer Error closing connection: {e}")


if __name__ == '__main__':
    main()
