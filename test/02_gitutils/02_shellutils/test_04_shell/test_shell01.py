
# Standard library
import os
import time

# Third-party
import pytest
import testutils

# Local imports
from lfc._vendor.gitutils._vendor.shellutils import (
    Shell,
    ShellutilsFileNotFoundError,
    ShellutilsFileExistsError,
    ShellutilsIsADirectoryError)


# Lists of files
TEST_FILE = "TEST_FILE"
TEST_FILE2 = "TEST_FILE2"
TEST_DIR = "TEST_DIR"
TEST_FILES = [
    TEST_FILE
]


# Create a shell
@testutils.run_sandbox(__file__, TEST_FILES)
def test_shell01():
    # Create a shell
    shell = Shell()
    # Get the list of files
    lsfiles = shell.listdir()
    # Check result
    assert lsfiles == TEST_FILES
    # Run a nonsense command to get some STDERR
    shell.run("ap5ap5ap5")
    # Get STDERR
    time.sleep(0.1)
    stderr = shell.read_stderr()
    assert "ap5ap5ap5" in stderr
    # Test folder check
    with pytest.raises(ShellutilsFileNotFoundError):
        shell.assert_isdir("nonsense_dir")
    # Test file check
    with pytest.raises(ShellutilsFileNotFoundError):
        shell.assert_isfile("nonsense_file")
    # Test STDOUT combiner
    shell.run("echo 'a' && sleep 0.2 && echo 'b'")
    shell.wait()
    assert shell._stdout.strip() == 'a\nb'
    # Create a folder
    shell.mkdir(TEST_DIR)
    shell.assert_isdir(TEST_DIR)
    # Error checks for repeat
    with pytest.raises(ShellutilsFileExistsError):
        shell.mkdir(os.path.abspath(TEST_DIR))
    # Get size of a file
    fsize = shell.getsize(TEST_FILE)
    assert fsize < 100
    # Go up a folder
    shell.chdir("..")
    # Try to create a new file that's already a folder
    with pytest.raises(ShellutilsIsADirectoryError):
        shell.newfile("work")
    # Try to remove a file that's a folder
    with pytest.raises(ShellutilsIsADirectoryError):
        shell.remove("work")
    # Test current folder
    cwd = shell.getcwd()
    assert cwd == os.path.dirname(__file__)
    # Create file in subdirectory
    shell.touch(f"work/{TEST_FILE2}")
    time.sleep(0.05)
    assert os.path.isfile(TEST_FILE2)
    # Reenter working folder
    shell.chdir("work")
    # Call newfile() when file exists
    shell.newfile(TEST_FILE2)
    # Delete a file
    shell.remove(TEST_FILE2)
    time.sleep(0.05)
    assert not os.path.isfile(TEST_FILE2)
    # Try to delete again
    with pytest.raises(ShellutilsFileNotFoundError):
        shell.remove(TEST_FILE2)
    # Run close function twice to test error checking
    shell.close()
    shell.close()
    # Test closing
    assert shell.proc.stdin.closed
    # Test trivial line of decoding
    assert shell._decode(None) is None


if __name__ == "__main__":
    test_shell01()
