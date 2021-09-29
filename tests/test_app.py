import pytest

from pyfuncify import app

def it_creates_a_route():
    assert app.fn_for_event("hello-route")() == "hello"


@app.route("hello-route")
def hello_handler():
    return "hello"
