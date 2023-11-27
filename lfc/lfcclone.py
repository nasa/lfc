r"""
``lfcclone``: Command-line interface for ``lfc-clone``
========================================================

The ``lfc clone`` command has a separate module (this one) in order to
create a separate entry point (:func:`main`). This is used for the
command ``git-lfc-clone``, which is a convenience executable. Users may
use

    .. code-block:: console

        $ git lfc-clone $SOURCE_REPO [$OUT_REPO [OPTIONS]]

or

    .. code-block:: console

        $ lfc clone $SOURCE_REPO [$OUT_REPO [OPTIONS]]

interchangeably.
"""

# Standard library
import posixpath
import os

# Local imports
from .lfcrepo import LFCRepo
from .lfcerror import LFCCloneError
from ._vendor.argread import ArgReader
from ._vendor.gitutils._vendor import shellutils


def lfc_clone(*a, **kw) -> int:
    r"""Clone a repo (using git) and pull all mode-2 LFC files

    :Call:
        >>> ierr = lfc_clone(in_repo, bare=False)
        >>> ierr = lfc_clone(in_repo, out_repo, bare=False)
    :Inputs:
        *in_repo*: :class:`str`
            URL to repo to clone
        *out_repo*: {``None``} | :class:`str`
            Explicit name of created repo; defaults to basename of
            *in_repo*
        *bare*: ``True`` | {``False``}
            Whether new repo should be a bare repo
    :Outputs:
        *ierr*: :class:`int`
            Return code
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
def main() -> int:
    r"""Clone a repo (using git) and pull all mode=-2 LFC files

    :Call:
        >>> ierr = main()
    :Inputs:
        (Determined from ``sys.argv``)
    :Outputs:
        *ierr*: :class:`int`
            Return code
    """
    # Create parser
    parser = ArgReader()
    # Parse args
    a, kw = parser.parse()
    kw.pop("__replaced__", None)
    # Clone
    return lfc_clone(*a, **kw)
