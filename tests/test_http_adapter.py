import pytest
import requests

from pyfuncify import http_adapter


def test_success_http_call(request_mock):
    result = http_adapter.post(endpoint="https://example.host/resource",
                               auth=None,
                               body={'a': "mock_body"},
                               http_timeout=10.0)

    assert(result.is_right()) == True

    status, body = result.value

    assert status == 200
    assert body == {'hello': 'there'}


def test_failed_http_call(request_http_failure_mock):
    result = http_adapter.post(endpoint="https://example.host/resource",
                               auth=None,
                               body={'a': "mock_body"})

    assert(result.is_left()) == True
    assert(result.error().ctx) == {'status': 'boom'}
    assert(result.error().code) == 401

@pytest.fixture
def request_mock(requests_mock):
    requests_mock.post("https://example.host/resource", json={'hello': "there"}, headers={'Content-Type': 'application/json; charset=utf-8'})

@pytest.fixture
def request_http_failure_mock(requests_mock):
    requests_mock.post("https://example.host/resource",
                       json={'status': "boom"},
                       status_code=401,
                       headers={'Content-Type': 'application/json; charset=utf-8'})
