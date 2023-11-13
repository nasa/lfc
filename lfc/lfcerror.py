r"""
``lfcerror``: Errors for :mod:`lfc` modules
===========================================================

This module provides a collection of error types relevant to the
:mod:`gitutils` package. They are essentially the same as standard error
types such as :class:`KeyError`, :class:`TypeError`, etc. but with an
extra parent of :class:`GitutilsError` to enable catching all errors
specifically raised by this package

"""

# Local imports
from ._vendor.gitutils.giterror import GitutilsError


# Error for loss of info from checkout
class LFCCheckoutError(SystemError, GitutilsError):
    r"""Error class for lfc-checkout commands

    Usually raised if an ``lfc checkout`` would delete an actual large
    file that is not in the cache"""
    pass


class LFCCloneError(SystemError, GitutilsError):
    r"""Error class for lfc-clone commands
    """
    pass


class LFCValueError(ValueError, GitutilsError):
    r"""Error class for wrong values in LFC"""
    pass
