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

def it_creates_a_route_matched_on_string():
    template, route_fn = app.route_fn_from_kind('hello')
    result = route_fn(dummy_request())

    assert result.value.response.value.serialisable == {'hello': 'there'}


def it_routes_based_on_tuple_and_template():
    template, route_fn = app.route_fn_from_kind(('API', 'GET', '/resourceBase/resource/uuid1/resource/uuid2'))

    result = route_fn(dummy_request())

    assert result.value.response.value.serialisable == {'resource': 'uuid1'}


def it_implements_the_serialiser_protocol_for_the_response():
    template, route_fn = app.route_fn_from_kind(('API', 'GET', '/resourceBase/resource/uuid1/resource/uuid2'))

    result = route_fn(dummy_request())

    assert result.value.response.value.serialisable == {'resource': 'uuid1'}
    assert result.value.response.value.serialise() == '{"resource": "uuid1"}'


def it_defaults_to_no_matching_routes_when_not_found():
    template, route_fn = app.route_fn_from_kind("bad_route")

    result = route_fn(dummy_request())

    assert result.error().error.message == 'no matching route'

def it_finds_the_route_pattern_by_function():
    template, route_fn = app.route_fn_from_kind(('API', 'GET', '/resourceBase/resource/uuid1'))

    assert app.template_from_route_fn(route_fn) == ('API', 'GET', '/resourceBase/resource/{id1}')

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

    assert event.kind == ('API', 'GET', '/resourceBase/resource/uuid1')
    assert event.request_function
    assert event.path_params == {'id1': 'uuid1'}
    assert event.headers
    assert event.query_params == {'param1': 'a', 'param2': 'b'}


def it_identifies_an_api_gateway_get_event_for_a_nested_resource(api_gateway_event_get_nested_resource):
    event = app.event_factory(api_gateway_event_get_nested_resource)

    assert isinstance(event, app.ApiGatewayRequestEvent)

    assert event.kind == ('API', 'GET', '/resourceBase/resource/uuid1/resource/resource-uuid2')
    assert event.request_function
    assert event.path_params == {'id1': 'uuid1', 'id2': 'resource-uuid2'}


#
# Helpers
#

@app.route("hello")
def hello_handler(request):
    return monad.Right(request.replace('response', monad.Right(app.DictToJsonSerialiser({'hello': 'there'}))))


@app.route("no_matching_route")
def handler_404(request):
    return monad.Left(request.replace('error', app.AppError(message='no matching route', code=404)))


@app.route(('API', 'GET', '/resourceBase/resource/{id1}'))
def get_resource(request):
    if request.event:
        pass
    return monad.Right(request.replace('response', monad.Right(app.DictToJsonSerialiser({'resource': 'uuid1'}))))

@app.route(('API', 'GET', '/resourceBase/resource/{id1}/resource/{id2}'))
def get_nested_resource(request):
    if request.event:
        breakpoint()
    return monad.Right(request.replace('response', monad.Right(app.DictToJsonSerialiser({'resource': 'uuid1'}))))


def noop_callable(value):
    return monad.Right(value)

def failed_expectations(value):
    return monad.Left(app.AppError(message="Env expectations failure", code=500))


def dummy_request():
    return app.Request(event={}, context={}, tracer={})
