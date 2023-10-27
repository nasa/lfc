
# Standard library
import os
import shutil
from subprocess import call

# Third-party
import pytest
import testutils

# Local imports
from lfc.cli import (
    lfc_add,
    lfc_checkout,
    lfc_init,
    lfc_pull,
    lfc_push,
    lfc_remote,
    lfc_replace_dvc,
    lfc_show
)
from lfc.lfcrepo import (
    GitutilsFileNotFoundError,
    LFCCheckoutError,
    LFCRepo
)


# List of files to copy
REPO_NAME = "repo"
COPY_FILES = [
    "sample.rst",
    "rando.dat",
]
OTHER_FILES = [
    "rando2.dat",
    "rando3.dat"
]


# Initialize a repo; test lfc_init, lfc_add, lfc_push
@testutils.run_sandbox(__file__, copydirs=REPO_NAME)
def test_repo01():
    # Paths to working and bare repo
    sandbox = os.getcwd()
    workrepo = os.path.join(sandbox, REPO_NAME)
    barerepo = os.path.join(sandbox, f"{REPO_NAME}.git")
    localcache = os.path.join(workrepo, ".lfc", "cache")
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
    fname02 = OTHER_FILES[0]
    fname03 = OTHER_FILES[1]
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
    repo.commit("Initialize LFC", a=True)
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
    # Create and add third binary file
    with open(fname03, 'wb') as fp:
        fp.write(os.urandom(128))
    lfc_add(fname03)
    assert os.path.isfile(f"{fname03}.lfc")
    repo.commit("Add third LFC file")
    # Manually remove it from the local cache for testing
    hash3 = repo.get_lfc_hash(fname03)
    fhash03 = os.path.join(localcache, hash3[:2], hash3[2:])
    assert os.path.isfile(fhash03)
    os.remove(fhash03)
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


# Clone a repo; test lfc-pull
@testutils.run_sandbox(__file__, fresh=False)
def test_repo02():
    # Name of cloned working repo
    fdir01 = "copy"
    # File names
    fname01 = COPY_FILES[1]
    fname02 = OTHER_FILES[0]
    # Paths to working and bare repo
    sandbox = os.getcwd()
    copyrepo = os.path.join(sandbox, fdir01)
    barerepo = os.path.join(sandbox, f"{REPO_NAME}.git")
    # Clone a second working repo
    ierr = call(["git", "clone", barerepo, fdir01])
    assert ierr == 0
    # Enter the copy repo
    os.chdir(copyrepo)
    # Make sure large file is *NOT* present
    assert not os.path.isfile(fname01)
    assert not os.path.isfile(fname02)
    # Pull the LFC stub
    lfc_pull(fname01)
    # Now the file should be there
    assert os.path.isfile(fname01)
    # Generic pull
    lfc_pull()
    # Noew both files should be present
    assert os.path.isfile(fname02)


# Test lfc-show
@testutils.run_sandbox(__file__, fresh=False)
def test_repo03():
    # Paths to working and bare repo
    sandbox = os.getcwd()
    workrepo = os.path.join(sandbox, REPO_NAME)
    barerepo = os.path.join(sandbox, f"{REPO_NAME}.git")
    # Enter the bare repo
    os.chdir(barerepo)
    # Some file names
    fname01 = COPY_FILES[0]
    fname02 = COPY_FILES[1]
    fname03 = OTHER_FILES[1]
    fname04 = "not_really.dat"
    # Read original file
    f1 = os.path.join(workrepo, fname01)
    f2 = os.path.join(workrepo, fname02)
    b1 = open(f1, 'rb').read()
    b2 = open(f2, 'rb').read()
    # Run lfc-show on other file
    ierr = lfc_show(f"{fname04}.lfc")
    assert ierr != 0
    # Instantiate repo
    repo = LFCRepo()
    # Run lfc-show on git-tracked file
    show1 = repo.lfc_show(fname01)
    assert b1 == show1
    # Run lfc-show on lfc-tracked file
    show2 = repo.lfc_show(fname02)
    assert b2 == show2
    # Run lfc-show on file missing from cache
    show3 = repo.lfc_show(fname03)
    assert show3 is None


# Test lfc-replace-dvc
@testutils.run_sandbox(__file__, fresh=False)
def test_repo04():
    # Go to the "copy" repo
    os.chdir("copy")
    # Instantiate repo
    repo = LFCRepo()
    # Move files to make it look like a DVC repo
    repo.mv(".lfc", ".dvc")
    assert os.path.isdir(".dvc")
    # Create a .dvcignore file
    with open(".dvcignore", 'w') as fp:
        fp.write("*.xlsx\n")
    # Create a .dvc/plots dir
    os.mkdir(os.path.join(".dvc", "plots"))
    # Put a file in it to add (DVC really has this file)
    fjson = os.path.join(".dvc", "plots", "confusion.json")
    with open(fjson, 'w') as fp:
        fp.write("{}\n")
    # Add those files
    repo.add(fjson)
    repo.add(".dvcignore")
    # Move a .lfc stub to a .dvc file
    flfc = repo.find_lfc_files(ext=".lfc")[0]
    fdvc = flfc[:-3] + "dvc"
    repo.mv(flfc, fdvc)
    # Commit these changes
    repo.commit("Pretend to be DVC")
    # Run the replace-dvc command
    lfc_replace_dvc()
    # Commit the results
    repo.commit("Replace dvc -> lfc")
    # Make sure the /.lfc folder is present
    assert os.path.isdir(".lfc")
    assert os.path.isfile(flfc)
    assert not os.path.isdir(".dvc")
    assert not os.path.isfile(fdvc)
    # Get the hash for an LFC file to test merging overlapping caches
    hash1 = repo.get_lfc_hash(flfc)
    p1 = hash1[:2]
    p2 = hash1[2:]
    # Recreate a ".dvc" folder to test merger of caches
    dvccache = os.path.join(".dvc", "cache")
    newp1 = os.path.join(dvccache, "p1")
    newp2 = os.path.join(newp1, "p2")
    os.mkdir(".dvc")
    os.mkdir(dvccache)
    os.mkdir(newp1)
    # And a file that's directly placed in .dvc/cache
    newf4 = os.path.join(dvccache, "afile")
    # Create a folder that overlaps with .lfc/cache
    oldp1 = os.path.join(dvccache, p1)
    oldp2 = os.path.join(oldp1, p2)
    mixp2 = os.path.join(oldp1, "p3")
    os.mkdir(oldp1)
    for fname in (mixp2, newf4, newp2, oldp2):
        with open(fname, 'wb') as fp:
            fp.write(os.urandom(16))
    # Rerun the command
    lfc_replace_dvc()
    # Get file names for final tests
    lfccache = os.path.join(".lfc", "cache")
    newf1 = os.path.join(lfccache, "p1", "p2")
    newf3 = os.path.join(lfccache, p1, "p3")
    # Test if the files were moved from .dvc/
    assert os.path.isfile(newf1)
    assert os.path.isfile(newf3)
    # One more time to create .lfc/cache if needed
    os.rename(lfccache, ".lfccache")
    os.mkdir(".dvc")
    os.mkdir(dvccache)
    lfc_replace_dvc()
    # Tests
    assert os.path.isdir(lfccache)
    os.rmdir(lfccache)
    os.rename(".lfccache", lfccache)


# Tests of basic operations
@testutils.run_sandbox(__file__, fresh=False)
def test_repo05():
    # Go into working folder
    os.chdir(REPO_NAME)
    # Instantiate repo
    repo = LFCRepo()
    # Try to hash a file that doesn't exist
    with pytest.raises(GitutilsFileNotFoundError):
        repo.genr8_hash(os.path.join("no_such_file.dat"))


# Test lfc-checkout
@testutils.run_sandbox(__file__, fresh=False)
def test_repo06():
    # Go into working folder
    os.chdir(REPO_NAME)
    # Instantiate repo
    repo = LFCRepo()
    # File names
    fname01 = COPY_FILES[1]
    fname02 = OTHER_FILES[1]
    # Checkout all files
    lfc_checkout(fname01)
    # Pull the second file
    repo.lfc_pull(fname02)
    # Get hash
    hash2 = repo.get_lfc_hash(fname02)
    # File to cache of *fname02*
    fhash2 = os.path.join(".lfc", "cache", hash2[:2], hash2[2:])
    # Delete it!
    if os.path.isfile(fhash2):
        os.remove(fhash2)
    # Now try to checkout *fname02*
    with pytest.raises(LFCCheckoutError):
        repo._lfc_checkout(fname02)
    # Now we're going to create a new version of *fname01*
    with open(fname01, 'wb') as fp:
        fp.write(os.urandom(127))
    # Try to checkout *fname01*; should fail b/c current uncached ver
    try:
        repo._lfc_checkout(fname01)
    except LFCCheckoutError as err:
        assert "uncached" in err.args[0]
    else:
        raise ValueError(f"lfc-checkout overwrote uncached '{fname01}'")
    # Now add the new file to the cache
    hash1 = repo.genr8_hash(fname01)
    fdir1 = os.path.join(".lfc", "cache", hash1[:2])
    fhash1 = os.path.join(fdir1, hash1[2:])
    if not os.path.isdir(fdir1):
        os.mkdir(fdir1)
    shutil.copy(fname01, fhash1)
    # Rerun the checkout command
    repo._lfc_checkout(fname01)
    # Should have a different hash now (the original one)
    assert repo.genr8_hash(fname01) != hash1
