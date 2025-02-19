# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2021 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

import datetime as dt

import pytest
import pytz
from dateutil.tz import datetime_exists

from hypothesis import assume, given
from hypothesis.errors import InvalidArgument
from hypothesis.extra.pytz import timezones
from hypothesis.strategies import data, datetimes, just, sampled_from, times
from hypothesis.strategies._internal.datetime import datetime_does_not_exist

from tests.common.debug import (
    assert_all_examples,
    assert_can_trigger_event,
    find_any,
    minimal,
)


def test_utc_is_minimal():
    assert pytz.UTC is minimal(timezones())


def test_can_generate_non_naive_time():
    assert minimal(times(timezones=timezones()), lambda d: d.tzinfo).tzinfo == pytz.UTC


def test_can_generate_non_naive_datetime():
    assert (
        minimal(datetimes(timezones=timezones()), lambda d: d.tzinfo).tzinfo == pytz.UTC
    )


@given(datetimes(timezones=timezones()))
def test_timezone_aware_datetimes_are_timezone_aware(dt):
    assert dt.tzinfo is not None


@given(sampled_from(["min_value", "max_value"]), datetimes(timezones=timezones()))
def test_datetime_bounds_must_be_naive(name, val):
    with pytest.raises(InvalidArgument):
        datetimes(**{name: val}).validate()


def test_underflow_in_simplify():
    # we shouldn't trigger a pytz bug when we're simplifying
    minimal(
        datetimes(
            max_value=dt.datetime.min + dt.timedelta(days=3), timezones=timezones()
        ),
        lambda x: x.tzinfo != pytz.UTC,
    )


def test_overflow_in_simplify():
    # we shouldn't trigger a pytz bug when we're simplifying
    minimal(
        datetimes(
            min_value=dt.datetime.max - dt.timedelta(days=3), timezones=timezones()
        ),
        lambda x: x.tzinfo != pytz.UTC,
    )


def test_timezones_arg_to_datetimes_must_be_search_strategy():
    with pytest.raises(InvalidArgument):
        datetimes(timezones=pytz.all_timezones).validate()
    with pytest.raises(InvalidArgument):
        tz = [pytz.timezone(t) for t in pytz.all_timezones]
        datetimes(timezones=tz).validate()


@given(times(timezones=timezones()))
def test_timezone_aware_times_are_timezone_aware(dt):
    assert dt.tzinfo is not None


def test_can_generate_non_utc():
    times(timezones=timezones()).filter(
        lambda d: assume(d.tzinfo) and d.tzinfo.zone != "UTC"
    ).validate()


@given(sampled_from(["min_value", "max_value"]), times(timezones=timezones()))
def test_time_bounds_must_be_naive(name, val):
    with pytest.raises(InvalidArgument):
        times(**{name: val}).validate()


@pytest.mark.parametrize(
    "bound",
    [
        {"min_value": dt.datetime.max - dt.timedelta(days=3)},
        {"max_value": dt.datetime.min + dt.timedelta(days=3)},
    ],
)
def test_can_trigger_error_in_draw_near_boundary(bound):
    assert_can_trigger_event(
        datetimes(**bound, timezones=timezones()),
        lambda event: "Failed to draw a datetime" in event,
    )


@given(data(), datetimes(), datetimes())
def test_datetimes_stay_within_naive_bounds(data, lo, hi):
    if lo > hi:
        lo, hi = hi, lo
    out = data.draw(datetimes(lo, hi, timezones=timezones()))
    assert lo <= out.replace(tzinfo=None) <= hi


@pytest.mark.parametrize(
    "kw",
    [
        # Ireland uses  *negative* offset DST, which means that our sloppy interpretation
        # of "is_dst=not fold" bypasses the filter for imaginary times.  This is basically
        # unfixable without redesigning pytz per PEP-495, and it's much more likely to be
        # replaced by dateutil or PEP-615 zoneinfo in the standard library instead.
        {
            "min_value": dt.datetime(2019, 3, 31),
            "max_value": dt.datetime(2019, 4, 1),
            "timezones": just(pytz.timezone("Europe/Dublin")),
        },
        # The day of a spring-forward transition in Australia; 2am is imaginary
        # (the common case so an optimistic `is_dst=bool(fold)` also fails the test)
        {
            "min_value": dt.datetime(2020, 10, 4),
            "max_value": dt.datetime(2020, 10, 5),
            "timezones": just(pytz.timezone("Australia/Sydney")),
        },
    ],
)
def test_datetimes_can_exclude_imaginary(kw):
    # Sanity check: fail unless those days contain an imaginary hour to filter out
    find_any(datetimes(**kw, allow_imaginary=True), lambda x: not datetime_exists(x))

    # Assert that with allow_imaginary=False we only generate existing datetimes.
    assert_all_examples(datetimes(**kw, allow_imaginary=False), datetime_exists)


def test_really_weird_tzinfo_case():
    x = dt.datetime(2019, 3, 31, 2, 30, tzinfo=pytz.timezone("Europe/Dublin"))
    assert x.tzinfo is not x.astimezone(dt.timezone.utc).astimezone(x.tzinfo)
    # And that weird case exercises the rare branch in our helper:
    assert datetime_does_not_exist(x)
