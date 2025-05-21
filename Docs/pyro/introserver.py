import Pyro4
import threading
import time

# Enable Pyro4 to use the name server
Pyro4.config.REQUIRE_EXPOSE = True

# Define a simple remote object
@Pyro4.expose
class MyRemoteObject:
    def __init__(self, name):
        self.name = name

    def greet(self, message):
        return f"{self.name} says: {message}"

    def add(self, a, b):
        return a + b

   

if __name__ == "__main__":
    daemon = Pyro4.Daemon()  # Create a Pyro daemon
    ns = Pyro4.locateNS()  # Locate the Pyro name server
    uri = daemon.register(MyRemoteObject("RemoteObject"))  # Register the remote object
    ns.register("example.remote.object", uri)  # Register the object with a name in the name server
    print("Server URI:", uri)
    print("Server is ready.")
    daemon.requestLoop()  # Start the event loop of the server to wait for calls
