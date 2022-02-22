import pytest
import jwt
import json
import time
from typing import Tuple

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa

from pyfuncify import chronos

"""
Test fixtures for JWTs and JWKS

Example:
    To generate a serialised and signed JWT for inbound API tests (that is, events which include a Bearer token
    in the HTTP headers):
        $ key = rsa_private_key()
        $ jwt = generate_signed_jwt(key)

Example:
    To generate a JWK Set (JWKS) to simulate the /.well-known/jwks.json of an OpenID Connect Authorisation Service:
        $ rsa_key = rsa_key_pair(kid="kid_id_1")
        $ jwks = jwk_key_set(rsa_key)

"""

def rsa_private_key():
    """
    Args:
        kid: a unique id for the key

    Returns:
        JWK pub/priv key pair with a KID
    """
    return rsa.generate_private_key(backend=default_backend(),public_exponent=65537,key_size=2048)

@pytest.fixture
def rsa_key_pair(kid="1"):
    """
    Args:
        kid: a unique id for the key

    Returns:
        JWK pub/priv key pair with a KID
    """
    return jwk.JWK.generate(kty='RSA', size=2048, kid=kid)


def generate_signed_jwt(rsa_private_key):
    """
    Generates an RSA signed JWT is serialised form
    """
    return jwt.encode(jwt_claims(), rsa_private_key, algorithm="RS256")

@pytest.fixture
def generate_expired_signed_jwt():
    """
    Generates an RSA signed JWT is serialised form which is expired
    """
    return jwt.encode(jwt_claims_expired(), rsa_private_key(), algorithm="RS256")

@pytest.fixture
def generate_valid_signed_jwt():
    return generate_signed_jwt(rsa_private_key())

@pytest.fixture
def jwk_key_set(rsa_key_pair):
    """
    Takes an RSA key pair and returns a JWKS containing the public key
    """
    priv, pub = jwk_rsa_keys(rsa_key_pair)
    return dict(keys=[json.loads(pub)])


def jwk_rsa_keys(pair) -> Tuple:
    """
    Returns a tuple of the priv and pub keys as a JSON encoded JWK
    """
    return pair.export_private(), pair.export_public()


def jwt_claims_expired():
    claims = jwt_claims()
    claims['exp'] = (int(chronos.time_now(tz=chronos.tz_utc(), apply=[chronos.epoch()])) - (60*60))
    return claims

def jwt_claims():
    return dict(iss="https://jarden-uat.au.auth0.com/",
                sub="1@clients",
                aud="https://api.jarden.io",
                iat=int(chronos.time_now(tz=chronos.tz_utc(), apply=[chronos.epoch()])),
                exp=(int(chronos.time_now(tz=chronos.tz_utc(), apply=[chronos.epoch()])) + (60*60*24)),
                azp="CJ5HhFu2H303aKMukkW9SDhJS1mQVzVD",
                gty="client-credentials")
