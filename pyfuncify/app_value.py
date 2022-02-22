from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from dataclasses import dataclass

from . import tracer, error, app_serialisers

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

    def returnable_session_state(self):
        return False

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
    web_session: Optional[Any] = None

    def clear_session(self):
        self.web_session = None
        self

    def returnable_session_state(self):
        return True



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
        return app_serialisers.DictToJsonSerialiser

    def error(self):
        return type(self).dict_to_json_serialiser()(super().error())
