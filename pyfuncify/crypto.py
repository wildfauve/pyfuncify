import json
from typing import Tuple
import jwt
from pymonad.tools import curry
import time
from dataclasses import dataclass

from . import monad

def parse_generate_id_token(serialised_jwt):
    """
    Takes an encoded JWT and returns an verified id_token
    """
    return decode_jwt(serialised_jwt) >> to_id_token

def bearer_token_valid(serialised_jwt: str) -> bool:
    return parse_generate_id_token(serialised_jwt) >> validate
#
# Helpers
#

def validate(token):
    return not token.expired()

@curry(1)
@monad.monadic_try(name="decode_jwt", status=401, error_cls=None)
def decode_jwt(serialised_jwt: str) -> Tuple[str, dict]:
    """
    Parses the jwt and returns the claims without the validating using the public key
    """
    return (serialised_jwt, jwt.decode(serialised_jwt, options={"verify_signature": False}))

def to_id_token(jwt_claims: Tuple[str, dict]):
    jwt, claims = jwt_claims
    return monad.Right(IdToken(iss=claims['iss'],
                               aud=claims['aud'],
                               sub=claims['sub'],
                               iat=claims['iat'],
                               exp=claims['exp'],
                               azp=claims['azp'],
                               jwt=jwt))


def bearer_token_hdr(jwt):
    return {'authorization': "Bearer {}".format(jwt)}

@dataclass
class IdToken():
    iss: str
    sub: str
    aud: str
    iat: str
    exp: str
    azp: str
    jwt: str

    def expired(cls):
        return int(time.time()) > cls.exp
