# filter_worker_pyro.py
import Pyro4
import re # For filtering
import time

# --- Configuration ---
DISPATCHER_NAME = "example.filter.dispatcher" # To find and register with the dispatcher

@Pyro4.expose
class FilterWorker:
    def __init__(self, worker_id="Worker"): # worker_id for logging
        self.worker_id = worker_id
        print(f"{self.worker_id}: Initialized.")

    def process_this_text(self, original_text, known_insults_list):
        """
        This method is called by the Dispatcher to filter a piece of text.
        It receives the text and the list of insults to use for filtering.
        """
        print(f"{self.worker_id}: Received text to filter: '{original_text[:50]}...' with {len(known_insults_list)} known insults.")
        
        # Basic filtering logic (same as in XMLRPC server for consistency)
        # For more robust filtering, a dedicated library or advanced regex would be better.
        # This assumes known_insults_list contains lowercased insults.
        
        # Convert known_insults_list to a set for efficient lookup if not already
        insults_to_check_set = set(insult.lower() for insult in known_insults_list)

        words = re.split(r'(\W+)', original_text) # Split by non-word characters, keeping delimiters
        censored_words = []
        for word in words:
            if word.lower() in insults_to_check_set:
                censored_words.append("CENSORED")
            else:
                censored_words.append(word)
        filtered_text = "".join(censored_words)
        
        print(f"{self.worker_id}: Filtering complete. Result: '{filtered_text[:50]}...'")
        return filtered_text # Return the filtered text to the dispatcher

def main():
    # --- Worker's local Pyro setup ---
    worker_daemon = Pyro4.Daemon(host="127.0.0.1") # Use specific host
    
    # Create a unique ID for this worker instance for logging/identification
    # (e.g., based on hostname/port if desired, or just a random part of its URI)
    # For now, let daemon pick port.
    
    worker_instance = FilterWorker() # ID could be passed here
    worker_uri = worker_daemon.register(worker_instance)
    # If worker_id was based on URI, it would be set after this.
    worker_instance.worker_id = f"Worker@{worker_uri.location}" # Update worker_id with its location
    
    print(f"{worker_instance.worker_id}: Active at URI {worker_uri}")

    # --- Register with the Dispatcher ---
    dispatcher_proxy = None
    try:
        dispatcher_proxy = Pyro4.Proxy(f"PYRONAME:{DISPATCHER_NAME}")
        print(f"{worker_instance.worker_id}: Attempting to register with Dispatcher '{DISPATCHER_NAME}'...")
        response = dispatcher_proxy.register_worker(str(worker_uri)) # Pass my URI as string
        print(f"{worker_instance.worker_id}: Dispatcher registration response: {response}")
    except Pyro4.errors.NamingError:
        print(f"{worker_instance.worker_id}: Error: Could not find Dispatcher '{DISPATCHER_NAME}'. Worker will not be able to process tasks from it.")
        worker_daemon.shutdown()
        return
    except Exception as e:
        print(f"{worker_instance.worker_id}: Error during registration with Dispatcher: {type(e).__name__} - {e}")
        worker_daemon.shutdown()
        return

    # --- Keep worker alive to process tasks ---
    print(f"{worker_instance.worker_id}: Listening for filter tasks. Press Ctrl+C to stop.")
    try:
        worker_daemon.requestLoop()
    except KeyboardInterrupt:
        print(f"\n{worker_instance.worker_id}: Shutting down (Ctrl+C)...")
    finally:
        print(f"{worker_instance.worker_id}: Cleaning up...")
        # Unregister from dispatcher (best effort)
        if dispatcher_proxy:
            try:
                print(f"{worker_instance.worker_id}: Attempting to unregister from Dispatcher...")
                dispatcher_proxy.unregister_worker(str(worker_uri))
            except Exception as e:
                print(f"{worker_instance.worker_id}: Could not unregister from Dispatcher: {type(e).__name__}")
        
        if worker_daemon: worker_daemon.shutdown()
        print(f"{worker_instance.worker_id}: Shutdown complete.")

if __name__ == "__main__":
    main()
