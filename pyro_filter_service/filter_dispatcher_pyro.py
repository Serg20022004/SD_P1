import Pyro4
import threading
import time
import random

# --- Configuration ---
DISPATCHER_NAME = "example.filter.dispatcher"
KNOWN_INSULTS_LIST = {"stupid", "idiot", "dummy", "moron", "lame", "darn", "heck"} # Lowercased

@Pyro4.expose
@Pyro4.behavior(instance_mode="single")
class FilterDispatcher:
    def __init__(self):
        self._worker_uris = [] # List to store URIs of registered worker objects
        self._filtered_results = [] # List to store {original, filtered, worker_uri, timestamp}
        self._lock = threading.Lock() # For worker_uris and filtered_results
        self._next_worker_index = 0 # For simple round-robin
        print("FilterDispatcher initialized.")

    def register_worker(self, worker_uri_str):
        """Called by a FilterWorker to register itself."""
        with self._lock:
            if worker_uri_str not in self._worker_uris:
                self._worker_uris.append(worker_uri_str)
                print(f"Dispatcher: Registered worker: {worker_uri_str}")
                return f"Worker {worker_uri_str} registered successfully."
            else:
                print(f"Dispatcher: Worker {worker_uri_str} already registered.")
                return f"Worker {worker_uri_str} already registered."

    def unregister_worker(self, worker_uri_str): # Graceful worker shutdown
        with self._lock:
            if worker_uri_str in self._worker_uris:
                self._worker_uris.remove(worker_uri_str)
                print(f"Dispatcher: Unregistered worker: {worker_uri_str}")
                return f"Worker {worker_uri_str} unregistered."
            return "Worker not found for unregistration."

    def submit_text_for_filtering(self, original_text):
        if not isinstance(original_text, str):
            raise ValueError("Text to filter must be a string.")

        selected_worker_uri = None
        worker_proxy = None

        with self._lock:
            if not self._worker_uris:
                print("Dispatcher: No workers registered to process the text.")

                return "Error: No workers available to filter text."
            
            # Simple round-robin to select a worker
            selected_worker_uri = self._worker_uris[self._next_worker_index % len(self._worker_uris)]
            self._next_worker_index += 1
        
        print(f"Dispatcher: Assigning text '{original_text[:30]}...' to worker {selected_worker_uri}")

        try:
            worker_proxy = Pyro4.Proxy(selected_worker_uri)
            # The worker needs the list of insults to perform the filtering
            # The worker's method should be like: filter_text_actual(text, insults_to_check)
            filtered_text = worker_proxy.process_this_text(original_text, list(KNOWN_INSULTS_LIST)) 
                                                            # Pass KNOWN_INSULTS_LIST
        except Pyro4.errors.CommunicationError as e:
            print(f"Dispatcher: Communication error with worker {selected_worker_uri}: {e}. Removing worker.")
            # Auto-remove worker if communication fails
            self.unregister_worker(selected_worker_uri) # Call method that handles lock
            return f"Error: Could not reach worker {selected_worker_uri}. Please resubmit."
        except Exception as e:
            print(f"Dispatcher: Error during filtering with worker {selected_worker_uri}: {type(e).__name__} - {e}")
            # Potentially remove worker here too, or mark as unreliable
            return f"Error processing text with worker: {e}"

        # Store the result centrally
        with self._lock:
            result_entry = {
                "original": original_text,
                "filtered": filtered_text,
                "processed_by_worker": selected_worker_uri,
                "timestamp": time.time()
            }
            self._filtered_results.append(result_entry)
        
        print(f"Dispatcher: Text processed by {selected_worker_uri}. Filtered: '{filtered_text[:30]}...'")
        return {"status": "success", "original": original_text, "filtered": filtered_text}


    def get_filtered_results(self):
        with self._lock:
            print(f"Dispatcher: Retrieving {len(self._filtered_results)} filtered results.")
            return list(self._filtered_results) # Return a copy

def start_dispatcher_server():
    daemon = Pyro4.Daemon(host="127.0.0.1")
    ns = Pyro4.locateNS()
    
    dispatcher_instance = FilterDispatcher()
    uri = daemon.register(dispatcher_instance)
    ns.register(DISPATCHER_NAME, uri)
    
    print(f"FilterDispatcherServer ready. URI: {uri}")
    print(f"Registered as '{DISPATCHER_NAME}' in the Name Server.")
    
    try:
        daemon.requestLoop()
    except KeyboardInterrupt:
        print("\nFilterDispatcherServer shutting down...")
    finally:
        print("FilterDispatcherServer: Cleaning up...")
        if ns:
            try: ns.remove(DISPATCHER_NAME)
            except Pyro4.errors.NamingError: pass
        if daemon: daemon.shutdown()
        print("FilterDispatcherServer: Shutdown complete.")

if __name__ == "__main__":
    start_dispatcher_server()
