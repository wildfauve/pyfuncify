import requests
import backoff
from typing import Dict, Tuple, Any

from . import monad, http, logger, circuit

@circuit.circuit_breaker()
@backoff.on_predicate(backoff.expo, circuit.monad_failure_predicate, max_tries=circuit.max_retries(), jitter=None)
def post(endpoint, body, auth=None, headers={}, encoding='json', circuit_config=None, name: str = __name__, http_timeout: float=5.0):
    return invoke(endpoint=endpoint, headers=headers, auth=auth, body=body, encoding=encoding, name=name, http_timeout=http_timeout)

@monad.monadic_try(name="http_adapter", exception_test_fn=http.http_response_monad(__name__, http.extract_by_content_type))
@logger.with_perf_log(perf_log_type='http', name=__name__)
def invoke(endpoint: str, headers: Dict, auth: Tuple, body: Any, encoding: str, name: str, http_timeout: float):
    if encoding == 'json':
        return requests.post(endpoint, auth=auth, headers=headers, json=body, timeout=http_timeout)
    else:
        return requests.post(endpoint, auth=auth, headers={**headers, **encoding_to_content_type(encoding)}, data=body, timeout=http_timeout)

def encoding_to_content_type(encoding):
    encodings = {'urlencoded': {'Content-Type': 'application/x-www-form-urlencoded'}}
    return encodings.get(encoding, {})
