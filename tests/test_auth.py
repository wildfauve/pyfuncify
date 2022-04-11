import pytest
from dataclasses import dataclass, field

from pyfuncify import authorisation as authz

@dataclass
class Pip:
    activities: set

def test_success_activity_auth(success_pip_activities_fn):
    result = authz.authorise_activity_policy(name="test_auth",
                                             namespace="service",
                                             ctx="service:resource:domain1:action1",
                                             pip_fn=success_pip_activities_fn,
                                             error_cls=None)(protected_fn)()


    assert result.is_right()

def test_failed_activity_auth(failed_pip_activities_fn):
    result = authz.authorise_activity_policy(name="test_auth",
                                             namespace="service",
                                             ctx="service:resource:domain1:action1",
                                             pip_fn=failed_pip_activities_fn,
                                             error_cls=None)(protected_fn)()

    assert result.is_left()


@pytest.fixture
def success_pip_activities_fn():
    def pip_fn():
        return {'sub': Pip(activities={'service:resource:domain1:action1'})}
    return pip_fn


@pytest.fixture
def failed_pip_activities_fn():
    def pip_fn():
        return {'sub': Pip(activities={'service:resource:domain2:action2'})}
    return pip_fn


def protected_fn(*args, **kwargs):
    return "called_successfully"
