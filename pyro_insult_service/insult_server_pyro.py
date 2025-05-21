# insult_server_pyro.py
import Pyro4
import threading
import time
import random

@Pyro4.expose
@Pyro4.behavior(instance_mode="single") # Ensures all clients interact with the same instance
class InsultServer:
    def __init__(self):
        self._insults = set()       # To store unique insults
        self._subscriber_uris = []  # List to store URIs of subscriber's notification objects
        self._lock = threading.Lock()
        
        # Start a daemon thread for broadcasting insults
        self._broadcaster_active = True
        self.broadcaster_thread = threading.Thread(target=self._periodic_broadcast, daemon=True)
        self.broadcaster_thread.start()
        print("InsultServer initialized and broadcaster thread started.")

    def add_insult(self, insult_string):
        with self._lock:
            if not isinstance(insult_string, str):
                # Example files often just print or have simple returns, 
                # but raising an error is also a Pyro way.
                # For simplicity aligned with examples, let's return a status.
                print("Error: Insult must be a string.")
                return "Error: Insult must be a string."
            if insult_string in self._insults:
                print(f"Insult '{insult_string}' already exists.")
                return f"Insult '{insult_string}' already exists."
            self._insults.add(insult_string)
            print(f"Added insult: '{insult_string}'")
            return f"Insult '{insult_string}' added successfully."

    def get_insults(self):
        with self._lock:
            print(f"Retrieving insults ({len(self._insults)} found).")
            return list(self._insults)

    def register_subscriber(self, subscriber_uri_str):
        # subscriber_uri_str is the string URI of the subscriber's notification object
        with self._lock:
            if subscriber_uri_str not in self._subscriber_uris:
                self._subscriber_uris.append(subscriber_uri_str)
                print(f"Subscriber URI {subscriber_uri_str} registered.")
                return f"Subscriber {subscriber_uri_str} registered."
            else:
                print(f"Subscriber URI {subscriber_uri_str} already registered.")
                return f"Subscriber {subscriber_uri_str} already registered."

    def unregister_subscriber(self, subscriber_uri_str):
        with self._lock:
            if subscriber_uri_str in self._subscriber_uris:
                self._subscriber_uris.remove(subscriber_uri_str)
                print(f"Subscriber URI {subscriber_uri_str} unregistered.")
                return f"Subscriber {subscriber_uri_str} unregistered."
            else:
                print(f"Subscriber URI {subscriber_uri_str} not found for unregistration.")
                return f"Subscriber {subscriber_uri_str} not found."

    def _notify_specific_subscriber(self, subscriber_uri_str, insult_message):
        """Attempts to notify a single subscriber."""
        try:
            # Create a proxy for the subscriber's remote notification object
            subscriber_notification_obj = Pyro4.Proxy(subscriber_uri_str)
            # Call the agreed-upon method on the subscriber's object
            subscriber_notification_obj.receive_insult(insult_message)
            print(f"  Successfully notified {subscriber_uri_str} with '{insult_message}'")
        except Pyro4.errors.CommunicationError:
            print(f"  Communication error with subscriber {subscriber_uri_str}. Will attempt to unregister.")
            # Auto-unregister problematic subscribers
            # Need to be careful with lock if calling unregister_subscriber directly
            # For now, just print. A more robust system would handle removal.
            # self.unregister_subscriber(subscriber_uri_str) # Potential deadlock if lock is not re-entrant or managed carefully
        except Exception as e:
            print(f"  Error notifying subscriber {subscriber_uri_str}: {type(e).__name__} - {e}")


    def _periodic_broadcast(self):
        """Daemon thread function to periodically send a random insult."""
        print("Broadcaster: Starting periodic broadcasts every 5 seconds.")
        while self._broadcaster_active:
            time.sleep(5)
            insult_to_send = None
            current_subscriber_uris_copy = []

            with self._lock:
                if self._insults and self._subscriber_uris:
                    insult_to_send = random.choice(list(self._insults))
                    current_subscriber_uris_copy = list(self._subscriber_uris) # Work on a copy

            if insult_to_send and current_subscriber_uris_copy:
                print(f"Broadcaster: Sending insult '{insult_to_send}' to {len(current_subscriber_uris_copy)} subscribers.")
                for sub_uri in current_subscriber_uris_copy:
                    self._notify_specific_subscriber(sub_uri, insult_to_send)
            elif not self._insults:
                # print("Broadcaster: No insults to send.") # Can be noisy
                pass
            elif not current_subscriber_uris_copy:
                # print("Broadcaster: No subscribers registered.") # Can be noisy
                pass
        print("Broadcaster: Stopped.")
        
    def shutdown_broadcaster(self): # Method to stop the thread gracefully if needed
        print("InsultServer: Shutting down broadcaster thread...")
        self._broadcaster_active = False
        # self.broadcaster_thread.join() # Wait for it to finish, might delay server shutdown

def start_server():
    daemon = Pyro4.Daemon(host="127.0.0.1") # Explicitly use 127.0.0.1
    ns = Pyro4.locateNS() # Find the Name Server
    
    # Create an instance of our InsultServer
    insult_service_instance = InsultServer()
    
    # Register the InsultServer instance with the daemon
    uri = daemon.register(insult_service_instance)
    
    # Register the URI with the Name Server under a logical name
    service_name = "example.insult.service"
    ns.register(service_name, uri)
    
    print(f"InsultServer ready. URI: {uri}")
    print(f"Registered as '{service_name}' in the Name Server.")
    
    try:
        daemon.requestLoop() # Start the event loop of the server to wait for calls
    except KeyboardInterrupt:
        print("InsultServer: Shutting down...")
    finally:
        print("InsultServer: Cleaning up...")
        insult_service_instance.shutdown_broadcaster() # Signal broadcaster to stop
        if ns: # Check if ns was found
            try:
                ns.remove(service_name) # Remove from Name Server
                print(f"Unregistered '{service_name}' from Name Server.")
            except Pyro4.errors.NamingError:
                print(f"'{service_name}' not found in Name Server during cleanup or NS is down.")
        if daemon: # Check if daemon was created
            daemon.shutdown() # Shutdown the daemon
        print("InsultServer: Shutdown complete.")


if __name__ == "__main__":
    start_server()
