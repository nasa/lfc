
# Third-party
import testutils

# Local imports
from lfc._vendor.gitutils._vendor.shellutils import (
    call,
    call_o,
    call_oe,
    call_q,
    check_o)


# This file
TEST_FILE = "empty.txt"


# Tests
@testutils.run_sandbox(__file__, TEST_FILE)
def test_check_o():
    # Run a simple command
    stdout, stderr = check_o(["ls"])
    # Test results
    assert stdout.strip() == TEST_FILE
    assert stderr is None


@testutils.run_sandbox(__file__, fresh=False)
def test_check_o_raise():
    # Run a command that doesn't work
    try:
        check_o(["test", "-d", TEST_FILE])
    except SystemError:
        return
    else:
        # Should have failed (exit code 1)
        assert False


@testutils.run_sandbox(__file__, TEST_FILE)
def test_call():
    # Run a simple command
    ierr = call(["ls"])
    # Test results
    assert ierr == 0


@testutils.run_sandbox(__file__, TEST_FILE)
def test_call_oe():
    # Try to create folder where file exists
    stdout, stderr, ierr = call_oe(["mkdir", TEST_FILE])
    # Should be a return code and some STDERR
    assert ierr != 0
    assert stdout.strip() == ""
    assert "cannot create" in stderr


@testutils.run_sandbox(__file__, TEST_FILE)
def test_call_o():
    # Run a simple command
    stdout, stderr, ierr = call_o(["ls"])
    # Test results
    assert ierr == 0
    assert stdout.strip() == TEST_FILE
    assert stderr is None


@testutils.run_sandbox(__file__, TEST_FILE)
def test_call_q():
    # Try to create folder where file exists
    ierr = call_q(["mkdir", TEST_FILE])
    # Should be a return code and some STDERR
    assert ierr != 0

