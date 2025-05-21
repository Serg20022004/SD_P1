# insult_server_xmlrpc.py

from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler
import threading
import time
import random
from xmlrpc.client import ServerProxy # For calling subscribers

# Restrict to a particular path.
class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)

class InsultService:
    def __init__(self):
        self._insults = set()  # Set to store unique insults
        self._subscribers = set() # Set to store unique subscriber URLs
        self._lock = threading.Lock() # To protect shared resources (insults, subscribers)
        
        # Start the broadcaster thread
        self.broadcaster_thread = threading.Thread(target=self._broadcast_insults, daemon=True)
        self.broadcaster_thread.start()
        print("InsultService initialized and broadcaster thread started.")

    def add_insult(self, insult_string):
        """
        Adds an insult to the list if it's not already present.
        Returns a message indicating success or if the insult already existed.
        """
        with self._lock:
            if not isinstance(insult_string, str):
                return "Error: Insult must be a string."
            if insult_string in self._insults:
                print(f"Attempted to add existing insult: '{insult_string}'")
                return f"Insult '{insult_string}' already exists."
            self._insults.add(insult_string)
            print(f"Added insult: '{insult_string}'")
            return f"Insult '{insult_string}' added successfully."

    def get_insults(self):
        """
        Returns the list of all stored insults.
        """
        with self._lock:
            # XMLRPC might not handle sets directly, so convert to list
            print(f"Retrieving insults. Current count: {len(self._insults)}")
            return list(self._insults)

    def register_subscriber(self, subscriber_url):
        """
        Registers a subscriber URL to receive periodic insult notifications.
        subscriber_url should be the full URL of the subscriber's XMLRPC server,
        e.g., 'http://localhost:9001/RPC2'
        """
        if not isinstance(subscriber_url, str):
            return "Error: Subscriber URL must be a string."
        with self._lock:
            if subscriber_url in self._subscribers:
                print(f"Subscriber '{subscriber_url}' already registered.")
                return f"Subscriber '{subscriber_url}' already registered."
            self._subscribers.add(subscriber_url)
            print(f"Registered subscriber: {subscriber_url}")
            return f"Subscriber '{subscriber_url}' registered successfully."

    def unregister_subscriber(self, subscriber_url):
        """
        Unregisters a subscriber URL.
        """
        if not isinstance(subscriber_url, str):
            return "Error: Subscriber URL must be a string."
        with self._lock:
            if subscriber_url in self._subscribers:
                self._subscribers.discard(subscriber_url)
                print(f"Unregistered subscriber: {subscriber_url}")
                return f"Subscriber '{subscriber_url}' unregistered successfully."
            else:
                print(f"Subscriber '{subscriber_url}' not found for unregistration.")
                return f"Subscriber '{subscriber_url}' not found."

    def _broadcast_insults(self):
        """
        Periodically sends a random insult to all registered subscribers.
        This method runs in a separate thread.
        """
        print("Broadcaster started. Will broadcast every 5 seconds.")
        while True:
            time.sleep(5) # Wait for 5 seconds
            
            insult_to_send = None
            subscribers_to_notify = []

            with self._lock:
                if self._insults and self._subscribers:
                    insult_to_send = random.choice(list(self._insults))
                    subscribers_to_notify = list(self._subscribers) # Create a copy for iteration
            
            if insult_to_send and subscribers_to_notify:
                print(f"Broadcasting insult: '{insult_to_send}' to {len(subscribers_to_notify)} subscribers.")
                for sub_url in subscribers_to_notify:
                    try:
                        # Each subscriber is an XMLRPC server, connect to it
                        subscriber_proxy = ServerProxy(sub_url)
                        # Assume subscriber has a method 'receive_insult_notification'
                        subscriber_proxy.receive_insult_notification(insult_to_send)
                        print(f"  Successfully notified {sub_url}")
                    except Exception as e:
                        print(f"  Error notifying subscriber {sub_url}: {e}")
                        # Optional: Consider removing unresponsive subscribers
            elif not self._insults:
                print("Broadcaster: No insults to broadcast.")
            elif not self._subscribers:
                print("Broadcaster: No subscribers to notify.")


def run_server(host="localhost", port=8000):
    """Starts the XMLRPC server."""
    # We're gonna use 127.0.0.1 according to the entorn pdf  	 	
    # from campus for less latency
    actual_host = "127.0.0.1" 
    server_address = (actual_host, port)
    server = SimpleXMLRPCServer(server_address, requestHandler=RequestHandler, allow_none=True)
    server.register_introspection_functions() 

    server.register_instance(InsultService())
    print(f"XMLRPC Insult Server listening on {actual_host}:{port}/RPC2...")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer shutting down.")
        server.server_close()

if __name__ == "__main__":
    run_server()
