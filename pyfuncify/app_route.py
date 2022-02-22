from typing import Optional, Dict, Any, List, Callable, Union, Tuple
from pymonad.tools import curry

from . import singleton, fn

class RouteMap(singleton.Singleton):
    routes = {}

    def add_route(self, pattern: Union[str, Tuple[str,str,str]], fn: Callable, opts: Dict):
        self.routes[pattern] = (fn, opts)
        pass

    def no_route(self, return_template=False) -> Union[Callable, Tuple[str, Callable]]:
        if return_template:
            return 'no_matching_routes', self.routes.get('no_matching_route', None), None
        return self.routes.get('no_matching_route', None)

    def get_route(self, route: Union[str, Tuple]) -> Tuple[Union[str, Tuple], Callable]:
        if isinstance(route, str):
            match = self.routes.get(route, self.no_route())
            return route, match[0], match[1]
        possible_matching_routes = self.event_matches(route[0], route[1], route[2])
        if not possible_matching_routes or len(possible_matching_routes) > 1:
            return self.no_route(True)

        # return the route_pattern, route_fn, and route_opts
        return possible_matching_routes[0][0], possible_matching_routes[0][1][0], possible_matching_routes[0][1][1],

    def route_pattern_from_function(self, route_fn: Callable):
        route_item = fn.find(self.route_function_predicate(route_fn), self.routes.items())
        if route_item:
            return route_item[0]
        return None

    @curry(3)
    def route_function_predicate(self, route_fn, route):
        return route[1][0] == route_fn

    def event_matches(self, pos1, pos2, pos3) -> Dict[Tuple, str]:
        return list(fn.select(self.match_predicate(pos1, pos2, pos3), self.routes.items()))

    @curry(5)
    def match_predicate(self, pos1, pos2, pos3, route_item: Tuple[Union[str, Tuple], Callable]):
        if isinstance(route_item[0], str):
            return None
        event_type, event_qual, event_template = route_item[0]
        if event_type == pos1 and event_qual == pos2 and self.template_matches(event_template, pos3):
            return True
        return None

    def template_matches(self, template, event):
        return self.matcher(fn.rest(template.split("/")), fn.rest(event.split("/")))

    def matcher(self, template_xs: List, event_xs: List):
        template_fst, template_rst = fn.first(template_xs), fn.rest(template_xs)
        ev_fst, ev_rst = fn.first(event_xs), fn.rest(event_xs)
        if not template_fst and not ev_fst:
            return True
        if not template_fst and ev_fst:
            return False
        if template_fst and not ev_fst:
            return False
        if not self.ismatch(template_fst, ev_fst):
            return False
        return self.matcher(template_rst, ev_rst)

    def ismatch(self, template_token, ev_token):
        return ("{" in template_token and "}" in template_token) or template_token == ev_token


def route(pattern: Union[str, Tuple[str, str, str]], opts: Dict = None):
    """
    Route Mapper
    """
    def inner(fn):
        RouteMap().add_route(pattern=pattern, fn=fn, opts=opts)
    return inner


def std_noop_response(request):
    return monad.Right(request.replace('response', monad.Right({})))

