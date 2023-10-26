
# Standard library
import os
from subprocess import call

# Third-party
import testutils

# Local imports
from lfc._vendor.gitutils.gitrepo import (
    GitRepo,
    GitutilsSystemError,
    get_gitdir
)


# List of files to copy
REPO_NAME = "repo"
GIT_FILES = (
    "sample.rst",
    "patch.rst"
)


# Run a test
@testutils.run_sandbox(__file__, copydirs=REPO_NAME)
def test_repo01():
    # Enter working folder
    os.chdir(REPO_NAME)
    # File name
    fname00 = GIT_FILES[0]
    # Initialize repo
    call(["git", "init"])
    call(["git", "add", fname00])
    call(["git", "commit", "-a", "-m", "Initial commit"])
    # Name of bare repo
    barerepo = f"{REPO_NAME}.git"
    # Clone it as a bare repo
    os.chdir("..")
    ierr = call(["git", "clone", "--bare", REPO_NAME])
    assert ierr == 0
    # Test for bare repo
    assert os.path.isdir(barerepo)
    # Enter bare repo
    os.chdir(barerepo)
    # Initialize repo
    repo = GitRepo()
    # Test location of config directory
    assert repo.get_configdir() == repo.gitdir
    # Get remotes
    remotes = repo.get_remotes()
    # Should be just one; "origin"
    assert "origin" in remotes
    assert os.path.isdir(remotes["origin"])
    # Test failure of assert_working() if working
    try:
        repo.assert_working(cmd=["git", "commit"])
    except GitutilsSystemError as err:
        assert "git commit" in err.args[0]
    else:
        assert False


# Test "patching" capabilities
@testutils.run_sandbox(__file__, fresh=False)
def test_patch01():
    # Enter the bare repo
    os.chdir(f"{REPO_NAME}.git")
    # Name of file tp patch
    fname00 = GIT_FILES[0]
    fname01 = GIT_FILES[1]
    fname02 = "newfile.rst"
    # Instantiate repo
    repo = GitRepo()
    # Create a file by patching it localy
    repo.patch_file(fname01, "Some random text", branch="main")
    # Test that file is present
    fnames = repo.ls_tree(fname01)
    assert fnames == [fname01]
    # Remove working repo; already gone
    repo.rm_working_repo()
    # Set nonsense
    repo._tmpdir = "nonsense"
    repo.rm_working_repo()
    # create_patch() won't work on Windows
    if os.name == "nt":
        return
    # Try creating a patch for a new file
    repo.create_patch(fname02, "new contents")
    # Make sure file got created
    assert os.path.isfile("ab.patch")
    # Patch an olde file
    repo.create_patch(fname00, "new contents")
    # Get contents of a file to create a null patch
    contents = repo.show(fname01)
    # Try to apply a null patch
    repo.create_patch(fname01, contents)


# Basic functions
@testutils.run_sandbox(__file__, fresh=False)
def test_gitrepo01():
    # Enter the working repo
    os.chdir(REPO_NAME)
    # Check the result
    gitdir = get_gitdir(os.getcwd())
    assert gitdir == os.getcwd()
    # Go to bare repo to repeat
    os.chdir(os.path.join("..", f"{REPO_NAME}.git"))
    # Check result of git_gitdir()
    gitdir = get_gitdir(os.getcwd())
    assert gitdir == os.getcwd()


# Tests run in full repo
def test_repo05():
    # Instantiate repo
    repo = GitRepo()
    # Don't test this on Windows
    if os.name != "nt":
        # Connect a shell, and reconnect
        shell1 = repo.connect()
        shell2 = repo.connect()
        # Should be the same object
        assert shell1 is shell2
    # Get remotes
    remotes = repo.get_remotes()
    # Find the one that points to pfe
    for remote, url in remotes.items():
        if url.startswith("pfe") and url.endswith(".git"):
            break
    else:
        raise ValueError("No pfe remote found")
    # Connect to hub
    repo = GitRepo(url)
    # This should be a bare repo
    assert repo.bare
