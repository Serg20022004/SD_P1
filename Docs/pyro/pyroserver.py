import Pyro4



# python -m Pyro4.naming
# Make the server object remotely accessible
@Pyro4.expose
class EchoServer:
    def echo(self, message):
        print("message received",message)
        return f"Server received: {message}"

# Start the Pyro4 Daemon
def main():
    daemon = Pyro4.Daemon()  # Create Pyro daemon
    ns = Pyro4.locateNS()  # Locate name server
    uri = daemon.register(EchoServer)  # Register EchoServer
    ns.register("echo.server", uri)  # Register with a unique name

    print("Echo server is running...")
    daemon.requestLoop()  # Keep server running

if __name__ == "__main__":
    main()
