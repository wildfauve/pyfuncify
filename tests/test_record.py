from pyfuncify import record

from dataclasses import dataclass

@dataclass
class Rec():
    attr1: str
    def attr2(self):
        return "there"


def test_at():
    assert record.at('attr1')(Rec(attr1="hello")) == "hello"

def test_at_prop():
    assert record.at_prop('attr2')(Rec(attr1="hello")) == "there"


def test_at_prop_when_not_callable():
    assert not record.at_prop('attr1')(Rec(attr1="hello"))
