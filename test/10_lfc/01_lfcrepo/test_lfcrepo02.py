
# Standard library
import os

# Third-party
import testutils

from lfc.lfcclone import (
    LFCCloneError,
    lfc_clone,
)
from lfc.lfcrepo import LFCRepo


# List of files to copy
REPO_NAME = "repo"
COPY_FILES = [
    "sample.rst",
    "rando.dat",
]
OTHER_FILES = [
    "rando2.dat",
    "rando3.dat",
    "rando4.dat",
    "rando5.dat",
]


# Test minor incarnations of lfc-clone
@testutils.run_sandbox(__file__, fresh=False)
def test_repo11():
    # Repo names
    repodir1 = REPO_NAME
    repodir2 = f"{REPO_NAME}3.git"
    repodir3 = f"{REPO_NAME}3"
    # Clone a bare repo
    lfc_clone(repodir1, repodir2, bare=True)
    # Check it
    repo2 = LFCRepo(repodir2)
    assert repo2.bare
    # Fail a clone
    try:
        lfc_clone("nonsense", repodir3)
    except LFCCloneError:
        # Expected failure
        pass
    else:
        raise SystemError(f"Expected 'lfc clone nonsense {repodir3}' to fail")
    # Clone from bare repo
    lfc_clone(repodir2)
    # Now "repo3" should exist
    assert os.path.isdir(repodir3)
