# insult_client_pyro.py
import Pyro4

def main():
    service_name = "example.insult.service"
    try:
        # Use PYRONAME to lookup the InsultServer from the Name Server
        insult_server = Pyro4.Proxy(f"PYRONAME:{service_name}")
        print(f"Connected to InsultServer ('{service_name}').")
    except Pyro4.errors.NamingError:
        print(f"Error: Could not find '{service_name}' in the Name Server.")
        print("Please ensure the Name Server is running and the InsultServer is registered.")
        return
    except Exception as e:
        print(f"An error occurred connecting to InsultServer: {e}")
        return

    # 1. Add some insults
    print("\n--- Adding Insults ---")
    insults_to_add = [
        "You are the human equivalent of a participation trophy.",
        "I'd agree with you, but then we'd both be wrong.",
        "You are the human equivalent of a participation trophy." # Duplicate
    ]
    for insult in insults_to_add:
        try:
            response = insult_server.add_insult(insult)
            print(f"Server: {response}")
        except Exception as e:
            print(f"Error adding insult '{insult}': {type(e).__name__} - {e}")

    # 2. Get all insults
    print("\n--- Retrieving All Insults ---")
    try:
        all_insults = insult_server.get_insults()
        if all_insults:
            print("Current insults on server:")
            for i, insult_text in enumerate(all_insults):
                print(f"  {i+1}. {insult_text}")
        else:
            print("No insults currently on the server.")
    except Exception as e:
        print(f"Error retrieving insults: {type(e).__name__} - {e}")


    print("\n--- Server Exposed Methods (via _pyroMethods) ---")
    try:
        print(insult_server._pyroMethods)
    except Exception:
        print("Could not retrieve methods (object might not be fully bound or error occurred).")


if __name__ == "__main__":
    main()
