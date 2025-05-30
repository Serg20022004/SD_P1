# filter_server_xmlrpc.py

from xmlrpc.server import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler
import threading
import queue #
import time
import re 

# Restrict to a particular path.
class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)

class FilterService:
    def __init__(self, known_insults_list=None):
        # List of insults to filter. Case-insensitive matching.
        if known_insults_list is None:
            self.known_insults = {
                "stupid", "idiot", "dummy", "moron", # Add more or load from file
                "dense", "lame" 
            } # Store as a set for efficient lookup, lowercased
        else:
            self.known_insults = {insult.lower() for insult in known_insults_list}

        self._task_queue = queue.Queue() # Internal queue for texts to be filtered
        self._filtered_texts = []      # List to store results
        self._lock = threading.Lock()  # To protect _filtered_texts
        
        self._worker_active = True
        self.worker_thread = threading.Thread(target=self._process_filter_tasks, daemon=True)
        self.worker_thread.start()
        print("FilterService initialized, worker thread started.")

    def _filter_text(self, original_text):
        """Filters known insults from the text, replacing them with 'CENSORED'."""
       
        # Build a regex pattern like: \b(stupid|idiot|dummy)\b
        # The \b ensures we match whole words.
        # re.IGNORECASE handles case-insensitivity.
        if not self.known_insults:
            return original_text

        # Split text into words, check, and rebuild.
        words = re.split(r'(\W+)', original_text) # Split by non-word characters, keeping delimiters
        censored_words = []
        for word in words:
            if word.lower() in self.known_insults:
                censored_words.append("CENSORED")
            else:
                censored_words.append(word)
        return "".join(censored_words)


    def _process_filter_tasks(self):
        """Worker thread function to process texts from the internal queue."""
        print("Filter worker: Starting to process tasks from queue.")
        while self._worker_active or not self._task_queue.empty():
            try:
                # Get a task from the queue, with a timeout to allow checking _worker_active
                original_text = self._task_queue.get(timeout=1) 
                
                print(f"Filter worker: Processing text: '{original_text[:50]}...'")
                filtered_text = self._filter_text(original_text)
                
                with self._lock:
                    self._filtered_texts.append({
                        "original": original_text,
                        "filtered": filtered_text,
                        "timestamp": time.time()
                    })
                print(f"Filter worker: Finished filtering. Result: '{filtered_text[:50]}...'")
                self._task_queue.task_done() # Signal that the task is done

            except queue.Empty:
                # Queue is empty, just continue if worker is still active
                if self._worker_active:
                    continue
                else:
                    # Worker is stopping and queue is empty
                    break 
            except Exception as e:
                print(f"Filter worker: Error processing task: {e}")
        print("Filter worker: Stopped.")

    # --- XMLRPC Exposed Methods ---
    def submit_text_for_filtering(self, text_content):
        """
        Client-callable method to submit a text string for filtering.
        The text is added to an internal queue for asynchronous processing.
        """
        if not isinstance(text_content, str):
            return "Error: Text content must be a string."
        
        self._task_queue.put(text_content)
        print(f"FilterService: Received text for filtering: '{text_content[:50]}...'. Added to queue.")
        return f"Text submitted successfully. Queue size: {self._task_queue.qsize()}"

    def get_filtered_results(self):
        """
        Client-callable method to retrieve all filtered texts processed so far.
        """
        with self._lock:
            print(f"FilterService: Retrieving {len(self._filtered_texts)} filtered results.")
            # Return a copy to prevent external modification if the list itself was mutable
            return list(self._filtered_texts) 
            
    def get_pending_task_count(self):
        """Returns the number of tasks currently in the processing queue."""
        return self._task_queue.qsize()

    def shutdown_worker(self): # For graceful shutdown
        print("FilterService: Signaling worker thread to shutdown...")
        self._worker_active = False
        # The worker will complete current item and then exit if queue becomes empty
 
# --- Main Server Setup ---
def run_filter_server(host="127.0.0.1", port=8001, known_insults=None):
    server_address = (host, port)
    server = SimpleXMLRPCServer(server_address, requestHandler=RequestHandler, allow_none=True)
    server.register_introspection_functions()

    filter_service_instance = FilterService(known_insults_list=known_insults)
    server.register_instance(filter_service_instance)
    print(f"XMLRPC Filter Service listening on {host}:{port}/RPC2...")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nFilter Server shutting down...")
    finally:
        print("Filter Server: Cleaning up...")
        filter_service_instance.shutdown_worker()
        # Wait for worker thread to finish
        if filter_service_instance.worker_thread.is_alive():
            print("Filter Server: Waiting for worker thread to complete...")
            filter_service_instance.worker_thread.join(timeout=2.0) 
        server.server_close()
        print("Filter Server: Shutdown complete.")

if __name__ == "__main__":
    example_insults = ["stupid", "idiot", "darn", "heck", "lame"] 
    run_filter_server(known_insults=example_insults)
