r"""
``lfc.lfrrepo``: Interface to git repos with large-file control
==================================================================

This module provides the :class:`LFCRepo`, which provides tools for
interacting with Git repositories. This includes actions to hash, store,
and transfer large files tracked with ``lfc``.
"""

# Standard library
import glob
import hashlib
import os
import posixpath
import re
import shutil
import socket
import sys
import time
from configparser import ConfigParser

# Third-party
import yaml

# Local imports
from .lfcerror import LFCCheckoutError
from ._vendor.gitutils._vendor import shellutils
from ._vendor.gitutils.giterror import (
    GitutilsKeyError,
    GitutilsSystemError,
    GitutilsValueError,
    assert_isinstance,
    assert_isfile)
from ._vendor.gitutils.gitrepo import (
    GitRepo,
    run_gitdir
)


# Regular expression for LFC remote section names
REGEX_LFC_REMOTE_SECTION = re.compile('\'remote "(?P<name>\\w+)"\'')


# Create new class
class LFCRepo(GitRepo):
   # --- Class attributes ---
    # Class attributes
    __slots__ = (
        "bare",
        "gitdir",
        "lfc_config",
        "lfc_portal",
        "lfc_remote",
        "_t_lfc_config")

   # --- __dunder__ ---
    def __init__(self, where=None):
        # Parent initializtion
        GitRepo.__init__(self, where)
        # Initialize other slots
        self.lfc_config = None
        self.lfc_portal = None
        self.lfc_remote = None
        self._t_lfc_config = None

   # --- SSH portal interface ---
    def make_lfc_portal(self, remote=None):
        r"""Open SSH/SFTP portal for large files

        :Call:
            >>> portal = repo.make_lfc_portal(slot="lfc_portal")
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *remote*: {``None``} | :class:`str`
                Name of remote, or default
        :Outputs:
            *portal*: ``None`` | :class:`shellutils.SSHPortal`
                Persistent file transfer portal
        :Versions:
            * 2022-12-20 ``@ddalle``: v1.0
        """
        # Resolve remote name
        remote = self.resolve_lfc_remote_name(remote)
        # Get current attribute
        portal = self.lfc_portal
        # Exit if already processed
        if remote == self.lfc_remote and portal is not None:
            # Return current portal
            return portal
        # Get remote
        fremote = self.get_lfc_remote_url(remote)
        # Get parts of remote
        host, path = _get_remote_host(fremote)
        # No portal if remote is local
        if host is None:
            return
        # Status update
        print(
            "Opening file transfer portal to '%s' (remote '%s')"
            % (host, remote))
        print("  Logging in twice (SSH, then SFTP)")
        # Open portal
        portal = shellutils.SSHPortal(host)
        # Check if remote cache exists
        if not portal.ssh.isdir(path):
            # If not, create it! (using SSH to get correct permissions)
            portal.ssh.mkdir(path)
        # Change directory
        portal.chdir_remote(path)
        # Save it
        self.lfc_portal = portal
        self.lfc_remote = remote
        # Return it
        return portal

    def close_lfc_portal(self):
        r"""Close large file transfer portal, if any

        :Call:
            >>> repo.close_lfc_portal()
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
        :Versions:
            * 2022-12-20 ``@ddalle``: v1.0
        """
        # Get current portal
        portal = self.lfc_portal
        # Close it
        if portal is not None:
            portal.close()
        # Reset LFC portal
        self.lfc_portal = None
        self.lfc_remote = None

   # --- LFC replace-DVC ---
    @run_gitdir
    def lfc_replace_dvc(self):
        r"""Fully subsitute local large file control in place of DVC

        This command will move all ``.dvc`` metadata stub files to the
        same name but with ``.lfc`` as the extension. It will also move
        the ``.dvc/`` folder to ``.lfc/`` and remove the ``.dvc/plots/``
        folder and ``.dvcignore`` file.

        It does not recompute any hashes as LFC can work with MD-5
        hashes. It cannot compute any new ones, but it can still utilize
        the old ones and have the two intermixed.

        :Call:
            >>> repo.lfc_replace_dvc()
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
        :Versions:
            * 2022-12-28 ``@ddalle``: v1.0
            * 2023-03-17 ``@ddalle``: v1.1; delete .dvc/plots first
        """
        # Only attempt in working repo
        self.assert_working()
        # Form expected folder names
        flfcdir = os.path.join(self.gitdir, ".lfc")
        fdvcdir = os.path.join(self.gitdir, ".dvc")
        fplotdir = os.path.join(fdvcdir, "plots")
        # Check if .dvc/plots folder was there
        if os.path.isdir(fplotdir):
            # Remove it
            self.rm(os.path.join(".dvc", "plots"), r=True)
        # Make sure .dvc exists but not .lfc
        if os.path.isdir(fdvcdir) and not os.path.isdir(flfcdir):
            # Move the folder (using git)
            self.mv(".dvc", ".lfc")
        # Check for .dvcignore
        if os.path.isfile(".dvcignore"):
            # Remove it
            self.rm(".dvcignore")
        # Find all the "*.dvc" files
        for fdvc in self.find_lfc_files(ext=".dvc"):
            # Form ".lfc" file name
            fbase = fdvc[:-4]
            flfc = fbase + ".lfc"
            # Status update
            print("%s{.dvc -> .lfc}" % fbase)
            # Move the file
            self.mv(fdvc, flfc)

   # --- LFC add ---
    def lfc_add(self, *fnames, **kw):
        r"""Add one or more large files

        :Call:
            >>> repo.lfc_add(*fnames, **kw)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *fnames*: :class:`tuple`\ [:class:`str`]
                Names or wildcard patterns of files to add using LFC
        :Versions:
            * 2022-12-28 ``@ddalle``: v1.0
        """
        # Loop through files
        for fname in fnames:
            # Expand
            fglob = glob.glob(fname)
            # Loop through matches
            for fj in fglob:
                self._lfc_add(fj)

    def _lfc_add(self, fname: str):
        # Strip .dvc if necessary
        fname = self.genr8_lfc_ofilename(fname)
        flfc = self.genr8_lfc_filename(fname)
        # Make sure main file is ignored
        self._ignore(fname)
        # Current terminal width
        twidth = shutil.get_terminal_size().columns
        # Truncate file name
        fname8 = self._trunc8_fname(fname, 20)
        # Check cache status
        if os.path.isfile(flfc) and self.check_status(flfc):
            # Status update
            print(f"File up to date: {fname8}")
            # Stub already added
            return
        # Status update
        sys.stdout.write(f"Calculating hash: {fname8}")
        sys.stdout.flush()
        # Generate the hash
        fhash = self.genr8_hash(fname)
        sys.stdout.write("\r%*s\r" % (twidth, ""))
        sys.stdout.flush()
        # We need the size of the file, too
        finfo = os.stat(fname)
        fsize = finfo.st_size
        # Write LFC metadata stub file
        with open(flfc, "w") as fp:
            fp.write("outs:\n")
            fp.write("- sha256: %s\n" % fhash)
            fp.write("  size: %i\n" % fsize)
            fp.write("  path: %s\n" % os.path.basename(fname))
        # Get cache location
        cachedir = self.get_cachedir()
        # Subdir
        fdir = os.path.join(cachedir, fhash[:2])
        # Cache file
        fcache = os.path.join(fdir, fhash[2:])
        # Create folders
        for _f in (cachedir, fdir):
            if not os.path.isdir(_f):
                os.mkdir(_f)
        # Check for existing cache
        if os.path.isfile(fcache):
            # Status update
            print(f"File in cache: {fname8}")
        else:
            # Copy file into cache
            shutil.copy(fname, fcache)
        # Add the stub
        self._add(flfc)

    def genr8_hash(self, fname: str):
        r"""Calculate SHA-256 hex digest of a file

        :Call:
            >>> hexhash = repo.genr8_hash(fname)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *fname*: :class:`str`
                Name of file to hash
        :Outputs:
            *hexhash*: :class:`str`
                SHA-256 hex digest of file's bytes
        :Versions:
            * 2022-12-28 ``@ddalle``: v1.0
        """
        # Check if file exists
        if not os.path.isfile(fname):
            raise GitutilsSystemError("No file '%s'" % fname)
        # Read the file and calculate SHA-256 hash
        obj = hashlib.sha256(open(fname, "rb").read())
        # Get the MD-5 hash out
        return obj.hexdigest()

   # --- LFC push ---
    def lfc_push(self, *fnames, **kw):
        r"""Push one or more large files to remote cache

        :Call:
            >>> repo.lfc_push(*fnames, **kw)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *fnames*: :class:`tuple`\ [:class:`str`]
                Names or wildcard patterns of files
        :Versions:
            * 2022-12-28 ``@ddalle``: v1.0
        """
        # Get remote
        remote = kw.get("remote", kw.get("r"))
        # Default file list
        if len(fnames) == 0:
            # Find all files w/i CWD or children
            fnames = self.find_lfc_files()
        # Loop through files
        for fname in fnames:
            # Expand
            fglob = self._genr8_lfc_glob(fname)
            # Loop through matches
            for fj in fglob:
                self._lfc_push(fj, remote)

    def _lfc_push(self, fname: str, remote=None):
        # Get info
        lfcinfo = self.read_lfc_file(fname)
        # Get name of original file name (for progress indicator)
        flarge = self.genr8_lfc_ofilename(fname)
        # Check if file is in the cache
        if not self._check_cache(lfcinfo):
            # Truncate long file names
            f1 = self._trunc8_fname(flarge, 31)
            # Status
            print("File '%s' is not in local cache" % f1)
            return
        # Unpack MD5 hash
        fhash = lfcinfo.get("sha256", lfcinfo.get("md5"))
        # Get remote location
        fremote = self.get_lfc_remote_url(remote)
        # Check remote/local
        if fremote.startswith("ssh://"):
            self._lfc_push_ssh(fhash, remote, flarge)
        else:
            self._lfc_push_local(fhash, remote)

    def _lfc_push_ssh(self, fhash, remote, fname):
        # Get source file
        fsrc = os.path.join(self.get_cachedir(), fhash[:2], fhash[2:])
        # Get remote location
        fremote = self.get_lfc_remote_url(remote)
        # Get parts of remote
        _, path = _get_remote_host(fremote)
        # Get portal
        portal = self.make_lfc_portal(remote)
        # Ensure correct folder
        portal.chdir_remote(path)
        # Get target file
        ftargdir = fhash[:2]
        ftarg = posixpath.join(ftargdir, fhash[2:])
        # Create target folder if needed
        if not portal.ssh.isdir(ftargdir):
            portal.ssh.mkdir(ftargdir)
        # Test if file exists
        if portal.ssh.isfile(ftarg):
            # Truncate long file name
            f1 = self._trunc8_fname(fname, 40)
            # Up-to-date
            print("Remote cache for file '%s' is up to date" % f1)
        else:
            # Upload it
            portal.put(fsrc, ftarg, fprog=fname)

    def _lfc_push_local(self, fhash, remote):
        # Get remote location
        fremote = self.get_lfc_remote_url(remote)
        # Get source file
        fsrc = os.path.join(self.get_cachedir(), fhash[:2], fhash[2:])
        # Get target file
        ftargdir = os.path.join(fremote, fhash[:2])
        ftarg = os.path.join(ftargdir, fhash[2:])
        # Test if target remote exists
        if not os.path.isdir(fremote):
            os.mkdir(fremote)
        # Test if target folder exists
        if not os.path.isdir(ftargdir):
            os.mkdir(ftargdir)
        # Test if file exists
        if not os.path.isfile(ftarg):
            # Copy it
            shutil.copy(fsrc, ftarg)

   # --- LFC pull ---
    def lfc_pull(self, *fnames, **kw):
        r"""Pull one or more large files from remote cache

        :Call:
            >>> repo.lfc_pull(*fnames, **kw)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *fnames*: :class:`tuple`\ [:class:`str`]
                Names or wildcard patterns of files
        :Versions:
            * 2022-12-28 ``@ddalle``: v1.0
        """
        # Get remote
        remote = kw.get("remote", kw.get("r"))
        # Default file list
        if len(fnames) == 0:
            # Find all files w/i CWD or children
            fnames = self.find_lfc_files()
        # Loop through files
        for fname in fnames:
            # Expand
            fglob = self._genr8_lfc_glob(fname)
            # Loop through matches
            for fj in fglob:
                self._lfc_pull(fj, remote)

    def _lfc_pull(self, fname: str, remote=None):
        self._lfc_fetch(fname, remote)
        self._lfc_checkout(fname)

    def _lfc_fetch(self, fname: str, remote=None):
        # Get info
        lfcinfo = self.read_lfc_file(fname)
        # Get original file name
        flarge = self.genr8_lfc_ofilename(fname)
        # Unpack MD5 hash
        fhash = lfcinfo.get("sha256", lfcinfo.get("md5"))
        # Get cache file name
        fcache = os.path.join(self.get_cachedir(), fhash[:2], fhash[2:])
        # Check if file is present in the cache
        if os.path.isfile(fcache):
            # Done
            return
        # Get remote location
        fremote = self.get_lfc_remote_url(remote)
        # Check remote/local
        if fremote.startswith("ssh://"):
            self._lfc_fetch_ssh(fhash, remote, flarge)
        else:
            self._lfc_fetch_local(fhash, remote)

    def _lfc_fetch_ssh(self, fhash, remote, fname):
        # Get remote location
        fremote = self.get_lfc_remote_url(remote)
        # Get parts of remote
        _, path = _get_remote_host(fremote)
        # Get portal
        portal = self.make_lfc_portal(remote)
        # Ensure correct folder
        portal.chdir_remote(path)
        # Get source file
        fsrc = posixpath.join(fhash[:2], fhash[2:])
        # Cache folder
        fcache = self.get_cachedir()
        # Get target file
        ftargdir = os.path.join(fcache, fhash[:2])
        ftarg = os.path.join(ftargdir, fhash[2:])
        # Make sure cache folder exists
        self.make_cachedir()
        # Create target folder if needed
        if not os.path.isdir(ftargdir):
            os.mkdir(ftargdir)
        # Check if remote cache contains file
        if not portal.ssh.isfile(fsrc):
            # Truncate long file name
            f1 = self._trunc8_fname(fname, 30)
            # Status update and exit
            print("Remote cache missing file '%s'" % f1)
            return
        # Copy file
        portal.get(fsrc, ftarg, fprog=fname)

    def _lfc_fetch_local(self, fhash, remote):
        # Get remote location
        fremote = self.get_lfc_remote_url(remote)
        # Get source file
        fsrc = os.path.join(fremote, fhash[:2], fhash[2:])
        # Get target file
        ftargdir = os.path.join(self.get_cachedir(), fhash[:2])
        ftarg = os.path.join(ftargdir, fhash[2:])
        # Make sure cache folder exists
        self.make_cachedir()
        # Create target folder if needed
        if not os.path.isdir(ftargdir):
            os.mkdir(ftargdir)
        # Check if remote cache contains file
        if not os.path.isfile(fsrc):
            raise GitutilsSystemError("Remote cache does not contain file")
        # Copy file
        shutil.copy(fsrc, ftarg)

   # --- LFC checkout --
    def lfc_checkout(self, *fnames, **kw):
        r"""Checkout one or more large files from current ``.lfc`` stub

        :Call:
            >>> repo.lfc_checkout(*fnames, **kw)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *fnames*: :class:`tuple`\ [:class:`str`]
                Names or wildcard patterns of files
        :Versions:
            * 2023-10-24 ``@ddalle``: v1.0
        """
        # Loop through files
        for fname in fnames:
            # Expand
            fglob = self._genr8_lfc_glob(fname)
            # Loop through matches
            for fj in fglob:
                self._lfc_checkout_cli(fj)

    def _lfc_checkout_cli(self, fname: str):
        # Strip .lfc if necessary
        fname = self.genr8_lfc_ofilename(fname)
        # Add the extension
        flfc = self.genr8_lfc_filename(fname)
        # Read metadata
        lfcinfo = self.read_lfc_file(flfc)
        # Unpack hash
        fhash = lfcinfo.get("sha256", lfcinfo.get("md5"))
        # Get path to cache
        cachedir = self.get_cachedir()
        # Check for existing file
        if os.path.isfile(fname):
            # Calculate hash of existing file
            hash1 = self.genr8_hash(fname)
            # Check if it's the same file
            if hash1 == fhash:
                return
            # Generate cache file name for existing file
            fcache1 = os.path.join(cachedir, fhash[:2], fhash[2:])
            # Check if file is present
            if not os.path.isfile(fcache1):
                raise LFCCheckoutError(
                    f"Cannot checkout '{fname}'; existing file not in cache")
            # Otherwise delete existing file
            os.remove(fname)
        # Copy cache file to working file
        shutil.copy(fhash, fname)

    def _lfc_checkout(self, fname: str):
        # Strip .lfc if necessary
        fname = self.genr8_lfc_ofilename(fname)
        # Get info
        lfcinfo = self.read_lfc_file(fname)
        # Unpack MD5 hash
        fhash = lfcinfo.get("sha256", lfcinfo.get("md5"))
        # Get cache file name
        fcache = os.path.join(self.get_cachedir(), fhash[:2], fhash[2:])
        # Check if file is present in the cache
        if not os.path.isfile(fcache):
            raise GitutilsSystemError("File for '%s' is not in cache" % fname)
        # Check if current file is present
        if os.path.isfile(fname):
            # Get stats about this file and cache file
            finfo = os.stat(fname)
            cinfo = os.stat(fcache)
            # Sizes
            fsize = finfo.st_size
            csize = cinfo.st_size
            # Modification times
            fmtime = finfo.st_mtime
            cmtime = cinfo.st_mtime
            # Get size and modification time
            if (fsize == csize) and (fmtime >= cmtime):
                # Truncate long file names
                f1 = self._trunc8_fname(fname, 23)
                # Already up to date!
                print("File '%s' is up to date" % f1)
                return
            # Remove the file
            os.remove(fname)
        # Copy file
        shutil.copy(fcache, fname)

   # --- LFC show ---
    def lfc_show(self, fname: str, ref=None, **kw):
        r"""Show the contents of an LFC file from a local cache

        :Call:
            >>> contents = repo.lfc_show(fname)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *fname*: :class:`str`
                Name of original file or large file stub
            *ref*: {``None``} | :class:`str`
                Optional git reference (default ``HEAD`` on bare repo)
        :Outputs:
            *contents*: :class:`bytes`
                Contents of large file read from LFC cache
        :Versions:
            * 2011-12-22 ``@ddalle``: v1.0
        """
        # Get name of LFC metadata file
        flfc = self.genr8_lfc_filename(fname)
        forig = self.genr8_lfc_ofilename(fname)
        # Check if LFC file
        if len(self.ls_tree(flfc, ref=ref)) == 0:
            # Just try to show it
            if len(self.ls_tree(forig, ref=ref)) == 0:
                raise GitutilsSystemError(
                    "No file '%s' or '%s' tracked by git" % (forig, flfc))
            # Read file if passing above test
            return self.show(forig, ref=ref)
        # Get hash
        fhash = self.get_lfc_hash(flfc, ref=ref)
        # Get path to large file relative to cache dir
        fcached = os.path.join(fhash[:2], fhash[2:])
        # List of possible caches to search
        cachedirs = [self.get_cachedir()]
        # Loop through remotes
        for remote in self.list_lfc_remotes():
            # Get url
            url = self.get_lfc_remote_url(remote)
            # Check if SSH
            if url.startswith("ssh://"):
                # Save the local path, ignoring host name
                path = "/" + url.split("/", 3)[-1]
            else:
                # Local path
                path = url
            # Save candidate cache location
            cachedirs.append(path)
        # Loop through candidates
        for cachedir in cachedirs:
            # Absolute file name
            fabs = os.path.join(cachedir, fcached)
            # Check if file exists
            if os.path.isfile(fabs):
                break
        else:
            # File not found
            return
        # Read the file
        return open(fabs, 'rb').read()

   # --- LFC info ---
    def get_lfc_hash(self, fname: str, ref=None):
        r"""Get hash code used by LFC for a large file

        :Call:
            >>> hashcode = repo.read_lfc_file(fname, ref=None)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *fname*: :class:`str`
                Name of original file or large file stub
            *ref*: {``None``} | :class:`str`
                Optional git reference (default ``HEAD`` on bare repo)
        :Outputs:
            *hashcode*: :class:`str`
                SHA-256 hash code from LFC file (MD-5 if added by DVC)
        :Versions:
            * 2011-12-22 ``@ddalle``: v1.0
        """
        # Read into of file
        info = self.read_lfc_file(fname, ref=ref)
        # Get hash
        return info.get("sha256", info.get("md5"))

    def read_lfc_file(self, fname: str, ref=None):
        r"""Read status information from large file stub

        :Call:
            >>> info = repo.read_lfc_file(fname, ref=None)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *fname*: :class:`str`
                Name of original file or large file stub
            *ref*: {``None``} | :class:`str`
                Optional git reference (default ``HEAD`` on bare repo)
        :Outputs:
            *info*: :class:`dict`
                Dictionary of information about large file
            *info["sha256"]*: :class:`str`
                Hex string of SHA-256 hash of file
            *info["md5"]*: :class:`str`
                Hex string of MD-5 hash of file added by ``dvc``
            *info["size"]*: :class:`str`
                String of integer of number of bytes in large file
            *info["path"]*: :class:`str`
                Name of original file
        :Versions:
            * 2011-12-20 ``@ddalle``: v1.0
        """
        # Get name of LFC metadata file
        fname = self.genr8_lfc_filename(fname)
        # Check if bare repo
        if self.bare or ref is not None:
            # Make sure the file exists
            if len(self.ls_tree(fname, ref=ref)) == 0:
                raise GitutilsSystemError("No file '%s' in repo" % fname)
            # Read the file, assume UTF-8 encoding
            txt = self.show(fname, ref=ref).decode("utf-8")
            # Parse as YAML
            info = yaml.safe_load(txt)
        else:
            # Make sure file exists
            assert_isfile(fname)
            # Read it
            with open(fname, "r") as fp:
                info = yaml.safe_load(fp)
        # Get the outputs
        return info["outs"][0]

   # --- LFC search ---
    def find_lfc_files(self, pattern=None, ext=None, **kw):
        r"""Find all large file stubs

        :Call:
            >>> lfcfiles = repo.find_lfc_files(pattern=None, ext=None)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *pattern*: {``None``} | :class:`str`
                Pattern to restrict search of large file stubs
            *ext*: {``None``} | ``".lfc"`` | ``".dvc"``
                Optional manual working stub extension to use
        :Outputs:
            *lfcfiles*: :class:`list`\ [:class:`str`]
                List of large file stubs, each ending with *ext*
        :Versions:
            * 2022-12-20 ``@ddalle``: v1.0
            * 2022-12-28 ``@ddalle``: v1.1; bug fix for empty result
        """
        # Get extension
        if ext is None:
            ext = self.get_lfc_ext()
        # Default pattern
        default_pattern = "*" + ext
        if pattern is None:
            # Search for all *ext* files from current directory
            pattern = default_pattern
        elif os.path.isdir(pattern):
            # Append extension to folder name (e.g. all .lfc in data/)
            pattern = os.path.join(pattern, default_pattern)
        elif not pattern.endswith(default_pattern):
            # Append default pattern
            pattern = pattern + default_pattern
        # List the files
        stdout = self.check_o(["git", "ls-files", pattern]).rstrip("\n")
        # Return as a list
        if stdout == "":
            # Empty list ("".split("\n") is [""] ... which is a prob)
            return []
        else:
            return stdout.split("\n")

    def _genr8_lfc_glob(self, fpat: str):
        # Search for files matching pattern
        fglob = glob.glob(fpat)
        # If there are matches; return them
        if len(fglob) > 0:
            return fglob
        # If that's empty, check for a file that's fpat + ".lfc"
        flfc = self.genr8_lfc_filename(fpat)
        # Check if file exists
        if os.path.isfile(flfc):
            return [flfc]
        # Otherwise we should alert users
        sys.tracebacklimit = 1
        raise GitutilsSystemError("No matches for pattern '%s'" % fpat)

   # --- LFC status ---
    def check_status(self, flfc):
        r"""Check if the LFC status of a large file is up-to-odate

        :Call:
            >>> status = repo.check_status(flfc)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *flfc*: :class:`str`
                Name of file
        :Outputs:
            *status*: ``True`` | ``False``
                Whether file is up-to-date
        :Versions:
            * 2022-12-28 ``@ddalle``: v1.0
        """
        # Get info
        lfcinfo = self.read_lfc_file(flfc)
        # Get file name
        fname = lfcinfo.get("path")
        # Check if file present
        if not os.path.isfile(fname):
            return False
        # Get file infos
        dinfo = os.stat(flfc)
        finfo = os.stat(fname)
        # Check if *fname* is newer
        if finfo.st_mtime > dinfo.st_mtime:
            return False
        # Check cache
        return self._check_cache(lfcinfo)

    def check_cache(self, flfc: str):
        r"""Check if large file is in local cache

        :Call:
            >>> status = repo.check_cache(flfc)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *fname*: :class:`str`
                Name of file
        :Outputs:
            *status*: ``True`` | ``False``
                Whether file is present in local cache
        :Versions:
            * 2022-12-28 ``@ddalle``: v1.0
        """
        # Get info
        lfcinfo = self.read_lfc_file(flfc)
        # Check cache
        return self._check_cache(lfcinfo)

    def _check_cache(self, lfcinfo):
        # Get cache file
        fhashabs = self._get_cachefile(lfcinfo)
        # Check if it's there
        return os.path.isfile(fhashabs)

    def _get_cachefile(self, lfcinfo):
        # Get hash
        fhash = lfcinfo.get("sha256", lfcinfo.get("md5"))
        # Assert type
        assert_isinstance(fhash, str, "file hash")
        # Get path to cache folder
        cachedir = self.get_cachedir()
        # Get relative folder
        fhashpath = os.path.join(fhash[:2], fhash[2:])
        # Absolute path
        return os.path.join(cachedir, fhashpath)

   # --- LFC basics ---
    def make_cachedir(self):
        r"""Create large file cache folder if necessary

        :Call:
            >>> repo.make_cachedir()
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
        :Versions:
            * 2022-12-19 ``@ddalle``: v1.0
        """
        # Get name of cache folder
        lfcdir = self.get_lfcdir()
        cachedir = self.get_cachedir()
        # If either doesn't exist, create them
        for fdir in (lfcdir, cachedir):
            if not os.path.isdir(fdir):
                os.mkdir(fdir)

    def get_cachedir(self):
        r"""Get name of large file cache folder

        :Call:
            >>> fdir = repo.get_cachedir()
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
        :Outputs:
            *fdir*: :class:`str`
                Absolute path to large file cache
        :Versions:
            * 2022-12-19 ``@ddalle``: v1.0
            * 2022-12-22 ``@ddalle``: v1.1: bare repo omits ".lfc"
        """
        # Check for bare repo
        if self.bare:
            # Use gitdir/cache
            return os.path.join(self.gitdir, "cache")
        else:
            # Get extension
            ext = self.get_lfc_ext()
            # Get path to cache
            return os.path.join(self.gitdir, ext, "cache")

    def get_lfcdir(self):
        r"""Get path to large file root dir

        :Call:
            >>> fdir = repo.get_lfcdir()
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
        :Outputs:
            *fdir*: :class:`str`
                Path to LFC/DVC settings dir, ``.lfc`` or ``.dvc``
        :Versions:
            * 2022-12-19 ``@ddalle``: v1.0
        """
        # Get extension
        ext = self.get_lfc_ext()
        # Append to .git folder
        return os.path.join(self.gitdir, ext)

    @run_gitdir
    def get_lfc_ext(self, vdef=".lfc"):
        r"""Get name of large file utility

        :Call:
            >>> ext = repo.get_lfc_ext(vdef=".lfc")
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *vdef*: {``".lfc"``} | ``".dvc"``
                Preferred default if neither is present
        :Outputs:
            *ext*: ``".dvc"`` | ``".lfc"``
                Working extenion to use for large file stubs
        :Versions:
            * 2022-12-19 ``@ddalle``: v1.0
            * 2022-12-22 ``@ddalle``: v2.0; valid for bare repos
        """
        # Check for both folders
        lfc_dirs = self.ls_tree(".lfc", ".dvc", r=False)
        # Check candidates
        for ext in (".lfc", ".dvc"):
            # Check if folder is tracked or exists
            if ext in lfc_dirs or os.path.isdir(ext):
                # this version exists
                return ext
        # If reaching this point, use default
        return vdef

   # --- LFC file names ---
    def genr8_lfc_filename(self, fname: str) -> str:
        r"""Produce name of large file stub

        :Call:
            >>> flfc = repo.genr8_lfc_filename(fname)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *fname*: :class:`str`
                Name of file, either original file or metadata stub
        :Outputs:
            *flfc*: :class:`str`
                Name of large file metadata stub file
        :Versions:
            * 2022-12-21 ``@ddalle``: v1.0
        """
        # Get working extension
        ext = self.get_lfc_ext()
        # Get DVC file if needed
        if not fname.endswith(ext):
            fname += ext
        # Output
        return fname

    def genr8_lfc_ofilename(self, fname: str) -> str:
        r"""Produce name of original large file

        This strips the ``.lfc`` or ``.dvc`` extension if necessary.

        :Call:
            >>> forig = repo.genr8_lfc_ofilename(fname)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *fname*: :class:`str`
                Name of file, either original file or metadata stub
        :Outputs:
            *forig*: :class:`str`
                Name of original large file w/o LFC extension
        :Versions:
            * 2022-12-21 ``@ddalle``: v1.0
        """
        # Get working extension
        ext = self.get_lfc_ext()
        # Get DVC file if needed
        if fname.endswith(ext):
            fname = fname[:-len(ext)]
        # Output
        return fname

    def _trunc8_fname(self, fname: str, n: int) -> str:
        # Length of current name
        l0 = len(fname)
        # Max width allowed (right now)
        maxwidth = shutil.get_terminal_size().columns - n
        # Check if truncation needed
        if l0 < maxwidth:
            # Use existing name
            return fname
        # Try to get leading folder
        if "/" in fname:
            # Get first folder, then everything else
            part1, part2 = fname.split("/", 1)
            # Try to truncate this
            fname = part1 + "/..." + part2[4 + len(part1) - maxwidth:]
        else:
            # Just truncate file name from end
            fname = fname[-maxwidth:]
        # Output
        return fname

   # --- LFC init ---
    def lfc_init(self, **kw):
        r"""Initialize a git repo for Large File Control

        :Call:
            >>> repo.lfc_init()
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
        :Versions:
            * 2022-12-28 ``@ddalle``: v1.0
            * 2023-10-25 ``@ddalle``: v1.1; better double-call behavior
        """
        # Only activate in working repo
        self.assert_working()
        # Directly form LFC dir and config file
        lfcdir = os.path.join(self.gitdir, ".lfc")
        # Config file for LFC
        fcfg = os.path.join(lfcdir, "config")
        # .gitignore file for LFC
        fgitignore = os.path.join(lfcdir, ".gitignore")
        # Create LFC dir if needed
        self.make_cachedir()
        # Write .lfc/.gitignore
        if not os.path.isfile(fgitignore):
            with open(fgitignore, 'w') as fp:
                # Write three files to ignore
                fp.write("/cache\n")
                fp.write("/config.local\n")
                fp.write("/tmp")
        # Write *fcfg*
        if not os.path.isfile(fcfg):
            with open(fcfg, 'w') as fp:
                # Write initial config
                fp.write("[core]\n")
                fp.write("autostage = true\n")
                fp.write("check_update = false\n")
        # Add the new files
        self._add(fcfg)
        self._add(fgitignore)

   # --- LFC config ---
    def lfc_config_get(self, fullopt: str) -> str:
        r"""Get an option from the large file client configuration

        :Call:
            >>> val = repo.lfc_config_get(section, opt)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *fullopt*: :class:`str`
                Name of LFC config section
            *opt*: :class:`str`
                Option in LFC config section to query
        :Outputs:
            *val*: :class:`str`
                Raw value of LCF config option
        :Raises:
            * :class:`GitutilsKeyError` if either *section* or *opt* is
              missing from the LFC config
        :Versions:
            * 2022-12-27 ``@ddalle``: v1.0
        """
        # Read LFC config
        config = self.make_lfc_config()
        # Split into section
        section, opt = self._split_fullopt(fullopt)
        # Check if section is present
        if section not in config.sections():
            raise GitutilsKeyError(
                "No large file config section '%s'" % section)
        # Check if option is present
        if opt not in config.options(section):
            raise GitutilsKeyError(
                "No option '%s' in large file config section '%s'" %
                (opt, section))
        # Get it
        return config.get(section, opt)

    def _split_fullopt(self, fullopt: str):
        r"""Split full option name into section and option"""
        # Check for a dot
        if "." not in fullopt:
            raise GitutilsValueError(
                "Option spec '%s' must contain '.'" % fullopt)
        # Split into exactly two parts
        return fullopt.split(".", 1)

    def _print_lfc_config_get(self, fullopt: str):
        # Get option
        val = self.lfc_config_get(fullopt)
        # Print it
        print(val)

    def lfc_config_set(self, fullopt: str, val):
        r"""Set an LFC configuration setting

        :Call:
            >>> repo.lfc_config_set(section, opt, val)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *fullopt*: :class:`str`
                Name of LFC config section
            *val*: :class:`object`
                Value to set (converted to :class:`str`)
        :Versions:
            * 2022-12-28 ``@ddalle``: v1.0
        """
        # Read LFC config
        config = self.make_lfc_config()
        # Split full option into section and option name
        section, opt = self._split_fullopt(fullopt)
        # Check if section is present
        if section not in config.sections():
            raise GitutilsKeyError(
                "No large file config section '%s'" % section)
        # Convert to string
        txt = self._to_ini(val)
        # Save it
        config.set(section, opt, txt)
        # Write it
        self.write_lfc_config(config)

   # --- LFC remote config ---
    def list_lfc_remotes(self) -> list:
        r"""List all large file remote names

        :Call:
            >>> remotenames = repo.list_lfc_remotes()
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
        :Outputs:
            *remotenames*: :class:`list`\ [:class:`str`]
        :Versions:
            * 2022-12-25 ``@ddalle``: v1.0
        """
        # Get config
        config = self.make_lfc_config()
        # Initialize output
        remotenames = []
        # Loop through sections
        for section in config.sections():
            # Check if it matches pattern
            match = REGEX_LFC_REMOTE_SECTION.fullmatch(section)
            # If it matches, save the name
            if match:
                remotenames.append(match.group("name"))
        # Output
        return remotenames

    def _print_lfc_remotes(self):
        # Loop through remotes
        for remote in self.list_lfc_remotes():
            # Get URL
            url = self.get_lfc_remote_url(remote)
            # Print
            print("%-8s: %s" % (remote, url))

    def rm_lfc_remote(self, remote: str):
        r"""Remove a large file client remote, if possible

        :Call:
            >>> repo.rm_lfc_remote(remote)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *remote*: :class:`str`
                Name of large file remote
        :Outputs:
            *remotenames*: :class:`list`\ [:class:`str`]
        :Versions:
            * 2022-12-27 ``@ddalle``: v1.0
        """
        # Get config
        config = self.make_lfc_config()
        # Section name
        section = '\'remote "%s"\'' % remote
        # Check if section is present
        if section not in config.sections():
            raise GitutilsKeyError("No LFC remote named '%s'" % remote)
        # Delete it
        config.remove_section(section)
        # Write
        self.write_lfc_config(config)

    def set_lfc_remote(self, remote: str, url: str, **kw):
        r"""Add or set URL of an LFC remote

        :Call:
            >>> repo.set_lfc_remote(remote, url, **kw)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *remote*: :class:`str`
                Name of LFC remote
            *url*: :class:`str`
                Path for LCF remote to point to
            *d*, *default*: ``True`` | {``False``}
                Also set *remote* as the default LFC remote
        :Versions:
            * 2022-12-25 ``@ddalle``: v1.0
        """
        # Get comfig
        config = self.make_lfc_config()
        # Section name
        section = '\'remote "%s"\'' % remote
        # Add section if necessary
        if section not in config.sections():
            config.add_section(section)
        # Set URL
        config.set(section, "url", url)
        # Check for default
        if kw.get("d", kw.get("default", "")):
            # Set core.remote
            config.set("core", "remote", remote)
        # Write
        self.write_lfc_config(config)

    def get_lfc_remote_url(self, remote=None):
        r"""Get URL for a large file client remote

        :Call:
            >>> url = repo.get_lfc_remote_url(remote)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *remote*: {``None``} | :class:`str`
                Optional explicit remote name
        :Outputs:
            *url*: :class:`str`
                Path to LFC remote, either local or SSH
        :Versions:
            * 2022-12-22 ``@ddalle``: v1.0
            * 2023-03-17 ``@ddalle``: v1.1; remote -> local *url* check
        """
        # Resolve default
        remote = self.resolve_lfc_remote_name(remote)
        # Read settings
        config = self.make_lfc_config()
        # Section name
        section = '\'remote "%s"\'' % remote
        # Test if defined
        if section not in config._sections:
            raise GitutilsKeyError(
                "No settings for LFC remote '%s'" % remote)
        # Get path
        url = config._sections[section].get("url")
        # Ensure it worked
        assert_isinstance(url, str, "URL for LFC remote %s" % remote)
        # Check for relative URL or remote host that matches current
        if not url.startswith("ssh://") and not os.path.isabs(url):
            # Remote given relative to the .lfc folder (not absolute)
            lfcdir = self.get_lfcdir()
            # This won't work on a bare repo
            url = os.path.join(lfcdir, url)
            # Get rid of ../..
            url = os.path.realpath(url)
        elif url.startswith("ssh://"):
            # Get target host to see if it matches the current one
            parts = url.split("/")
            host = parts[2]
            # Check for match
            if socket.gethostname().startswith(host):
                # Use local path (absolute)
                local_url = "/" + "/".join(parts[3:])
                local_par = os.path.dirname(local_url)
                # Test if it exists
                if os.path.isdir(local_url) or os.path.isdir(local_par):
                    # Use local remote instead of remote
                    url = local_url
        # Output
        return url.rstrip("/")

    def resolve_lfc_remote_name(self, remote=None):
        r"""Resolve default LFC remote, if necessary

        :Call:
            >>> remotename = repo.resolve_lfc_remote_name(remote)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *remote*: {``None``} | :class:`str`
                Optional explicit remote name
        :Outputs:
            *remotename*: :class:`str`
                Either *remote* or LFC setting for *core.remote*
        :Versions:
            * 2022-12-22 ``@ddalle``: v1.0
        """
        # If *remote* given, no checks
        if remote:
            return remote
        # Read settings
        config = self.make_lfc_config()
        # Get default remote
        return config.get("core", "remote")

    def make_lfc_config(self):
        r"""Read large file client config file, or access current

        :Call:
            >>> config = repo.make_lfc_config()
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
        :Outputs:
            *config*: :class:`configparser.ConfigParser`
                Python interface to LFC configuration
        :Versions:
            * 2022-12-22 ``@ddalle``: v1.0
        """
        # Get config
        config = self.lfc_config
        # Check if already read
        if isinstance(config, ConfigParser):
            # On bare repos, nothing else to check
            if self.bare:
                return config
            # Path to config file
            fcfg = self.get_lfc_configfile()
            # Check time stamp
            if self._t_lfc_config >= os.path.getmtime(fcfg):
                # Config is up-to-date (or better)
                return config
        # Config is either empty or older than the config file
        config = self.read_lfc_config()
        # Save it
        self._t_lfc_config = time.time()
        self.lfc_config = config
        # Output
        return config

    def read_lfc_config(self):
        r"""Read large file client config file, even on bare repo

        :Call:
            >>> config = repo.read_lfc_config()
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
        :Outputs:
            *config*: :class:`configparser.ConfigParser`
                Python interface to LFC configuration
        :Versions:
            * 2022-12-22 ``@ddalle``: v1.0
        """
        # Get path to config file
        fcfg = self.get_lfc_configfile()
        # Initialize config itnerface
        config = ConfigParser()
        # Check if bare
        if self.bare:
            # Get contents of file
            contents = self.show(fcfg)
            # Read those as a string
            config.read_string(contents.decode("utf-8"))
        else:
            # Check for file
            assert_isfile(fcfg)
            # Read file
            config.read(fcfg)
        # Output
        return config

    def write_lfc_config(self, config):
        r"""Write current large file configuration to file

        :Call:
            >>> repo.write_lfc_config(config)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *config*: :class:`configparser.ConfigParser`
                Python interface to LFC configuration
        :Versions:
            * 2022-12-27 ``@ddalle``: v1.0
        """
        # Do nothing on bare repo
        self.assert_working()
        # Get path to config file
        fcfg = self.get_lfc_configfile()
        # Write
        with open(fcfg, "w") as fp:
            config.write(fp)

    def get_lfc_configfile(self, ext=None):
        r"""Get name of LFC configuration file

        In a bare repo, this will return the path relative to the root,
        e.g. ``".lfc/config"``. In a working repo, it will return the
        absolute path.

        :Call:
            >>> fcfg = repo.get_lfc_configfile(ext=None)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *ext*: {``None``} | ``".lfc"`` | ``".dvc"``
                Optional manual override for file extension
        :Outputs:
            *fcfg*: :class:`str`
                Name of large file client configuration
        :Versions:
            * 2022-12-20 ``@ddalle``: v1.0
            * 2022-12-28 ``@ddalle``: v1.1; optional *ext* input
        """
        # Get extension
        if ext is None:
            ext = self.get_lfc_ext()
        # Check if bare
        if self.bare:
            # Path relative to root
            return os.path.join(ext, "config")
        else:
            # Return absolute path
            return os.path.join(self.gitdir, ext, "config")


def _get_remote_host(fremote):
    # Split all the slashes except first two
    parts = fremote[6:].split("/")
    # Split host and remaining portions
    host = parts[0]
    path = "/" + "/".join(parts[1:])
    # Combine
    return host, path
