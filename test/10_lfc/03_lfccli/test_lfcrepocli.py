
# Standard library
import os
import sys
from subprocess import call

# Third-party
import testutils

# Local imports
from lfc.__main__ import main
from lfc.cli import (
    IERR_ARGS,
    IERR_CMD,
    lfc_config,
    lfc_remote,
    lfc_show
)
from lfc.lfcrepo import (
    LFCRepo
)


# List of files to copy
REPO_NAME = "repo"
GIT_FILE = "sample.rst"
LFC_FILE = "rand0.dat"


# Test CLI functions
@testutils.run_sandbox(__file__)
def test_cli01():
    # Paths to working and bare repo
    sandbox = os.getcwd()
    barerepo = os.path.join(sandbox, f"{REPO_NAME}.git")
    remotecache = os.path.join(barerepo, "cache")
    # Create repo
    os.mkdir(REPO_NAME)
    # Enter the "repo" dir
    os.chdir(REPO_NAME)
    # Create some files
    with open(GIT_FILE, 'w') as fp:
        fp.write("A sample file\n")
    with open(LFC_FILE, 'wb') as fp:
        fp.write(os.urandom(128))
    # Initialize repo
    call(["git", "init"])
    # Initialize repo
    repo = LFCRepo()
    # Add a file
    repo.add(GIT_FILE)
    # Issue a commit
    repo.commit("Initial commit", a=True)
    # Initialize LFC
    repo.lfc_init()
    # Add a remote
    lfc_remote("add", "hub", remotecache, d=True)
    # Add a file with LFC
    repo.lfc_add(LFC_FILE)
    # Commit first file
    repo.commit("Add LFC file", a=True)
    # Remember original STDOUT
    sysstdout = sys.stdout
    # Redirect STDOUT
    fp = open("stdout", 'w')
    sys.stdout = fp
    # Run lfc-config get
    lfc_config("get", "core.remote")
    # Compare STDOUT to expectation
    fp.close()
    testutils.compare_files("stdout", "hub\n")
    # New STDOUT file
    fp = open("stdout", 'w')
    sys.stdout = fp
    # Run lfc-remote list
    lfc_remote("list")
    # Read STDOUT for expectation
    fp.close()
    stdout = open("stdout", 'r').read()
    # Test results
    assert len(stdout.split(":")) == 2
    assert stdout.split(":")[0].strip() == "hub"
    assert stdout.split(":")[1].strip() == remotecache
    # Restore original stdout
    sys.stdout = sysstdout
    # Run invalid lfc_config() commands
    ierr = lfc_config()
    assert ierr == IERR_ARGS
    ierr = lfc_config("scope", "core.remote")
    assert ierr == IERR_CMD
    # Run invalid lfc_remote() commands
    ierr = lfc_remote()
    assert ierr == IERR_ARGS
    ierr = lfc_remote("scope", "hub", "someplace")
    assert ierr == IERR_CMD
    # Invalid lfc_show() command
    ierr = lfc_show()
    assert ierr == IERR_ARGS


# Test more CLI functions
@testutils.run_sandbox(__file__, fresh=False)
def test_cli02():
    # Enter repo
    os.chdir(REPO_NAME)
    # Remember original STDOUT
    sysstdout = sys.stdout
    # Redirect STDOUT
    fp = open("stdout", 'w')
    sys.stdout = fp
    # Use main function to list files
    sys.argv = ["lfc", "ls-files"]
    ierr = main()
    assert ierr == 0
    # Compare STDOUT to target
    fp.close()
    stdout = open("stdout").read()
    assert stdout == f"{LFC_FILE}.lfc\n"
    # Restore original STDOUT
    sys.stdout = sysstdout
    # Run the help function
    sys.argv = ["lfc", "-h"]
    ierr = main()
    assert ierr == 0
    # Invalid subcommand
    sys.argv = ["lfc", "collect"]
    ierr = main()
    assert ierr == IERR_CMD
    # Test error catching
    cmd = ["lfc", "config", "get", "missingsection.name"]
    ierr = call([sys.executable, "-m"] + cmd)
    assert ierr


# Test more CLI functions
@testutils.run_sandbox(__file__, fresh=False)
def test_cli03():
    # Enter the test repo
    os.chdir(REPO_NAME)
    # Test lfc-show
    fp = open("stdout", 'wb')
    sys.stdout = fp
    # Use main function to run lfc-show
    sys.argv = ["lfc", "show", f"{LFC_FILE}.lfc"]
    ierr = main()
    assert ierr == 0
    # Close file and read STDOUT
    fp.close()
    stdout = open("stdout", "rb").read()
    # Read LFC file
    expected = open(LFC_FILE, 'rb').read()
    assert stdout == expected

