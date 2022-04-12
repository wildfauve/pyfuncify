import json
from typing import Tuple
from jwcrypto import jwk, jwt
import requests
from pymonad.tools import curry
import collections
from simple_memory_cache import GLOBAL_CACHE
import re
import time

from . import monad, http_adapter, http, logger, singleton, circuit, chronos, error, crypto

jwks_cache = GLOBAL_CACHE.MemoryCachedVar('jwks_cache')

event_authorisation_hdr_key = "Authorization"

class JwksGetError(error.PyFuncifyError):
    pass


class SubjectTokenConfig(singleton.Singleton):
    """
    The Subject Token config is setup by the library caller to provide 2 arguments:

    + jwks_endpoint. Returns the endpoint of the IDP for the JWKS call.
    + circuit_state_provider.  An implementation of the CircuitStateProviderProtocol
    + asserted_iss: The iss must be asserted when decoding the JWT.  Provide the iss str as it will appear in the JWT
    """

    def configure(self,
                  jwks_endpoint: str,
                  asserted_iss: str = "",
                  circuit_state_provider: circuit.CircuitStateProviderProtocol = None):
        self.jwks_endpoint = jwks_endpoint
        self.circuit_state_provider = circuit_state_provider
        self.asserted_iss = asserted_iss
        pass


def parse_generate_id_token(serialised_jwt):
    """
    Takes an encoded JWT and returns an verified id_token
    """
    return cacheable_jwks() >> crypto.decode_jwt(claims_to_assert(), serialised_jwt) >> crypto.to_id_token


def claims_to_assert():
    return {'iss': SubjectTokenConfig().asserted_iss,
            'exp': int(chronos.time_now(tz=chronos.tz_utc(), apply=[chronos.epoch()]))}


def cacheable_jwks():
    return jwks_cache.get()


@jwks_cache.on_first_access
def _jwks():
    """
    Takes a key id (kid), requests the jwks from the identity jwks well-known service,
    returning a monadic jwt.JWKkeys
    """
    return monad.Right(jwks_resource()) >> get_jwks >> jwks_from_json


def jwk_cache_invalidate():
    jwks_cache.invalidate()


@monad.monadic_try(name="jwks_from_json")
def jwks_from_json(jwks: str):
    """
    Takes a JSON JWKS keyset and returns a wrapper object
    """
    _status, keys = jwks
    return jwk.JWKSet.from_json(keys)


@curry(3)
@monad.monadic_try(name="")
def rsa_key_from_kid(kid, op, jwks):
    """
    Takes a jwks object, extracts a public key based on KID and returns an
    openssl.rsa._RSAPublicKey
    """
    return jwks.get_key(kid).get_op_key(op)


def get_jwks(endpoint):
    """
    Get the JWKS json from the Identity well known resource.
    Inject the http_status_exception to test for a Right from the request, but a failure HTTP status
    """
    result = http_adapter.get(endpoint=endpoint,
                              name='jwks_service',
                              circuit_state_provider=SubjectTokenConfig().circuit_state_provider,
                              exception_test_fn=http.http_response_monad(__name__, http.extract_fn_raw),
                              error_cls=JwksGetError)

    return result


def jwks_resource():
    return SubjectTokenConfig().jwks_endpoint


def idp_endpoint():
    return Env.idp_endpoint


def parse_bearer_token(hdrs: dict) -> str:
    """
    Takes HTTP hdrs and extracts the bearer token from the Authorization header
    Support Camel and lowercase versions of the header
    """
    auth_hdr = hdrs.get(event_authorisation_hdr_key, hdrs.get(event_authorisation_hdr_key.lower()))
    return re.search(r'(Bearer)\s(.*)', auth_hdr).group(2)


def bearer_token_hdr(jwt):
    return {'authorization': "Bearer {}".format(jwt)}
