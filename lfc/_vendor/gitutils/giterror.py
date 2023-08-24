r"""
:mod:`giterror`: Errors for :mod:`gitutils` Git repo tools
===========================================================

This module provides a collection of error types relevant to the
:mod:`gitutils` package. They are essentially the same as standard error
types such as :class:`KeyError`, :class:`TypeError`, etc. but with an
extra parent of :class:`GitutilsError` to enable catching all errors
specifically raised by this package

"""

# Standard library
import os


# Basic error family
class GitutilsError(Exception):
    r"""Parent error class for :mod:`gitutils` errors

    Inherits from :class:`Exception`
    """
    pass


class GitutilsAttributeError(AttributeError, GitutilsError):
    r"""Error related to accessing attributes of :class:`OptionsDict`

    Inherits from :class:`AttributeError` and :class:`OpdictError`.
    """
    pass


class GitutilsNameError(NameError, GitutilsError):
    r"""Error for badly named options in :class:`OptionsDict`

    Inherits from :class:`NameError` and :class:`GitutilsError`
    """
    pass


class GitutilsJSONError(ValueError, GitutilsError):
    r"""Exception class for errors while parsing JSON files

    Inherits from :class:`ValueError` and :class:`GitutilsError`
    """
    pass


class GitutilsKeyError(KeyError, GitutilsError):
    r"""Exception for missing key in :mod:`gitutils`

    Inherits from :class:`KeyError` and :class:`GitutilsError`
    """
    pass


class GitutilsSystemError(SystemError, GitutilsError):
    r"""Exception for system errors raised by :mod:`gitutils`
    """
    pass


class GitutilsTypeError(TypeError, GitutilsError):
    r"""Exception for unexpected type of parameter in :mod:`Gitutils`
    """
    pass


class GitutilsValueError(ValueError, GitutilsError):
    r"""Exception for unexpected value of parameter in :mod:`Gitutils`
    """
    pass


class GitutilsExprError(ValueError, GitutilsError):
    r"""Exception for invalid ``@expr``

    Applies to :func:`Gitutils.optitem.getel` or :class:`OptionsDict`
    """
    pass


# Assert type of a variable
def assert_isinstance(obj, cls_or_tuple, desc=None):
    r"""Conveniently check types

    Applies ``isinstance(obj, cls_or_tuple)`` but also constructs
    a :class;`TypeError` and appropriate message if test fails

    :Call:
        >>> assert_isinstance(obj, cls, desc=None)
        >>> assert_isinstance(obj, cls_tuple, desc=None)
    :Inputs:
        *obj*: :class:`object`
            Object whose type is checked
        *cls*: :class:`type`
            Single permitted class
        *cls_tuple*: :class:`tuple`\ [:class:`type`]
            Tuple of allowed classes
    :Raises:
        :class:`GitutilsTypeError`
    :Versions:
        * 2022-09-17 ``@ddalle``: Version 1.0
    """
    # Special case for ``None``
    if cls_or_tuple is None:
        return
    # Check for passed test
    if isinstance(obj, cls_or_tuple):
        return
    # Generate type error message
    msg = _genr8_type_error(obj, cls_or_tuple, desc)
    # Raise
    raise GitutilsTypeError(msg)


# Assert that file exists
def assert_isfile(fname):
    # Check for file
    if not os.path.isfile(fname):
        # Start message
        msg = "File '%s' does not exist" % fname
        # Check for absolute path
        if not os.path.isabs(fname):
            # Show working directory
            msg += "\n  relative to '%s'" % os.getcwd()
        raise GitutilsSystemError(msg)


# Create error message for type errors
def _genr8_type_error(obj, cls_or_tuple, desc=None):
    # Check for single type
    if isinstance(cls_or_tuple, tuple):
        # Multiple types
        names = [cls.__name__ for cls in cls_or_tuple]
    else:
        # Single type
        names = [cls_or_tuple.__name__]
    # Create error message
    if desc is None:
        # No description; msg2 is "Got type"
        msg1 = "G"
    else:
        # Add description; msg is "got type"
        msg1 = "For %s: g" % desc
    msg2 = "ot type '%s'; " % type(obj).__name__
    msg3 = "expected '%s'" % ("' | '".join(names))
    # Output
    return msg1 + msg2 + msg3
