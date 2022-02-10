import pytest

from pyfuncify import app

def it_creates_a_route():
    assert app.fn_for_event("hello-route")() == "hello"

def it_defaults_to_no_matching_routes_when_not_found():
    assert app.fn_for_event("bad_route")() == 404

@app.route("hello-route")
def hello_handler():
    return "hello"

@app.route("no_matching_route")
def handler_404():
    return 404