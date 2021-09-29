from typing import Callable

from . import singleton

class RouteMap(singleton.Singleton):
    routes = {}

    def add_route(self, event: str, fn: Callable):
        self.routes[event] = fn
        pass

def fn_for_event(event: str) -> Callable:
    return RouteMap().routes.get(event, RouteMap().routes.get('not_found', None))

def route(event):
    """
    Route Mapper

    """
    def inner(fn):
        RouteMap().add_route(event=event, fn=fn)
    return inner
