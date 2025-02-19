#!/bin/bash
set -e -o xtrace

HERE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$HERE/.."

python -c '
import os
for k, v in sorted(dict(os.environ).items()):
    print("%s=%s" % (k, v))
'

pip install .


PYTEST="python -m pytest -nauto"

# Run all the no-extra-dependency tests for this version (except slow nocover tests)
$PYTEST tests/cover tests/pytest

# Run tests for each extra module while the requirements are installed
pip install ".[pytz, dateutil, zoneinfo]"
$PYTEST tests/datetime/
pip uninstall -y pytz python-dateutil

pip install ".[dpcontracts]"
$PYTEST tests/dpcontracts/
pip uninstall -y dpcontracts

pip install fakeredis
$PYTEST tests/redis/
pip uninstall -y redis fakeredis

pip install 'typing_extensions!=3.10.0.1'
$PYTEST tests/typing_extensions/
if [ "$(python -c 'import sys; print(sys.version_info[:2] <= (3, 7))')" = "False" ] ; then
  # Required by importlib_metadata backport, which we don't want to break
  pip uninstall -y typing_extensions
fi

pip install ".[lark]"
$PYTEST tests/lark/
pip install lark-parser==0.7.1
$PYTEST tests/lark/
pip uninstall -y lark-parser

if [ "$(python -c $'import platform, sys; print(sys.version_info.releaselevel == \'final\' and platform.python_implementation() != "PyPy")')" = "True" ] ; then
  pip install ".[codemods,cli]"
  $PYTEST tests/codemods/
  pip uninstall -y libcst click

  pip install black numpy
  $PYTEST tests/ghostwriter/
  pip uninstall -y black numpy
fi

if [ "$(python -c 'import sys; print(sys.version_info[:2] == (3, 8))')" = "False" ] ; then
  exit 0
fi

$PYTEST tests/nocover/

# Run some tests without docstrings or assertions, to catch bugs
# like issue #822 in one of the test decorators.  See also #1541.
PYTHONOPTIMIZE=2 $PYTEST tests/cover/test_testdecorators.py

if [ "$(python -c 'import platform; print(platform.python_implementation())')" != "PyPy" ]; then
  pip install .[django]
  HYPOTHESIS_DJANGO_USETZ=TRUE python -m tests.django.manage test tests.django
  HYPOTHESIS_DJANGO_USETZ=FALSE python -m tests.django.manage test tests.django
  pip uninstall -y django pytz

  pip install numpy
  $PYTEST tests/numpy

  pip install pandas
  $PYTEST tests/pandas
fi
