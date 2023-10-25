
# Local imports
from lfc._vendor.gitutils._vendor.shellutils import call


# Hub location on pfe
HOST = "pfe"
HUB = "/nobackupp16/ddalle/cape/hub"
PKG = "src/shellutils.git"


# Tests
def test_host_cwd():
    # Run a simple command
    ierr = call(["test", "-d", PKG], host=HOST, cwd=HUB)
    # Test results
    assert ierr == 0

