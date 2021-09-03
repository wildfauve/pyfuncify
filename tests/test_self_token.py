import os
import pytest
import time_machine
import datetime as dt

from .shared import *

from pyfuncify import self_token, chronos, fn, monad, circuit

class TokenPersistenceProvider():
    def __init__(self):
        self.bearer_token = None
        pass

    def write(self, key, value):
        self.bearer_token = value
        return monad.Right(value)

    def read(self, key):
        self.value = self.bearer_token
        return monad.Right(self)

class Env():
    def __init__(self):
        pass

    def client_id(self):
        return os.environ.get('CLIENT_ID')

    def client_secret(self):
        return os.environ.get('CLIENT_SECRET')

    def identity_token_endpoint(self):
        return os.environ.get('IDENTITY_TOKEN_ENDPOINT')

    def bearer_token(self):
        return None

    def set_env_var_with_value(self, key, value):
        os.environ[key] = value
        return ('ok', key, value)

class Tracer():
    def serialise(self):
        return {'env': 'test', 'handler_id': 'e5655b5f-e677-4a12-b8d7-0fa0b7e9dd20', 'aws_request_id': 'handler-id-1'}


def setup_function():
    self_token.invalidate_cache()
    if 'BEARER_TOKEN' in os.environ:
        del os.environ['BEARER_TOKEN']


def test_get_token_for_the_very_first_time(set_up_token_config_with_provider, set_up_env, identity_request_mock):
    result = self_token.token(tracer=Tracer())

    assert result.is_right() == True
    assert result.value.sub == "1@clients"

def test_token_persisted_in_provider(set_up_token_config_with_provider, set_up_env, identity_request_mock):
    result = self_token.token(tracer=Tracer())

    token = self_token.TokenConfig().token_persistence_provider.read(self_token.BEARER_TOKEN)

    assert result.value.jwt == token.value.value


def it_refreshes_the_token_from_cache_when_not_in_env(dynamo_mock_empty,
                                                      set_up_token_config_with_provider,
                                                      set_up_env,
                                                      identity_request_mock,
                                                      generate_valid_signed_jwt):
    self_token.TokenConfig().token_persistence_provider.write(self_token.BEARER_TOKEN, value=generate_valid_signed_jwt)

    result = self_token.token()

    assert(result.is_right()) == True

    token = self_token.TokenConfig().token_persistence_provider.read(self_token.BEARER_TOKEN)

    assert(token.is_right()) == True
    assert(looks_like_a_jwt(token.value.value)) == True


def test_re_get_token_when_expired_on_first_get(set_up_token_config_with_provider,
                                                set_up_env,
                                                identity_request_mock,
                                                generate_expired_signed_jwt):

    self_token.TokenConfig().token_persistence_provider.write(self_token.BEARER_TOKEN, generate_expired_signed_jwt)

    result = self_token.token()

    assert(result.value.expired()) == False

def test_re_get_token_when_expired_after_first_get(set_up_token_config_with_provider,
                                                   set_up_env,
                                                   identity_request_mock):
    result = self_token.token()

    assert(result.value.expired()) == False

    traveller = time_machine.travel(chronos.time_with_delta(hours=25))
    traveller.start()

    result = self_token.token()

    assert(result.value.expired()) == False

    traveller.stop()

def test_re_get_token_when_in_expired_window(set_up_token_config_with_provider,
                                             set_up_env,
                                             identity_request_mock):
    result1 = self_token.token()

    assert(result1.value.expired()) == False

    traveller = time_machine.travel(chronos.time_with_delta(hours=23))
    traveller.start()

    assert result1.value.expired() == False

    result2 = self_token.token()

    assert(result2.value.expired()) == False
    assert result2.value.jwt != result1.value.jwt

    traveller.stop()


def test_token_grant_error(set_up_token_config_with_provider,
                           set_up_env,
                           identity_request_error_mock):
    result = self_token.token()

    assert result.is_left()
    assert result.error().message == 'HTTP Error Response; Method:POST; Host: test.host'
    assert result.error().ctx == {'error': 'access_denied', 'error_description': 'Unauthorized'}
    assert result.error().code == 401

def it_initialies_the_circuit_as_open_on_first_access_with_empty_circuit(set_up_token_config_with_provider_and_circuit,
                                                                         set_up_env,
                                                                         identity_request_mock):

    self_token.token()

    assert self_token.TokenConfig().circuit_state_provider.circuit_state == 'closed'
    assert self_token.TokenConfig().circuit_state_provider.failures == 0


def it_sets_the_circuit_to_half_open_on_failure(set_up_token_config_with_provider_and_circuit,
                                                set_up_env,
                                                identity_request_error_mock):

    self_token.token()

    assert self_token.TokenConfig().circuit_state_provider.circuit_state == 'half_open'
    assert self_token.TokenConfig().circuit_state_provider.failures == 1


def it_errors_with_circuit_open(set_up_token_config_with_provider_and_open_circuit,
                                set_up_env,
                                identity_request_mock):

    result = self_token.token()

    assert result.is_left()
    assert result.error().error() == {'error': 'Circuit Open', 'code': 500, 'step': 'self token', 'ctx': {'circuit_state': 'open', 'failures': 3}}

def it_sets_the_circuit_to_half_closed_from_open_on_success(set_up_token_config_with_provider_and_open_circuit,
                                                            set_up_env,
                                                            identity_request_mock):

    traveller = time_machine.travel(chronos.time_with_delta(minutes=10))
    traveller.start()

    result = self_token.token()

    assert self_token.TokenConfig().circuit_state_provider.circuit_state == 'half_closed'
    assert self_token.TokenConfig().circuit_state_provider.failures == 0

    traveller.stop()


def test_with_a_dynamo_backed_circuit(dynamo_mock_empty,
                                      set_up_env,
                                      identity_request_mock,
                                      generate_expired_signed_jwt):

    set_up_token_config_with_provider_and_dynamo_backed_circuit(DynamoCircuitStore(circuit_name="test-circuit"))

    self_token.TokenConfig().token_persistence_provider.write(self_token.BEARER_TOKEN, generate_expired_signed_jwt)

    self_token.token()

    cir = repo.find_circuit_by_id('test-circuit')

    assert( cir.value.circuit_state) == 'closed'

def test_with_a_dynamo_backed_circuit_when_initialised(dynamo_mock_empty,
                                                       set_up_env,
                                                       identity_request_mock,
                                                       generate_expired_signed_jwt):
    repo.create_circuit('test-circuit')

    cir = repo.find_circuit_by_id('test-circuit')

    assert cir.is_right()

    set_up_token_config_with_provider_and_dynamo_backed_circuit(DynamoCircuitStore(circuit_name="test-circuit"))

    self_token.TokenConfig().token_persistence_provider.write(self_token.BEARER_TOKEN, generate_expired_signed_jwt)

    self_token.token()

    cir = repo.find_circuit_by_id('test-circuit')

    assert( cir.value.circuit_state) == 'closed'



def looks_like_a_jwt(possible_token):
    return (fn.match('^ey', possible_token) is not None) and (len(possible_token.split(".")) == 3)


@pytest.fixture
def identity_request_mock(requests_mock):
    requests_mock.post("https://test.host/token", json=success_token_callback, headers={'Content-Type': 'application/json; charset=utf-8'})

@pytest.fixture
def identity_request_error_mock(requests_mock):
    requests_mock.post("https://test.host/token",
                       json={"error": "access_denied","error_description": "Unauthorized"},
                       status_code=401,
                       headers={'Content-Type': 'application/json; charset=utf-8'})

@pytest.fixture
def set_up_token_config_with_provider():
    self_token.TokenConfig().configure(token_persistence_provider=TokenPersistenceProvider(), env=Env())

@pytest.fixture
def set_up_token_config_with_provider_and_circuit(circuit_state_provider):
    circuit.CircuitConfiguration().configure()
    self_token.TokenConfig().configure(token_persistence_provider=TokenPersistenceProvider(),
                                       env=Env(),
                                       circuit_state_provider=circuit_state_provider)

def set_up_token_config_with_provider_and_dynamo_backed_circuit(provider):
    self_token.TokenConfig().configure(token_persistence_provider=TokenPersistenceProvider(),
                                       env=Env(),
                                       circuit_state_provider=provider)


@pytest.fixture
def set_up_token_config_with_provider_and_open_circuit(circuit_state_provider_in_open_state):
    circuit.CircuitConfiguration().configure()
    self_token.TokenConfig().configure(token_persistence_provider=TokenPersistenceProvider(),
                                       env=Env(),
                                       circuit_state_provider=circuit_state_provider_in_open_state)


@pytest.fixture
def set_up_env():
    os.environ['CLIENT_ID'] = 'id'
    os.environ['CLIENT_SECRET'] = 'secret'
    os.environ['IDENTITY_TOKEN_ENDPOINT'] = 'https://test.host/token'

def success_token_callback(request, context):
    context.status_code = 200
    return success_token()

def success_token():
    return {
                "access_token": crypto.generate_signed_jwt(crypto.rsa_private_key()),
                "expires_in": 86400,
                "token_type": "Bearer"
            }
