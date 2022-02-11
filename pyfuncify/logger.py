from typing import Dict, Optional, Union, Tuple
from pino import pino
import sys
from functools import reduce
import time

from . tracer import Tracer
from . import chronos

# public interface
def log(level: str, msg: str, tracer: Optional[Tracer], status: str = 'ok', ctx: Dict[str, str] = {}) -> None:
    levels = {'info': info}
    levels.get(level, info)(logger(), msg, meta(tracer, status, ctx))

def with_perf_log(perf_log_type: str = None, name: str = None):
    """
    Decorator which wraps the fn in a timer and writes a performance log
    """
    def inner(fn):
        def invoke(*args, **kwargs):
            t1 = time.time()
            result = fn(*args, **kwargs)
            t2 = time.time()
            if perf_log_type == 'http' and 'name' in kwargs:
                fn_name = kwargs['name']
            else:
                fn_name = name or fn.__name__
            perf_log(fn=fn_name, delta_t=(t2-t1)*1000.0)
            return result
        return invoke
    return inner


def log_decorator(fn):
    def log_writer(*args, **kwargs):
        log(
            level='info',
            msg='Handling Command {fn}'.format(fn=fn.__name__),
            ctx=args[0].event,
            tracer=args[0].tracer
        )
        return fn(*args, **kwargs)
    return log_writer

def logger():
    return pino(bindings={"apptype": "prototype", "context": "main"})

def info(lgr, msg: str, meta: Dict) -> None:
    lgr.info(meta, msg)

def perf_log(fn: str, delta_t: float):
    info(logger(), "PerfLog", {'ctx': {'fn': fn, 'delta_t': delta_t}})

def meta(tracer, status: Union[str, int], ctx: Dict):
    coersed_ctx = reduce(type_coersed, ctx.items(), {})
    return {**trace_meta(tracer), **{'ctx': coersed_ctx}, **{'status': status}}

def type_coersed(result: Dict, kv: Tuple):
    k, v = kv
    if type(v) in [str, int]:
        result[k] = v
        return result
    coerse_fn = getattr(sys.modules[__name__], "coerser_{}".format(type(v).__name__), None)
    if coerse_fn:
        result[k] = coerse_fn(v)
    return result

def coerser_datetime(dt):
    return chronos.iso8601()(dt)

def trace_meta(tracer):
    return tracer.serialise() if tracer else {}
