r"""
Large File Control (``lfc``) is a Python package to track large files
in git repositories. It provides both an API (see :class:`LFCRepo`) and
a command-line interface (see :mod:`lfc.cli`).

The package works by calculating SHA-256 hashes of each "large" file.
Users determine which files are "large" by running ``lfc_add()`` on
them. The package can also share these large files remotely using a
simultaneous SSH and SFTP connection to a remote server.

"""

# Local imports
from .lfcrepo import LFCRepo
