import os
import pytest
import time_machine
import datetime as dt

from .shared import *

from pyfuncify import self_token, chronos, fn, monad

# from common import parameter_store, constants, chronos, fn
# from functions.trading_event_publisher.domain import db_cache

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



def setup_function():
    self_token.invalidate_cache()
    if 'BEARER_TOKEN' in os.environ:
        del os.environ['BEARER_TOKEN']


def test_get_token_for_the_very_first_time(set_up_token_config_with_provider, set_up_env, identity_request_mock):
    result = self_token.token()

    assert result.is_right() == True
    assert result.value.sub == "1@clients"

def test_token_persisted_in_provider(set_up_token_config_with_provider, set_up_env, identity_request_mock):
    result = self_token.token()

    token = self_token.TokenConfig().token_persistence_provider.read(self_token.BEARER_TOKEN)

    assert result.value.jwt == token.value.value


def it_refreshes_the_token_from_cache_when_not_in_env(set_up_token_config_with_provider,
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
    assert result.error().message == 'Client Credentials Grant Failure with status 401'
    assert result.error().ctx == {'error': 'access_denied', 'error_description': 'Unauthorized'}
    assert result.error().code == 401

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