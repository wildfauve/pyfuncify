from typing import Optional, List, Dict, Tuple, Callable, Any, Union, Protocol
from dataclasses import dataclass, field
from datetime import datetime
from pymonad.tools import curry
import json
from . import monad, span_tracer, logger, fn, tracer, error

from . import singleton

"""
App provides a number of helpers to build a Lambda event handling pipeline.  

@app.route
---------- 
Maintains simple routing state; mapping a function to a route "symbol.  The function will receive a Request object 
and is expected to pass it back wrapped in an monad.MEither, with the following state options (which will be understood by the 
app.responder fn.
+ monad.Right(Request.response), with a value JSON serialisable.
+ monad.Left(Request.response), with a value JSON serialisable.
+ monad.Left(Request), with error property containing an object which responds to 'error()' are returns a value JSON serialisable.

Example: 
@app.route('s3_bucket_name_part')
def run_a_handler(request: RequestEvent) -> monad.MEither:
    return handler(request=request)

Another approach is to use the 3-part Tuple form for the route template.  This is useful when wanting to pattern match on the 
event.  For an API Gateway event, the event kind is constructed like this:

                        ('API', {METHOD}, {path-template}); for example...

> ('API', 'GET', '/resourceBase/resource/uuid1')

Therefore a route defined as follows will match this pattern:
> @app.route(('API', 'GET', '/resourceBase/resource/{id}'))

Additionally, the Request.event property will (an instance of ApiGatewayRequestEvent) will include a 'path_params'
property (Dict) which will extract the templated arguments; for example:

> {'id': uuid1}     

 

app.pipeline
------------
The main event pipeline handler.  Your lambda initiates the pipeline by calling this function with:
+ the aws event.
+ the aws event context
+ the env (as a str)
+ an optional request parser
+ an optional policy information point initiator
+ a handler guard condition function.

It parses the event, using hints within the event to determine the app.route to be called.
+ S3 events.  The object S3StateChangeEvent is created with a collection of S3Object.  S3StateChangeEvent.kind is 
              used to determine the app.route symbol.  The fn domain_from_bucket_name() collects the unique bucket names
              (there should only be one), and takes the most significant part based on the default separator (DEFAULT_S3_BUCKET_SEP)
              This then is the symbol expected on an app.route.  

"""

DEFAULT_S3_BUCKET_SEP = "."
DEFAULT_RESPONSE_HDRS = {'Content-Type': 'application/json'}

@dataclass
class DataClassAbstract:
    def replace(self, key, value):
        setattr(self, key, value)
        return self

@dataclass
class RequestEvent(DataClassAbstract):
    event: Dict
    kind: str
    request_function: Callable

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
class ApiGatewayRequestEvent(RequestEvent):
    method: str
    headers: Dict
    path: str
    path_params: Dict
    body: str
    query_params: Optional[dict] = None
    request_session_state: Optional[Any] = None
    result_session_state: Optional[Any] = None


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
    response_headers: Optional[dict] = None

class AppError(error.PyFuncifyBaseError):
    @classmethod
    def dict_to_json_serialiser(cls):
        return DictToJsonSerialiser

    def error(self):
        return type(self).dict_to_json_serialiser()(super().error())

class Serialiser(Protocol):
    def __init__(self, serialisable: Any, serialisation: Callable):
        ...

    def serialise(self):
        ...


class DictToJsonSerialiser(Serialiser):
    def __init__(self, serialisable, serialisaton=None):
        self.serialisable = serialisable
        self.serialisation = serialisaton

    def serialise(self):
        return json.dumps(self.serialisable)



class RouteMap(singleton.Singleton):
    routes = {}

    def add_route(self, event: str, fn: Callable):
        self.routes[event] = fn
        pass

    def no_route(self, return_template=False) -> Union[Callable, Tuple[str, Callable]]:
        if return_template:
            return 'no_matching_routes', self.routes.get('no_matching_route', None)
        return self.routes.get('no_matching_route', None)

    def get_route(self, route: Union[str, Tuple]) -> Tuple[Union[str, Tuple], Callable]:
        if isinstance(route, str):
            return route, self.routes.get(route, self.no_route())
        possible_matching_routes = self.event_matches(route[0], route[1], route[2])
        if not possible_matching_routes or len(possible_matching_routes) > 1:
            return self.no_route(True)

        return possible_matching_routes[0][0], possible_matching_routes[0][1]

    def route_pattern_from_function(self, route_fn: Callable):
        route_item = fn.find(self.route_function_predicate(route_fn), self.routes.items())
        if route_item:
            return route_item[0]
        return None

    @curry(3)
    def route_function_predicate(self, route_function, route):
        return route[1] == route_function

    def event_matches(self, pos1, pos2, pos3) -> Dict[Tuple, str]:
        return list(fn.select(self.match_predicate(pos1, pos2, pos3), self.routes.items()))

    @curry(5)
    def match_predicate(self, pos1, pos2, pos3, route_item: Tuple[Union[str, Tuple], Callable]):
        if isinstance(route_item[0], str):
            return None
        event_type, event_qual, event_template = route_item[0]
        if event_type == pos1 and event_qual == pos2 and self.template_matches(event_template, pos3):
            return True
        return None

    def template_matches(self, template, event):
        return self.matcher(fn.rest(template.split("/")), fn.rest(event.split("/")))

    def matcher(self, template_xs: List, event_xs: List):
        template_fst, template_rst = fn.first(template_xs), fn.rest(template_xs)
        ev_fst, ev_rst = fn.first(event_xs), fn.rest(event_xs)
        if not template_fst and not ev_fst:
            return True
        if not template_fst and ev_fst:
            return False
        if template_fst and not ev_fst:
            return False
        if not self.ismatch(template_fst, ev_fst):
            return False
        return self.matcher(template_rst, ev_rst)

    def ismatch(self, template_token, ev_token):
        return ("{" in template_token and "}" in template_token) or template_token == ev_token


def route(event):
    """
    Route Mapper

    """
    def inner(fn):
        RouteMap().add_route(event=event, fn=fn)
    return inner


def std_noop_response(request):
    return monad.Right(request.replace('response', monad.Right({})))


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
        result = run_pipeline(event=event,
                              context=context,
                              env=env,
                              params_parser=params_parser,
                              pip_initiator=pip_initiator)
    else:
        result = monad.Left(build_value(event=event, context=context, env=env, error=guard_outcome.error()).value)
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
        return build_s3_state_change_event(event)
    if event.get('httpMethod', None):
        return build_http_event(event)
    return build_noop_event(event)

def build_noop_event(event):
    template, route_fn = route_fn_from_kind('no_matching_route')
    return NoopEvent(event=event,
                     kind=template,
                     request_function=route_fn)

def build_s3_state_change_event(event: Dict) -> S3StateChangeEvent:
    objects = s3_objects_from_event(event)
    kind = domain_from_bucket_name(objects)
    template, route_fn = route_fn_from_kind(kind)
    return S3StateChangeEvent(event=event,
                              kind=kind,
                              request_function=route_fn,
                              objects = objects)

def build_http_event(event: Dict) -> ApiGatewayRequestEvent:
    """
    method: str
    headers: Dict
    resource: str
    body: str
    query_params: Optional[dict]=None
    """
    kind = route_from_http_event(event['httpMethod'], event['path'])
    template, route_fn = route_fn_from_kind(kind)
    return ApiGatewayRequestEvent(kind=kind,
                                  request_function=route_fn,
                                  event=event,
                                  method=event['httpMethod'],
                                  headers=event['headers'],
                                  path=event['path'],
                                  path_params=path_template_to_params(kind[2], template[2]),
                                  body=event['body'],
                                  query_params=event['queryStringParameters'])

def route_from_http_event(method, path):
    return ('API', method, path)

def path_template_to_params(kind, template) -> Dict:
    """
    Remove the leading "/"
    """
    return params_comparer_builder(kind[1::].split("/"), template[1::].split("/"), {})

def params_comparer_builder(kind_xs, template_xs, injector):
    template_fst, template_rst = fn.first(template_xs), fn.rest(template_xs)
    kind_fst, kind_rst = fn.first(kind_xs), fn.rest(kind_xs)
    if not template_fst:
        return injector
    if "{" in template_fst:
        return params_comparer_builder(kind_rst,
                                       template_rst,
                                       {**injector, **{template_fst.replace("{", "").replace("}", ""): kind_fst}})
    return params_comparer_builder(kind_rst, template_rst, injector)


def s3_objects_from_event(s3_event: Dict) -> List[Dict]:
    return [s3_object(record) for record in s3_event['Records']]

def domain_from_bucket_name(objects: List[S3Object]) -> str:
    domain = {object.bucket for object in objects}
    if len(domain) > 1:
        return 'no_matching_route'
    return domain.pop().split(DEFAULT_S3_BUCKET_SEP)[0]


def s3_object(record: Dict) -> S3Object:
    return S3Object(bucket=fn.deep_get(record, ['s3', 'bucket', 'name']),
                    key=fn.deep_get(record, ['s3', 'object', 'key']))

def route_invoker(request):
    return request.event.request_function(request=request)

def route_fn_from_kind(kind):
    """
    Assumes that noop_event function is defined
    """
    return RouteMap().get_route(kind)


def template_from_route_fn(route_fn: Callable) -> Union[str, Tuple]:
    return RouteMap().route_pattern_from_function(route_fn)

def log_start(request):
    logger.log(level='info',
               msg='Start Handler',
               tracer=request.tracer,
               ctx={'event': event_kind_to_log_ctx(request)})
    return monad.Right(request)

def event_kind_to_log_ctx(request: Request) -> str:
    return "{event_type}:{kind}".format(event_type=type(request.event).__name__, kind=request.event.kind)

def responder(request):
    """
    The Request object must be returned with the following outcomes:
    + Wrapped in an Either.
    + 'response' property with the response to be sent wrapped in an Either.  The Request.value.result.value
      must be able to be serialised to JSON; using the Serialiser protocol
    + The Request can be Right, but the contained response is left.  In this case the response needs to implement an
      error() fn which returns an object serialisable to JSON.
    + Otherwise, Request.error() should be an Either-wrapping an object which responds to error() which is JSON serialisable
    """

    if request.is_right() and request.value.response.is_right():
        # When the processing pipeline completes successfully and the response Dict is a success
        body = {'statusCode': 200,
                'headers': build_headers(request.value.response_headers),
                'body': request.value.response.value.serialise()}
        status = 'ok'
    elif request.is_right() and request.value.response.is_left():
        # When the processing pipeline completes successfully but the response Dict is a failure
        body = {'statusCode': 200,
                'headers': build_headers(request.value.response_headers),
                'body':  request.value.response.error().serialise()}
        status = 'fail'
    else:
        # When the processing pipeline fails, with the error in the 'error' property of the request.
        body = {'statusCode': 400,
                'headers': build_headers(request.error().response_headers),
                'body':  request.error().error.error().serialise()}
        status = 'fail'


    logger.log(level='info', msg="End Handler", tracer=request.lift().tracer, ctx={}, status=status)

    return body

def build_headers(hdrs: Dict) -> Dict:
    return {**hdrs, **DEFAULT_RESPONSE_HDRS} if hdrs else DEFAULT_RESPONSE_HDRS

def init_tracer(env: str, aws_context=None):
    aws_request_id = aws_context.aws_request_id if aws_context else None
    return span_tracer.SpanTracer(env=env,
                                  kv={'handler_id': aws_request_id})
