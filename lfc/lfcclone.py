
# Standard library
import posixpath
import os

# Local imports
from .lfcrepo import LFCRepo
from .lfcerror import LFCCloneError
from ._vendor.argread import ArgReader
from ._vendor.gitutils._vendor import shellutils


def lfc_clone(*a, **kw):
    r"""Clone a repo (using git) and pull all mode=-2 LFC files

    :Call:
        >>> self.lfc_clone()
    :Inputs:
        *repo*: :class:`GitRepo`
            Interface to git repository
    """
    # Create nominal command
    cmd = ["git", "clone", *a]
    # Check for --bare option
    if kw.pop("bare", False):
        cmd.append("--bare")
    # Clone the repo using git
    ierr = shellutils.call(cmd, **kw)
    # Check for errors
    if ierr:
        raise LFCCloneError(f"git-clone failed with status {ierr}")
    # Get name of repo
    repo_name = posixpath.basename(os.path.basename(a[-1]))
    # Check if we should remove .git: ``git clone repo.git`` -> repo
    if repo_name.endswith(".git") and len(a) == 1:
        # Cloned bare repo -> working repo
        repo_name = repo_name[:-4]
    # Enter the repo
    fpwd = os.getcwd()
    os.chdir(repo_name)
    # Instantiate
    repo = LFCRepo()
    # Exit if bare
    if repo.bare:
        os.chdir(fpwd)
        return 0
    # Install hooks
    repo.lfc_install_hooks()
    # Pull all mode-2 files
    repo.lfc_pull(mode=2)
    # Return to original location
    os.chdir(fpwd)
    # Return code
    return 0


# Main function
def main():
    # Create parser
    parser = ArgReader()
    # Parse args
    a, kw = parser.parse()
    kw.pop("__replaced__", None)
    # Clone
    return lfc_clone(*a, **kw)
