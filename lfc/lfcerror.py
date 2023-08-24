r"""
``lfcerror``: Errors for :mod:`lfcutils` Git repo tools
===========================================================

This module provides a collection of error types relevant to the
:mod:`gitutils` package. They are essentially the same as standard error
types such as :class:`KeyError`, :class:`TypeError`, etc. but with an
extra parent of :class:`GitutilsError` to enable catching all errors
specifically raised by this package

"""

# Local imports
from ._vendor.gitutils.giterror import GitutilsError
