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
import difflib
import os
import posixpath
import re
import shutil
import sys
from typing import Optional

# Local imports
from .lfcerror import GitutilsError, LFCCloneError
from .lfcrepo import LFCRepo
from ._vendor.argread import ArgReader
from ._vendor.argread.clitext import compile_rst
from ._vendor.gitutils._vendor import shellutils


# Regular expression for "pfe;" or other messed-up remote paths
REGEX_WINREMOTE = re.compile("[A-Za-z][A-Za-z0-9.-]*;")
# Base path to bash executable
BASH_EXEC = shutil.which("bash")
# Root to WINPTY OS base (on Windows when using git-bash.exe)
WPTY_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(BASH_EXEC)))


# Customized CLI parser
class LFCArgParser(ArgReader):
    # No attributes
    __slots__ = ()

    # Aliases
    _optmap = {
        "d": "default",
        "f": "force",
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

    # Allowed values
    _optvals = {
        "mode": (1, 2),
    }

    # Descriptions
    _help_opt = {
        "1": "Limit operations to mode-1 files",
        "2": "Limit operations to mode-2 files",
        "bare": "The new repo will be bare (no working files)",
        "default": "Declare specified remote as default",
        "force": "Overwrite unchached large file or purge file not on remote",
        "fname": "Name of file to display",
        "help": "Display this help message and exit",
        "mode": "LFC-mode to use {1} | 2",
        "quiet": "Reduce STDOUT",
        "ref": "Git ref, e.g. commit hash or branch; default is ``HEAD``",
        "remote": "Use LFC remote named *REMOTE* (else use default remote)",
        "file1": "First file name or file name pattern",
        "file2": "Second file name or file name pattern",
    }

    # Arg names in option help messages
    _help_optarg = {
        "ref": "REF",
        "remote": "REMOTE",
    }


# Special parser for lfc-add
class LFCAddParser(LFCArgParser):
    # No attributes
    __slots__ = ()

    # Command name
    _name = "lfc-add"

    # Viable options
    _optlist = (
        "help",
        "mode",
        "1",
        "2",
        "quiet",
    )

    # One input required
    _nargmin = 1

    # Primary purpose of command
    _help_title = "Add or update a large file"

    # Longer description
    _help_description = """
    \rThis command first finds all files in a WORKING repo (non-bare) that
    \rmatch one or more user-specified file name patterns relative to the
    \rcurrent working directory and then  performs the following actions for
    \reach corresponding large file:

    * Calculates the SHA-256 hash of the contents of that file
    * Stores that file in ``.lfc/cache/``
    * Creates a metadata file that appends ``.lfc`` to the file name"""

    # List of arguments (for help)
    _arglist = (
        "pat",
        "pat1",
    )

    # Description for additional options
    _help_opt = {
        "pat": "Pattern for file(s) to add",
        "pat1": "Second pattern for files to add",
    }


# Special parser for lfc-auto-pull
class LFCAutoPullParser(LFCArgParser):
    # No attributes
    __slots__ = ()

    # Command name
    _name = "lfc-auto-pull"

    # Viable options
    _optlist = (
        "help",
        "remote",
    )

    # Primary purpose of command
    _help_title = "Pull all mode-2 files"

    # Longer description
    _help_description = """
    \rThis command can only be run in a WORKING repo. It will pull the latest
    \rversion of all mode-2 files. It will not pull any old versions of large
    \rfiles. This can be configured to be either all large files (modes 1 and
    \r2) or no large files.

    \rThis command is triggered automatically after ``git-pull`` if the LFC
    \rhooks are installed.
    """


# Special parser for lfc-auto-push
class LFCAutoPushParser(LFCArgParser):
    # No attributes
    __slots__ = ()

    # Command name
    _name = "lfc-auto-push"

    # Viable options
    _optlist = (
        "help",
        "remote",
    )

    # Primary purpose of command
    _help_title = "Push all mode-2 files"

    # Longer description
    _help_description = """
    \rThis command can only be run in a WORKING repo. It will push the latest
    \rversion of all mode-2 files. It will not push any old versions of large
    \rfiles. This can be configured to be either all large files (modes 1 and
    \r2) or no large files.

    \rThis command is triggered automatically after ``git-push`` if the LFC
    \rhooks are installed.
    """


# Special parser for lfc-checkout
class LFCCheckoutParser(LFCArgParser):
    # No attributes
    __slots__ = ()

    # Command name
    _name = "lfc-checkout"

    # Viable options
    _optlist = (
        "help",
        "force",
    )

    # Primary purpose of command
    _help_title = "Check out a large file from cache"

    # Longer description
    _help_description = """
    \rThis function first finds one or more files that match at least one of
    \rthe file name patterns given by the user. The goal is to find ``.lfc``
    \rfiles, since the original large files are not expected to exist. Then
    \rfor each such file, it will try to copy a file from the local cache
    \rbased on the hash in the ``.lfc`` file."""

    # Custom option description
    _help_opt = {
        "force": "overwrite existing uncached working file",
    }


# Special parser for lfc-clone
class LFCCloneParser(LFCArgParser):
    # No attributes
    __slots__ = ()

    # Command name
    _name = "lfc-clone"

    # Viable options
    _optlist = (
        "help",
        "bare",
    )

    # Positional parameters
    _arglist = (
        "in_repo",
        "out_repo",
    )

    # Minimum args
    _nargmin = 1

    # Primary purose of function
    _help_title = "Clone a repo (using git) and pull all mode-2 LFC files"

    # Longer description
    _help_description = """
    \rThis function is equivalent to calling ``git clone`` but with two
    \radditional actions after the git clone operation is completed:

    \r1. Install hooks (see ``lfc install-hooks``)
    \r2. Pull most recent version of all mode-2 files (``lfc auto-pull``)

    \rIt is equivalent to a normal git clone followed by those two commands.
    """

    # Additional option descriptions
    _help_opt = {
        "in_repo": "URL of repo to fork or clone",
        "out_repo": "(optional) name of new repo",
    }


# Ront-desk for lfc-config
class LFCConfigParser(LFCArgParser):
    # No attributes
    __slots__ = ()

    # Command name
    _name = "lfc-config"

    # Viable options
    _optlist = (
        "help",
    )

    # Allowed values
    _optvals = {
        "cmd": ("get", "set"),
    }

    # Positional parameters
    _arglist = (
        "cmdname",
        "opt",
        "val",
    )

    # Minimum arg count
    _nargmin = 2
    _nargmax = 3

    # Primary purpose of command
    _help_title = "View or set LFC config variables"

    # Longer description
    _help_extra = """
    \r:Examples:
    \r    This will set the default "remote" to ``hub``:

    \r    .. code-block:: console

    \r        $ lfc config set core.remote hub

    \r    This will print the name of the default remote (if set)

    \r    .. code-block:: console

    \r        $ lfc config get core.remote
    \r        hub
    """

    # Additional option descriptions
    _help_opt = {
        "cmdname": "Name of config action (get | set)",
        "opt": "Section and option name joined by ``.``, e.g. ``core.remote``",
        "val": "Value to set for option when using ``set``",
    }


# Special parser for lfc-init
class LFCInitParser(LFCArgParser):
    # No attributes
    __slots__ = ()

    # Name of command
    _name = "lfc-init"

    # Viable options
    _optlist = (
        "help",
    )

    # Primary purpose of command
    _help_title = "Initialize LFC repo"

    # Longer description
    _help_description = """
    \rThis creates two folders (if they don't exist):

    \r* ``.lfc/``
    \r* ``.lfc/cache/``

    \rAnd several files:

    \r* ``.lfc/config``
    \r* ``.lfc/.gitignore``
    """


# Special parser for lfc-install-hooks
class LFCInstallHooksParser(LFCArgParser):
    # No attributes
    __slots__ = ()

    # Name of command
    _name = "lfc-install-hooks"

    # Viable options
    _optlist = (
        "help",
    )

    # Primary purpose of command
    _help_title = "Install LFC git-hooks"

    # Longer description
    _help_description = """
    \rThis will create two executable files

    \r* ``.git/hooks/pre-push``
    \r* ``.git/hooks/post-merge``

    \rrelative to the top-level folder, unless they already exist.
    """


# Special parser for lfc-ls-files
class LFCListFilesParser(LFCArgParser):
    # No attributes
    __slots__ = ()

    # Name of command
    _name = "lfc-ls-files"

    # Viable options
    _optlist = (
        "help",
    )

    # Positional parameters
    _arglist = (
        "pat1",
        "pat2",
    )

    # Required arguments
    _nargmin = 0

    # Primary purpose of command
    _help_title = "List large files"

    # Longer description
    _help_description = """
    \rThis command lists all ``.lfc`` files matching specified constraints. If
    \rno arguments are given, it will list all ``.lfc`` files in the current
    \rworking directory or any folder within (recursively). Users can limit
    \rthis to all files starting with ``m``, for example, or apply any other
    \rconstratins.
    """

    # Description of additional options
    _help_opt = {
        "pat1": "First pattern for files to list",
        "pat2": "Second pattern for files to list",
    }


# Special parser for lfc-pull
class LFCPullParser(LFCArgParser):
    # No attributes
    __slots__ = ()

    # Name of command
    _name = "lfc-pull"

    # Viable options
    _optlist = (
        "help",
        "remote",
        "mode",
        "1",
        "2",
        "force",
        "quiet",
    )

    # Positional parameters
    _arglist = (
        "pat1",
        "pat2",
    )

    # Primary purpose of command
    _help_title = "Retrieve and checkout one or more large files"

    # Longer description
    _help_description = """
    \rThis function retrieves (either through remote or local copy) files,
    \rputs them in the local cache, and then checks out a copy to the WORKING
    \rrepo. This command cannot be called from a bare repo.

    \rThe first step is to find all ``.lfc`` files matching the users input.
    \rUsers can specify which files to get by providing a list of file name
    \rpatterns. If the user does not specify any patterns, all files in the
    \rcurrent working directory or child directories (recursive) are pulled.

    \rThen for each ``.lfc`` file that meets these constraints, it downloads
    \rthe file into the working repo's ``.lfc/cache/`` folder and then copies
    \rthe local cache file to the working repo.
    """

    # Custom option description
    _help_opt = {
        "force": "overwrite existing uncached working file",
        "pat1": "First file name or pattern for files to pull",
        "pat2": "Second file name or pattern for files to pull",
    }

    # Even more help
    _help_extra = """
    \r:Examples:
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


# Special parser for lfc-purge
class LFCPurgeParer(LFCArgParser):
    # No attributes
    __slots__ = ()

    # Command name
    _name = "lfc-purge"

    # Viable options
    _optlist = (
        "help",
        "remote",
        "force",
        "quiet",
    )

    # Positional parameters
    _arglist = (
        "file1",
        "file2",
    )

    # Primary purpose of command
    _help_title = "Remove large file(s) from working copy and cache"

    # Viable options
    _optlist = (
        "help",
        "remote",
        "force",
        "quiet",
    )

    # Longer description
    _help_description = """
    \rThis function clears large file(s) from a (usually working) repo when
    \rthe user no longer needs them. It deletes both working copies (if
    \rappropriate) and local cache files.
    """


# Special parser for lfc-push
class LFCPushParser(LFCArgParser):
    # No attributes
    __slots__ = ()

    # Name of command
    _name = "lfc-push"

    # Viable options
    _optlist = (
        "help",
        "remote",
        "mode",
        "1",
        "2",
        "quiet",
    )

    # Positional parameters
    _arglist = (
        "pat1",
        "pat2",
    )

    # Primary purpose of command
    _help_title = "Push one or more large files to remote cache"

    # Longer description
    _help_description = """
    \rThis sends files from a WORKING repo to a remote cache. It copies files
    \rfrom the local cache to a remote cache, so if large files are not cached
    \r(using ``lfc add``), they cannot be pushed.

    \rThe first step is to find all ``.lfc`` files matching the users input.
    \rUsers can specify which files to get by providing a list of file name
    \rpatterns. If the user does not specify any patterns, all files in the
    \rcurrent working directory or child directories (recursive) are pulled.

    \rThen for each ``.lfc`` file that meets these constraints, it reads that
    \rfile to find the hash. It then checks the working repo's cache,
    \r``.lfc/cache/`` for that file. If it's present, it copies it to the
    \rremote cache
    """

    # Custom option description
    _help_opt = {
        "pat1": "First file name or pattern for files to push",
        "pat2": "Second file name or pattern for files to push",
    }

    # Even more help
    _help_extra = """
    \r:Examples:
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


# Special parser for lfc-remote-add
class LFCRemoteAddParser(LFCArgParser):
    # No attributes
    __slots__ = ()

    # Command name
    _name = "lfc-remote-add"

    # Viable options
    _optlist = (
        "help",
        "default",
    )

    # Positional parameters
    _arglist = (
        "remote",
        "url",
    )

    # Required args
    _nargmin = 2
    _nargmax = 2

    # Primary purpose of command
    _help_title = "Set or modify URL for an LFC remote cache"

    # Additional descriptions
    _help_opt = {
        "url": "Path to remote cache (SSH or local)",
    }


# Special parser for lfc-remote-add-hosts
class LFCRemoteAddHostsParser(LFCArgParser):
    # No attributes
    __slots__ = ()

    # Command name
    _name = "lfc-remote-add-hosts"

    # Viable options
    _optlist = (
        "help",
    )

    # Positional parameters
    _arglist = (
        "remote",
        "host1",
        "host2",
    )

    # Required args
    _nargmin = 2

    # Primary purpose of command
    _help_title = "Add regular exprs for host names to consider 'local'"

    # Additional information
    _help_description = """
    \rSpecify one or more regular expressions for host names. LFC will then
    \rcompare the current host name to this expression(s); if it matches,
    \rLFC will not use SSH for data transfers.

    \rThis is useful in cases where multiple machines may have local access
    \rto a shared file system.
    """

    # Additional descriptions
    _help_opt = {
        "host1": "Regular expression for local hostname(s)",
        "host2": "Additional local hostname regular expression",
    }


# Special parser for lfc-remote-list
class LFCRemoteListParser(LFCArgParser):
    # No attributes
    __slots__ = ()

    # Command name
    _name = "lfc-remote-list"

    # Viable options
    _optlist = (
        "help",
    )

    # Primary purpose of command
    _help_title = "Remove an LFC remote from config"


# Special parser for lfc-remote-add
class LFCRemoteRemoveParser(LFCArgParser):
    # No attributes
    __slots__ = ()

    # Command name
    _name = "lfc-remote-rm"

    # Viable options
    _optlist = (
        "help",
    )

    # Positional parameters
    _arglist = (
        "remote",
    )

    # Required args
    _nargmin = 1
    _nargmax = 1

    # Primary purpose of command
    _help_title = "Set or modify URL for an LFC remote cache"

    # Additional descriptions
    _help_opt = {
        "url": "Path to remote cache (SSH or local)",
    }


# Front desk for LFC-remote
class LFCRemoteFrontDesk(ArgReader):
    # No attributes
    __slots__ = ()

    # List of commands
    _cmdlist = (
        "add",
        "add-hosts",
        "list",
        "rm",
    )

    # Optional command names
    _cmdmap = {
        "add-host": "add-hosts",
        "ls": "list",
        "remove": "rm",
        "set-url": "add",
    }

    # Sub-parsers for each command
    _cmdparsers = {
        "add": LFCRemoteAddParser,
        "add-hosts": LFCRemoteAddHostsParser,
        "list": LFCRemoteListParser,
        "rm": LFCRemoteRemoveParser,
    }

    # Aliases
    _optmap = {
        "h": "help",
    }

    # Name of command
    _name = "lfc-remote"

    # Primary purpose of command
    _help_title = "Show or set URL for an LFC remote cache"

    # Descriptions for options
    _help_opt = {
        "help": "Display this help message and exit",
    }

    # Description for each command
    _help_cmd = {
        "add": "Add or modify an LFC remote",
        "add-hosts": "Add regular expressions for local hostname(s)",
        "list": "Display current LFC remote URLs",
        "rm": "Remove an LFC remote from config",
    }


# Special parser for lfc-replace-dvc
class LFCReplaceDVCParser(LFCArgParser):
    # No attributes
    __slots__ = ()

    # Command name
    _name = "lfc-replace-dvc"

    # Viable options
    _optlist = (
        "help",
    )

    # Primary purpose of command
    _help_title = "Replace any DVC settings and file names"

    # Longer description
    _help_description = """
    \rAlthough LFC can work in an existing DVC repo, using ``lfc-add`` will
    \rbreak DVC's ability to function. It is usually preferable to make a
    \rrepo where you intend to use LFC use the ``.lfc`` file extension instead
    \rof ``.dvc``.  This command removes some DVC artifacts and rename others.

    \rThis will rename some files and folders:

        * ``.dvc/`` -> ``.lfc/``
        * ``*.dvc`` -> ``*.lfc``

    \rIt will also delete some JSON files used by DVC if present.

    \rThe function is safe to call multiple times if DVC has been
    \rpartially replaced. If there are no DVC artifacts, this function
    \rwill take no action.

    \rIt does **not** recompute hashes. If any existing MD-5 hashes are
    \rpresent, LFC will continue to use them, but updating the file
    \r(using ``lfc add``) will still use a SHA-256 hash.
    """


# Special parser for lfc-set-mode
class LFCSetModeParser(LFCArgParser):
    # No attributes
    __slots__ = ()

    # Command name
    _name = "lfc-set-mode"

    # Viable options
    _optlist = (
        "help",
        "mode",
        "1",
        "2",
    )

    # Positional parameters
    _arglist = (
        "file1",
        "file2",
    )

    # Required inputs
    _nargmin = 1

    # Primary purose of command
    _help_title = "Set the mode of one or more LFC files"

    # Longer description
    _help_description = """
    \rThis file can change the mode of one or more large files that have
    \ralready been added (and therefore a ``.lfc`` file exists). You can
    \rset the mode to either ``1`` or ``2``:

    \r* Mode-1 files are auto-pushed and -pulled with git pushes and pulls
    \r* Mode-2 files are explicitly on-demand
    """


# Custom parser for lfc-show
class LFCShowParser(LFCArgParser):
    # No attributes
    __slots__ = ()

    # Command name
    _name = "lfc-show"

    # Viable options
    _optlist = (
        "help",
        "ref",
    )

    # Positional parameters
    _arglist = (
        "fname",
    )

    # Required args
    _nargmin = 1
    _nargmax = 1

    # Purpose of command
    _help_title = "Print contents of a large file to STDOUT"

    # Longer description
    _help_description = """
    \rPrint contents of a large file to STDOUT, even in a bare repo. This
    \rfunction does not decode the bytes so that binary files can be piped
    \rfrom bare repos through STDOUT.
    """


# Front-desk for LFC, to decide which subcommand
class LFCFrontDesk(ArgReader):
    # No attributes
    __slots__ = ()

    # List of commands
    _cmdlist = (
        "add",
        "auto-pull",
        "auto-push",
        "checkout",
        "clone",
        "config",
        "init",
        "install-hooks",
        "ls-files",
        "pull",
        "push",
        "purge",
        "remote",
        "replace-dvc",
        "set-mode",
        "show",
    )

    # Command aliases
    _cmdmap = {
        "autopull": "auto-pull",
        "autopush": "auto-push",
        "list-files": "ls-files",
    }

    # Sub-parsers for each command
    _cmdparsers = {
        "add": LFCAddParser,
        "auto-pull": LFCAutoPullParser,
        "auto-push": LFCAutoPushParser,
        "checkout": LFCCheckoutParser,
        "clone": LFCCloneParser,
        "config": LFCConfigParser,
        "init": LFCInitParser,
        "install-hooks": LFCInstallHooksParser,
        "ls-files": LFCListFilesParser,
        "pull": LFCPullParser,
        "purge": LFCPurgeParer,
        "push": LFCPushParser,
        "remote": LFCRemoteFrontDesk,
        "replace-dvc": LFCReplaceDVCParser,
        "set-mode": LFCSetModeParser,
        "show": LFCShowParser,
        "_default_": LFCArgParser,
    }

    # Aliases
    _optmap = {
        "h": "help",
    }

    # Name of command
    _name = "lfc"

    # Overall description
    _help_title = "Large File Control"

    # Longer description
    _help_description = (
        "Track and share large and/or binary files in git repositories")

    # Options (universal)
    _help_optlist = (
        "help",
    )

    # Descriptions for options
    _help_opt = {
        "help": "Display this help message and exit",
    }

    # Description for each command
    _help_cmd = {
        "add": "Add or update a large file",
        "auto-pull": "Pull all mode-2 files in working repo",
        "auto-push": "Push all mode-2 files in working repo",
        "clone": "Clone git repo, install hooks, and autopull",
        "checkout": "Check out version of large file",
        "config": "View or set an LFC config variable",
        "init": "Initialize LFC for current git repo",
        "install-hooks": "Create git hooks for autopll and autopush",
        "ls-files": "List some or all ``.lfc`` files",
        "pull": "Pull one or more large files",
        "push": "Push one or more large files",
        "remote": "View or set an LFC remote cache",
        "replace-dvc": "Replace DVC with LFC for current repo",
        "set-mode": "Change mode of an LFC file",
        "show": "Show bytes of large file, even in bare repo",
    }


# Commands for ``lfc remote``
CMD_REMOTE_DICT = {
    "add": LFCRepo.set_lfc_remote,
    "add-host": LFCRepo.set_lfc_remote_hosts,
    "add-hosts": LFCRepo.set_lfc_remote_hosts,
    "list": LFCRepo._print_lfc_remotes,
    "ls": LFCRepo._print_lfc_remotes,
    "rm": LFCRepo.rm_lfc_remote,
    "set-hosts": LFCRepo.set_lfc_remote_hosts,
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


def _parse(
        parser: Optional[ArgReader] = None,
        argv: Optional[list] = None,
        cls: type = LFCArgParser) -> LFCArgParser:
    # Check for parser
    parser = parser if parser is not None else cls()
    # Set args if necessary
    if (len(parser.argv) == 0) or (argv is not None):
        # Parse CLI
        parser.parse(_get_argv(argv))
    # Output
    return parser


def lfc_add(parser=None, argv=None):
    r"""Calculate metadata for large file(s) and cache them

    :Call:
        >>> lfc_add(parser=None, argv=None)
    :Inputs:
        *parser*: {``None``} | :class:`LFCArgPraser`
            Parser instance with pre-parsed CLI args
        *argv*: {``None``} | :class:`list`\ [:class:`str`]
            Optional list of CLI args to use (or use ``sys.argv``)
    """
    # Get parser
    parser = _parse(parser, argv, LFCAddParser)
    # Check for help
    if _help(parser):
        return
    # Read the repo
    repo = LFCRepo()
    # Get args
    a, kw = parser.get_args()
    # Check for -2 -> mode=2
    _parse_mode(kw)
    # Add it
    repo.lfc_add(*a, **kw)


def lfc_autopull(parser=None, argv=None):
    r"""Pull most recent version of mode-2 (configurable) LFC files

    Normally this will pull all mode-2 files, but that can be configured
    to all files or no files by setting ``core.autopull`` in
    ``.lfc/config``. Users may also limit the pull to specific files,
    but that is not the primary use case.

    :Call:
        >>> lfc_autopull(parser=None, argv=None)
    :Inputs:
        *parser*: {``None``} | :class:`LFCArgPraser`
            Parser instance with pre-parsed CLI args
        *argv*: {``None``} | :class:`list`\ [:class:`str`]
            Optional list of CLI args to use (or use ``sys.argv``)
    """
    # Get parser
    parser = _parse(parser, argv, LFCAutoPullParser)
    # Check for help
    if _help(parser):
        return
    # Read the repo
    repo = LFCRepo()
    # Get args
    a, kw = parser.get_args()
    # Get mode
    mode = repo.get_lfc_autopull()
    # Settings
    kw.setdefault("quiet", True)
    kw["mode"] = mode
    # Push
    repo.lfc_pull(*a, **kw)


def lfc_autopush(parser=None, argv=None):
    r"""Push most recent version of mode-2 (configurable) LFC files

    Normally this will push all mode-2 files, but that can be configured
    to all files or no files by setting ``core.autopull`` in
    ``.lfc/config``. Users may also limit the push to specific files,
    but that is not the primary use case.

    :Call:
        >>> lfc_autopush(parser=None, argv=None)
    :Inputs:
        *parser*: {``None``} | :class:`LFCArgPraser`
            Parser instance with pre-parsed CLI args
        *argv*: {``None``} | :class:`list`\ [:class:`str`]
            Optional list of CLI args to use (or use ``sys.argv``)
    """
    # Get parser
    parser = _parse(parser, argv, LFCAutoPushParser)
    # Check for help
    if _help(parser):
        return
    # Read the repo
    repo = LFCRepo()
    # Get args
    a, kw = parser.get_args()
    # Get mode
    mode = repo.get_lfc_autopush()
    # Settings
    kw.setdefault("quiet", True)
    kw["mode"] = mode
    # Push
    repo.lfc_push(*a, **kw)


def lfc_checkout(parser=None, argv=None):
    r"""Check out one or more large files (from local cache)

    If no patterns are specified, the target will be all large files
    that are in the current folder or children thereof.

    :Call:
        >>> lfc_checkout(parser=None, argv=None)
    :Inputs:
        *parser*: {``None``} | :class:`LFCArgPraser`
            Parser instance with pre-parsed CLI args
        *argv*: {``None``} | :class:`list`\ [:class:`str`]
            Optional list of CLI args to use (or use ``sys.argv``)
    """
    # Get parser
    parser = _parse(parser, argv, LFCCheckoutParser)
    # Check for help
    if _help(parser):
        return
    # Read the repo
    repo = LFCRepo()
    # Get args
    a, kw = parser.get_args()
    # Checkout
    repo.lfc_checkout(*a, **kw)


def lfc_clone(parser=None, argv=None):
    r"""Clone a repo (using git) and pull all mode-2 LFC files

    :Call:
        >>> ierr = lfc_clone(parser=None, argv=None)
    :Inputs:
        *parser*: {``None``} | :class:`LFCArgPraser`
            Parser instance with pre-parsed CLI args
        *argv*: {``None``} | :class:`list`\ [:class:`str`]
            Optional list of CLI args to use (or use ``sys.argv``)
    :Outputs:
        *ierr*: :class:`int`
            Return code
    """
    # Get parser
    parser = _parse(parser, argv, LFCCloneParser)
    # Check for help
    if _help(parser):
        return IERR_OK
    # Get args
    a, kw = parser.get_args()
    # Create nominal command
    cmd = ["git", "clone", *a]
    # Check for --bare option
    if kw.pop("bare", False):
        cmd.append("--bare")
    # Clone the repo using git
    ierr = shellutils.call(cmd, **kw)
    # Check for errors
    if ierr:
        raise LFCCloneError(f"git-clone failed with status {ierr}")
    # Get name of repo
    repo_name = posixpath.basename(os.path.basename(a[-1]))
    # Check if we should remove .git: ``git clone repo.git`` -> repo
    if repo_name.endswith(".git") and len(a) == 1:
        # Cloned bare repo -> working repo
        repo_name = repo_name[:-4]
    # Enter the repo
    fpwd = os.getcwd()
    os.chdir(repo_name)
    # Instantiate
    repo = LFCRepo()
    # Exit if bare
    if repo.bare:
        os.chdir(fpwd)
        return 0
    # Install hooks
    repo.lfc_install_hooks()
    # Pull all mode-2 files
    repo.lfc_pull(mode=2)
    # Return to original location
    os.chdir(fpwd)
    # Return code
    return 0


def lfc_config(parser=None, argv=None):
    r"""Print or set an LFC configuration variable

    :Call:
        >>> lfc_config(parser=None, argv=None)
    :Inputs:
        *parser*: {``None``} | :class:`LFCArgPraser`
            Parser instance with pre-parsed CLI args
        *argv*: {``None``} | :class:`list`\ [:class:`str`]
            Optional list of CLI args to use (or use ``sys.argv``)
    """
    # Get parser
    parser = _parse(parser, argv, LFCListFilesParser)
    # Check for help
    if _help(parser):
        return
    # Read the repo
    repo = LFCRepo()
    # Get args
    a, kw = parser.get_args()
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


def lfc_init(parser=None, argv=None) -> int:
    r"""Initialize a repo as an LFC repo

    This will create (if necessary) the following folders:

    *   ``.lfc/``
    *   ``.lfc/cache/``

    and the following files:

    *   ``.lfc/config``
    *   ``.lfc/.gitignore``

    :Call:
        >>> lfc_init(parser=None, argv=None)
    :Inputs:
        *parser*: {``None``} | :class:`LFCArgPraser`
            Parser instance with pre-parsed CLI args
        *argv*: {``None``} | :class:`list`\ [:class:`str`]
            Optional list of CLI args to use (or use ``sys.argv``)
    """
    # Get parser
    parser = _parse(parser, argv, LFCInitParser)
    # Check for help
    if _help(parser):
        return
    # Read the repo
    repo = LFCRepo()
    # Get args
    a, kw = parser.get_args()
    # Push it
    repo.lfc_init(*a, **kw)


def lfc_install_hooks(parser=None, argv=None):
    r"""Install git-hooks in current LFC repo

    This creates the following files relative to the top-level folder
    of the working repository:

    *   ``.git/hooks/post-merge``
    *   ``.git/hooks/pre-push``

    If the files exist, this will not overwrite them. After writing the
    file, it also makes the executable.

    :Call:
        >>> lfc_install_hooks(parser=None, argv=None)
    :Inputs:
        *parser*: {``None``} | :class:`LFCArgPraser`
            Parser instance with pre-parsed CLI args
        *argv*: {``None``} | :class:`list`\ [:class:`str`]
            Optional list of CLI args to use (or use ``sys.argv``)
    """
    # Get parser
    parser = _parse(parser, argv, LFCInstallHooksParser)
    # Check for help
    if _help(parser):
        return
    # Read the repo
    repo = LFCRepo()
    # Get args
    a, kw = parser.get_args()
    # Install hooks
    repo.lfc_install_hooks(*a, **kw)


def lfc_ls_files(parser=None, argv=None):
    r"""List files tracked by LFC

    If called from a working repository, only files in the current
    folder or a subfolder thereof are listed.

    :Call:
        >>> lfc_ls_files(parser=None, argv=None)
    :Inputs:
        *parser*: {``None``} | :class:`LFCArgPraser`
            Parser instance with pre-parsed CLI args
        *argv*: {``None``} | :class:`list`\ [:class:`str`]
            Optional list of CLI args to use (or use ``sys.argv``)
    :STDOUT:
        Each matching ``*.lfc`` file is printed to a line in STDOUT
    """
    # Get parser
    parser = _parse(parser, argv, LFCListFilesParser)
    # Check for help
    if _help(parser):
        return
    # Read the repo
    repo = LFCRepo()
    # Get args
    a, kw = parser.get_args()
    # Check for -2 -> mode=2
    _parse_mode(kw)
    # List files
    filelist = repo.find_lfc_files(*a, **kw)
    # Print them
    print("\n".join(filelist))


def lfc_pull(parser=None, argv=None):
    r"""Pull (fetch and checkout) one or more large files

    If no patterns are specified, the target will be all large files
    that are in the current folder or children thereof.

    :Call:
        >>> lfc_pull(parser=None, argv=None)
    :Inputs:
        *parser*: {``None``} | :class:`LFCArgPraser`
            Parser instance with pre-parsed CLI args
        *argv*: {``None``} | :class:`list`\ [:class:`str`]
            Optional list of CLI args to use (or use ``sys.argv``)
    """
    # Get parser
    parser = _parse(parser, argv, LFCPullParser)
    # Check for help
    if _help(parser):
        return
    # Read the repo
    repo = LFCRepo()
    # Get args
    a, kw = parser.get_args()
    # Check for -2 -> mode=2
    _parse_mode(kw)
    # Push it
    repo.lfc_pull(*a, **kw)


def lfc_purge(parser=None, argv=None):
    r"""Purge large files from cache and working files

    If no patterns are specified, the target will be all large files
    that are in the current folder or children thereof.

    :Call:
        >>> lfc_purge(parser=None, argv=None)
    :Inputs:
        *parser*: {``None``} | :class:`LFCArgPraser`
            Parser instance with pre-parsed CLI args
        *argv*: {``None``} | :class:`list`\ [:class:`str`]
            Optional list of CLI args to use (or use ``sys.argv``)
    """
    # Get parser
    parser = _parse(parser, argv, LFCPurgeParer)
    # Check for help
    if _help(parser):
        return
    # Read the repo
    repo = LFCRepo()
    # Get args
    a, kw = parser.get_args()
    # Check for -2 -> mode=2
    _parse_mode(kw)
    # Push it
    repo.lfc_purge(*a, **kw)


def lfc_push(parser=None, argv=None):
    r"""Push one or more large files

    If no patterns are specified, the target will be all large files
    that are in the current folder or children thereof.

    :Call:
        >>> lfc_push(parser=None, argv=None)
    :Inputs:
        *parser*: {``None``} | :class:`LFCArgPraser`
            Parser instance with pre-parsed CLI args
        *argv*: {``None``} | :class:`list`\ [:class:`str`]
            Optional list of CLI args to use (or use ``sys.argv``)
    """
    # Get parser
    parser = _parse(parser, argv, LFCListFilesParser)
    # Check for help
    if _help(parser):
        return
    # Read the repo
    repo = LFCRepo()
    # Get args
    a, kw = parser.get_args()
    # Check for -2 -> mode=2
    _parse_mode(kw)
    # Push it
    repo.lfc_push(*a, **kw)


def lfc_remote(parser=None, argv=None):
    r"""Show or set URL to an LFC remote cache

    :Call:
        >>> lfc_remote(parser=None, argv=None)
    :Inputs:
        *parser*: {``None``} | :class:`LFCArgPraser`
            Parser instance with pre-parsed CLI args
        *argv*: {``None``} | :class:`list`\ [:class:`str`]
            Optional list of CLI args to use (or use ``sys.argv``)
    """
    # Reconstruct a parer
    parser = _parse(parser, argv, LFCRemoteFrontDesk)
    # Re-parse
    cmdname, subparser = parser.fullparse()
    # Check for no commands/bad command
    ierr = _help_frontdesk(cmdname, LFCRemoteFrontDesk)
    if ierr:
        return ierr & IERR_CMD
    # Check for sub-command help
    if _help(subparser):
        return
    # Read repo
    repo = LFCRepo()
    # Get function
    func = CMD_REMOTE_DICT.get(cmdname)
    # Get args
    a = subparser.argvals
    kw = subparser.get_kwargs()
    # Run function
    func(repo, *a, **kw)


def lfc_replace_dvc(parser=None, argv=None):
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
        >>> lfc_replace_dvc(parser=None, argv=None)
    :Inputs:
        *parser*: {``None``} | :class:`LFCArgPraser`
            Parser instance with pre-parsed CLI args
        *argv*: {``None``} | :class:`list`\ [:class:`str`]
            Optional list of CLI args to use (or use ``sys.argv``)
    """
    # Get parser
    parser = _parse(parser, argv, LFCReplaceDVCParser)
    # Check for help
    if _help(parser):
        return
    # Read the repo
    repo = LFCRepo()
    # Replace
    repo.lfc_replace_dvc()


def lfc_set_mode(parser=None, argv=None):
    r"""Set the mode of one or more LFC files

    :Call:
        >>> lfc_set_mode(parser=None, argv=None)
    :Inputs:
        *parser*: {``None``} | :class:`LFCArgPraser`
            Parser instance with pre-parsed CLI args
        *argv*: {``None``} | :class:`list`\ [:class:`str`]
            Optional list of CLI args to use (or use ``sys.argv``)
    """
    # Get parser
    parser = _parse(parser, argv, LFCSetModeParser)
    # Check for help
    if _help(parser):
        return
    # Read the repo
    repo = LFCRepo()
    # Get args
    a, kw = parser.get_args()
    # Check for -2 -> mode=2
    _parse_mode(kw)
    # Set mode
    repo.lfc_set_mode(*a, **kw)


def lfc_show(parser=None, argv=None):
    r"""Print contents of a large file to STDOUT, even in bare repo

    This function does not decode the bytes so that binary files can be
    piped from bare repos through STDOUT.

    :Call:
        >>> lfc_show(parser=None, argv=None)
    :Inputs:
        *parser*: {``None``} | :class:`LFCArgPraser`
            Parser instance with pre-parsed CLI args
        *argv*: {``None``} | :class:`list`\ [:class:`str`]
            Optional list of CLI args to use (or use ``sys.argv``)
    """
    # Get parser
    parser = _parse(parser, argv, LFCShowParser)
    # Check for help
    if _help(parser):
        return
    # Read the repo
    repo = LFCRepo()
    # Get args
    a, kw = parser.get_args()
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
    "purge": lfc_purge,
    "remote": lfc_remote,
    "replace-dvc": lfc_replace_dvc,
    "set-mode": lfc_set_mode,
    "show": lfc_show,
}


# Main function
def main(argv: Optional[list] = None) -> int:
    r"""Main command-line interface to ``lfc``

    The function works by reading the second word of ``sys.argv`` and
    dispatching a dedicated function for that purpose.

    :Call:
        >>> ierr = main(argv=None)
    :Inputs:
        *argv*: {``None``} | :class:`list`\ [:class:`str`]
            Optional list of CLI args to use (or use ``sys.argv``)
    :Outputs:
        *ierr*: :class:`int`
            Return code
    """
    # Create parser
    parser = LFCFrontDesk()
    # Apply fixes to raw command-line args if necessary
    argv = _get_argv(argv)
    # Identify subcommand
    cmdname, subparser = parser.fullparse(argv)
    # Check for top-level help message
    ierr = _help_frontdesk(cmdname, LFCFrontDesk)
    if ierr:
        return ierr & IERR_CMD
    # Get function
    func = CMD_DICT[cmdname]
    # Run function
    try:
        ierr = func(subparser)
    except GitutilsError as err:
        print(f"{err.__class__.__name__}:")
        print(f"  {err}")
        return 1
    # Convert None -> 0
    ierr = IERR_OK if ierr is None else ierr
    # Normal exit
    return ierr


# Print help message
def _help(parser: LFCArgParser) -> bool:
    # Check for help message
    if parser.get("help", False) and parser._cmdlist is None:
        # Print help message
        print(compile_rst(parser.genr8_help()))
        return True
    else:
        # No help
        return False


# Print help message for front-desk
def _help_frontdesk(cmdname: Optional[str], cls: type) -> int:
    # Check for null commands
    if cmdname is None:
        print(compile_rst(cls().genr8_help()))
        return 1
    # Check if command was recognized
    if cmdname not in cls._cmdlist:
        # Get closest matches
        close = difflib.get_close_matches(
            cmdname, cls._cmdlist, n=4, cutoff=0.3)
        # Use all if no matches
        close = close if close else cls._cmdlist
        # Generate list as text
        matches = " | ".join(close)
        # Display them
        print(f"Unexpected '{cls._name}' command '{cmdname}'")
        print(f"Closest matches: {matches}")
        return IERR_CMD
    # No problems
    return 0


# Get command-line args, filtering out weird ``winpty`` fixes
def _get_argv(sysargv: Optional[list] = None) -> list:
    r"""Get CLI args, but undo any ``winpty`` "fixes"

    This will replace

    ``pfe;C:\Users\...\nobackup\``

    with

    ``pfe:/nobackup/``

    :Call:
        >>> argv = _get_argv(sysargv=None)
    :Inputs:
        *sysargv*: {``None``} | :class:`list`\ [:class:`str`]
            Optional list of CLI args to use
    :Outputs:
        *argv*: :class:`list`\ [:class:`str`]
            List of filtered command-line arguments
    """
    # Initialize output
    argv = []
    # Get CLI args if none given
    sysargv = sys.argv if sysargv is None else sysargv
    # Loop through command-line args
    for argi in sysargv:
        # Check for unusual remote path start
        if REGEX_WINREMOTE.match(argi):  # pragma: no cover
            # Split full path by semicolon
            host, path = argi.split(';', 1)
            # Check for weird prefix of git-bash path
            if path.startswith(WPTY_ROOT):
                # Strip root
                path = path[len(WPTY_ROOT):]
            # Replace \ with / if necessary
            path = path.replace(os.sep, '/')
            # Rejoin full path
            argj = f"{host}:{path}"
        else:
            # Use arg as is
            argj = argi
        # Append
        argv.append(argj)
    # Output
    return argv
