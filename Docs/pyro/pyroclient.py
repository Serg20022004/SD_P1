import Pyro4

# Connect to the remote EchoServer object
def main():
    echo_server = Pyro4.Proxy("PYRONAME:echo.server")  # Get remote object

   
    response = echo_server.echo("HOLA")  # Call remote method
    print(f"Response from server: {response}")

if __name__ == "__main__":
    main()
