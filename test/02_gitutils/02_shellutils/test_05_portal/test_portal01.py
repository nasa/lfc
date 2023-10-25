
# Standard library
import os
import shutil

# Third-party
import pytest
import testutils

# Local imports
from lfc._vendor.gitutils._vendor.shellutils import (
    SSHPortal,
    ShellutilsFileNotFoundError)


# Lists of files
TEST_FILE1 = "TEST_FILE_SHELLUTILS01"
TEST_FILE2 = "TEST_FILE_SHELLUTILS02"
TEST_FILE3 = "TEST_FILE_SHELLUTILS03"
TEST_DIR = "TEST_DIR"
TEST_FILES = [
    TEST_FILE1
]
SIZE2 = 4000
# Location for remote
HOST = "pfe"
REMOTE_DIR = "/tmp"


# Create a shell
@testutils.run_sandbox(__file__, TEST_FILES)
def test_shell01():
    # Create an SSH/SFTP portal
    portal = SSHPortal(HOST)
    # Go to temp folder
    portal.chdir_remote(REMOTE_DIR)
    # Locally change to nonsense folder
    with pytest.raises(ShellutilsFileNotFoundError):
        portal.chdir_local("nonsense_dir")
    # Test folders
    assert portal.sftp.getcwd_remote() == REMOTE_DIR
    assert portal.sftp.getcwd_local() == os.getcwd()
    # Make sure local file is present
    portal.assert_isfile_local(TEST_FILE1)
    with pytest.raises(ShellutilsFileNotFoundError):
        portal.assert_isfile_local("nonsense_file")
    # Create second file
    with open(TEST_FILE2, 'w') as fp:
        fp.write("X" * SIZE2)
    # Test file size
    assert portal._getsize_l(TEST_FILE2) == SIZE2
    assert portal._getsize_l("nonsense_file") == 0
    # Copy file to *HOST*
    portal.put(TEST_FILE2)
    # Test file size after copy
    assert portal._getsize_r(TEST_FILE2) == SIZE2
    assert portal._getsize_r("nonsense_file_gIb83r1sh") == 0
    # Remove the local file
    portal.remove_local(TEST_FILE2)
    # Get it back
    portal.get(TEST_FILE2)
    portal.get(TEST_FILE2)
    # Make sure it's back
    portal.assert_isfile_local(TEST_FILE2)
    # Use SFTP instance directly to test cmds w/o destination fname
    portal.sftp.put(TEST_FILE1)
    portal.sftp.get(TEST_FILE1)
    # Change local path
    portal.chdir_local("..")
    assert portal.sftp.getcwd_local() == os.path.dirname(__file__)
    # Close the portal
    portal.close()
    # Test getting absolute path locally (should do nothing)
    fabs = portal.abspath_local(os.path.expanduser("~"))
    assert fabs == os.path.expanduser("~")
    # Test file name truncation
    twidth = shutil.get_terminal_size().columns
    f1 = portal._trunc8_fname("file.dat", twidth - 6)
    f2 = portal._trunc8_fname("folder/file.dat", twidth - 12)
    assert len(f1) == 6
    assert len(f2) == 12

