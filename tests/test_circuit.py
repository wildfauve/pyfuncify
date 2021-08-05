import pytest
from typing import Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field

from pyfuncify import circuit, monad

@dataclass
class NoOpCircuitConfig:
    circuit_state: Optional[str] = None
    failures: Optional[int] = None
    last_state_chg_time: Optional[datetime] = None
    circuit_state_writer: Optional[Callable] = None

def test_1st_failure_to_half_open(circuit_config):
    failure()(circuit_config=circuit_config)
    assert(circuit_config.circuit_state) == "half_open"
    assert(circuit_config.failures) == 1

def test_failure_then_success_to_closed(circuit_config):
    failure()(circuit_config=circuit_config)
    success()(circuit_config=circuit_config)
    assert(circuit_config.circuit_state) == "closed"
    assert(circuit_config.failures) == 0


def failure():
    @circuit.circuit_breaker()
    def run(circuit_config):
        return monad.Left("boom")
    return run

def success():
    @circuit.circuit_breaker()
    def run(circuit_config):
        return monad.Right("OK")
    return run

@pytest.fixture
def circuit_config():
    return NoOpCircuitConfig(circuit_state_writer=lambda _x: _x)
