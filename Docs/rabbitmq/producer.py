import pika

# Connect to RabbitMQ
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

# Declare a queue
channel.queue_declare(queue='hello')

# Publish a message
channel.basic_publish(exchange='', routing_key='hello', body='Hello, RabbitMQ!')
print(" [x] Sent 'Hello, RabbitMQ!'")

# Close connection
connection.close()
