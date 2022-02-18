from typing import Dict, List
from http import cookies
from pymonad.tools import curry

from . import fn

class SessionProperty:

    def __init__(self, name: str, value: cookies.Morsel):
        self.name = name
        self.morsel = value

    def serialise(self) -> str:
        return self.morsel.OutputString()

    def value(self):
        return self.morsel.value

    def is_name(self, search_name):
        return self.name == search_name


class WebSession():

    def session_from_headers(self, headers: Dict):
        hdrs = headers.get('Cookie', None)
        if not hdrs:
            self.session_state = None
            return self
        cookie = cookies.SimpleCookie()
        cookie.load(hdrs)
        self.properties = [SessionProperty(item[0], item[1]) for item in cookie.items()]
        return self

    def serialise_state_as_multi_header(self) -> Dict[str, List]:
        return {'Set-Cookie': [prop.serialise() for prop in self.properties]}

    def get(self, name) -> SessionProperty:
        return fn.find(self.prop_name_predicate(name), self.properties)

    @curry(3)
    def prop_name_predicate(self, name, prop):
        return prop.is_name(name)

