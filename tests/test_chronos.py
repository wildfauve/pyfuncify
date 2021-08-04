import pytest

from pyfuncify import chronos

def it_returns_time_now_in_iso_utc():
    time_now_utc = chronos.time_now(tz=chronos.tz_utc())
    assert(time_now_utc.tzname()) == 'UTC'

def it_returns_time_in_iso8601_format():
    time_now_utc_iso = chronos.time_now(tz=chronos.tz_utc(), apply=[chronos.iso8601()])

    assert(isinstance(time_now_utc_iso,str)) == True
    assert('+00:00' in time_now_utc_iso) == True


def it_returns_time_as_epoch():
    time_epoch = chronos.time_now(tz=chronos.tz_utc(), apply=[chronos.epoch()])

    assert(isinstance(time_epoch, float)) == True
