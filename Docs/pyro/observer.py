import Pyro4

@Pyro4.expose
class Observer:
    def update(self, message):
        """This method is called when the observable sends a notification."""
        print(f"🔔 Received update: {message}")

def main():
    ns = Pyro4.locateNS()
    observable = Pyro4.Proxy(ns.lookup("example.observable"))

    with Pyro4.Daemon() as daemon:
        observer = Observer()
        observer_uri = daemon.register(observer)  # Get remote URI
        
        observable.register_observer(observer_uri)  # Register observer with the observable
        
        print(f"Observer registered with URI: {observer_uri}")
        print("🔄 Waiting for notifications...")

        daemon.requestLoop()  # Keep the observer running to receive updates

if __name__ == "__main__":
    main()
