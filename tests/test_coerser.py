from pyfuncify import coerser, chronos
#
# nested_coerse
#
def it_replaces_things():
    import datetime
    d = {"a": {"b": {'c': chronos.time_now()}, 'd': 2}, 'x': [1,2,3]}

    result = coerser.nested_coerse({}, d)

    assert isinstance(result['a']['b']['c'], str)