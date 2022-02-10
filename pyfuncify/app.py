from typing import Callable

from . import singleton

class RouteMap(singleton.Singleton):
    routes = {}

    def add_route(self, event: str, fn: Callable):
        self.routes[event] = fn
        pass

    def get_route(self, route_name) -> Callable:
        return self.routes.get(route_name, self.routes.get('no_matching_route', None))

def fn_for_event(event: str) -> Callable:
    return RouteMap().get_route(event)

def route(event):
    """
    Route Mapper

    """
    def inner(fn):
        RouteMap().add_route(event=event, fn=fn)
    return inner
