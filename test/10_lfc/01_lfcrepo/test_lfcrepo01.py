
# Standard library
import os
import shutil
from subprocess import call

# Third-party
import testutils

# Local imports
from lfc.cli import (
    lfc_add,
    lfc_init,
    lfc_push,
    lfc_remote
)
from lfc.lfcrepo import (
    LFCRepo
)


# List of files to copy
REPO_NAME = "repo"
COPY_FILES = [
    "sample.rst",
    "rando.dat",
]


# Initialize a repo
@testutils.run_sandbox(__file__, copydirs=REPO_NAME)
def test_repo01():
    # Paths to working and bare repo
    sandbox = os.getcwd()
    workrepo = os.path.join(sandbox, REPO_NAME)
    barerepo = os.path.join(sandbox, f"{REPO_NAME}.git")
    remotecache = os.path.join(barerepo, "cache")
    # Enter the "repo" dir
    os.chdir(REPO_NAME)
    # Initialize repo
    ierr = call(["git", "init"])
    assert ierr == 0
    # Check for .git/ folder
    assert os.path.isdir(".git")
    # Initialize repo
    repo = LFCRepo()
    # Key file names
    fname00 = COPY_FILES[0]
    fname01 = COPY_FILES[1]
    fname02 = "rando2.dat"
    # Add a file
    repo.add(fname00)
    # Issue a commit
    repo.commit("Initial commit", a=True)
    # Initialize LFC
    lfc_init()
    # Should be a .lfc/ folder
    assert os.path.isdir(".lfc")
    # Add a remote
    lfc_remote("add", "hub", remotecache, d=True)
    # Commit it
    repo.commit("Initialize LFC")
    # Add a file with LFC
    lfc_add(fname01)
    # Commit first file
    repo.commit("Add LFC file")
    # Make sure cache is present
    os.path.isdir(os.path.join(".lfc", "cache"))
    # Add it again to make sure it handles that situation correctly
    lfc_add(fname01)
    # Copy the file
    shutil.copy(fname01, fname02)
    # Add the second file to make sure the file doesn't get added twice
    lfc_add(fname02)
    repo.commit("Add same LFC file with new name")
    # Make sure second stub is present
    assert os.path.isfile(fname02 + ".lfc")
    # Go back to sandbox parent
    os.chdir(sandbox)
    # Clone the repo
    ierr = call(["git", "clone", REPO_NAME, f"{REPO_NAME}.git", "--bare"])
    assert ierr == 0
    # Enter the working repo
    os.chdir(workrepo)
    # Push the file
    lfc_push()
    # Get the hash
    hash = repo.get_lfc_hash(fname01)
    # Path to hash
    fhash = os.path.join(hash[:2], hash[2:])
    fhash_local = os.path.join(repo.get_cachedir(), fhash)
    fhash_remote = os.path.join(remotecache, fhash)
    # Make sure the file was pushed
    assert os.path.isfile(fhash_local)
    assert os.path.isfile(fhash_remote)
    # Use check_cache() interface
    assert repo.check_cache(fname01)
    assert repo.check_cache(fname02)
