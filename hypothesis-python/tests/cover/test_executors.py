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

import inspect
from unittest import TestCase

import pytest

from hypothesis import example, given
from hypothesis.executors import ConjectureRunner
from hypothesis.strategies import booleans, integers


def test_must_use_result_of_test():
    class DoubleRun:
        def execute_example(self, function):
            x = function()
            if inspect.isfunction(x):
                return x()

        @given(booleans())
        def boom(self, b):
            def f():
                raise ValueError()

            return f

    with pytest.raises(ValueError):
        DoubleRun().boom()


class TestTryReallyHard(TestCase):
    @given(integers())
    def test_something(self, i):
        pass

    def execute_example(self, f):
        f()
        return f()


class Valueless:
    def execute_example(self, f):
        try:
            return f()
        except ValueError:
            return None

    @given(integers())
    @example(1)
    def test_no_boom_on_example(self, x):
        raise ValueError()

    @given(integers())
    def test_no_boom(self, x):
        raise ValueError()

    @given(integers())
    def test_boom(self, x):
        raise AssertionError


def test_boom():
    with pytest.raises(AssertionError):
        Valueless().test_boom()


def test_no_boom():
    Valueless().test_no_boom()


def test_no_boom_on_example():
    Valueless().test_no_boom_on_example()


class TestNormal(ConjectureRunner, TestCase):
    @given(booleans())
    def test_stuff(self, b):
        pass
