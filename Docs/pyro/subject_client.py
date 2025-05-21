import Pyro4
observable = Pyro4.Proxy("PYRONAME:example.observable")
observable.notify_observers("Hello, Observers!")
