
# Standard library
import shutil

# Third-party
import testutils

# Local imports
from lfc._vendor.gitutils import giterror


# Files to copy
COPY_FILES = [
    "sample.rst"
]


# Test file checker
@testutils.run_sandbox(__file__, COPY_FILES)
def test_isfile():
    # Name of existing, then nonexistent files
    fname00 = COPY_FILES[0]
    fname01 = "nope.txt"
    # Assert that a file does *not* exist
    try:
        # Check for file
        giterror.assert_isfile(fname01)
    except giterror.GitutilsFileNotFoundError as err:
        # Check message
        assert fname01 in err.args[0]
    else:
        # Error expected
        raise ValueError("Exception expected")
    # Test file that does exist
    giterror.assert_isfile(fname00)
    # Test truncation of long file name w/o slash
    f1 = giterror.trunc8_fname("a"*80, n=40)
    # Won't test the output, except to make sure it's short enough
    twidth = shutil.get_terminal_size().columns
    assert len(f1) + 40 <= twidth


# Test type checker
def test_isinstance():
    # Null check should always pass
    giterror.assert_isinstance(1, None)
    # Normal valid check
    giterror.assert_isinstance(1, int)
    # Failed check: single type
    try:
        giterror.assert_isinstance(1, float)
    except giterror.GitutilsTypeError as err:
        # Check type name in message
        assert 'float' in err.args[0]
    else:
        assert False
    # Failed check: multiple types
    try:
        giterror.assert_isinstance(1, (str, float), "abcdef")
    except giterror.GitutilsTypeError as err:
        assert 'abcdef' in err.args[0]
    else:
        assert False
