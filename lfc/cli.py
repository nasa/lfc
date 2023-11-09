
# Standard library
import os
import sys

# Local imports
from .lfcclone import lfc_clone
from .lfcerror import GitutilsError
from .lfcrepo import LFCRepo
from ._vendor.argread import ArgReader


# Help message
HELP_LFC = r"""GitUtils and Large File Control control (lfc)

:Usage:

    .. code-block:: console

        $ lfc CMD [OPTIONS]
"""


# Customized CLI parser
class LFCArgParser(ArgReader):
    # No attributes
    __slots__ = ()

    # Aliases
    _optmap = {
        "d": "default",
        "q": "quiet",
    }

    # Options that never take a value
    _optlist_noval = (
        "default",
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
    # Read the repo
    repo = LFCRepo()
    # Check for -2 -> mode=2
    _parse_mode(kw)
    # Add it
    repo.lfc_add(*a, **kw)


def lfc_autopull(*a, **kw):
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
    # Read the repo
    repo = LFCRepo()
    # Get mode
    mode = repo.get_lfc_autopush()
    # Settings
    kw.setdefault("quiet", True)
    kw["mode"] = mode
    # Push
    repo.lfc_push(*a, **kw)


def lfc_config(*a, **kw):
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
    # Read the repo
    repo = LFCRepo()
    # Push it
    repo.lfc_init(*a, **kw)


def lfc_install_hooks(*a, **kw):
    # Read the repo
    repo = LFCRepo()
    # Install hooks
    repo.lfc_install_hooks(*a, **kw)


def lfc_ls_files(*a, **kw):
    # Read the repo
    repo = LFCRepo()
    # Check for -2 -> mode=2
    _parse_mode(kw)
    # List files
    filelist = repo.find_lfc_files(*a, **kw)
    # Print them
    print("\n".join(filelist))


def lfc_pull(*a, **kw):
    # Read the repo
    repo = LFCRepo()
    # Check for -2 -> mode=2
    _parse_mode(kw)
    # Push it
    repo.lfc_pull(*a, **kw)


def lfc_checkout(*a, **kw):
    # Read the repo
    repo = LFCRepo()
    # Checkout
    repo.lfc_checkout(*a, **kw)


def lfc_push(*a, **kw):
    # Read the repo
    repo = LFCRepo()
    # Check for -2 -> mode=2
    _parse_mode(kw)
    # Push it
    repo.lfc_push(*a, **kw)


def lfc_remote(*a, **kw):
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
    # Read the repo
    repo = LFCRepo()
    # Replace
    repo.lfc_replace_dvc(*a, **kw)


def lfc_set_mode(*a, **kw):
    # Read the repo
    repo = LFCRepo()
    # Check for -2 -> mode=2
    _parse_mode(kw)
    # Set mode
    repo.lfc_set_mode(*a, **kw)


def lfc_show(*a, **kw):
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
def main():
    # Create parser
    parser = LFCArgParser()
    # Parse args
    a, kw = parser.parse()
    kw.pop("__replaced__", None)
    # Check for no commands
    if len(a) == 0:
        print(HELP_LFC)
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
