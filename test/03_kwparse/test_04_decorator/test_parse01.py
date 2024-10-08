
# Local imports
from lfc._vendor.argread._vendor.kwparse import KwargParser, KWParseError


# Create custom class
class MyKwargs(KwargParser):
    _optlist = (
        "a",
        "b",
        "c",
    )
    _optconverters = {
        "a": int,
    }
    _opttypes = {
        "a": int,
        "b": str,
    }
    _rc = {
        "a": 4,
    }


# Decorate a function
@MyKwargs.parse
def f1(**kw):
    return kw


# Test decorated function
def test_deco01():
    # Basic methods
    kw = f1(a='2', b='name')
    # Check that it was parsed
    assert isinstance(kw["a"], int)
    assert kw["a"] == 2
    assert kw["b"] == "name"
    # Test default
    kw = f1()
    # Check that default got applied
    assert "a" in kw
    assert kw["a"] == MyKwargs._rc["a"]


# Test errors
def test_deco02():
    try:
        f1(a=2, b=3)
    except KWParseError as err:
        # Make sure it starts with f1()
        assert err.args[0].startswith("f1()")
