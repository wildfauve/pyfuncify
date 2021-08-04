import requests
import backoff
from typing import Dict, Tuple, Any

from . import monad, http, logger, circuit, constants

@circuit.circuit_breaker()
@backoff.on_predicate(backoff.expo, circuit.monad_failure_predicate, max_tries=circuit.max_retries(), jitter=None)
def post(endpoint, body, auth=None, headers={}, encoding='json', circuit_config=None, name: str = __name__):
    return invoke(endpoint=endpoint, headers=headers, auth=auth, body=body, encoding=encoding, name=name)

@monad.monadic_try(name="http_adapter", exception_test_fn=http.http_response_monad(__name__, http.extract_by_content_type))
@logger.with_perf_log(perf_log_type='http', name=__name__)
def invoke(endpoint: str, headers: Dict, auth: Tuple, body: Any, encoding: str, name: str):
    if encoding == 'json':
        return requests.post(endpoint, auth=auth, headers=headers, json=body, timeout=constants.HTTP_TIMEOUT)
    else:
        return requests.post(endpoint, auth=auth, headers={**headers, **encoding_to_content_type(encoding)}, data=body, timeout=constants.HTTP_TIMEOUT)

def encoding_to_content_type(encoding):
    encodings = {'urlencoded': {'Content-Type': 'application/x-www-form-urlencoded'}}
    return encodings.get(encoding, {})
