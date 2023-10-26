
# Standard library
import os

# Local imports
from lfc._vendor.gitutils._vendor.shellutils import identify_host


# Hub location on pfe
HOST = "pfe"
HUB = "/nobackupp16/ddalle/cape/hub"
PKG = "src/shellutils.git"


# Tests
def test_host_cwd():
    # Test for remote path
    host, path = identify_host(HOST + ":" + HUB)
    # Test results
    assert host == HOST
    assert path == HUB
    # Test for alternamte method
    host, path = identify_host(f"ssh://{HOST}{HUB}")
    # Test results
    assert host == HOST
    assert path == HUB
    # Test for local path
    host, path = identify_host(PKG)
    # Test results
    assert host is None
    assert path == PKG
    # Default
    host, path = identify_host(None)
    assert host is None
    assert path == os.getcwd()
