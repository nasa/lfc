r"""
``cli``: Command-line interface to ``lfc``
=============================================

This module provides several functions that are the main user interface
to LFC. There is a function :func:`main` that reads ``sys.argv`` (the
command-line strings of the current command). Then :func:`main`
dispatches one of several other functions, for example

    * :func:`lfc_clone`
    * :func:`lfc_init`
    * :func:`lfc_add`
    * :func:`lfc_pull`
    * :func:`lfc_push`

These secondary commands read Python argumennts and keyword arguments
rather than parsing ``sys.argv``, so they are usable to Python API
programmers as well.
"""

# Standard library
import os
import sys

# Local imports
from .lfcclone import lfc_clone
from .lfcerror import GitutilsError
from .lfcrepo import LFCRepo
from ._vendor.argread import ArgReader
from ._vendor.argread.clitext import compile_rst


# Help message
HELP_LFC = r"""File Control control (lfc)

Track and share large and/or binary files in git repositories.

:Usage:
    .. code-block:: console

        $ lfc CMD [OPTIONS]

:Inputs:
    * *CMD*: name of command to run

    Available commands are:

    ==================  ===========================================
    Command             Description
    ==================  ===========================================
    ``add``             Add or update a large file
    ``auto-pull``       Pull all mode-2 files in working repo
    ``auto-push``       Push all mode-2 files in working repo
    ``clone``           Clone git repo, install hooks, and autopull
    ``checkout``        Check out version of large file
    ``config``          View or set an LFC config variable
    ``init``            Initialize LFC for current git repo
    ``install-hooks``   Create git hooks for autopll and autopush
    ``ls-files``        List some or all ``.lfc`` files
    ``pull``            Pull one or more large files
    ``push``            Push one or more large files
    ``remote``          View or set an LFC remote cache
    ``replace-dvc``     Replace DVC with LFC for current repo
    ``set-mode``        Change mode of an LFC file
    ``show``            Show bytes of large file, even in bare repo
    ==================  ===========================================
"""

HELP_ADD = r"""
``lfc-add``: Add or update a large file
=======================================================

This command first finds all files in a WORKING repo (non-bare) that
match one or more user-specified file name patterns relative to the
current working directory and then  performs the following actions for
each corresponding large file:

    * Calculates the SHA-256 hash of the contents of that file
    * Stores that file in ``.lfc/cache/``
    * Creates a metadata file that appends ``.lfc`` to the file name

:Usage:
    .. code-block:: console

        $ lfc add FILE1 [FILE2, ...] [OPTIONS]

:Inputs:
    * *FILE1*: Name or pattern for first large file(s) to add
    * *FILE2*: Name or pattern for second large file(s) to add

:Options:
    -h, --help
        Display this help message and exit

    --mode MODE
        Set mode of large file(s) to *MODE*: {1} | 2

    -1
        Shortcut for ``--mode 1`` (default)

    -2
        Shortcut for ``--mode 2``
"""

HELP_AUTOPULL = r"""
``lfc-auto-pull``: Pull all mode-2 files
============================================================

This command can only be run in a WORKING repo. It will pull the latest
version of all mode-2 files. It will not pull any old versions of large
files. This can be configured to be either all large files (modes 1 and
2) or no large files.

This command is triggered automatically after ``git-pull`` if the LFC
hooks are installed.

:Usage:
    .. code-block:: console

        $ lfc auto-pull

:Options:
    -h, --help
        Display this help message and exit

    -r, --remote REMOTE
        Use remote cache named *REMOTE* (w/o ``-r`` flag, use default
        remote)
"""
HELP_AUTOPULL

HELP_AUTOPUSH = r"""
``lfc-auto-push``: Push all mode-2 files
============================================================

This command can only be run in a WORKING repo. It will push the latest
version of all mode-2 files. It will not push any old versions of large
files. This can be configured to be either all large files (modes 1 and
2) or no large files.

This command is triggered automatically after ``git-push`` if the LFC
hooks are installed.

:Usage:
    .. code-block:: console

        $ lfc auto-push

:Options:
    -h, --help
        Display this help message and exit

    -r, --remote REMOTE
        Use remote cache named *REMOTE* (w/o ``-r`` flag, use default
        remote)
"""

HELP_CHECKOUT = r"""
``lfc-checkout``: Check out a large file from cache
======================================================================

This function first finds one or more files that match at least one of
the file name patterns given by the user. The goal is to find ``.lfc``
files, since the original large files are not expected to exist. Then
for each such file, it will try to copy a file from the local cache
based on the hash in the ``.lfc`` file.

:Usage:
    .. code-block:: console

        $ lfc checkout FILE1 [FILE2 ...] [OPTIONS]

:Inputs:
    * *FILE1*: First file name or file name pattern
    * *FILE2*: Second file name or file name pattern

:Options:
    -h, --help
        Display this help message and exit

    -f, --force
        Overwrite existing large file even if uncached
"""

HELP_CONFIG = r"""
``lfc-config``: View or set LFC config variables
==================================================================

:Call:
    .. code-block:: console

        $ lfc config get SECTION.OPT [OPTIONS]
        $ lfc config set SECTION.OPT VAL [OPTIONS]

:Inputs:
    * *SECTION*: Config section name
    * *OPT*: Option within section to view/set
    * *VAL*: Value to set option to

:Options:
    -h, --help
        Display this help message and exit

:Examples:
    This will set the default "remote" to ``hub``:

    .. code-block:: console

        $ lfc config set core.remote hub

    This will print the name of the default remote (if set)

    .. code-block:: console

        $ lfc config get core.remote
"""

HELP_INIT = r"""
``lfc-init``: Initialize LFC repo
=================================================

This creates two folders (if they don't exist):

* ``.lfc/``
* ``.lfc/cache/``

And several files:

* ``.lfc/config``
* ``.lfc/.gitignore``

:Usage:
    .. code-block:: console

        $ lfc init [OPTIONS]

:Options:
    -h, --help
        Display this help message and exit
"""

HELP_INSTALL_HOOKS = r"""
``lfc-install-hooks``: Install LFC git-hooks
==============================================

This will create two executable files

* ``.git/hooks/pre-push``
* ``.git/hooks/post-merge``

relative to the top-level folder, unless they already exist.

:Usage:
    .. code-block:: console

        $ lfc install-hooks [OPTIONS]

:Options:
    -h, --help
        Display this help message and exit
"""

HELP_LS_FILES = r"""
``lfc-ls-files``: List large files
====================================

This command lists all ``.lfc`` files matching specified constraints. If
no arguments are given, it will list all ``.lfc`` files in the current
working directory or any folder within (recursively). Users can limit
this to all files starting with ``m``, for example, or apply any other
constratins.

:Usage:
    .. code-block:: console

        $ lfc ls-files [PAT1 [PAT2 ...]] [OPTIONS]

:Inputs:
    * *PAT1*: First pattern for files to list
    * *PAT2*: Second pattern for files to list

:Options:
    -h, --help
        Display this help message and exit
"""

HELP_PULL = r"""
``lfc-pull``: Retrieve and checkout one or more large files
============================================================

This function retrieves (either through remote or local copy) files,
puts them in the local cache, and then checks out a copy to the WORKING
repo. This command cannot be called from a bare repo.

The first step is to find all ``.lfc`` files matching the users input.
Users can specify which files to get by providing a list of file name
patterns. If the user does not specify any patterns, all files in the
current working directory or child directories (recursive) are pulled.

Then for each ``.lfc`` file that meets these constraints, it downloads
the file into the working repo's ``.lfc/cache/`` folder and then copies
the local cache file to the working repo.

:Usage:
    .. code-block:: console

        $ lfc pull [PAT1 [PAT2 ...]] [OPTIONS]

:Inputs:
    * *PAT1*: First pattern for files to list
    * *PAT2*: Second pattern for files to list

:Options:
    -h, --help
        Display this help message and exit

    -r, --remote REMOTE
        Use remote cache named *REMOTE* (w/o ``-r`` flag, use default
        remote)

    --mode MODE
        Only pull files of mode *MODE*: 1 | 2 | {both}

    -1
        Shortcut for ``--mode 1``

    -2
        Shortcut for ``--mode 2``

    -f, --force
        Overwrite uncached working files if they exist

    -q, --quiet
        Reduce STDOUT during download (no messages for up-to-date files)

:Examples:
    This will download and checkout the file ``myfile.dat`` if the file
    ``myfile.dat.lfc`` exists:

        .. code-block:: console

            $ lfc pull myfile.dat

    Note that

        .. code-block:: console

            $ lfc pull myfile.dat.lfc

    is equivalent. Suppose the hash for this file is ``'a4b3f7'``. Then
    it will look for the file ``a4/b3f7`` on the remote cache, copy it
    to the local cache, and then copy that file to ``myfile.dat`` in the
    current working directory.

    This will download and check out all files starting with ``a`` or
    ``b`` for which an ``.lfc`` file exists:

        .. code-block:: console

            $ lfc pull "a*.lfc" "b*.lfc"

    Suppose the current folder has these files:

        a1.dat
        a1.dat.lfc
        a2.dat
        a3.dat.lfc

    Then the above command would act on the files ``a1.dat`` and
    ``a3.dat``. ``a2.dat`` is not processed because there is no large
    file metadata file.
"""

HELP_PUSH = r"""
``lfc-push``: Push one or more large files to remote cache
============================================================

This sends files from a WORKING repo to a remote cache. It copies files
from the local cache to a remote cache, so if large files are not cached
(using ``lfc add``), they cannot be pushed.

The first step is to find all ``.lfc`` files matching the users input.
Users can specify which files to get by providing a list of file name
patterns. If the user does not specify any patterns, all files in the
current working directory or child directories (recursive) are pulled.

Then for each ``.lfc`` file that meets these constraints, it reads that
file to find the hash. It then checks the working repo's cache,
``.lfc/cache/`` for that file. If it's present, it copies it to the
remote cache.

:Usage:
    .. code-block:: console

        $ lfc push [PAT1 [PAT2 ...]] [OPTIONS]

:Inputs:
    * *PAT1*: First pattern for files to list
    * *PAT2*: Second pattern for files to list

:Options:
    -h, --help
        Display this help message and exit

    -r, --remote REMOTE
        Use remote cache named *REMOTE* (w/o ``-r`` flag, use default
        remote)

    --mode MODE
        Only push files of mode *MODE*: 1 | 2 | {both}

    -1
        Shortcut for ``--mode 1``

    -2
        Shortcut for ``--mode 2``

    -q, --quiet
        Reduce STDOUT during download (no messages for up-to-date files)

:Examples:
    This will push the files ``myfile.dat`` and ``otherfile.dat`` if the
    files ``myfile.dat.lfc`` and ``otherfile.dat.lfc`` exist and are
    present in the local cache:

        .. code-block:: console

            $ lfc push myfile.dat otherfile.dat

    Note that

        .. code-block:: console

            $ lfc push myfile.dat.lfc otherfile.dat.lfc

    is equivalent. Suppose the hash for this file is ``'a4b3f7'``. Then
    it will look for the file ``a4/b3f7`` in the local cache  and then
    copy it to the remote cache with the same file name.

    This will push all files starting with ``a`` with mode=2 in the
    current folder or any child thereof

        .. code-block:: console

            $ lfc push "a*.lfc" -2
"""

HELP_REMOTE = r"""
``lfc-remote``: Show or set URL to an LFC remote cache
========================================================

Define the URL for a remote or list all current remotes.

:Usage:
    .. code-block:: console

        $ lfc remote CMDNAME [REMOTENAME URL] [OPTIONS]

:Inputs:
    * *CMDNAME*: name of sub-command: ``list`` | ``add``
    * *REMOTENAME*: name of remote for which to set *URL*
    * *URL*: SSH or local path to remote cache

:Options:
    -h, --help
        Display this help message and exit

    -d, --default
        Set *REMOTENAME* as the default LFC remote
"""

HELP_REPLACE_DVC = r"""
``lfc-replace-dvc``: Replace any DVC settings and file names
===============================================================

Although LFC can work in an existing DVC repo, using ``lfc-add`` will
break DVC's ability to function. It is usually preferable to make a
repo where you intend to use LFC use the ``.lfc`` file extension instead
of ``.dvc``.  This command removes some DVC artifacts and rename others.

This will rename some files and folders:

    * ``.dvc/`` -> ``.lfc/``
    * ``*.dvc`` -> ``*.lfc``

It will also delete some JSON files used by DVC if present.

The function is safe to call multiple times if DVC has been
partially replaced. If there are no DVC artifacts, this function
will take no action.

It does **not** recompute hashes. If any existing MD-5 hashes are
present, LFC will continue to use them, but updating the file
(using ``lfc add``) will still use a SHA-256 hash.

:Usage:
    .. code-block:: console

        $ lfc replace-dvc [OPTIONS]

:Options:
    -h, --help
        Display this help message and exit
"""

HELP_SET_MODE = r"""
``lfc-set-mode``: Set the mode of one or more LFC files
=========================================================

This file can change the mode of one or more large files that have
already been added (and therefore a ``.lfc`` file exists). You can
set the mode to either ``1`` or ``2``:

* Mode-1 files are auto-pushed and -pulled with git pushes and pulls
* Mode-2 files are explicitly on-demand

:Usage:
    .. code-block:: console

        $ lfc set-mode [PAT1 [PAT2 ...]] [OPTIONS]

:Inputs:
    * *PAT1*: First pattern for files to list
    * *PAT2*: Second pattern for files to list

:Options:
    -h, --help
        Display this help message and exit

    --mode MODE
        Set all matching files to mode *MODE*: {1} | 2

    -1
        Shortcut for ``--mode 1`` or ``mode=1``

    -2
        Shortcut for ``--mode 2`` or ``mode=2``
"""

HELP_SHOW = r"""
``lfc-show``: Print contents of a large file to STDOUT
=========================================================

Print contents of a large file to STDOUT, even in a bare repo. This
function does not decode the bytes so that binary files can be piped
from bare repos through STDOUT.

:Usage:
    .. code-block:: console

        $ lfc show FNAME [OPTIONS]

:Inputs:
    * *FNAME*: name of large file (including ``.lfc``) to show

:Options:
    -h, --help
        Display this help message and exit

    --ref REF
        Use specified git ref, for example commit hash or branch name;
        default is ``HEAD``
"""


# Dictionary of help commands
HELP_DICT = {
    "add": HELP_ADD,
    "auto-pull": HELP_AUTOPULL,
    "auto-push": HELP_AUTOPUSH,
    "checkout": HELP_CHECKOUT,
    "config": HELP_CONFIG,
    "init": HELP_INIT,
    "install-hooks": HELP_INSTALL_HOOKS,
    "ls-files": HELP_LS_FILES,
    "pull": HELP_PULL,
    "push": HELP_PUSH,
    "remote": HELP_REMOTE,
    "replace-dvc": HELP_REPLACE_DVC,
    "set-mode": HELP_SET_MODE,
    "show": HELP_SHOW,
}


# Customized CLI parser
class LFCArgParser(ArgReader):
    # No attributes
    __slots__ = ()

    # Aliases
    _optmap = {
        "d": "default",
        "h": "help",
        "q": "quiet",
        "r": "remote",
    }

    # Options that never take a value
    _optlist_noval = (
        "default",
        "help",
        "quiet",
    )

    # Options that convert from string
    _optconverters = {
        "mode": int,
    }


# Commands for ``lfc remote``
CMD_REMOTE_DICT = {
    "add": LFCRepo.set_lfc_remote,
    "list": LFCRepo._print_lfc_remotes,
    "ls": LFCRepo._print_lfc_remotes,
    "rm": LFCRepo.rm_lfc_remote,
    "set-url": LFCRepo.set_lfc_remote,
}

# Commands for ``lfc config``
CMD_CONFIG_DICT = {
    "get": LFCRepo._print_lfc_config_get,
    "set": LFCRepo.lfc_config_set,
}

# Return codes
IERR_OK = 0
IERR_CMD = 16
IERR_ARGS = 32
IERR_FILE_NOT_FOUND = 128


def lfc_add(*a, **kw):
    r"""Calculate metadata for large file(s) and cache them

    :Call:
        >>> lfc_add(*a, **kw)
        >>> lfc_add(pat1, mode=1)
        >>> lfc_add(pat1, pat2, ..., mode=1)
    :Inputs:
        *pat1*: :class:`str`
            Name of large file or file name pattern
        *pat2*: :class:`str`
            Second file name or file name pattern
        *mode*: {``1``} | ``2``
            LFC mode for each added file
    """
    # Read the repo
    repo = LFCRepo()
    # Check for -2 -> mode=2
    _parse_mode(kw)
    # Add it
    repo.lfc_add(*a, **kw)


def lfc_autopull(*a, **kw):
    r"""Pull most recent version of mode-2 (configurable) LFC files

    Normally this will pull all mode-2 files, but that can be configured
    to all files or no files by setting ``core.autopull`` in
    ``.lfc/config``. Users may also limit the pull to specific files,
    but that is not the primary use case.

    :Call:
        >>> lfc_autopull()
        >>> lfc_autopull(pat1, pat2, ..., quiet=True)
    :Inputs:
        *pat1*: :class:`str`
            Name of large file or file name pattern
        *pat2*: :class:`str`
            Second file name or file name pattern
        *quiet*: {``True``} | ``False``
            Option to suppress STDOUT for files already up-to-date
    """
    # Read the repo
    repo = LFCRepo()
    # Get mode
    mode = repo.get_lfc_autopull()
    # Settings
    kw.setdefault("quiet", True)
    kw["mode"] = mode
    # Push
    repo.lfc_pull(*a, **kw)


def lfc_autopush(*a, **kw):
    r"""Push most recent version of mode-2 (configurable) LFC files

    Normally this will push all mode-2 files, but that can be configured
    to all files or no files by setting ``core.autopull`` in
    ``.lfc/config``. Users may also limit the push to specific files,
    but that is not the primary use case.

    :Call:
        >>> lfc_autopush()
        >>> lfc_autopush(pat1, pat2, ..., quiet=True)
    :Inputs:
        *pat1*: :class:`str`
            Name of large file or file name pattern
        *pat2*: :class:`str`
            Second file name or file name pattern
        *quiet*: {``True``} | ``False``
            Option to suppress STDOUT for files already up-to-date
    """
    # Read the repo
    repo = LFCRepo()
    # Get mode
    mode = repo.get_lfc_autopush()
    # Settings
    kw.setdefault("quiet", True)
    kw["mode"] = mode
    # Push
    repo.lfc_push(*a, **kw)


def lfc_checkout(*a, **kw):
    r"""Check out one or more large files (from local cache)

    If no patterns are specified, the target will be all large files
    that are in the current folder or children thereof.

    :Call:
        >>> lfc_checkout()
        >>> lfc_checkout(pat1, pat2, ..., force=False)
    :Inputs:
        *pat1*: :class:`str`
            Name of large file or file name pattern
        *pat2*: :class:`str`
            Second file name or file name pattern
        *f*, *force*: ``True`` | {``False``}
            Delete uncached working file if present
    """
    # Read the repo
    repo = LFCRepo()
    # Checkout
    repo.lfc_checkout(*a, **kw)


def lfc_config(*a, **kw):
    r"""Print or set an LFC configuration variable

    :Call:
        >>> lfc_config(cmdname, fullopt)
        >>> lfc_config(cmdname, fullopt, val)
    :Inputs:
        *cmdname*: ``"get"`` | ``"set"``
            LFC configuration operation to take
        *fullopt*: :class:`str`
            Full option name, ``"{sec}.{opt}"``
        *val*: :class:`object`
            Value to set if *cmdname* is ``"set"``
    """
    # Read the repo
    repo = LFCRepo()
    # Check command
    if len(a) < 1:
        print("lfc-config got %i arguments; at least 1 required" % len(a))
        return IERR_ARGS
    # Get command name
    cmdname = a[0]
    # Get function
    func = CMD_CONFIG_DICT.get(cmdname)
    # Check it
    if func is None:
        # Unrecognized function
        print("Unexpected 'lfc-remote' command '%s'" % cmdname)
        print("Options are: " + " | ".join(list(CMD_CONFIG_DICT.keys())))
        return IERR_CMD
    # Run function
    func(repo, *a[1:], **kw)


def lfc_init(*a, **kw):
    r"""Initialize a repo as an LFC repo

    This will create (if necessary) the following folders:

    *   ``.lfc/``
    *   ``.lfc/cache/``

    and the following files:

    *   ``.lfc/config``
    *   ``.lfc/.gitignore``

    :Call:
        >>> lfc_init()
    """
    # Read the repo
    repo = LFCRepo()
    # Push it
    repo.lfc_init(*a, **kw)


def lfc_install_hooks(*a, **kw):
    r"""Install git-hooks in current LFC repo

    This creates the following files relative to the top-level folder
    of the working repository:

    *   ``.git/hooks/post-merge``
    *   ``.git/hooks/pre-push``

    If the files exist, this will not overwrite them. After writing the
    file, it also makes the executable.

    :Call:
        >>> lfc_install_hooks()
    """
    # Read the repo
    repo = LFCRepo()
    # Install hooks
    repo.lfc_install_hooks(*a, **kw)


def lfc_ls_files(*a, **kw):
    r"""List files tracked by LFC

    If called from a working repository, only files in the current
    folder or a subfolder thereof are listed.

    :Call:
        >>> lfc_ls_files()
        >>> lfc_ls_files(*pats)
    :Inputs:
        *pats*: :class:`tuple`\ [:class:`str`]
            (Optional) list of file name patterns to use
    :STDOUT:
        Each matching ``*.lfc`` file is printed to a line in STDOUT
    """
    # Read the repo
    repo = LFCRepo()
    # Check for -2 -> mode=2
    _parse_mode(kw)
    # List files
    filelist = repo.find_lfc_files(*a, **kw)
    # Print them
    print("\n".join(filelist))


def lfc_pull(*a, **kw):
    r"""Pull (fetch and checkout) one or more large files

    If no patterns are specified, the target will be all large files
    that are in the current folder or children thereof.

    :Call:
        >>> lfc_pull()
        >>> lfc_pull(pat1, pat2, ..., quiet=True)
    :Inputs:
        *pat1*: :class:`str`
            Name of large file or file name pattern
        *pat2*: :class:`str`
            Second file name or file name pattern
        *mode*: {``None``} | ``1`` | ``2``
            Optionally only pull files of a specified mode
        *quiet*: {``True``} | ``False``
            Option to suppress STDOUT for files already up-to-date
        *f*, *force*: ``True`` | {``False``}
            Delete uncached working file if present
    """
    # Read the repo
    repo = LFCRepo()
    # Check for -2 -> mode=2
    _parse_mode(kw)
    # Push it
    repo.lfc_pull(*a, **kw)


def lfc_push(*a, **kw):
    r"""Push one or more large files

    If no patterns are specified, the target will be all large files
    that are in the current folder or children thereof.

    :Call:
        >>> lfc_push()
        >>> lfc_push(pat1, pat2, ..., quiet=True)
    :Inputs:
        *pat1*: :class:`str`
            Name of large file or file name pattern
        *pat2*: :class:`str`
            Second file name or file name pattern
        *mode*: {``None``} | ``1`` | ``2``
            Optionally only push files of a specified mode
        *quiet*: {``True``} | ``False``
            Option to suppress STDOUT for files already up-to-date
    """
    # Read the repo
    repo = LFCRepo()
    # Check for -2 -> mode=2
    _parse_mode(kw)
    # Push it
    repo.lfc_push(*a, **kw)


def lfc_remote(*a, **kw):
    r"""Show or set URL to an LFC remote cache

    :Call:
        >>> lfc_remote(cmdname)
        >>> lfc_remote("list")
        >>> lfc_remote("add", remote, url, **kw)
    :Inputs:
        *cmdname*: ``"list"`` | ``"add"`` | ``"set-url"``
            Name of LFC action to take
        *remote*: :class:`str`
            Name of LFC remote
        *url*: :class:`str`
            Path to remote cache (local or SSH)
        *d*, *default*: ``True`` | {``False``}
            Set *remote* as the default LFC remote
    """
    # Read the repo
    repo = LFCRepo()
    # Check command
    if len(a) < 1:
        print("lfc-remote got %i arguments; at least 1 required" % len(a))
        return IERR_ARGS
    # Get command name
    cmdname = a[0]
    # Get function
    func = CMD_REMOTE_DICT.get(cmdname)
    # Check it
    if func is None:
        # Unrecognized function
        print("Unexpected 'lfc-remote' command '%s'" % cmdname)
        print("Options are: " + " | ".join(list(CMD_REMOTE_DICT.keys())))
        return IERR_CMD
    # Run function
    func(repo, *a[1:], **kw)


def lfc_replace_dvc(*a, **kw):
    r"""Replace any DVC settings and file names

    This will rename some files and folders:

        * ``.dvc/`` -> ``.lfc/``
        * ``*.dvc`` -> ``*.lfc``

    It will also delete some JSON files used by DVC if present.

    The function is safe to call multiple times if DVC has been
    partially replaced. If there are no DVC artifacts, this function
    will take no action.

    It does **not** recompute hashes. If any existing MD-5 hashes are
    present, LFC will continue to use them, but updating the file
    (using ``lfc add``) will still use a SHA-256 hash.

    :Call:
        >>> lfc_replace_dvc()
    """
    # Read the repo
    repo = LFCRepo()
    # Replace
    repo.lfc_replace_dvc(*a, **kw)


def lfc_set_mode(*a, **kw):
    r"""Set the mode of one or more LFC files

    :Call:
        >>> lfc_set_mode(*pats, mode=None)
    :Inputs:
        *pat1*: :class:`str`
            Name of large file or file name pattern
        *pat2*: :class:`str`
            Second file name or file name pattern
        *mode*: ``1`` | ``2``
            Required LFC mode to set for each file matching any *pat*
    """
    # Read the repo
    repo = LFCRepo()
    # Check for -2 -> mode=2
    _parse_mode(kw)
    # Set mode
    repo.lfc_set_mode(*a, **kw)


def lfc_show(*a, **kw):
    r"""Print contents of a large file to STDOUT, even in bare repo

    This function does not decode the bytes so that binary files can be
    piped from bare repos through STDOUT.

    :Call:
        >>> lfc_show(fname, ref="HEAD")
    :Inputs:
        *fname*: :class:`str`
            Name of original file or large file stub
        *ref*: {``None``} | :class:`str`
            Optional git reference (default ``HEAD`` on bare repo)
    """
    # Read the repo
    repo = LFCRepo()
    # Check if *a* has exactly one file
    if len(a) != 1:
        print("lfc-show got %i arguments; expected %i" % (len(a), 1))
        return IERR_ARGS
    # Call the *show* command
    contents = repo.lfc_show(a[0], **kw)
    # Check for result
    if contents is None:
        return IERR_FILE_NOT_FOUND
    # Write contents back to STDOUT
    os.write(sys.stdout.fileno(), contents)


def _parse_mode(kw):
    # Check for -2 or -1
    for val in ("1", "2"):
        # Transfer it to mode=1 or mode=2
        if val in kw:
            kw["mode"] = int(val)
            kw.pop(val)


# Command dictionary
CMD_DICT = {
    "add": lfc_add,
    "auto-pull": lfc_autopull,
    "auto-push": lfc_autopush,
    "clone": lfc_clone,
    "checkout": lfc_checkout,
    "config": lfc_config,
    "init": lfc_init,
    "install-hooks": lfc_install_hooks,
    "ls-files": lfc_ls_files,
    "pull": lfc_pull,
    "push": lfc_push,
    "remote": lfc_remote,
    "replace-dvc": lfc_replace_dvc,
    "set-mode": lfc_set_mode,
    "show": lfc_show,
}


# Main function
def main() -> int:
    r"""Main command-line interface to ``lfc``

    The function works by reading the second word of ``sys.argv`` and
    dispatching a dedicated function for that purpose.

    :Call:
        >>> ierr = main()
    :Inputs:
        (read from ``sys.argv``)
    :Outputs:
        *ierr*: :class:`int`
            Return code
    """
    # Create parser
    parser = LFCArgParser()
    # Parse args
    a, kw = parser.parse()
    kw.pop("__replaced__", None)
    # Check for no commands
    if len(a) == 0:
        print(compile_rst(HELP_LFC))
        return 0
    # Get command name
    cmdname = a[0]
    # Get function
    func = CMD_DICT.get(cmdname)
    # Check it
    if func is None:
        # Unrecognized function
        print("Unexpected command '%s'" % cmdname)
        print("Options are: " + " | ".join(list(CMD_DICT.keys())))
        return IERR_CMD
    # Check for "help" option
    if kw.get("help", False):
        # Get help message for this command; default to main help
        msg = HELP_DICT.get(cmdname, HELP_LFC)
        print(compile_rst(msg))
        return 0
    # Run function
    try:
        ierr = func(*a[1:], **kw)
    except GitutilsError as err:
        print(f"{err.__class__.__name__}:")
        print(f"  {err}")
        return 1
    # Convert None -> 0
    ierr = IERR_OK if ierr is None else ierr
    # Normal exit
    return ierr
