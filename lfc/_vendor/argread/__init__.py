#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
``argread``: Parse command-line arguments and options
==========================================================

This class provides the :class:`ArgReader` class, instances of
which can be used to customize available command-line options for a
given inteface.
"""

# Standard library
import re
import sys

# Local imports
from ._vendor.kwparse import (
    KWTypeError,
    KwargParser,
    assert_isinstance
)


# Regular expression for options like "cdfr=1.3"
REGEX_EQUALKEY = re.compile(r"(\w+)=([^=].*)")


# Custom error class
class ArgReadError(Exception):
    pass


# Argument read class
class ArgReader(KwargParser):
    r"""Class to parse command-line interface arguments

    :Call:
        >>> parser = ArgReader(**kw)
    :Outputs:
        *parser*: :class:`ArgReader`
            Instance of command-line argument parser
    """
   # --- Class attributes ---
    # List of instance attributes
    __slots__ = (
        "argv",
        "prog",
        "kwargs_sequence",
        "kwargs_replaced",
        "kwargs_single_dash",
        "kwargs_double_dash",
        "kwargs_equal_sign",
        "param_sequence",
    )

    # Options that cannot take values
    _optlist_noval = ()

    # Enforce _optlist
    _restrict = False

    # Options
    single_dash_split = False
    single_dash_lastkey = False
    equal_sign_key = True

    # Base exception class
    exc_cls = ArgReadError

   # --- __dunder__ ---
    def __init__(self):
        r"""Initialization method

        :Versions:
            * 2021-11-21 ``@ddalle``: v1.0
        """
        # Initialize attributes
        self.argv = []
        self.prog = None
        self.argvals = []
        self.kwargs_sequence = []
        self.kwargs_replaced = []
        self.kwargs_single_dash = {}
        self.kwargs_double_dash = {}
        self.kwargs_equal_sign = {}
        self.param_sequence = []

    def parse(self, argv=None):
        r"""Parse args

        :Call:
            >>> a, kw = parser.parse(argv=None)
        :Inputs:
            *parser*: :class:`ArgReader`
                Command-line argument parser
            *argv*: {``None``} | :class:`list`\ [:class:`str`]
                Optional arguments to parse, else ``sys.argv``
        :Outputs:
            *a*: :class:`list`
                List of positional arguments
            *kw*: :class:`dict`
                Dictionary of options and their values
            *kw["__replaced__"]*: :class:`list`\ [(:class:`str`, *any*)]
                List of any options replaced by later values
        :Versions:
            * 2021-11-21 ``@ddalle``: v1.0
        """
        # Process optional args
        if argv is None:
            # Copy *sys.argv*
            argv = list(sys.argv)
        else:
            # Check type of *argv*
            assert_isinstance(argv, list, "'argv'")
            # Check each arg is a string
            for j, arg in enumerate(argv):
                # Check type
                assert_isinstance(arg, str, f"argument {j}")
            # Copy args
            argv = list(argv)
        # Save copy of args to *self*
        self.argv = list(argv)
        # (Re)initialize attributes storing parsed arguments
        self.argvals = []
        self.kwargs_sequence = []
        self.kwargs_replaced = []
        self.kwargs_single_dash = {}
        self.kwargs_double_dash = {}
        self.kwargs_equal_sign = {}
        self.param_sequence = []
        # Check for command name
        if len(argv) == 0:
            raise KWTypeError(
                "Expected at least one argv entry (program name)")
        # Save command name
        self.prog = argv.pop(0)
        # Loop until args are gone
        while argv:
            # Extract first argument
            arg = argv.pop(0)
            # Parse argument
            prefix, key, val, flags = self._parse_arg(arg)
            # Check for flags
            if flags:
                # Set all to ``True``
                for flag in flags:
                    self.save_single_dash(flag, True)
            # Check if arg
            if prefix == "":
                # Positional parameter
                self.save_arg(val)
                continue
            # Check option type: "-opt", "--opt", "opt=val"
            if prefix == "=":
                # Equal-sign option
                self.save_equal_key(key, val)
                continue
            elif key is None:
                # This can happen when only flags, like ``"-lh"``
                continue
            # Determine save function based on prefix
            if prefix == "-":
                save = self.save_single_dash
            else:
                save = self.save_double_dash
            # Check for "--no-mykey"
            if key.startswith("no-"):
                # This is interpreted "mykey=False"
                save(key[3:], False)
                continue
            # Check for "noval" options, or if next arg is available
            if key in self._optlist_noval or (len(argv) == 0):
                # No following arg to check
                save(key, True)
                continue
            # Check next arg
            prefix1, _, val1, _ = self._parse_arg(argv[0])
            # If it is not a key, save the value
            if prefix1 == "":
                # Save value like ``--extend 2``
                save(key, val1)
                # Pop argument
                argv.pop(0)
            else:
                # Save ``True`` for ``--qsub``
                save(key, True)
        # Output current values
        return self.get_args()

    # Return the args and kwargs
    def get_args(self):
        r"""Get full list of args and options from parsed inputs

        :Call:
            >>> args, kwargs = parser.get_args()
        :Outputs:
            *args*: :class:`list`\ [:class:`str`]
                List of positional parameter argument values
            *kwargs*: :class:`dict`
                Dictionary of named options and their values
        :Versions:
            * 2023-11-08 ``@ddalle``: v1.0
        """
        # Get list of arguments
        args = list(self.argvals)
        # Get full dictionary of outputs, applying defaults
        kwargs = self.get_kwargs()
        # Set __replaced__
        kwargs["__replaced__"] = [
            tuple(opt) for opt in self.kwargs_replaced]
        # Output
        return args, kwargs

   # --- Parsers ---
    # Parse a single arg
    def _parse_arg(self, arg: str):
        r"""Parse type for a single CLI arg

        :Call:
            >>> prefix, key, val, flags = parser._parse_arg(arg)
        :Inputs:
            *parser*: :class:`ArgReader`
                Command-line argument parser
            *arg*: :class:`str`
                Single arg to parse, usually from ``sys.argv``
        :Outputs:
            *prefix*: ``""`` | ``"-'`` | ``"--"`` | ``"="``
                Argument prefix
            *key*: ``None`` | :class:`str`
                Option name if *arg* is ``--key`` or ``key=val``
            *val*: ``None`` | :class:`str`
                Option value or positional parameter value
            *flags* ``None`` | :class:`str`
                List of single-character flags, e.g. for ``-lh``
        :Versions:
            * 2021-11-23 ``@ddalle``: v1.0
        """
        # Global settings
        splitflags = self.single_dash_split
        lastflag = self.single_dash_lastkey
        equalkey = self.equal_sign_key
        # Check for options like "cdfr=1.2"
        if equalkey:
            # Test the arg
            match = REGEX_EQUALKEY.match(arg)
        else:
            # Do not test
            match = None
        # Check if it starts with a hyphen
        if match:
            # Already processed key and value
            key, val = match.groups()
            flags = None
            prefix = "="
        elif not arg.startswith("-"):
            # Positional parameter
            key = None
            val = arg
            flags = None
            prefix = ""
        elif arg.startswith("--"):
            # A normal, long-form key
            key = arg.lstrip("-")
            val = None
            flags = None
            prefix = "--"
        elif splitflags:
            # Single-dash option, like '-d' or '-cvf'
            prefix = "-"
            val = None
            # Check for special handling of last flag
            if len(arg) == 1:
                # No flags, no key
                flags = ""
                key = ""
            elif len(arg) == 2:
                # No flags, one key
                flags = ""
                key = arg[-1]
            elif lastflag:
                # Last "flag" is special
                flags = arg[1:-1]
                key = arg[-1]
            else:
                # Just list of flags
                flags = arg[1:]
                key = None
        else:
            # Single-dash opton
            prefix = "-"
            key = arg[1:]
            val = None
            flags = None
        # Output
        return prefix, key, val, flags

   # --- Arg/Option interface ---
    def save_arg(self, arg):
        r"""Save a positional argument

        :Call:
            >>> parser.save_arg(arg, narg=None)
        :Inputs:
            *parser*: :class:`ArgReader`
                Command-line argument parser
            *arg*: :class:`str`
                Name/value of next parameter
        :Versions:
            * 2021-11-23 ``@ddalle``: v1.0
        """
        self._save(None, arg)

    def save_double_dash(self, k, v=True):
        r"""Save a double-dash keyword and value

        :Call:
            >>> parser.save_double_dash(k, v=True)
        :Inputs:
            *parser*: :class:`ArgReader`
                Command-line argument parser
            *k*: :class:`str`
                Name of key to save
            *v*: {``True``} | ``False`` | :class:`str`
                Value to save
        :Versions:
            * 2021-11-23 ``@ddalle``: v1.0
        """
        self._save(k, v)
        self.kwargs_double_dash[k] = v

    def save_equal_key(self, k, v):
        r"""Save an equal-sign key/value pair, like ``"mach=0.9"``

        :Call:
            >>> parser.save_equal_key(k, v)
        :Inputs:
            *parser*: :class:`ArgReader`
                Command-line argument parser
            *k*: :class:`str`
                Name of key to save
            *v*: :class:`str`
                Value to save
        :Versions:
            * 2021-11-23 ``@ddalle``: v1.0
        """
        self._save(k, v)
        self.kwargs_equal_sign[k] = v

    def save_single_dash(self, k, v=True):
        r"""Save a single-dash keyword and value

        :Call:
            >>> parser.save_single_dash(k, v=True)
        :Inputs:
            *parser*: :class:`ArgReader`
                Command-line argument parser
            *k*: :class:`str`
                Name of key to save
            *v*: {``True``} | ``False`` | :class:`str`
                Value to save
        :Versions:
            * 2021-11-23 ``@ddalle``: v1.0
        """
        self._save(k, v)
        self.kwargs_single_dash[k] = v

    def _save(self, rawopt: str, rawval):
        # Append to universal list of args
        self.param_sequence.append((rawopt, rawval))
        # Check option vs arg
        if rawopt is None:
            # Get index
            j = len(self.argvals)
            # Save arg
            self.set_arg(j, rawval)
        else:
            # Validate value
            opt, val = self.validate_opt(rawopt, rawval)
            # Universal keyword arg sequence
            self.kwargs_sequence.append((opt, val))
            # Check if a previous key
            if opt in self:
                # Save to "replaced" options
                self.kwargs_replaced.append((opt, self[opt]))
            # Save to current kwargs
            self[opt] = val


# Class with single_dash_split=False (default)
class KeysArgReader(ArgReader):
    __slots__ = ()
    single_dash_split = False


# Class with single_dash_split=True (flags)
class FlagsArgReader(ArgReader):
    __slots__ = ()
    single_dash_split = True


# Class with args like ``tar -cvf this.tar``
class TarFlagsArgReader(ArgReader):
    __slots__ = ()
    single_dash_split = True
    single_dash_lastkey = True


# Read keys
def readkeys(argv=None):
    r"""Parse args where ``-cj`` becomes ``cj=True``

    :Call:
        >>> a, kw = readkeys(argv=None)
    :Inputs:
        *argv*: {``None``} | :class:`list`\ [:class:`str`]
            List of args other than ``sys.argv``
    :Outputs:
        *a*: :class:`list`\ [:class:`str`]
            List of positional args
        *kw*: :class:`dict`\ [:class:`str` | :class:`bool`]
            Keyword arguments
    :Versions:
        * 2021-12-01 ``@ddalle``: v1.0
    """
    # Create parser
    parser = KeysArgReader()
    # Parse args
    return parser.parse(argv)


# Read flags
def readflags(argv=None):
    r"""Parse args where ``-cj`` becomes ``c=True, j=True``

    :Call:
        >>> a, kw = readflags(argv=None)
    :Inputs:
        *argv*: {``None``} | :class:`list`\ [:class:`str`]
            List of args other than ``sys.argv``
    :Outputs:
        *a*: :class:`list`\ [:class:`str`]
            List of positional args
        *kw*: :class:`dict`\ [:class:`str` | :class:`bool`]
            Keyword arguments
    :Versions:
        * 2021-12-01 ``@ddalle``: v1.0
    """
    # Create parser
    parser = FlagsArgReader()
    # Parse args
    return parser.parse(argv)


# Read flags like ``tar`
def readflagstar(argv=None):
    r"""Parse args where ``-cf a`` becomes ``c=True, f="a"``

    :Call:
        >>> a, kw = readflags(argv=None)
    :Inputs:
        *argv*: {``None``} | :class:`list`\ [:class:`str`]
            List of args other than ``sys.argv``
    :Outputs:
        *a*: :class:`list`\ [:class:`str`]
            List of positional args
        *kw*: :class:`dict`\ [:class:`str` | :class:`bool`]
            Keyword arguments
    :Versions:
        * 2021-12-01 ``@ddalle``: v1.0
    """
    # Create parser
    parser = TarFlagsArgReader()
    # Parse args
    return parser.parse(argv)


