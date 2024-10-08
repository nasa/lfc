
# Local imports
from lfc._vendor.argread._vendor.kwparse import KwargParser


# Create custom class
class MyKwargs(KwargParser):
    _opttypes = {
        "a": int,
    }
    _rc = {
        "a": 4
    }


# Test basic get_opt behavior
def test_getopt01():
    # Instantiate
    kw = MyKwargs(b=2)
    # Option present
    assert kw.get_opt("b") == 2
    # Default
    assert kw.get_opt("a") == MyKwargs._rc["a"]
    # User-supplied default
    assert kw.get_opt("a", vdef=1) == 1
