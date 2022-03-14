from typing import Dict, Tuple
from pymonad.tools import curry

@curry(2)
def at(attr, rec):
    return getattr(rec, attr, None)


@curry(2)
def at_prop(prop, rec):
    property = getattr(rec, prop, None)
    return property() if property and callable(property) else None

