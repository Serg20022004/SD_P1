import Pyro4

@Pyro4.expose
@Pyro4.behavior(instance_mode="single")
class Observable:
    def __init__(self):
        self.observers = []  # List to store observer references

    def register_observer(self, observer_uri):
        """Register an observer using its remote URI."""
        observer = Pyro4.Proxy(observer_uri)  # Convert URI into a Pyro proxy
        self.observers.append(observer)
        print(f"Observer {observer_uri} registered.")

    def unregister_observer(self, observer_uri):
        """Unregister an observer."""
        self.observers = [obs for obs in self.observers if obs._pyroUri != observer_uri]
        print(f"Observer {observer_uri} unregistered.")

    def notify_observers(self, message):
        """Notify all registered observers."""
        print("Notifying observers...")
        for observer in self.observers:
            try:
                observer.update(message)  # Remote method call
            except Pyro4.errors.CommunicationError:
                print(f"Observer {observer._pyroUri} unreachable. Removing.")
                self.observers.remove(observer)

# Start the Pyro daemon and register the observable object
def start_server():
    daemon = Pyro4.Daemon()
    ns = Pyro4.locateNS()
    uri = daemon.register(Observable)
    ns.register("example.observable", uri)
    print(f"Observable server is running. URI: {uri}")
    daemon.requestLoop()

if __name__ == "__main__":
    start_server()
