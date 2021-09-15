from typing import Dict, Tuple
from pymonad.tools import curry

@curry(2)
def at(attr, rec):
    return getattr(rec, attr, None)


