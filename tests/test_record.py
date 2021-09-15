from pyfuncify import record

from dataclasses import dataclass

@dataclass
class Rec():
    attr1: str


def test_at():
    assert record.at('attr1')(Rec(attr1="hello")) == "hello"

