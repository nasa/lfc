# -*- coding: utf-8 -*-
r"""
:mod:`gitutils.gitrepo`: Interact with git repos using system interface
========================================================================

This module provides the :class:`GitRepo` class, which both provides a
basic interface to a git repository (whether working or bare) and a
large-file client (LFC) to handle files not optimized for tracking
directly by git.

"""

# Standard library
import functools
import os
import sys
from subprocess import Popen, PIPE

# Local imports
from ._vendor import shellutils
from .giterror import GitutilsSystemError


# Decorator for moving directories
def run_gitdir(func):
    r"""Decorator to run a function within the parent folder

    :Call:
        >>> func = run_rootdir(func)
    :Wrapper Signature:
        >>> v = repo.func(*a, **kw)
    :Inputs:
        *func*: :class:`func`
            Name of function
        *cntl*: :class:`Cntl`
            Control instance from which to use *cntl.RootDir*
        *a*: :class:`tuple`
            Positional args to :func:`cntl.func`
        *kw*: :class:`dict`
            Keyword args to :func:`cntl.func`
    :Versions:
        * 2018-11-20 ``@ddalle``: v1.0
        * 2020-02-25 ``@ddalle``: v1.1: better exceptions
    """
    # Declare wrapper function to change directory
    @functools.wraps(func)
    def wrapper_func(self, *args, **kwargs):
        # Recall current directory
        fpwd = os.getcwd()
        # Go to specified directory
        os.chdir(self.gitdir)
        # Run the function with exception handling
        try:
            # Attempt to run the function
            v = func(self, *args, **kwargs)
        except Exception:
            # Go back to original folder
            os.chdir(fpwd)
            # Raise the error
            raise
        except KeyboardInterrupt:
            # Go back to original folder
            os.chdir(fpwd)
            # Raise the error
            raise
        # Go back to original folder
        os.chdir(fpwd)
        # Return function values
        return v
    # Apply the wrapper
    return wrapper_func


# Class to interface one repo
class GitRepo(object):
    r"""Git repository interface class

    :Call:
        >>> repo = GitRepo(where=None)
    :Inputs:
        *where*: {``None``} | :class:`str`
            Path from which to look for git repo (default is CWD)
    :Outputs:
        *repo*: :class:`GitRepo`
            Interface to git repository
    :Versions:
        * 2022-12-21 ``@ddalle``: v1.0
        * 2023-08-24 ``@ddalle``: v2.0; remove LFC methods
    """
   # --- Class attributes ---
    # Class attributes
    __slots__ = (
        "bare",
        "gitdir")

   # --- __dunder__ ---
    def __init__(self, where=None):
        # Check for a bare repo
        self.bare = is_bare(where)
        # Record root directory
        self.gitdir = get_gitdir(where, bare=self.bare)

   # --- Status Operations ---
    def check_ignore(self, fname):
        r"""Check if *fname* is (or would be) ignored by git

        :Call:
            >>> q = repo.check_ignore(fname)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *fname*: :class:`str`
                Name of file
        :Outputs:
            *q*: ``True`` | ``False``
                Whether file is ignored (even if file doesn't exist)
        :Versions:
            * 2022-12-20 ``@ddalle``: v1.0
        """
        # Structure a command for git
        _, _, ierr = shellutils.call_oe(["git", "check-ignore", fname])
        # If ignored, return code is 0
        return ierr == 0

    def check_track(self, fname):
        r"""Check if a file is tracked by git

        :Call:
            >>> q = repo.check_track(fname)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *fname*: :class:`str`
                Name of file
        :Outputs:
            *q*: ``True`` | ``False``
                Whether file is tracked
        :Versions:
            * 2022-12-20 ``@ddalle``: v1.0
        """
        # Structure a command for git
        stdout = self.check_o(["git", "ls-files", fname])
        # If tracked, it will be listed in stdout
        return stdout.strip() != ""

    def assert_working(self, cmd=None):
        r"""Assert that current repo is working (non-bare)

        :Call:
            >>> repo.assert_working(cmd=None)
        :Inputs:
            *repo*: :class:`GitRepo`
                Inteface to git repository
            *cmd*: {``None``} | :class:`str`
                Command name for error message
        :Versions:
            * 2022-12-20 ``@ddalle``: v1.0
        """
        # Check if a bare repo
        if self.bare:
            # Form message
            msg = "Cannot run command in bare repo"
            # Check for a command
            if cmd:
                msg += "\n> %s" % " ".join(cmd)
            # Exception
            raise GitutilsSystemError(cmd)

   # --- Add ---
    def add(self, fname: str):
        # Only perform on working repo
        self.assert_working()
        # Perform 'git add' command
        self._add(fname)

    def _add(self, fname: str):
        self.check_call(["git", "add", fname])

   # --- Move ---
    def mv(self, fold: str, fnew: str):
        r"""Move a file or folder and inform git of change

        :Call:
            >>> repo.mv(fold, fnew)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *fold*: :class:`str`
                Name of existing file
            *fnew*: :class:`str`
                Name of file after move
        :Versions:
            * 2022-12-28 ``@ddalle``: v1.0
        """
        # Only perform on working repo
        self.assert_working()
        # Move the file and check exit status
        self.check_call(["git", "mv", fold, fnew])

   # --- Remove ---
    def rm(self, fname: str, *fnames, r=False):
        r"""Remove files or folders and stage deletions for git

        :Call:
            >>> repo.rm(fname, *fnames, r=False)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *fname*: :class:`str`
                Name of first file/folder to remove
            *fnames*: :class:`tuple`\ [:class:`str`]
                Additional file/folder names or patterns to remove
            *r*: ``True`` | {``False``}
                Recursive option needed to delete folders
        :Versions:
            * 2022-12-29 ``@ddalle``: v1.0
        """
        # Only perform on working repo
        self.assert_working()
        # Form command
        if r:
            # Recursive (remove folders)
            cmd_list = ["git", "rm", "-r", fname]
        else:
            # Only individual files
            cmd_list = ["git", "rm", fname]
        # Add additional files/folders
        cmd_list.extend(fnames)
        # Attempt to remove the files and inform git
        self.check_call(cmd_list)

   # --- List files ---
    def ls_tree(self, *fnames, r=True, ref="HEAD"):
        r"""List files tracked by git, even in a bare repo

        Calling this function with no arguments will show all files
        tracked in *repo*.

        :Call:
            >>> filelist = repo.ls_tree(*fnames, r=True, ref="HEAD")
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *fnames*: :class:`tuple`\ [:class:`str`]
                Name of 0 or more files to search for
            *r*: {``True``} | ``False``
                Whether or not to search recursively
            *ref*: {``"HEAD"``} | :class:`str`
                Git reference, can be branch name, tag, or commit hash
        :Outputs:
            *filelist*: :class:`list`\ [:class:`str`]
                List of file names meeting above criteria
        :Versions:
            * 2022-12-21 ``@ddalle``: v1.0
        """
        # Handle ref=None
        ref = _safe_ref(ref)
        # Basic command
        cmdlist = ["git", "ls-tree", "--name-only"]
        # Append -r (recursive) option if appropriate
        if r:
            cmdlist.append("-r")
        # Add ref name (branch, commit, etc.)
        cmdlist.append(ref)
        # Add any specific files or folders
        cmdlist.extend(fnames)
        # List all files
        stdout = self.check_o(cmdlist).rstrip("\n")
        # Check if empty
        if len(stdout) == 0:
            # No files
            return []
        else:
            # Split into lines
            return stdout.split("\n")

   # --- Show ---
    def show(self, fname, ref="HEAD"):
        r"""Show contents of a file, even on a bare repo

        :Call:
            >>> fbytes = repo.show(fname, ref="HEAD")
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *fname*: :class:`str`
                Name of file to read
            *ref*: {``"HEAD"``} | :class:`str`
                Git reference, can be branch name, tag, or commit hash
        :Outputs:
            *fbytes*: :class:`bytes`
                Contents of *fname* in repository, in raw bytes
        :Versions:
            * 2022-12-22 ``@ddalle``: v1.0
        """
        # Handle ref=None
        ref = _safe_ref(ref)
        # Create command
        cmdlist = ["git", "show", "%s:%s" % (ref, fname)]
        # Run command using subprocess
        proc = Popen(cmdlist, stdout=PIPE, stderr=PIPE)
        # Wait for command
        stdout, stderr = proc.communicate()
        # Check status
        if proc.returncode or stderr:
            # Fixed portion of message
            msg = (
                ("Cannot show file '%s' from ref '%s'\n" % (fname, ref)) +
                ("Return code: %i" % proc.returncode))
            # Check for STDERR
            if stderr:
                msg += ("\nSTDERR: %s" % (stderr.decode("ascii").strip()))
            # Exception
            raise GitutilsSystemError(msg)
        # Otherwise, return the result, but w/o decoding
        return stdout

   # --- Shell utilities ---
    def check_o(self, cmd, codes=None, cwd=None):
        r"""Run a command, capturing STDOUT and checking return code

        :Call:
            >>> stdout = repo.check_o(cmd, codes=None, cwd=None)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *cmd*: :class:`list`\ [:class:`str`]
                Command to run in list form
            *codes*: {``None``} | :class:`list`\ [:class:`int`]
                Collection of allowed return codes (default only ``0``)
            *cwd*: {``None``} | :class:`list`
                Location in which to run subprocess
        :outputs:
            *stdout*: :class:`str`
                Captured STDOUT from command, if any
        :Versions:
            * 2023-01-08 ``@ddalle``: v1.0
        """
        # Run the command as requested, capturing STDOUT and STDERR
        stdout, stderr, ierr = shellutils.call_oe(cmd, cwd=cwd)
        # Check for errors, perhaps *fname* starts with --
        if codes and ierr in codes:
            # This exit code is allowed
            return stdout
        # Check for errors, perhaps mal-formed command
        if ierr:
            sys.tracebacklimit = 1
            raise GitutilsSystemError(
                ("Unexpected exit code %i from command\n" % ierr) +
                ("> %s\n\n" % " ".join(cmd)) +
                ("Original error message:\n%s" % stderr))
        # Output
        return stdout

    def check_call(self, cmd, codes=None, cwd=None):
        r"""Run a command and check return code

        :Call:
            >>> ierr = repo.check_call(cmd, codes=None, cwd=None)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *cmd*: :class:`list`\ [:class:`str`]
                Command to run in list form
            *codes*: {``None``} | :class:`list`\ [:class:`int`]
                Collection of allowed return codes (default only ``0``)
            *cwd*: {``None``} | :class:`list`
                Location in which to run subprocess
        :outputs:
            *ierr*: :class:`int`
                Return code from subprocess
        :Versions:
            * 2023-01-08 ``@ddalle``: v1.0
        """
        # Run the command as requested, capturing STDOUT and STDERR
        ierr = shellutils.call(cmd, cwd=cwd)
        # Check for errors, perhaps *fname* starts with --
        if codes and ierr in codes:
            # This exit code is allowed
            return ierr
        # Check for errors, perhaps mal-formed command
        if ierr:
            sys.tracebacklimit = 1
            raise GitutilsSystemError(
                ("Unexpected exit code %i from command\n" % ierr) +
                ("> %s\n\n" % " ".join(cmd)))
        # Output
        return ierr

   # --- Ignore ---
    def _ignore(self, fname):
        # Check if file already ignored by git
        if self.check_ignore(fname):
            return
        # Get path to .gitignore in same folder as *fname*
        frel, fbase = os.path.split(fname)
        fgitignore = os.path.join(frel, ".gitignore")
        # Ignore main file
        with open(fgitignore, "a") as fp:
            fp.write(fbase + "\n")
        # Add gitignore
        self._add(fgitignore)

   # --- Config ---
    def _to_ini(self, val) -> str:
        # Check for special cases
        if val is True:
            return "true"
        elif val is False:
            return "false"
        else:
            return str(val)


def get_gitdir(where=None, bare=None):
    r"""Get absolute path to git repo root, even on bare repos

    :Call:
        >>> gitdir = get_gitdir(where=None, bare=None)
    :Inputs:
        *where*: {``None``} | :class:`str`
            Working directory; can be local path or SSH path
        *bare*: {``None``} | ``True`` | ``False``
            Whether repo is bare (can be detected automatically)
    :Outputs:
        *gitdir*: :class:`str`
            Full path to top-level of working repo or git-dir of bare
    :Versions:
        * 2022-12-22 ``@ddalle``: v1.1; support older git vers
    """
    # Check for local/remote
    host, cwd = shellutils.identify_host(where)
    # Check if bare if needed
    if bare is None:
        bare = is_bare(where)
    # Get the "git-dir" for bare repos and "toplevel" for working repos
    if bare:
        # Get relative git dir
        gitdir, _ = shellutils.check_o(
            ["git", "rev-parse", "--git-dir"], cwd=cwd, host=host)
        # Absolute *gitdir* (--absolute-git-dir not avail on older git)
        gitdir = os.path.realpath(os.path.join(cwd, gitdir.strip()))
    else:
        gitdir, _ = shellutils.check_o(
            ["git", "rev-parse", "--show-toplevel"], cwd=cwd, host=host)
    # Output
    return gitdir.strip()


def is_bare(where=None):
    r"""Check if a location is in a bare git repo

    :Call:
        >>> q = is_bare(where=None)
    :Inputs:
        *where*: {``None``} | ;class:`str`
            Location to check
    :Outputs:
        *q*: ``True`` | ``False``
            Whether or not *where* is in a bare git repo
    :Versions:
        * 2023-01-08 ``@ddalle``: v1.0
    """
    # Check for local/remote
    host, cwd = shellutils.identify_host(where)
    # Check if bare
    bare, _, ierr = shellutils.call_oe(
        ["git", "config", "core.bare"], cwd=where, host=host)
    # Check for issues
    if ierr:
        path = _assemble_path(host, cwd)
        raise SystemError("Path is not a git repo: %s" % path)
    # Otherwise output
    return bare.strip() == "true"


def _assemble_path(host, cwd):
    if host is None:
        return cwd
    else:
        return host + ":" + cwd


def _safe_ref(ref=None):
    # Default ref
    if ref is None:
        ref = "HEAD"
    # Output
    return ref
