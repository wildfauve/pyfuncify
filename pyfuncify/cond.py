from pymonad.tools import curry

@curry(3)
def either(test, fn_ok, fn_fail, value):
    return fn_ok(value) if test(value) else fn_fail(value)
