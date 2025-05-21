import Pyro4

try:
    ns = Pyro4.locateNS()  # Locate the Pyro name server
    uri = ns.lookup("example.remote.object")  # Lookup the URI of the remote object
    remote_object = Pyro4.Proxy(uri)  # Create a proxy for the remote object

    result = remote_object.greet("Hello from dynamic introspection!")
    print("Result of greet method:", result)

    result = remote_object.add(5, 10)
    print("Result of add method:", result)

    # Dynamically introspect the remote object
    print("Available methods on the remote object:")
    for method_name in remote_object._pyroMethods:
        print(f"- {method_name}")

    
except Exception as e:
    print(f"Error during dynamic introspection: {e}")