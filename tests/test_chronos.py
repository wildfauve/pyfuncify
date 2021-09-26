import pytest
from datetime import datetime
import time_machine

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




@time_machine.travel(datetime(2021, 8, 2, 9, 5, tzinfo=chronos.tz_utc()))
def it_generates_now_year_and_day():
    year, day = chronos.now_year_day()

    assert year == 2021
    assert day == 214