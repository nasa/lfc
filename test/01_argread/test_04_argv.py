
# Standard library
import sys

# Local imports
from lfc._vendor.argread import readkeys


def test_readkeys01():
    sys.argv = ["p", "-cj"]
    a, kw = readkeys()
    assert a == []
    assert kw == {
        "cj": True,
        "__replaced__": [],
    }

