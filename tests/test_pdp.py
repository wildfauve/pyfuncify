import pytest

from pyfuncify import error, pdp , pip, monad

class UnAuthorised(error.PyFuncifyError):
    pass

def test_success_activity_auth():
    result = call_the_service(pip=success_pip_activities())

    assert result.is_right()
    assert result.value == "called_successfully"


def test_failed_activity_auth():
    result = call_the_service(pip=failed_pip_activities())

    assert result.is_left()
    assert isinstance(result.error(), UnAuthorised)


#
# Helpers
#
def success_pip_activities():
    return pip.Pip(id_token=None,
                   subject=userinfo_mock(['service:resource:domain1:action1']))

def failed_pip_activities():
    return pip.Pip(id_token=None,
                   subject=userinfo_mock(['service:resource:domain1:action2']))


@pdp.activity_policy_pdp("a_service", "service:resource:domain1:action1", "service", UnAuthorised)
def call_the_service(pip: pip.Pip) -> monad.MEither:
    return "called_successfully"


def userinfo_mock(activities):
    class Subject(pip.UserinfoStateProtocol):
        def __init__(self, state):
            self.state = state

        def activities(self):
            return self.state['activities']

    return monad.Right(Subject(state={'sub': 'subject1', 'activities': activities}))
