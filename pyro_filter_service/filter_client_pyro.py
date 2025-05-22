# filter_client_pyro.py
import Pyro4
import time

DISPATCHER_NAME = "example.filter.dispatcher"

def main():
    try:
        dispatcher_proxy = Pyro4.Proxy(f"PYRONAME:{DISPATCHER_NAME}")
        print(f"Connected to FilterDispatcher ('{DISPATCHER_NAME}').")
    except Pyro4.errors.NamingError:
        print(f"Error: Could not find FilterDispatcher '{DISPATCHER_NAME}'.")
        print("Ensure Name Server and FilterDispatcher are running.")
        return
    except Exception as e:
        print(f"Error connecting: {e}")
        return

    texts_to_filter = [
        "This is a stupid example text with some bad words like idiot.",
        "A perfectly clean and fine statement.",
        "What a LAME thing to say, you moron!",
        "This darn computer is so dense and heck."
    ]

    print("\n--- Submitting Texts for Filtering ---")
    for i, text in enumerate(texts_to_filter):
        try:
            print(f"Submitting: '{text}'")
            # submit_text_for_filtering on dispatcher will call a worker
            response_dict = dispatcher_proxy.submit_text_for_filtering(text)
            if isinstance(response_dict, dict) and response_dict.get("status") == "success":
                print(f"  Dispatcher: Text processed. Filtered: '{response_dict['filtered']}'")
            else:
                print(f"  Dispatcher response/error: {response_dict}") # If it's an error string
            time.sleep(0.5) # Give some time between submissions
        except Exception as e:
            print(f"  Error submitting text {i+1}: {type(e).__name__} - {e}")
            
    print("\nWaiting a moment for any queued processing...")
    time.sleep(2)

    print("\n--- Retrieving All Filtered Results from Dispatcher ---")
    try:
        results = dispatcher_proxy.get_filtered_results()
        if results:
            print("Centrally Stored Filtered Results:")
            for item in results:
                print(f"  Original : '{item['original']}'")
                print(f"  Filtered : '{item['filtered']}'")
                print(f"  Worker   : {item.get('processed_by_worker', 'N/A')}") # get() in case key is missing
                print(f"  Timestamp: {time.ctime(item['timestamp'])}")
                print("-" * 20)
        else:
            print("No filtered results available from dispatcher yet.")
    except Exception as e:
        print(f"Error retrieving results: {e}")

if __name__ == "__main__":
    main()
