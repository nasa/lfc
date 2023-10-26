
# Third-party
import pytest

# Local imports
from lfc._vendor.gitutils._vendor.shellutils import (
    ShellutilsFilenameError,
    validate_dirname,
    validate_filename,
    validate_globname,
)


# Test bad file or folder names
def test_valid_filenames01():
    # Try some valid file names, etc.
    validate_filename("nice_and_normal.dat")
    validate_dirname("NothingSpecial123")
    validate_globname("found_in_*_zone_[a-e]")
    # Colon only allowed in position 1
    validate_filename(r"C:")
    # Folder ending with ".", not allowed on Windows
    with pytest.raises(ShellutilsFilenameError):
        validate_dirname("horse.")
    # File ending with ".", also not allowed on Windows
    with pytest.raises(ShellutilsFilenameError):
        validate_filename("horse.")
    # Glob pattern including >
    with pytest.raises(ShellutilsFilenameError):
        validate_filename("horse_*>")
    # Super long file name
    with pytest.raises(ShellutilsFilenameError):
        validate_filename("too_long_" * 1000)
