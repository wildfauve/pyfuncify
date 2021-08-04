from pymonad.tools import curry
from . import monad, slack, env, fn, error


activity_namespace = "opbot"

def authorise_slack_verification_token_policy(name: str):
    """
    Checks the validity of the SLack verification token from the event
    """
    def inner(f):
        def invoke(*args, **kwargs):
            valid_token = slack.verify_slack_token(token=fn.deep_get(kwargs['request'].request, ['body', 'token']))
            if valid_token:
                return monad.Right(f(*args, **kwargs))
            else:
                return monad.Left(error.ServiceError("Unauthorised", name, 401))
        return invoke
    return inner


def authorise_slack_event_policy(name: str):
    """
    Adds slack event Signature check policy to handler
    """
    def inner(fn):
        def invoke(*args, **kwargs):
            valid_signature = slack.verify_slack_signature(event_body=kwargs['request'].request['body'],
                                                           event_headers=kwargs['request'].request['headers'],
                                                           slack_signing_secret=env.Env.slack_client_signing_secret())
            if valid_signature:
                return monad.Right(fn(*args, **kwargs))
            else:
                return monad.Left(error.ServiceError("Unauthorised", name, 401))
        return invoke
    return inner


def authorise_activity_policy(name: str, ctx: str):
    """
    Adds activity-based policy checking to the function.
    Ctx is injected (the tokenised activity ctx of the fn).
    The args must include the Policy Information Point (PIP) containing activity claims
    """
    def inner(f):
        def invoke(*args, **kwargs):
            pip = kwargs['request'].pip
            if pip is None:
                return monad.Left(error.ServiceError("Unauthorised", name, 401))
            if activity_policy(pip['subject'].activities, ctx):
                return monad.Right(f(*args, **kwargs))
            else:
                return monad.Left(error.ServiceError("Unauthorised", name, 401))
        return invoke
    return inner


@curry(2)
def activity_policy(activities: list, ctx: dict) -> monad.MEither:
    """
    Takes Activities from an activity collection, and tests the provided context against them.
    Example:
        $ activity_policy(['opbot:resource:mention:request'])("opbot:resource:mention:request")
    """
    return any(activity_matcher(ctx, activity) for activity in filter_for_service(activities))


def filter_for_service(ctx: list) -> list:
    return list(filter(lambda ct: activity_namespace in ct, ctx))

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
