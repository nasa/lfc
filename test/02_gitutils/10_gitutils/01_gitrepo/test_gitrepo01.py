
# Standard library
import posixpath
import os
from subprocess import call

# Third-party
import pytest
import testutils

# Local imports
from lfc._vendor.gitutils.gitrepo import (
    GitRepo,
    GitutilsFileNotFoundError,
    GitutilsSystemError,
    GitutilsValueError,
    _assemble_path,
    _safe_ref,
    is_bare,
    run_gitdir)


# List of files to copy
COPY_FILES = [
    "sample.rst",
    "rando.dat",
]


# Subclass to test wrapper
class MyRepo(GitRepo):
    # Show the path
    @run_gitdir
    def getcwd(self):
        return os.getcwd()

    # List files or something
    @run_gitdir
    def ls(self, fdir="."):
        return os.listdir(fdir)


# Run a test
@testutils.run_sandbox(__file__, COPY_FILES)
def test_repo01():
    # Initialize repo
    ierr = call(["git", "init"])
    assert ierr == 0
    # Check for .git/ folder
    assert os.path.isdir(".git")
    # Initialize repo
    repo = GitRepo()
    # Add a file
    fname = COPY_FILES[0]
    repo.add(*COPY_FILES)
    # Show status
    statusdict = repo.status()
    # Test result
    assert fname in statusdict
    assert statusdict[fname] == "A "
    # Issue a commit
    repo.commit("Initial commit", a=True)
    # Test contents of "show"
    txt1 = repo.show(fname).decode("utf-8")
    # Compare
    testutils.compare_files(fname, txt1)
    # Test location of config directory
    configdir = repo.get_configdir()
    # Test location
    assert configdir == os.path.join(os.getcwd(), ".git")
    # Create another branch
    ierr = call(["git", "checkout", "-b", "devel"])
    assert ierr == 0
    # Get list of branches
    branches = repo.get_branch_list()
    # Assert the contents and order
    assert branches == ["devel", "main"]
    # Checkout the main branch again
    repo.checkout_branch()
    repo.checkout_branch("main")
    # Assert the contents and order
    assert repo.get_branch_list() == ["main", "devel"]
    # Test branch validator
    repo.validate_branch(None)
    repo.validate_branch("main")
    with pytest.raises(GitutilsValueError):
        repo.validate_branch("debug")
    # Check if file is ignored
    assert not repo.check_ignore(fname)
    # Check if file is tracked
    assert repo.check_track(fname)
    # Get commit from a ref name
    hash = repo.get_ref()
    assert isinstance(hash, str)
    # Test failure of assert_bare() if working
    with pytest.raises(GitutilsSystemError):
        repo.assert_bare(cmd=["git", "made-up"])


# Basic operations
@testutils.run_sandbox(__file__, fresh=False)
def test_repo02():
    # Initialize repo
    repo = GitRepo()
    # Initial file name
    fname00 = COPY_FILES[0]
    # New file name
    fname01 = "moved.rst"
    # Other file
    fname02 = COPY_FILES[1]
    # Sub folder
    fdir01 = "subdir"
    fname03 = os.path.join(fdir01, "test2.txt")
    # Test the "mv" command
    repo.mv(fname00, fname01)
    # Commit
    repo.commit("Rename .rst file")
    # Make sure old file is not there
    assert not os.path.isfile(fname00)
    assert os.path.isfile(fname01)
    # Create a folder
    os.mkdir(fdir01)
    # Add some files therein
    with open(fname03, 'w') as fp:
        fp.write("Some text")
    # Add the folder
    repo.add(fdir01)
    repo.commit("Add a folder")
    # Remove (once recursively and once not)
    repo.rm(fdir01, r=True)
    repo.rm(fname02)
    # Make sure those are gone
    assert not os.path.isfile(fname02)
    assert not os.path.isdir(fdir01)
    # Commit removals
    repo.commit("Remove two files")
    # Ignore a file
    repo._ignore("temp.dat")
    repo._ignore("temp.dat")
    assert repo.check_ignore("temp.dat")


# Indirect commands
@testutils.run_sandbox(__file__, fresh=False)
def test_repo03():
    # Get repo
    repo = GitRepo()
    # Initial file name
    fname00 = COPY_FILES[0]
    # New file name
    fname01 = "moved.rst"
    # Test ls-tree
    assert repo.ls_tree() == [fname01]
    assert repo.ls_tree(fname00) == []
    # Show a file that's no more
    with pytest.raises(GitutilsSystemError):
        repo.show(fname00)


# Patching
@testutils.run_sandbox(__file__, fresh=False)
def test_repo04():
    # Instantiate repo
    repo = GitRepo()
    # File to patch
    fname02 = COPY_FILES[1]
    fname03 = os.path.join("nonexistentfolder", "test.txt")
    # New contents of file
    msg = "Rewritten contents"
    # Patch the contents of it
    repo.patch_file(fname02, msg)
    # Get the version of the file currently committed
    txt1 = repo.show(fname02).decode("utf-8")
    # Test that the new version was actually committed
    assert txt1 == msg
    # Try to patch a file that's in a folder that doesn't exist
    with pytest.raises(GitutilsFileNotFoundError):
        repo.patch_file(fname03, "a")
    # Path to working repo
    assert repo.get_tmpdir() == os.path.basename(repo.gitdir)


# Config
@testutils.run_sandbox(__file__, fresh=False)
def test_repo05():
    # Instantiate repo
    repo = GitRepo()
    # Conversions for config
    assert repo._to_ini("normal") == "normal"
    assert repo._to_ini(True) == "true"
    assert repo._to_ini(False) == "false"


# Wrapper
@testutils.run_sandbox(__file__, fresh=False)
def test_repo06():
    # Instantiate repo
    repo = MyRepo()
    # Create a folder
    os.mkdir("testdir")
    os.chdir("testdir")
    # Save path
    cwd = os.getcwd()
    # Call the cwd() function that tests the run_gitdir wrapper
    assert repo.getcwd() == repo.gitdir
    assert repo.getcwd() != os.getcwd()
    # Test an exception
    with pytest.raises(FileNotFoundError):
        repo.ls("not_there")
    # Make sure we're back to original location
    assert os.getcwd() == cwd


# Tests run in full repo
def test_fullrepo01():
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
        if url.startswith("linux252") and url.endswith(".git"):
            break
    else:
        raise ValueError("No linux252 remote found")
    # Connect to hub
    repo = GitRepo(url)
    # This should be a bare repo
    assert repo.bare
    # Connect a shell
    shell = repo.connect()
    # Check that it's remote
    assert shell.host
    # Test is_bare() in a folder that exists but it's not a repo
    with pytest.raises(SystemError):
        is_bare(posixpath.dirname(url))


# Basic utilities test
def test_gitrepo01():
    # Assemble a path
    path = _assemble_path(None, os.getcwd())
    assert path == os.getcwd()
    # Assemble a remote path
    path = _assemble_path("linux252", ".ssh")
    assert path == "linux252:.ssh"
    # Default git ref
    assert _safe_ref() == "HEAD"


# Shell tests
@testutils.run_sandbox(__file__, fresh=False)
def test_reposhell01():
    # Instantiate repo
    repo = GitRepo()
    # check_output() w/ allowed nonzero status
    repo.check_o(["git", "show", "HEAD:nothing"], codes=(0, 128))
    with pytest.raises(GitutilsSystemError):
        repo.check_o(["git", "show", "HEAD:nothing"])
    # check_call() w/ allowed nonzero status
    repo.check_call(["git", "show", "HEAD:nothing"], codes=(0, 128))
    with pytest.raises(GitutilsSystemError):
        repo.check_call(["git", "show", "HEAD:nothing"])
    # call()
    ierr = repo.call(["git", "show", "HEAD:nothing"])
    assert ierr == 128
