from typing import Dict, List, Union
from http import cookies
from pymonad.tools import curry

from . import fn

class SessionProperty:

    def __init__(self, name: str, value: Union[cookies.Morsel, str]):
        self.name = name
        self.morsel = self.coerse_value(name, value)

    def coerse_value(self, name, val):
        if isinstance(val, cookies.Morsel):
            return val
        morsel = cookies.Morsel()
        morsel.set(name, val, val)
        return morsel

    def update(self, val):
        self.morsel.set(self.name, val, val)
        pass


    def serialise(self) -> str:
        return self.morsel.OutputString()

    def value(self):
        return self.morsel.value

    def is_name(self, search_name):
        return self.name == search_name


class WebSession():

    def __init__(self):
        self.properties = []

    def session_from_headers(self, headers: Dict):
        if not headers:
            return self

        hdrs = headers.get('Cookie', None)

        if not hdrs:
            return self
        cookie = cookies.SimpleCookie()
        cookie.load(hdrs)
        self.properties = [SessionProperty(item[0], item[1]) for item in cookie.items()]
        return self

    def serialise_state_as_multi_header(self) -> Dict[str, List]:
        if not self.properties:
            return {}
        return {'Set-Cookie': [prop.serialise() for prop in self.properties]}

    def get(self, name) -> SessionProperty:
        if not self.properties:
            return None
        return fn.find(self.prop_name_predicate(name), self.properties)

    def set(self, name, value):
        prop = self.get(name)
        if prop:
            prop.update(value)
        else:
            self.properties.append(SessionProperty(name, value))
        return self

    @curry(3)
    def prop_name_predicate(self, name, prop):
        return prop.is_name(name)

