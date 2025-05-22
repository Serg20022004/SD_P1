# filter_results_collector_rabbit.py
import pika
import sys
import signal
import json
import time # For ctime

RABBITMQ_HOST = 'localhost'
RESULTS_QUEUE_NAME = 'filter_results_data_queue'

# Global channel for signal handler
consuming_channel = None

def signal_shutdown(signum, frame):
    global consuming_channel
    print("\n[Collector] Shutdown signal received...")
    if consuming_channel and consuming_channel.is_open:
        try:
            consuming_channel.stop_consuming()
            print("[Collector] Consumption stopping command sent.")
        except Exception as e:
            print(f"[Collector] Error stopping consumption: {e}")

signal.signal(signal.SIGINT, signal_shutdown)
signal.signal(signal.SIGTERM, signal_shutdown)

def display_result_callback(ch, method, properties, body):
    try:
        result_data_str = body.decode()
        result_data = json.loads(result_data_str) # Parse JSON string
        
        print("\n--- Filtered Result Received ---")
        print(f"  Original : '{result_data.get('original', 'N/A')}'")
        print(f"  Filtered : '{result_data.get('filtered', 'N/A')}'")
        print(f"  Worker ID: {result_data.get('worker_id', 'N/A')}")
        print(f"  Timestamp: {time.ctime(result_data.get('timestamp', 0))}")
        
        ch.basic_ack(delivery_tag=method.delivery_tag) # Acknowledge received result
    except json.JSONDecodeError:
        print(f"[Collector] Error: Could not decode JSON from results queue: {body.decode()}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False) # Discard malformed message
    except Exception as e:
        print(f"[Collector] Error processing result message: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False) # Discard on other errors


def main():
    global consuming_channel
    connection = None
    print(f"Results Collector: Starting... Listening to queue '{RESULTS_QUEUE_NAME}'.")

    while True: # Connection retry loop
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
            consuming_channel = connection.channel()

            # Declare the results queue (durable, as workers publish to it)
            consuming_channel.queue_declare(queue=RESULTS_QUEUE_NAME, durable=True)
            print(f"Collector: Connected to RabbitMQ. Queue '{RESULTS_QUEUE_NAME}' ready.")
            
            consuming_channel.basic_qos(prefetch_count=1) # Process one result at a time
            consuming_channel.basic_consume(
                queue=RESULTS_QUEUE_NAME,
                on_message_callback=display_result_callback
                # auto_ack=False by default
            )

            print("Collector: Waiting for filtered results. To exit press CTRL+C")
            consuming_channel.start_consuming()
            
            print("Collector: Consumption loop finished.") # If stop_consuming was called
            break 

        except pika.exceptions.AMQPConnectionError as e:
            print(f"Collector: RabbitMQ Connection Error: {e}. Retrying in 5 seconds...")
            if consuming_channel and consuming_channel.is_open: consuming_channel.close()
            if connection and connection.is_open: connection.close()
            consuming_channel, connection = None, None
            time.sleep(5)
        except KeyboardInterrupt:
            print("\nCollector: KeyboardInterrupt received.")
            break
        except Exception as e:
            print(f"Collector: An unexpected error occurred: {e}. Retrying in 5s...")
            if consuming_channel and consuming_channel.is_open: consuming_channel.close()
            if connection and connection.is_open: connection.close()
            consuming_channel, connection = None, None
            time.sleep(5)
        finally:
            if consuming_channel and consuming_channel.is_open:
                consuming_channel.close()
            if connection and connection.is_open:
                connection.close()
            print("Collector: Connection closed in finally block.")
            
    print("Results Collector: Exited.")

if __name__ == '__main__':
    main()
