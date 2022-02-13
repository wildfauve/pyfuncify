from typing import Optional, List, Dict, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
import json
from . import monad, span_tracer, logger, fn, tracer, error

from . import singleton

@dataclass
class DataClassAbstract:
    def replace(self, key, value):
        setattr(self, key, value)
        return self

@dataclass
class RequestEvent(DataClassAbstract):
    event: Dict
    kind: str

@dataclass
class S3Object(DataClassAbstract):
    bucket: str
    key: str
    event_time: Optional[datetime] = None
    object: Optional[list] = None
    meta: Optional[Dict] = None

    def s3_event_path(self):
        return "{bucket}/{key}".format(bucket=self.bucket, key=self.key)


@dataclass
class NoopEvent(RequestEvent):
    pass

@dataclass
class S3StateChangeEvent(RequestEvent):
    objects: List[S3Object]


@dataclass
class Request(DataClassAbstract):
    event: RequestEvent
    context: dict
    tracer: tracer.Tracer
    request_handler: Optional[Callable] = None
    pip: Optional[dict] = None
    results: Optional[list] = None
    error: Optional[Any] = None
    response: Optional[dict] = None


class RouteMap(singleton.Singleton):
    routes = {}

    def add_route(self, event: str, fn: Callable):
        self.routes[event] = fn
        pass

    def get_route(self, route_name) -> Callable:
        return self.routes.get(route_name, self.routes.get('no_matching_route', None))

def fn_for_event(event: str) -> Callable:
    return RouteMap().get_route(event)

def route(event):
    """
    Route Mapper

    """
    def inner(fn):
        RouteMap().add_route(event=event, fn=fn)
    return inner



def pipeline(event: Dict, 
             context: Dict,
             env: str,
             params_parser: Callable, 
             pip_initiator: Callable, 
             handler_guard_fn: Callable):
    """
    Runs a general event handler pipeline.  Initiated by the main handler function.

    It takes the Lambda Event and Context objects.  It builds a request object and invokes the handler based on the event context
    and the routes provided by the handler via the @app.route decorator


    The main handler can then insert 3 functions to configure the pipeline:
    + params_parser: Takes the request object optionally transforms it, and returns it wrapper in an Either.
    + pip_initiator:  Policy Information Point
    + handler_guard_fn: A pre-processing guard fn to determine whether the handler should be invoked.  It returns an Either.  When the handler
                        shouldnt run the Either wraps an Exception.  In this case, the request is passed directly to the responder
    """
    guard_outcome = handler_guard_fn(event)

    if guard_outcome.is_right():
        result = run_pipeline(event, context, env, params_parser, pip_initiator)
    else:
        result = monad.Left(build_value(event, context, guard_outcome.error()).value)
    return responder(result)


def run_pipeline(event: Dict, context: Dict, env: Any, params_parser: Callable, pip_initiator: Callable):
    return build_value(event, context, env) >> log_start >> params_parser >> pip_initiator >> route_invoker


def build_value(event, context, env, error=None):
    """
    Initialises the Request object to be passed to the pipeline
    """
    req = Request(event=event_factory(event),
                  context=context,
                  tracer=init_tracer(env=env, aws_context=context),
                  pip=None,
                  response=None,
                  error=error)
    return monad.Right(req)

def event_factory(event: Dict) -> RequestEvent:
    if event.get('Records', None):
        objects = s3_objects_from_event(event)
        return S3StateChangeEvent(event=event, kind=domain_from_bucket_name(objects), objects=objects)
    return NoopEvent(event=event, kind='no_matching_route')


def s3_objects_from_event(s3_event: Dict) -> List[Dict]:
    return [s3_object(record) for record in s3_event['Records']]

def domain_from_bucket_name(objects: List[S3Object]) -> str:
    domain = {object.bucket for object in objects}
    if len(domain) > 1:
        return 'no_matching_route'
    return domain.pop().split('.')[0]


def s3_object(record: Dict) -> S3Object:
    return S3Object(bucket=fn.deep_get(record, ['s3', 'bucket', 'name']),
                    key=fn.deep_get(record, ['s3', 'object', 'key']))

def route_invoker(request):
    return route_fn_from_kind(request.event.kind)(request=request)

def route_fn_from_kind(kind):
    """
    Assumes that noop_event function is defined
    """
    return fn_for_event(event=kind)


def log_start(request):
    logger.log(level='info',
               msg='Start Handler',
               tracer=request.tracer,
               ctx={'event': event_kind_to_log_ctx(request)})
    return monad.Right(request)

def event_kind_to_log_ctx(request: Request) -> str:
    return "{event_type}:{kind}".format(event_type=type(request.event).__name__, kind=request.event.kind)

def responder(request):
    hdrs = {
        'Content-Type': 'application/json'
    }
    if request.is_right() and request.value.response.is_right():
        # When the processing pipeline completes successfully and the response Dict is a success
        body = {"statusCode": 200, 'headers': hdrs, "body": json.dumps(request.value.response.value)}
        status = 'ok'
    elif request.is_right() and request.value.response.is_left():
        # When the processing pipeline completes successfully but the response Dictis a failure
        body = {"statusCode": 400, 'headers': hdrs, "body":  json.dumps(request.value.response.error())}
        status = 'fail'
    else:
        # When the processing pipeline fails, with the error in the 'error' property of the request.
        body = {"statusCode": 400, 'headers': hdrs, "body":  json.dumps( request.error().error.error())}
        status = 'fail'


    logger.log(level='info', msg="End Handler", tracer=request.lift().tracer, ctx={}, status=status)

    return body


def init_tracer(env: str, aws_context=None):
    aws_request_id = aws_context.aws_request_id if aws_context else None
    return span_tracer.SpanTracer(env=env,
                                  kv={'handler_id': aws_request_id})
