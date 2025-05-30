# filter_worker_rabbit.py
import pika
import time
import re
import signal
import os
import json
import random

RABBITMQ_HOST = 'localhost'
TASK_QUEUE_NAME = 'filter_task_work_queue'
RESULTS_QUEUE_NAME = 'filter_results_data_queue'

KNOWN_INSULTS = {"stupid", "idiot", "dummy", "moron", "lame", "darn", "heck"} # Lowercased

# --- Graceful shutdown ---
# Global channel for signal handler to attempt stopping consumption
consuming_channel = None
worker_id = os.getpid() # Unique ID for this worker instance

def signal_shutdown(signum, frame):
    global consuming_channel
    print(f"\nWorker {worker_id}: Shutdown signal received...")
    if consuming_channel and consuming_channel.is_open:
        try:
            # Tells RabbitMQ to stop sending messages to this consumer.
            # The current message being processed (if any) should still be acked/nacked.
            # The start_consuming() loop will then typically exit.
            consuming_channel.stop_consuming()
            print(f"Worker {worker_id}: Consumption stopping command sent.")
        except Exception as e:
            print(f"Worker {worker_id}: Error trying to stop consuming: {e}")
    # The main loop's finally block will handle closing the connection.

signal.signal(signal.SIGINT, signal_shutdown)
signal.signal(signal.SIGTERM, signal_shutdown)


def filter_text_logic(original_text, known_insults_set):
    words = re.split(r'(\W+)', original_text)
    censored_words = []
    for word in words:
        if word.lower() in known_insults_set:
            censored_words.append("CENSORED")
        else:
            censored_words.append(word)
    return "".join(censored_words)

def process_message_callback(ch, method, properties, body):
    """Callback executed when a message is received from the task queue."""
    original_text = body.decode()
    print(f"\nWorker {worker_id}: Received task: '{original_text[:50]}...'")

    filtered_text = filter_text_logic(original_text, KNOWN_INSULTS)
    print(f"Worker {worker_id}: Filtered result: '{filtered_text[:50]}...'")

    # Prepare result data
    result_data = {
        "original": original_text,
        "filtered": filtered_text,
        "worker_id": worker_id,
        "timestamp": time.time()
    }
    result_body = json.dumps(result_data)

    try:
        # Publish the filtered result to the results queue
        ch.queue_declare(queue=RESULTS_QUEUE_NAME, durable=True) # Ensures results queue exists
        ch.basic_publish(
            exchange='', # Default exchange
            routing_key=RESULTS_QUEUE_NAME,
            body=result_body,
            properties=pika.BasicProperties(delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE)
        )
        print(f"Worker {worker_id}: Sent filtered result to queue '{RESULTS_QUEUE_NAME}'.")
        
        # Acknowledge the message from the task queue after successful processing AND result publishing
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f"Worker {worker_id}: Task acknowledged.")

    except Exception as e:
        print(f"Worker {worker_id}: Error publishing result or acknowledging task: {e}")
        # Decide on retry logic or nack (negative acknowledgment)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False) # Don't requeue if we can't process result
        print(f"Worker {worker_id}: Task NACKed (not requeued) due to result processing error.")


def main():
    global consuming_channel, worker_id
    connection = None # Initialize to None

    print(f"Filter Worker {worker_id}: Starting...")
    
    while True: # Outer loop for connection retries
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
            consuming_channel = connection.channel()

            # Declare the task queue (workers should also declare it to ensure it exists)
            consuming_channel.queue_declare(queue=TASK_QUEUE_NAME, durable=True)
            # Also declare the results queue that this worker will publish to
            consuming_channel.queue_declare(queue=RESULTS_QUEUE_NAME, durable=True) 
            print(f"Worker {worker_id}: Connected to RabbitMQ. Queues '{TASK_QUEUE_NAME}' and '{RESULTS_QUEUE_NAME}' ready.")

            # Fair dispatch: Don't give more than one message to a worker at a time.
            # The worker will send an ack when it's done.
            consuming_channel.basic_qos(prefetch_count=1)

            consuming_channel.basic_consume(
                queue=TASK_QUEUE_NAME,
                on_message_callback=process_message_callback
                # auto_ack=False by default, which is what we want for manual ack
            )

            print(f"Worker {worker_id}: Waiting for tasks on '{TASK_QUEUE_NAME}'. To exit press CTRL+C")
            consuming_channel.start_consuming() # Blocking call
            
            # If start_consuming() exits (e.g., due to stop_consuming() from signal handler)
            print(f"Worker {worker_id}: Consumption loop finished.")
            break # Exit outer while loop if consumption finished gracefully

        except pika.exceptions.AMQPConnectionError as e:
            print(f"Worker {worker_id}: RabbitMQ Connection Error: {e}. Retrying in 5 seconds...")
            if consuming_channel and consuming_channel.is_open: consuming_channel.close()
            if connection and connection.is_open: connection.close()
            consuming_channel, connection = None, None
            time.sleep(5)
        except KeyboardInterrupt: # Should be caught by signal handler ideally
            print(f"Worker {worker_id}: KeyboardInterrupt received in main loop.")
            break # Exit outer while loop
        except Exception as e:
            print(f"Worker {worker_id}: An unexpected error occurred in main loop: {e}. Retrying in 5s...")
            if consuming_channel and consuming_channel.is_open: consuming_channel.close()
            if connection and connection.is_open: connection.close()
            consuming_channel, connection = None, None
            time.sleep(5)
        finally:
            if consuming_channel and consuming_channel.is_open:
                consuming_channel.close()
            if connection and connection.is_open:
                connection.close()
            print(f"Worker {worker_id}: Connection closed in finally block.")
    
    print(f"Filter Worker {worker_id}: Exited.")

if __name__ == "__main__":
    main()
