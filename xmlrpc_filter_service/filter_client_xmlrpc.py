# filter_client_xmlrpc.py

import xmlrpc.client
import time

def main():
    server_url = "http://127.0.0.1:8001/RPC2"
    try:
        filter_proxy = xmlrpc.client.ServerProxy(server_url, allow_none=True)
        print(f"Connected to XMLRPC Filter Service at {server_url}")
    except Exception as e:
        print(f"Error connecting to Filter Service: {e}")
        return

    texts_to_filter = [
        "This is a stupid example text with some bad words like idiot.",
        "A perfectly clean and fine statement.",
        "What a LAME thing to say, you moron!",
        "This darn computer is so dense."
    ]

    print("\n--- Submitting Texts for Filtering ---")
    for i, text in enumerate(texts_to_filter):
        try:
            print(f"Submitting: '{text}'")
            response = filter_proxy.submit_text_for_filtering(text)
            print(f"  Server response: {response}")
            time.sleep(0.2) # Give server a little time to queue/process
        except Exception as e:
            print(f"  Error submitting text {i+1}: {e}")
            
    print("\nWaiting a bit for processing to occur...")
    # Check pending tasks
    try:
        pending_count = filter_proxy.get_pending_task_count()
        print(f"Initial pending tasks: {pending_count}")
    except Exception as e:
        print(f"Error getting pending task count: {e}")

    time.sleep(3) # Wait for the worker thread to process some tasks

    try:
        pending_count_after = filter_proxy.get_pending_task_count()
        print(f"Pending tasks after waiting: {pending_count_after}")
    except Exception as e:
        print(f"Error getting pending task count: {e}")


    print("\n--- Retrieving Filtered Results ---")
    try:
        results = filter_proxy.get_filtered_results()
        if results:
            print("Filtered Results:")
            for item in results:
                print(f"  Original : '{item['original']}'")
                print(f"  Filtered : '{item['filtered']}'")
                print(f"  Timestamp: {time.ctime(item['timestamp'])}")
                print("-" * 20)
        else:
            print("No filtered results available yet, or an error occurred.")
    except Exception as e:
        print(f"Error retrieving results: {e}")

if __name__ == "__main__":
    main()
