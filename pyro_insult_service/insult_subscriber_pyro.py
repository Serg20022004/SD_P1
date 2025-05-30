# insult_subscriber_pyro.py
import Pyro4
import time # For a small delay

@Pyro4.expose # This class will receive remote calls
class NotificationReceiver:
    def receive_insult(self, insult_message):
        """This method is called by the InsultServer when a new insult is broadcast."""
        print(f"\n[SUBSCRIBER] >>> Received Insult: {insult_message}")
        return "ACK: Insult received."

def main():
    # --- Subscriber's local Pyro setup ---
    # Create a daemon for this subscriber to host its NotificationReceiver
    subscriber_daemon = Pyro4.Daemon(host="127.0.0.1") 
    
    # Create an instance of our receiver object
    receiver_object = NotificationReceiver()
    
    # Register the receiver object with our local daemon to get its URI
    # This URI will be passed to the main InsultServer
    receiver_uri = subscriber_daemon.register(receiver_object)
    print(f"Subscriber's NotificationReceiver is active.")
    print(f"  My URI for receiving insults: {receiver_uri}")

    # --- Connect to the main InsultServer and register ---
    main_server_name = "example.insult.service"
    insult_server_proxy = None # Initialize
    try:
        insult_server_proxy = Pyro4.Proxy(f"PYRONAME:{main_server_name}")
        print(f"Connected to main InsultServer ('{main_server_name}') for registration.")
        
        # Register this subscriber's receiver_uri with the main server
        print(f"Attempting to register URI: {receiver_uri} with server...")
        response = insult_server_proxy.register_subscriber(str(receiver_uri)) # Pass URI as string
        print(f"Server registration response: {response}")

    except Pyro4.errors.NamingError:
        print(f"Error: Could not find main InsultServer '{main_server_name}' in Name Server.")
        print("Ensure Name Server and InsultServer are running.")
        subscriber_daemon.shutdown() # Shutdown local daemon if we can't register
        return
    except Exception as e:
        print(f"An error occurred during connection or registration: {type(e).__name__} - {e}")
        subscriber_daemon.shutdown()
        return

    # --- Keep subscriber alive to receive notifications ---
    print("\nSubscriber is now listening for insult broadcasts...")
    print("Press Ctrl+C to stop.")
    try:
        subscriber_daemon.requestLoop() # Start event loop for this subscriber's daemon
    except KeyboardInterrupt:
        print("\nSubscriber shutting down (Ctrl+C)...")
    finally:
        print("Subscriber: Cleaning up...")
        # Unregister from the main server (best effort)
        if insult_server_proxy: # Check if proxy was created
            try:
                print("Attempting to unregister from main InsultServer...")
                insult_server_proxy.unregister_subscriber(str(receiver_uri))
            except Exception as e:
                print(f"Could not unregister from main server during shutdown: {type(e).__name__} - {e}")
        
        if subscriber_daemon: # Check if daemon was created
            subscriber_daemon.shutdown() # Shutdown local daemon
        print("Subscriber: Shutdown complete.")

if __name__ == "__main__":
    main()
