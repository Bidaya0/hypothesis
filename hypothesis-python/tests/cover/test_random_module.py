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

import gc
import random

import pytest

from hypothesis import core, find, given, register_random, reporting, strategies as st
from hypothesis.errors import InvalidArgument
from hypothesis.internal import entropy
from hypothesis.internal.compat import PYPY
from hypothesis.internal.entropy import deterministic_PRNG

from tests.common.utils import capture_out


def gc_on_pypy():
    # CPython uses reference counting, so objects (without circular refs)
    # are collected immediately on `del`, breaking weak references.
    # PyPy doesn't, so we use this function in tests before counting the
    # surviving references to ensure that they're deterministic.
    if PYPY:
        gc.collect()


def test_can_seed_random():
    with capture_out() as out:
        with reporting.with_reporter(reporting.default):
            with pytest.raises(AssertionError):

                @given(st.random_module())
                def test(r):
                    raise AssertionError

                test()
    assert "RandomSeeder(0)" in out.getvalue()


@given(st.random_module(), st.random_module())
def test_seed_random_twice(r, r2):
    assert repr(r) == repr(r2)


@given(st.random_module())
def test_does_not_fail_health_check_if_randomness_is_used(r):
    random.getrandbits(128)


def test_cannot_register_non_Random():
    with pytest.raises(InvalidArgument):
        register_random("not a Random instance")


def test_registering_a_Random_is_idempotent():
    gc_on_pypy()
    n_registered = len(entropy.RANDOMS_TO_MANAGE)
    r = random.Random()
    register_random(r)
    register_random(r)
    assert len(entropy.RANDOMS_TO_MANAGE) == n_registered + 1
    del r
    gc_on_pypy()
    assert len(entropy.RANDOMS_TO_MANAGE) == n_registered


def test_manages_registered_Random_instance():
    r = random.Random()
    register_random(r)
    state = r.getstate()
    result = []

    @given(st.integers())
    def inner(x):
        v = r.random()
        if result:
            assert v == result[0]
        else:
            result.append(v)

    inner()
    assert state == r.getstate()


def test_registered_Random_is_seeded_by_random_module_strategy():
    r = random.Random()
    register_random(r)
    state = r.getstate()
    results = set()
    count = [0]

    @given(st.integers())
    def inner(x):
        results.add(r.random())
        count[0] += 1

    inner()
    assert count[0] > len(results) * 0.9, "too few unique random numbers"
    assert state == r.getstate()


@given(st.random_module())
def test_will_actually_use_the_random_seed(rnd):
    a = random.randint(0, 100)
    b = random.randint(0, 100)
    random.seed(rnd.seed)
    assert a == random.randint(0, 100)
    assert b == random.randint(0, 100)


def test_given_does_not_pollute_state():
    with deterministic_PRNG():

        @given(st.random_module())
        def test(r):
            pass

        test()
        state_a = random.getstate()
        state_a2 = core._hypothesis_global_random.getstate()

        test()
        state_b = random.getstate()
        state_b2 = core._hypothesis_global_random.getstate()

        assert state_a == state_b
        assert state_a2 != state_b2


def test_find_does_not_pollute_state():
    with deterministic_PRNG():

        find(st.random_module(), lambda r: True)
        state_a = random.getstate()
        state_a2 = core._hypothesis_global_random.getstate()

        find(st.random_module(), lambda r: True)
        state_b = random.getstate()
        state_b2 = core._hypothesis_global_random.getstate()

        assert state_a == state_b
        assert state_a2 != state_b2


def test_evil_prng_registration_nonsense():
    gc_on_pypy()
    n_registered = len(entropy.RANDOMS_TO_MANAGE)
    r1, r2, r3 = random.Random(1), random.Random(2), random.Random(3)
    s2 = r2.getstate()

    # We're going to be totally evil here: register two randoms, then
    # drop one and add another, and finally check that we reset only
    # the states that we collected before we started
    register_random(r1)
    k = max(entropy.RANDOMS_TO_MANAGE)  # get a handle to check if r1 still exists
    register_random(r2)
    assert len(entropy.RANDOMS_TO_MANAGE) == n_registered + 2

    with deterministic_PRNG(0):
        del r1
        gc_on_pypy()
        assert k not in entropy.RANDOMS_TO_MANAGE, "r1 has been garbage-collected"
        assert len(entropy.RANDOMS_TO_MANAGE) == n_registered + 1

        r2.seed(4)
        register_random(r3)
        r3.seed(4)
        s4 = r3.getstate()

    # Implicit check, no exception was raised in __exit__
    assert r2.getstate() == s2, "reset previously registered random state"
    assert r3.getstate() == s4, "retained state when registered within the context"
