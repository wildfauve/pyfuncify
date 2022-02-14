import pytest

from .shared import *

from pyfuncify import app, monad, error

#
# Pipeline Functions
#

def it_executes_a_pipeline_from_s3_event(set_up_env,
                                         s3_event_hello):
    result = app.pipeline(event=s3_event_hello,
                          context={},
                          env=Env().env,
                          params_parser=noop_callable,
                          pip_initiator=noop_callable,
                          handler_guard_fn=noop_callable)

    assert result['statusCode'] == 200
    assert result['headers'] == {'Content-Type': 'application/json'}
    assert result['body'] == '{"hello": "there"}'


def it_fails_on_expectations():
    result = app.pipeline(event={},
                          context={},
                          env=Env().env,
                          params_parser=noop_callable,
                          pip_initiator=noop_callable,
                          handler_guard_fn=failed_expectations)
    assert result['statusCode'] == 400
    assert result['headers'] == {'Content-Type': 'application/json'}
    assert result['body'] == '{"error": "Env expectations failure", "code": 500, "step": "", "ctx": {}}'


def it_executes_the_noop_path():
    result = app.pipeline(event={},
                          context={},
                          env=Env().env,
                          params_parser=noop_callable,
                          pip_initiator=noop_callable,
                          handler_guard_fn=noop_callable)

    assert result['statusCode'] == 400
    assert result['headers'] == {'Content-Type': 'application/json'}
    assert result['body'] == '{"error": "no matching route", "code": 404, "step": "", "ctx": {}}'

#
# Router Functions
#

def it_creates_a_route():
    result = app.fn_for_event("hello")(dummy_request())

    assert result.value.response.value == {'hello': 'there'}


def it_routes_based_on_tuple():
    result = app.fn_for_event(('GET', '/resource/1'))(dummy_request())

    assert result.value.response.value == {'resource': '1'}


def it_defaults_to_no_matching_routes_when_not_found():
    result = app.fn_for_event("bad_route")(dummy_request())

    assert result.error().error.message == 'no matching route'
    

#
# Request Builder Functions
#

def it_identifies_an_s3_event(s3_event_hello):
    event = app.event_factory(s3_event_hello)

    assert isinstance(event, app.S3StateChangeEvent)
    assert event.kind == 'hello'
    assert len(event.objects) == 1
    assert event.objects[0].bucket == 'hello'
    assert event.objects[0].key == 'hello_file.json'

def it_identifies_an_api_gateway_get_event(api_gateway_event_get):
    event = app.event_factory(api_gateway_event_get)
    
    assert isinstance(event, app.ApiGatewayRequestEvent)
    assert event.kind == ('GET', '/resourceBase/resource/id/resource/id2')
    assert event.headers
    assert event.query_params == {'param1': 'a', 'param2': 'b'}


#
# Helpers
#

@app.route("hello")
def hello_handler(request):
    return monad.Right(request.replace('response', monad.Right({'hello': 'there'})))


@app.route("no_matching_route")
def handler_404(request):
    return monad.Left(request.replace('error', error.AppError(message='no matching route', code=404)))

@app.route(('GET', '/resource/1'))
def get_resource(request):
    return monad.Right(request.replace('response', monad.Right({'resource': '1'})))


def noop_callable(value):
    return monad.Right(value)

def failed_expectations(value):
    return monad.Left(error.AppError(message="Env expectations failure", code=500))


def dummy_request():
    return app.Request(event={}, context={}, tracer={})
