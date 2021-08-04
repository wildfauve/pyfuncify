from typing import Tuple, Callable
from simple_memory_cache import GLOBAL_CACHE
import time, datetime

from . import env, chronos, monad, http_adapter, error, constants, crypto, random_retry_window, logger, util

token_cache = GLOBAL_CACHE.MemoryCachedVar('token_cache')

class TokenError(error.ServiceError):
    pass

class TokenEnvError(error.ServiceError):
    pass

class TokenConfig(util.Singleton):

    def configure(self, token_persistence_provider: Callable) -> None:
        self.token_persistence_provider = token_persistence_provider
        pass


def token():
    if not env.Env.expected_set():
        return TokenEnvError(message="Token can not the retrieved due failure in env setup")
    result = get()
    if result.is_right() and (result.value.expired() or in_token_retry_window(result.value)):
        logger.log(level='info',
                   msg='Self Token Cache Miss',
                   ctx={'expired': result.value.expired(), 'in_window': in_token_retry_window(result.value)}, tracer=None)
        invalidate_cache()
        return get()
    return result

def get():
    result = cacheable_token()
    if result.is_right():
        return crypto.parse_generate_id_token(result.value)
    else:
        return result

def invalidate_cache():
    token_cache.invalidate()
    pass

@token_cache.on_first_access
def get_token():
    """
    First ever access is when the token is not set in parameter store and hence the environment:
        + Check the env anyway
        + get a new token from the token service
        + write it to parameter store
        + add it to the env and return it
    All other scenarios; when in env in either expired or not expired state
        + Get from Env
        + get a new token from the token service (check whether expired)
        + write it to parameter store (only when expired)
        + add it to the env and return it (only when expired)
    """
    # returns Either((status, name, value))
    result = bearer_token_from_env() >> from_cache >> token_service >> cache

    if result.is_right():
        return monad.Right(result.value[2])
    else:
        return result

def token_service(bearer_token):
    if bearer_token and crypto.bearer_token_valid(bearer_token) and not_in_token_retry_window(bearer_token):
        if bearer_token_from_env().value is None:
            return monad.Right(('from_cache', bearer_token))
        else:
            return monad.Right(('from_env', bearer_token))


    if bearer_token:
        not_in_wind = not_in_token_retry_window(bearer_token)
        token_state = (crypto.bearer_token_valid(bearer_token), crypto.parse_generate_id_token(bearer_token).value.exp)
    else:
        not_in_wind = None
        token_state = ("No Token", "No Exp")

    logger.log(level='info',
               msg='Self Token Expired or not in Window',
               ctx={'valid': token_state[0],
                    'exp': token_state[1],
                    'in_window': not_in_wind},
               tracer=None)

    result = http_adapter.post(endpoint=identity_token_endpoint(),
                               auth=(client_id(), client_secret()),
                               headers={},
                               body=token_request_data(),
                               encoding='urlencoded',
                               name='token_service')

    return monad.Right(('from_grant', result.value[1]['access_token'])) if result.is_right() else monad.Left(build_token_error(result.error()))

def from_cache(bearer_token):
    result = cache_reader(TokenConfig().token_persistence_provider)
    if result is None or result.is_left():
        return monad.Right(bearer_token)
    return monad.Right(result.value.value)

def cache(bearer_token_tuple: Tuple[str, str]) -> monad.MEither:
    """
    Cache the token.  This is a dispatcher.  It takes the configured token persistence provider (Parameter Store or Dynamo)
    and writes to the provider.
    """
    get_location, bearer_token = bearer_token_tuple
    if get_location == 'from_env':
        return monad.Right(('ok', constants.BEARER_TOKEN, bearer_token))

    if get_location == "from_cache":
        env.set_env_var_with_value(constants.BEARER_TOKEN, bearer_token)
        return monad.Right(('ok', constants.BEARER_TOKEN, bearer_token))

    result = cache_writer(TokenConfig().token_persistence_provider, bearer_token)
    env.set_env_var_with_value(constants.BEARER_TOKEN, bearer_token)
    return result

def cache_reader(provider: Callable):
    if not hasattr(provider, 'read'):
        return None
    return provider.read(key=constants.BEARER_TOKEN)


def cache_writer(provider: Callable, bearer_token: str) -> monad.MEither:
    result = provider.write(constants.BEARER_TOKEN, bearer_token)
    if result.is_right():
        return monad.Right(('ok', constants.BEARER_TOKEN, bearer_token))
    return result

def client_id() -> str:
    return env.Env.client_id()

def client_secret() -> str:
    return env.Env.client_secret()

def identity_token_endpoint() -> str:
    return env.Env.identity_token_endpoint()

def bearer_token_from_env():
    return monad.Right(env.Env.bearer_token())

def token_request_data():
    return {'audience': 'https://api.jarden.io', 'grant_type': 'client_credentials', 'scopes': 'openid'}

def not_in_token_retry_window(bearer_token: str) -> bool:
    id_token = crypto.parse_generate_id_token(bearer_token)
    return random_retry_window.left_of_window(width=constants.WINDOW_WIDTH,
                                              end=id_token.value.exp - constants.EXPIRY_THRESHOLD,
                                              at=int(chronos.time_now(tz=chronos.tz_utc(), apply=[chronos.epoch()])))

def in_token_retry_window(id_token):
    return random_retry_window.in_window(width=constants.WINDOW_WIDTH,
                                         end=id_token.exp - constants.EXPIRY_THRESHOLD,
                                         at=int(chronos.time_now(tz=chronos.tz_utc(), apply=[chronos.epoch()])))

def cacheable_token():
    return token_cache.get()

def build_token_error(result):
    return TokenError(message="Client Credentials Grant Failure with status {}".format(result.code),
                      name="self token",
                      ctx=result.ctx,
                      code=result.code, retryable=False)
