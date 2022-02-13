import pytest

from .shared import *

from pyfuncify import app, monad, error

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


def it_creates_a_route():
    result = app.fn_for_event("hello")(dummy_request())

    assert result.value.response.value == {'hello': 'there'}

def it_defaults_to_no_matching_routes_when_not_found():
    result = app.fn_for_event("bad_route")(dummy_request())

    assert result.error().error.message == 'no matching route'
    

@app.route("hello")
def hello_handler(request):
    return monad.Right(request.replace('response', monad.Right({'hello': 'there'})))


@app.route("no_matching_route")
def handler_404(request):
    return monad.Left(request.replace('error', error.AppError(message='no matching route', code=404)))


def noop_callable(value):
    return monad.Right(value)


def dummy_request():
    return app.Request(event={}, context={}, tracer={})
