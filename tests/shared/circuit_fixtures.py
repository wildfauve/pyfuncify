import pytest
from typing import Optional, Callable, Union
from datetime import datetime
from pyfuncify import circuit

class CircuitStateProvider(circuit.CircuitStateProviderProtocol):
    def __init__(self):
        self.circuit_state = None
        self.failures = 0
        self.last_state_chg_time = None

    def circuit_state(self, new_state):
        self.circuit_state = new_state
        return new_state

    def last_state_chg_time(self, new_time):
        self.last_state_chg_time = new_time
        return new_time

    def failures(self, count):
        self.failures = count
        return count

    def update_state(self, failures: int,  last_state_chg_time: datetime, circuit_state: Union[None, str]):
        self.failures = failures
        self.last_state_chg_time = last_state_chg_time
        self.circuit_state = circuit_state
        return self

@pytest.fixture
def circuit_state_provider():
    return CircuitStateProvider()
