from typing import Any, Callable
from datetime import datetime

from . import monad, error, state_machine, chronos, singleton

# Circuit States, transitions, and state machine
transition_failure           = 'failure'
transition_persistent_failure = 'persistent_failure'
transition_success           = 'success'
state_half_open              = 'half_open'
state_half_closed            = 'half_closed'
state_open                   = 'open'
state_closed                 = 'closed'
circuit_state_map = state_machine.state_transition_map([(None,              transition_failure,            state_half_open),
                                                       (None,               transition_persistent_failure, state_open),
                                                       (state_half_open,    transition_persistent_failure, state_open),
                                                       (state_half_closed,  transition_persistent_failure, state_open),
                                                       (state_half_closed,  transition_failure,            state_half_open),
                                                       (state_half_open,    transition_success,            state_closed),
                                                       (state_open,         transition_success,            state_half_closed),
                                                       (state_closed,       transition_success,            state_closed),
                                                       (state_half_closed,  transition_success,            state_closed)])


class CircuitOpen(error.PyFuncifyError):
    pass


class CircuitConfig(singleton.Singleton):
    max_retries = 3
    # Factors that determine if a circuit should be placed in open state.
    # 3 failures in a 5 min period, opens the circuit
    failure_threshold_seconds = 5 * 60 # 5 minutes
    failure_count_threshold = 3

    # The number of minutes from the time a circuit transitioned to open before it can be retried
    open_stand_down_period = 5 * 60

    def configure(self, *args, **kwargs):
        self.circuit_store = kwargs.get('circuit_store', None)
        pass

def max_retries():
    return CircuitConfig().max_retries

def circuit_breaker():
    """
    Circuit Breaker Decorator.

    The kwargs MAY include a 'circuit_config' which can manage the state of the circuit over multiple invocations.  Its not implemented
    here, but must be injected in the args.  If its available it must support the following methods:
    + circuit_state
    + failures
    + last_state_chg_time: Takes and returns the last state change time as a ISO8601 formatted str.
    + circuit_state_writer

    """
    def inner(fn):
        def breaker(*args, **kwargs):
            circuit_config = kwargs.get('circuit_config', None)
            if circuit_config and is_open(circuit_config) and is_in_stand_down_period(circuit_config.last_state_chg_time):
                return monad.Left(CircuitOpen(message="Circuit Open", code=500))

            result = fn(*args, **kwargs)

            if circuit_config:
                if result.is_left():
                    circuit_failure(circuit_config)
                else:
                    transition_circuit_on_success(circuit_config)
            return result
        return breaker
    return inner


def monad_failure_predicate(monad_result: monad.MEither) -> bool:
    return monad_result.is_left() #and env.Env.production()

def circuit_failure(circuit_config: Any) -> Any:
    if exhasted_failures_over_period(last_state_chg_time=circuit_config.last_state_chg_time, failures=circuit_config.failures):
        open_circuit(circuit_config)
        pass
    else:
        update_circuit_failures(circuit_config)
    pass

def transition_circuit_on_success(circuit_config: Any) -> Any:
    transition = circuit_transition(from_state=circuit_config.circuit_state, with_transition=transition_success)
    if circuit_config.circuit_state != transition.value:
        circuit_config.circuit_state = transition.value
        circuit_config.last_state_chg_time = chronos.time_now(tz=chronos.tz_utc())
        circuit_config.failures = 0
        circuit_config.circuit_state_writer(circuit_config)
    return circuit_config

def exhasted_failures_over_period(last_state_chg_time: datetime, failures: int) -> bool:
    if last_state_chg_time is None:
        return False
    return failures_within_time_threshold(last_state_chg_time) and (failures >= (CircuitConfig().failure_count_threshold) )

def failures_within_time_threshold(circuit_time: datetime) -> bool:
    """
    When the circuit is half open, we can retry until we reach the failure threshold.
    """
    return (chronos.time_now(tz=chronos.tz_utc(), apply=[chronos.epoch()]) - circuit_time.timestamp()) < CircuitConfig().failure_threshold_seconds

def is_in_stand_down_period(last_state_chg_time: datetime) -> bool:
    """
    When the circuit is open there is a stand down period where the circuit will not be retried
    """
    return (chronos.time_now(tz=chronos.tz_utc(), apply=[chronos.epoch()]) - last_state_chg_time.timestamp()) < CircuitConfig().open_stand_down_period

def open_circuit(circuit_config: Any) -> Any:
    if circuit_config.circuit_state == state_open:
        return circuit_config

    circuit_config.circuit_state = circuit_transition(from_state=circuit_config.circuit_state, with_transition=transition_persistent_failure).value
    circuit_config.last_state_chg_time = chronos.time_now(tz=chronos.tz_utc())
    circuit_config.failures = 0
    circuit_config.circuit_state_writer(circuit_config)
    return circuit_config

def update_circuit_failures(circuit_config: Any) -> Any:
    transition = circuit_transition(from_state=circuit_config.circuit_state, with_transition=transition_failure).value
    if transition !=circuit_config.circuit_state:
        circuit_config.circuit_state = transition
        circuit_config.last_state_chg_time = chronos.time_now(tz=chronos.tz_utc())
    circuit_config.failures = 1 if circuit_config.failures is None else circuit_config.failures + 1
    circuit_config.circuit_state_writer(circuit_config)
    return circuit_config

#
# Circuit State Management
#
def circuit_transition(from_state: str, with_transition: str) -> monad.MEither:
    return state_machine.transition(state_map=circuit_state_map, from_state=from_state, with_transition=with_transition)

def is_open(config):
    return config.circuit_state == state_open
