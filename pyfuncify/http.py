from typing import Dict, Tuple
from pymonad.tools import curry
import requests

from . import monad

class HttpError(error.PyFuncifyError):
    pass

class BearerTokenAuth(requests.auth.AuthBase):
    """
    Custom Bearer token Authn
    """
    def __init__(self, token):
        self.token = token
    def __call__(self, r):
        r.headers["authorization"] = "Bearer " + self.token
        return r


def extract_fn_raw(response):
    return response.text

def extract_fn_json(response):
    return response.json()

def extract_fn_text(response):
    return response.text()

def extract_by_content_type(response):
    """
    Looks for the content type in the response; e.g. application/json; charset=utf-8
    and find the appropriate extract fn and apply the response to that fn.  Otherwise return raw.
    """
    factory = {'application/json': extract_fn_json, 'application/text': extract_fn_text}
    return factory.get(response.headers['Content-Type'].split(";")[0], extract_fn_raw)(response)

@curry(3)
def http_response_monad(step, extract_fn, response) -> Tuple[int, dict]:
    if response.value.status_code in [200,201]:
        return monad.Right((response.value.status_code, extract_fn(response.value)))
    else:
        return monad.Left(HttpError(message="HTTP Error Response; Method:{}; Host: {}".format(response.value.request.method, response.value.request.hostname),
                                    name=step,
                                    code=response.value.status_code,
                                    ctx=extract_fn(response.value)))
