# filter_producer_rabbit.py (Modified for variable load)
import pika
import sys
import time
import random

RABBITMQ_HOST = 'localhost'
TASK_QUEUE_NAME = 'filter_task_work_queue'

SAMPLE_TEXTS = [
    "Dynamic load: This is a stupid example text.",
    "Dynamic load: Another LAME example from a moron for testing.",
    "Dynamic load: A clean text here for a bit.",
    "Dynamic load: heck this is a test of the darn system."
] * 50

def send_batch(channel, num_messages, batch_name="Batch"):
    print(f"\nProducer: Sending {batch_name} of {num_messages} messages...")
    for i in range(num_messages):
        text_content = random.choice(SAMPLE_TEXTS) + f" msg_{i}"
        channel.basic_publish(
            exchange='', routing_key=TASK_QUEUE_NAME, body=text_content,
            properties=pika.BasicProperties(delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE)
        )
        if (i + 1) % 100 == 0: # Print progress for large batches
            print(f"  Producer ({batch_name}): Sent {i+1}/{num_messages}...")
    print(f"Producer ({batch_name}): Finished sending {num_messages} messages.")

def main():
    connection = None
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        channel = connection.channel()
        channel.queue_declare(queue=TASK_QUEUE_NAME, durable=True)
        print(f"Producer: Connected to RabbitMQ, queue '{TASK_QUEUE_NAME}' ready.")

        # Scenario: Burst, Pause, Smaller Burst, Pause, Steady Load
        
        # Burst 1
        send_batch(channel, 3000, "Burst 1") # Approx 3000 / 50rps_est_lambda = 60s of work if lambda=50
        
        print("\nProducer: Pausing for 30 seconds (low load period)...")
        time.sleep(30)
        
        # Burst 2
        send_batch(channel, 6000, "Burst 2") # Approx 120s
        
        print("\nProducer: Pausing for 20 seconds (low load period)...")
        time.sleep(20)

        # Steady load
        print("\nProducer: Starting steady load (100 msgs every 2s for 60s)...")
        for _ in range(30): # 30 * 2s = 60s
            send_batch(channel, 100, "Steady Batch") 
            time.sleep(2)


        print("\nProducer: All tasks for scenario sent.")

    except pika.exceptions.AMQPConnectionError as e:
        print(f"Producer Error: Could not connect or publish to RabbitMQ: {e}")
    except KeyboardInterrupt:
        print("\nProducer: Interrupted.")
    except Exception as e:
        print(f"Producer: An unexpected error occurred: {e}")
    finally:
        if connection and connection.is_open:
            connection.close()
            print("Producer: Connection closed.")

if __name__ == '__main__':
    main()
