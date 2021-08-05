from typing import Callable, Any
from pymonad.tools import curry
from . import monad, fn

def authorise_activity_policy(name: str, ctx: str, namespace: str, pip_fn: Callable, error_cls: Any=None):
    """
    Adds activity-based policy checking to the function.

    + Ctx is injected (the tokenised activity ctx of the fn).
    + pip_fn is a callable which provides the PIP.  The PIP MUST be a dict with a 'subject' key, which has a function
      'activities' which returns a set of activities.  For example:
      {'subject': SlackSubject(slack_user='U09U563QC', profile_id='uuid_1', activities={'opbot:resource:mention:request', 'marketdata:resource:instrument:read-all'})}
    """
    def inner(fn):
        def invoke(*args, **kwargs):
            pip = pip_fn()
            if pip is None:
                return monad.Left(error_cls("Unauthorised", name, 401)) if error_cls else monad.Left("Unauthorised")
            if activity_policy(namespace, pip['subject'].activities, ctx):
                return monad.Right(fn(*args, **kwargs))
            else:
                return monad.Left(error_cls("Unauthorised", name, 401)) if error_cls else monad.Left("Unauthorised")
        return invoke
    return inner


@curry(3)
def activity_policy(namespace: str, activities: list, ctx: dict) -> monad.MEither:
    """
    Takes Activities from an activity collection, and tests the provided context against them.
    Example:
        $ activity_policy(['opbot:resource:mention:request'])("opbot:resource:mention:request")
    """
    return any(activity_matcher(ctx, activity) for activity in filter_for_service(namespace, activities))


def filter_for_service(namespace, ctx: list) -> list:
    return list(filter(lambda ct: namespace in ct, ctx))

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
