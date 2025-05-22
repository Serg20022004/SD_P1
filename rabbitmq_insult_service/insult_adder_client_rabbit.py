# insult_adder_client_rabbit.py
import pika
import sys
import time

RABBITMQ_HOST = 'localhost'
ADD_INSULT_QUEUE_NAME = 'add_insult_queue' # Must match processor's queue

def main():
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        channel = connection.channel()

        # Declare the queue: this ensures it exists.
        # The processor also declares it as durable.
        channel.queue_declare(queue=ADD_INSULT_QUEUE_NAME, durable=True)

        default_insults = [
            "Your code is so messy, it looks like a spaghetti factory exploded.",
            "Are you always this stupid, or is today a special occasion?",
            "I'd explain it to you, but I don't have any crayons.",
            "Your code is so messy, it looks like a spaghetti factory exploded." # Duplicate
        ]
        
        insults_to_send = default_insults
        if len(sys.argv) > 1:
            insults_to_send = sys.argv[1:]
            print(f"Sending insults from command line arguments...")
        else:
            print(f"Sending default insults...")

        for insult_text in insults_to_send:
            channel.basic_publish(
                exchange='', # Default exchange
                routing_key=ADD_INSULT_QUEUE_NAME, # Name of the queue
                body=insult_text,
                properties=pika.BasicProperties(
                    delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE, # Make message persistent
                )
            )
            print(f" [x] Sent '{insult_text}' to queue '{ADD_INSULT_QUEUE_NAME}'")
            time.sleep(0.05) # Tiny pause

        connection.close()
        print("All insults sent and connection closed.")

    except pika.exceptions.AMQPConnectionError as e:
        print(f"Error: Could not connect to RabbitMQ at {RABBITMQ_HOST} - {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    main()
