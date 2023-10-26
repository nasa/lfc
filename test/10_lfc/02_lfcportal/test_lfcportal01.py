
# Standard library
import os
import posixpath
from subprocess import call

# Third-party
import testutils

# Local imports
from lfc.lfcrepo import (
    LFCRepo
)


# Generate some random sequences
B1 = os.urandom(128)
B2 = os.urandom(128)
B3 = os.urandom(128)
B4 = os.urandom(128)


# Name of remote to use
LOCAL = "local"
REMOTE = "mirror"
# Get current repo
REPO = LFCRepo()
# Get "mirror" remote
MIRROR_URL = REPO.get_remotes()[REMOTE]
# Create a cache for testing
TEST_CACHE = posixpath.join(MIRROR_URL, "testcache")
# Get host and path to remote cache
CACHEHOST, CACHEDIR = TEST_CACHE.split(':', 1)
# Reformat URL
TEST_CACHE = TEST_CACHE.replace(":", "")
TEST_CACHE = f"ssh://{TEST_CACHE}"

# List of files to copy
REPO_NAME = "repo"
FORK_NAME = "fork"
COPY_FILES = [
    "sample.rst",
]


# Initialize a repo; test lfc_init, lfc_add, lfc_push
@testutils.run_sandbox(__file__, copydirs=REPO_NAME)
def test_repo01():
    # Delete the remote cache if appropriate
    ierr = call(["ssh", CACHEHOST, "rm", "-rf", CACHEDIR])
    # Paths to working and bare repo
    sandbox = os.getcwd()
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
    # Add a file
    repo.add(fname00)
    repo.commit("Initial commit")
    # Initialize LFC
    repo.lfc_init()
    repo.set_lfc_remote(REMOTE, TEST_CACHE, default=True)
    repo.set_lfc_remote(LOCAL, remotecache)
    # Commit it
    repo.commit("Initialize LFC", a=True)
    # File names
    fname01 = "rand01.dat"
    fname02 = "rand02.dat"
    # Write some binary files
    with open(fname01, 'wb') as fp:
        fp.write(B1)
    with open(fname02, 'wb') as fp:
        fp.write(B2)
    # Add some files
    repo.lfc_add(fname01, fname02)
    # Get hashes
    hash1 = repo.get_lfc_hash(fname01)
    hash2 = repo.get_lfc_hash(fname02)
    # File names thereof
    fhash1 = posixpath.join(hash1[:2], hash1[2:])
    fhash2 = posixpath.join(hash2[:2], hash2[2:])
    # Connect a local portal (should do nothing)
    breakpoint()
    portal = repo.make_lfc_portal(LOCAL)
    assert portal is None
    # Get portal
    portal = repo.make_lfc_portal(REMOTE)
    # Push to remote
    repo.lfc_push(fname01, fname02)
    # Ensure the files were pushed
    assert portal.ssh.isfile(fhash1)
    assert portal.ssh.isfile(fhash2)
    # Close the portal
    repo.close_lfc_portal(REMOTE)
    # Make sure it was closed
    assert REMOTE not in repo.lfc_portals


if __name__ == "__main__":
    test_repo01()
