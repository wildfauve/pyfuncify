import pytest

from pyfuncify import monad, error

def test_try_success():
    assert success_function().is_right()


def test_custom_expection_test_fn():
    assert success_function_with_custom_success().is_left()


def test_exception_calls_error_return_fn():
    expected_result = {'error': 'division by zero', 'code': 500, 'step': 'exception_thrower', 'ctx': {}}
    assert exception_thrower() == expected_result


#
# Helpers
#
def turn_true_into_error(result):
    if result.is_right() and result.value:
        return monad.Left(True)
    return result


def wrap_error_in_dict(result):
    return result.error().error()

@monad.monadic_try()
def success_function():
    return True


@monad.monadic_try(exception_test_fn=turn_true_into_error)
def success_function_with_custom_success():
    return True


@monad.monadic_try(error_result_fn=wrap_error_in_dict, error_cls=error.PyFuncifyError, status=500)
def exception_thrower():
    return 1/0
