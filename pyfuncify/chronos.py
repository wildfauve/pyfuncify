from typing import Callable, List, Tuple
from dateutil.parser import parse as date_parser
from datetime import datetime, timedelta, timezone
from operator import methodcaller
from functools import reduce

def time_now(tz: timezone = timezone.utc, apply: Callable = None) -> datetime:
    """
    Generates Time now as a DateTime object without args.

    Add a TZ by providing a TZ arg:
    > time_now(tz=tz_utc)

    Call an addition functions on the datetime using the apply arg.
    + To format in iso8601, provide the iso8601 function
    > time_now(tz=tz_utc, apply=[iso8601()]
    """
    dt = datetime.now(tz)
    if apply is None:
        return dt
    return apply_appliers(dt, apply)

def apply_appliers(obj, appliers: List[Callable]):
    return reduce(apply_applier, appliers, obj)

def apply_applier(obj, applier: Callable):
    return applier(obj)

def iso8601():
    """
    Generates a callable to convert a time into a ISO8601 Format
    """
    return methodcaller('isoformat')

def epoch():
    """
    Generates a callable to convert a time into a unix epoch timestamp
    """
    return methodcaller('timestamp')

def tz_utc():
    return timezone.utc

def time_now_with_delta_seconds(delta):
    inc = timedelta(seconds=delta)
    return time_now(tz=timezone.utc) + inc

def time_with_delta(time=time_now(tz=timezone.utc), hours=0, minutes=0, seconds=0, direction='inc'):
    delta = timedelta(hours=hours, minutes=minutes, seconds=seconds)
    return time + delta if direction == 'inc' else time - delta


def iso_time_to_date_time(iso_time: str) -> datetime:
    return date_parser(iso_time)

def hours_from_start_from_year(time: datetime) -> int:
    return ((int(time.strftime("%j")) - 1) * 24) + time.hour

def hours_from_start_from_year_to_days_hours(start_time: datetime, hour: int) -> datetime:
    return time_with_delta(start_time, hours=hour)

def now_year_day() -> Tuple[int, int]:
    t = time_now(tz=timezone.utc)
    return (t.year, t.strftime("%j"))
