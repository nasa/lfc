
# Standard library
import os
import sys

# Local imports
from .lfcerror import GitutilsError
from .lfcrepo import LFCRepo
from ._vendor import argread


# Help message
HELP_LFC = r"""GitUtils and Large File Control control (lfc)

:Usage:

    .. code-block:: console

        $ lfc CMD [OPTIONS]
"""


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
    # Add it
    repo.lfc_add(*a, **kw)


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


def lfc_ls_files(*a, **kw):
    # Read the repo
    repo = LFCRepo()
    # List files
    filelist = repo.find_lfc_files(*a, **kw)
    # Print them
    print("\n".join(filelist))


def lfc_pull(*a, **kw):
    # Read the repo
    repo = LFCRepo()
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


# Command dictionary
CMD_DICT = {
    "add": lfc_add,
    "checkout": lfc_checkout,
    "config": lfc_config,
    "init": lfc_init,
    "ls-files": lfc_ls_files,
    "pull": lfc_pull,
    "push": lfc_push,
    "remote": lfc_remote,
    "replace-dvc": lfc_replace_dvc,
    "show": lfc_show,
}


# Main function
def main():
    # Parse args
    a, kw = argread.readkeys(sys.argv)
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
