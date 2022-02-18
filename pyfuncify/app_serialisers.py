from typing import Optional, List, Dict, Tuple, Callable, Any, Protocol
import json

class Serialiser(Protocol):
    def __init__(self, serialisable: Any, serialisation: Callable):
        ...

    def serialise(self):
        ...


class DictToJsonSerialiser(Serialiser):
    def __init__(self, serialisable, serialisaton=None):
        self.serialisable = serialisable
        self.serialisation = serialisaton

    def serialise(self):
        return json.dumps(self.serialisable)
