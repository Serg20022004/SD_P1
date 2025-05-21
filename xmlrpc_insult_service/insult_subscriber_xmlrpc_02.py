# insult_subscriber_xmlrpc.py

from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler
import xmlrpc.client
import threading 
import time # For sleep

class SubscriberRequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)

class InsultNotificationHandler:
    def receive_insult_notification(self, insult_string):
        print(f"\n[SUBSCRIBER] Received insult notification: '{insult_string}'")
        return "Notification received."

def run_subscriber_server(host="127.0.0.1", port=9002): # Bind subscriber server to 127.0.0.1
    server_address = (host, port)
    server = SimpleXMLRPCServer(server_address, requestHandler=SubscriberRequestHandler, allow_none=True)
    server.register_introspection_functions()
    server.register_instance(InsultNotificationHandler())
    
    print(f"Subscriber XMLRPC Server listening on {host}:{port}/RPC2...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nSubscriber server shutting down.")
        server.server_close()

def register_with_main_server(subscriber_url, main_server_url="http://127.0.0.1:8000/RPC2"):
    try:
        main_server_proxy = xmlrpc.client.ServerProxy(main_server_url)
        response = main_server_proxy.register_subscriber(subscriber_url)
        print(f"Registration response from main server: {response}")
    except ConnectionRefusedError:
        print(f"Connection refused. Is the main Insult Server running at {main_server_url}?")
    except Exception as e:
        print(f"Error registering subscriber: {e}")

if __name__ == "__main__":
    subscriber_host = "127.0.0.1" # Subscriber listens on 127.0.0.1
    subscriber_port = 9002
    my_subscriber_url = f"http://{subscriber_host}:{subscriber_port}/RPC2"

    server_thread = threading.Thread(target=run_subscriber_server, args=(subscriber_host, subscriber_port), daemon=True)
    server_thread.start()
    
    print(f"Subscriber server starting on {my_subscriber_url}...")
    time.sleep(1) 

    register_with_main_server(my_subscriber_url)

    print("Subscriber is active. Press Ctrl+C to stop this subscriber client (and its server).")
    try:
        while server_thread.is_alive():
            server_thread.join(timeout=0.5) 
    except KeyboardInterrupt:
        print("\nShutting down subscriber client...")
