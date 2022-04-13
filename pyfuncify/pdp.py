from typing import Callable, Any, Optional
from pymonad.tools import curry
from . import monad, fn

def activity_policy_pdp(name: str,
                        ctx: str,
                        namespace: Optional[str]=None,
                        error_cls: Any=None):
    """
    Adds activity-based policy checking to the function.

    + name: (str); to be included in the error_cls on error.
    + ctx:  (str); the activity being tested against.
    + namespace (Optional[str])
    + error_cls: (Optional[Any]); In the case of an authorisation error, the error class to be used to encapsulate the failure.
                 If not provides, a monad wrapped str is returned.

    The decorated function must have a kwarg called "pip" which is an instance of pip.PipConfig.
    + The pip has fn "subject", which returns a monad whose value has an activities fn which returns List[str].
      pip.PipConfig implements this protocol
      e.g pip.subject.value.activities => ['activity1', 'activity2']
    """
    def inner(fn):
        def invoke(*args, **kwargs):
            pip = kwargs.get('pip', None)
            if pip is None or pip.subject.is_left():
                return monad.Left(error_cls("Unauthorised", name, 401)) if error_cls else monad.Left("Unauthorised")

            if activity_policy(namespace, pip.subject.value.activities(), ctx):
                return monad.Right(fn(*args, **kwargs))
            else:
                return monad.Left(error_cls("Unauthorised", name, 401)) if error_cls else monad.Left("Unauthorised")
        return invoke
    return inner


@curry(3)
def activity_policy(namespace: Optional[str], activities: list, ctx: dict) -> monad.MEither:
    """
    Takes Activities from an activity collection, and tests the provided context against them.
    Example:
        $ activity_policy(['service:resource:action:action1'])("service:resource:action:action2")
    """
    return any(activity_matcher(ctx, activity) for activity in filter_for_service(namespace, activities))


def filter_for_service(namespace, activities: list) -> list:
    if not namespace:
        return activities
    return list(filter(lambda ct: namespace in ct, activities))

@curry(2)
def activity_matcher(context, activity):
    return matcher(fn.rest(context.split(":")), fn.rest(activity.split(":")))

def matcher(ctx_xs: list, activity_xs: list):
    ctx_fst, ctx_rst = fn.first(ctx_xs), fn.rest(ctx_xs)
    act_fst, act_rst = fn.first(activity_xs), fn.rest(activity_xs)
    if ctx_fst is None:
        return True
    if not ismatch(ctx_fst, act_fst):
        return False
    return matcher(ctx_rst, act_rst)

def ismatch(ctx_token, act_token):
    return act_token == "*" or ctx_token == act_token
