from pyfuncify import circuit, monad

from .shared import *


def test_1st_failure_to_half_open(circuit_state_provider):
    failure()(circuit_state_provider=circuit_state_provider)
    assert(circuit_state_provider.circuit_state) == "half_open"
    assert(circuit_state_provider.failures) == 1

def test_failure_then_success_to_closed(circuit_state_provider):
    failure()(circuit_state_provider=circuit_state_provider)
    success()(circuit_state_provider=circuit_state_provider)
    assert(circuit_state_provider.circuit_state) == "closed"
    assert(circuit_state_provider.failures) == 0


def failure():
    @circuit.circuit_breaker()
    def run(circuit_state_provider=circuit_state_provider):
        return monad.Left("boom")
    return run

def success():
    @circuit.circuit_breaker()
    def run(circuit_state_provider=circuit_state_provider):
        return monad.Right("OK")
    return run
