from pyfuncify import subject_token
from pyfuncify import crypto as Cy

from jwcrypto import jwk, jwt
import time

from .shared import *


def setup_module():
    crypto.Idp().init_keys(jwk=jwk_rsa_key_pair())

def setup_function(fn):
    set_up_token_config()
    subject_token.jwk_cache_invalidate()

def test_get_jwks(jwks_mock):
    jwks = subject_token.cacheable_jwks()

    assert jwks.is_right()
    assert isinstance(jwks.value, jwk.JWKSet)

def test_get_jwks_request_failure(jwks_request_failure_mock):
    jwks = subject_token.cacheable_jwks()

    assert jwks.is_left()
    assert jwks.error().name == "jwks_service"
    assert jwks.error().message == "http_failure"

def test_get_jwks_with_key_id(jwks_mock):

    jwks = subject_token.cacheable_jwks().value
    assert isinstance(jwks.get_key("1"), jwk.JWK)
    assert jwks.get_key("bad_key_id") is None

def test_generate_id_token_from_jwt(jwks_mock):
    jwt = crypto.generate_signed_jwt(crypto.Idp().jwk)

    id_token = subject_token.parse_generate_id_token(jwt)

    assert id_token.is_right()
    assert id_token.value.id_claims().sub == "1@clients"

def test_token_failed_when_expired(jwks_mock):
    exp = (int(chronos.time_now(tz=chronos.tz_utc(), apply=[chronos.epoch()])) - (60))
    jwt = crypto.generate_signed_jwt(crypto.Idp().jwk, exp)

    id_token = subject_token.parse_generate_id_token(jwt)

    assert id_token.is_left()
    assert isinstance(id_token.error(), Cy.JwtDecodingError)
    assert "Expired at {}".format(exp) in id_token.error().message

def test_token_failed_when_jwks_failure(jwks_request_failure_mock):
    jwt = crypto.generate_signed_jwt(crypto.Idp().jwk)

    id_token = subject_token.parse_generate_id_token(jwt)

    assert id_token.is_left()
    assert isinstance(id_token.error(), subject_token.JwksGetError)
    assert id_token.error().message == "http_failure"
#
# Helpers
#
def set_up_token_config():
    subject_token.SubjectTokenConfig().configure(jwks_endpoint="https://idp.example.com/.well-known/jwks",
                                                 asserted_iss="https://idp.example.com/")

