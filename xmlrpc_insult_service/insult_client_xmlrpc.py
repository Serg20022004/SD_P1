# insult_client_xmlrpc.py

import xmlrpc.client

def main():
    # Connect to the XMLRPC server using "127.0.0.1"
    server_address = "http://127.0.0.1:8000/RPC2" 
    try:
        server_proxy = xmlrpc.client.ServerProxy(server_address)
        print(f"Connected to Insult Server at {server_address}.")
    except ConnectionRefusedError:
        print(f"Connection refused. Is the Insult Server running at {server_address} ?")
        return
    except Exception as e:
        print(f"An error occurred during connection: {e}")
        return

    # --- Test adding insults ---
    insults_to_add = [
        "You're so dense, light bends around you.",
        "If brains were dynamite, you wouldn't have enough to blow your nose.",
        "You're the reason the gene pool needs a lifeguard.",
        "You're so dense, light bends around you." # Duplicate for testing
    ]

    print("\n--- Adding Insults ---")
    for insult in insults_to_add:
        try:
            response = server_proxy.add_insult(insult)
            print(f"Server response for '{insult}': {response}")
        except Exception as e:
            print(f"Error adding insult '{insult}': {e}")

    # --- Test getting insults ---
    print("\n--- Retrieving All Insults ---")
    try:
        all_insults = server_proxy.get_insults()
        if all_insults:
            print("Current insults on server:")
            for i, insult_text in enumerate(all_insults):
                print(f"  {i+1}. {insult_text}")
        else:
            print("No insults currently on the server.")
    except Exception as e:
        print(f"Error retrieving insults: {e}")

    print("\n--- Available Server Methods (Introspection) ---")
    try:
        methods = server_proxy.system.listMethods()
        print("Methods:", methods)
    except Exception as e:
        print(f"Error listing methods: {e}")


if __name__ == "__main__":
    main()
