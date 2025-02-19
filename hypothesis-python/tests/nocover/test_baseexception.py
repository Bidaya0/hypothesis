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

import pytest

from hypothesis import given
from hypothesis.errors import Flaky
from hypothesis.strategies import composite, integers


@pytest.mark.parametrize(
    "e", [KeyboardInterrupt, SystemExit, GeneratorExit, ValueError]
)
def test_exception_propagates_fine(e):
    @given(integers())
    def test_raise(x):
        raise e

    with pytest.raises(e):
        test_raise()


@pytest.mark.parametrize(
    "e", [KeyboardInterrupt, SystemExit, GeneratorExit, ValueError]
)
def test_exception_propagates_fine_from_strategy(e):
    @composite
    def interrupt_eventually(draw):
        raise e

    @given(interrupt_eventually())
    def test_do_nothing(x):
        pass

    with pytest.raises(e):
        test_do_nothing()


@pytest.mark.parametrize("e", [KeyboardInterrupt, ValueError])
def test_baseexception_no_rerun_no_flaky(e):
    runs = [0]
    interrupt = 3

    @given(integers())
    def test_raise_baseexception(x):
        runs[0] += 1
        if runs[0] == interrupt:
            raise e

    if issubclass(e, (KeyboardInterrupt, SystemExit, GeneratorExit)):
        # Here SystemExit and GeneratorExit are passed through
        with pytest.raises(e):
            test_raise_baseexception()

        assert runs[0] == interrupt
    else:
        with pytest.raises(Flaky):
            test_raise_baseexception()


@pytest.mark.parametrize(
    "e", [KeyboardInterrupt, SystemExit, GeneratorExit, ValueError]
)
def test_baseexception_in_strategy_no_rerun_no_flaky(e):
    runs = [0]
    interrupt = 3

    @composite
    def interrupt_eventually(draw):
        runs[0] += 1
        if runs[0] == interrupt:
            raise e
        return draw(integers())

    @given(interrupt_eventually())
    def test_do_nothing(x):
        pass

    if issubclass(e, KeyboardInterrupt):
        with pytest.raises(e):
            test_do_nothing()

        assert runs[0] == interrupt

    else:
        # Now SystemExit and GeneratorExit are caught like other exceptions
        with pytest.raises(Flaky):
            test_do_nothing()


TEMPLATE = """
from hypothesis import given, note, strategies as st

@st.composite
def things(draw):
    raise {exception}


@given(st.data(), st.integers())
def test(data, x):
    if x > 100:
        data.draw({strategy})
        raise {exception}
"""


@pytest.mark.parametrize("exc_name", ["SystemExit", "GeneratorExit"])
@pytest.mark.parametrize("use_composite", [True, False])
def test_explanations(testdir, exc_name, use_composite):
    code = TEMPLATE.format(
        exception=exc_name, strategy="things()" if use_composite else "st.none()"
    )
    test_file = str(testdir.makepyfile(code))
    pytest_stdout = str(testdir.runpytest_inprocess(test_file, "--tb=native").stdout)
    assert "x=101" in pytest_stdout
    assert exc_name in pytest_stdout
