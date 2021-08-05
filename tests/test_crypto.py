import pytest

from pyfuncify import crypto

from .shared import crypto as fixture_crypto

def test_extract_claims_from_token():
    result = crypto.parse_generate_id_token(fixture_crypto.generate_signed_jwt(fixture_crypto.rsa_private_key()))

    assert(result.is_right()) == True
    assert(result.value.sub) == "1@clients"

def test_malformed_jwt():
    result = crypto.parse_generate_id_token("malformed")

    assert(result.is_right()) == False
