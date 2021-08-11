from typing import List, Any, Tuple, Callable
from dataclasses import dataclass, field
from pymonad.reader import Pipe
from pymonad.tools import curry

from . import fn, monad

@dataclass
class StateTransitionMap:
    map: List[Tuple[str, str, str]]

def state_transition_map(map: List[Tuple[str]]) -> StateTransitionMap:
    return StateTransitionMap(map)

def valid_transitions_from(state_map: StateTransitionMap, from_state: str) -> List[str]:
    return (Pipe(state_map)
           .then(map_selector(extract_from_state, (from_state, None, None)))
           .then(extract_transition_from_map)
           .flush())

def valid_state_transition(state_map: StateTransitionMap, from_state: str, with_transition: str) -> bool:
    return (Pipe(state_map)
           .then(map_selector(extract_from_state_and_transition, (from_state, with_transition, None)))
           .then(list)
           .then(fn.only_one)
           .flush())

def transition(state_map: StateTransitionMap, from_state: str, with_transition: str) -> str:
    return (Pipe(state_map)
           .then(map_selector(extract_from_state_and_transition, (from_state, with_transition, None)))
           .then(list)
           .then(validate_and_extract_new_state)
           .flush())


@curry(3)
def map_selector(extractor_fn: Callable, map_tester: Tuple, state_map: StateTransitionMap) -> filter:
    return fn.select(fn.equality(extractor_fn, map_tester), state_map.map)

def validate_and_extract_new_state(state_map_items: List[Tuple[str, str, str]]) -> str:
    if fn.only_one(state_map_items):
        return monad.Right(state_map_items[0][2])
    return monad.Left("invalid transition")


def extract_from_state(state_map_item: Tuple) -> Tuple[str, None, None]:
    current, _transition, _new = state_map_item
    return (current, None, None)

def extract_from_state_and_transition(state_map_item: Tuple) -> Tuple:
    current, transition, _new = state_map_item
    return (current, transition, None)


def extract_transition(state_map_item: Tuple[str, str, str]) -> str:
    _current, transition, new = state_map_item
    return transition


def extract_transition_from_map(state_map: List[Tuple[str, str, str]]) -> str:
    return list(map(extract_transition, state_map))

#   def transition(state, event)
#     {event: event, new_state: @transitions.fetch([state, event])}
#   end
#
# end

#     def states(map)
#       metaclass.instance_eval do
#         define_method(:state_map) { map }
#       end
#     end
#
#     # The mandatory method to be invoked post transition with the new state
#     #
#     # Usage:
#     # > state_writer :state
#     def state_writer(method)
#       metaclass.instance_eval do
#         define_method(:state_writer_method) { method }
#       end
#     end
#
#     # The method to be invoked to retrieve the current state.  Useful when retrieving a state string from a DB and
#     # casting to a Symbol (or some other object).  If this macro is not defined, the value of the state_writer will be used.
#     #
#     # Usage:
#     # > state_reader :current_state
#     def state_reader(method)
#       metaclass.instance_eval do
#         define_method(:state_reader_method) { method }
#       end
#     end
#
#     # Provide a Lambda (curried) is called after the state transition.  The fn is envoked with 3 params;
#     # + self (the current object hosting the state machine)
#     # + the existing current state (a symbol from the state map)
#     # + the transition; A Result wrapping a hash with keys [:event, :new_state], e.g. Success({:event=>:new, :new_state=>:initiated})
#     #
#     # Declare the fn by either providing a Lambda or a symbol which refers to a method which returns a Lambda.
#     # Should return the current state
#     #
#     # Usage:
#     # > callback_fn -> current_state, transition { transition.value_or[:new_state] }.curry
#     # > callback_fn -> :audit_state_change
#     def state_change_callback_fn(fn)
#       metaclass.instance_eval do
#         define_method(:callback_fn) { fn }
#       end
#     end
#
#
#     def metaclass
#       class << self ; self ; end
#     end
#   end
#
#   module InstanceMethods
#
#     def apply_transition(transition)
#       write_state(fsm_fn(current_state).(transition))
#     end
#
#     def apply_persisted_transition(transition)
#       implemented?(-> obj { self.respond_to?(:save!)  }, "Persistent transitions require a :save! method")
#       new_state = fsm_fn(current_state_accessor).(transition)
#       # we wont change state if its not valid.
#       write_state(new_state) if new_state
#       status_value.new(status: status(save!), context: self)
#     end
#
#     def fsm_fn(initial_state)
#       state_transition.(fsm).(callback).(initial_state)
#     end
#
#     def valid_state_transitions
#       fsm.valid_transitions_from(current_state_accessor)
#     end
#
#     def valid_state_transition_event(event)
#       fsm.valid_state_transition_event(current_state_accessor, event)
#     end
#
#     # Handy callback fn which creates a audit of the transition and add it to host ActiveRecord model.
#     # Requires the model to provide a :state_audit property.
#     def audit_state_change(obj, current_state, transition)
#       obj.state_audit << state_audit_value(current_state, transition.value_or) if transition.success? && obj.respond_to?(:state_audit)
#     end
#
#     # A Noop callback
#     def noop_callback_fn
#       -> _obj, _current_state, transition {
#         nil
#       }.curry
#     end
#
#     private
#
#     def state_transition
#       -> map_fn, callback_fn, current_state, event {
#         result = map_fn.(current_state, event)
#         callback_fn.(self, current_state, result)
#         result.success? ? result.value_or[:new_state] : raise(StateTransitionError.new("#{self.class.name} cant transition from #{current_state} with event #{event}"))
#       }.curry
#     end
#
#     def callback
#       if macro_defined?(:callback_fn)
#         to_callable(self.class.callback_fn, 3)
#       else
#         noop_callback_fn
#       end
#     end
#
#     def fsm
#       implemented?(-> obj { macro_defined?(:state_map)  }, "Must define the state map via the states macro")
#       @fsm ||= self.class.state_map
#     end
#
#     def current_state_accessor
#       implemented?(-> obj { macro_defined?(:state_reader_method) && self.class.state_reader_method.is_a?(Symbol) },
#                    "Must define the method used to access the current state via the current_state_method")
#       self.send(self.class.current_state_access_method)
#     end
#
#     def write_state(state)
#       self.send("#{self.class.state_writer_method}=", state)
#     end
#
#     def current_state_accessor
#       macro_defined?(:state_reader_method) ? self.send(self.class.state_reader_method) : self.send(self.class.state_writer_method)
#     end
#
#     def status_value
#       IC['common.domain.status_value']
#     end
#
#
#   end
#
# end
#
