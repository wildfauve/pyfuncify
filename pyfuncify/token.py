import json
from typing import Tuple
from jwcrypto import jwk, jwt
import requests
from pymonad.tools import curry
import collections
from simple_memory_cache import GLOBAL_CACHE
import re
import time

from . import *

jwks_cache = GLOBAL_CACHE.MemoryCachedVar('jwks_cache')

event_authorisation_hdr_key = "Authorization"

def std_claims() -> dict :
    return dict(exp=time.time(), aud="https://api.jarden.io")

def parse_generate_id_token(serialised_jwt, asserted_claims=std_claims()):
    """
    Takes an encoded JWT and returns an verified id_token
    """
    return cacheable_jwks() >> decode_jwt(serialised_jwt, asserted_claims) >> to_id_token


@curry(3)
@monad.monadic_try(name="decode_jwt", status=401)
def decode_jwt(serialised_jwt: str, asserted_claims: dict, jwks) -> Tuple:
    """
    Parses the jwt, validing the signature (from JWKS) and the EXP/AUD claims
    """
    return (serialised_jwt, jwt.JWT(jwt=serialised_jwt, key=jwks, check_claims=asserted_claims))

def to_id_token(decoded_jwt_tuple):
    jwt, decoded_jwt = decoded_jwt_tuple
    return M.Right(IdToken(jwt, (json.loads(decoded_jwt.claims))))

def cacheable_jwks():
    return jwks_cache.get()

@jwks_cache.on_first_access
def _jwks():
    """
    Takes a key id (kid), requests the jwks from the identity jwks well-known service,
    returning a monadic jwt.JWKkeys
    """
    return get_jwks() >> jwks_from_json

def jwk_cache_invalidate():
    jwks_cache.invalidate()

@monad.monadic_try(name="jwks_from_json")
def jwks_from_json(jwks: str):
    """
    Takes a JSON JWKS keyset and returns a wrapper object
    """
    return jwk.JWKSet.from_json(jwks)

@curry(3)
@monad.monadic_try(name="")
def rsa_key_from_kid(kid, op, jwks):
    """
    Takes a jwks object, extracts a public key based on KID and returns an
    openssl.rsa._RSAPublicKey
    """
    return jwks.get_key(kid).get_op_key(op)


@monad.monadic_try(name="get_jwks", exception_test_fn=http.http_status_exception(http.extract_fn_raw))
@logger.with_perf_log(name=__name__)
def get_jwks():
    """
    Get the JWKS json from the Identity well known resource.
    Inject the http_status_exception to test for a Right from the request, but a failure HTTP status
    """
    return requests.get(jwks_resource())


def jwks_resource():
    return "{}/.well-known/jwks.json".format(identity_endpoint())

def identity_endpoint():
    return Env.identity_endpoint

def parse_bearer_token(hdrs: dict) -> str:
    """
    Takes HTTP hdrs and extracts the bearer token from the Authorization header
    Support Camel and lowercase versions of the header
    """
    auth_hdr = hdrs.get(event_authorisation_hdr_key, hdrs.get(event_authorisation_hdr_key.lower()))
    return re.search('(Bearer)\s(.*)', auth_hdr).group(2)

def bearer_token_hdr(jwt):
    return {'authorization': "Bearer {}".format(jwt)}

class IdToken:
    claims_value = collections.namedtuple('IdTokenClaims', ['iss', 'sub', 'aud', 'iat', 'exp', 'azp'])

    def __init__(self, jwt, claims):
        self.jwt = jwt
        self.claims = claims

    def id_claims(self):
        return self.claims_value(iss=self.claims['iss'],
                                 sub=self.claims['sub'],
                                 aud=self.claims['aud'],
                                 iat=self.claims['iat'],
                                 exp=self.claims['exp'],
                                 azp=self.claims['azp'])
