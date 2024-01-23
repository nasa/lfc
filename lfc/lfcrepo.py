r"""
``lfcrepo``: Interface to git repos with large-file control
==================================================================

This module provides the :class:`LFCRepo`, which provides tools for
interacting with Git repositories. This includes actions to hash, store,
and transfer large files tracked with ``lfc``.
"""

# Standard library
import fnmatch
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
from .lfcerror import LFCCheckoutError, LFCValueError
from ._vendor.gitutils._vendor import shellutils
from ._vendor.gitutils.giterror import (
    GitutilsFileNotFoundError,
    GitutilsKeyError,
    GitutilsValueError,
    assert_isinstance,
    assert_isfile,
    trunc8_fname)
from ._vendor.gitutils.gitrepo import (
    GitRepo,
    run_gitdir
)


# Regular expression for LFC remote section names
REGEX_LFC_REMOTE_SECTION = re.compile('\'remote "(?P<name>\\w+)"\'')

# Error codes
IERR_OK = 0
IERR_FILE_NOT_FOUND = 128


# Create new class
class LFCRepo(GitRepo):
    r"""LFC interface to individual repositories

    :Call:
        >>> repo = LFCRepo(where=None)
    :Inputs:
        *where*: {``None``} | :class:`str`
            Location of repo (``None`` -> ``os.getcwd()``)
    """
   # --- Class attributes ---
    # Class attributes
    __slots__ = (
        "bare",
        "gitdir",
        "lfc_config",
        "lfc_portals",
        "_t_lfc_config")

   # --- __dunder__ ---
    def __init__(self, where=None):
        # Parent initializtion
        GitRepo.__init__(self, where)
        # Initialize other slots
        self.lfc_config = None
        self.lfc_portals = {}
        self._t_lfc_config = None

   # --- SSH portal interface ---
    def make_lfc_portal(self, remote=None) -> shellutils.SSHPortal:
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
            * 2023-10-26 ``@ddalle``: v1.1; multiple portals
        """
        # Resolve remote name
        remote = self.resolve_lfc_remote_name(remote)
        # Get current attribute
        portal = self.lfc_portals.get(remote)
        # Exit if already processed
        if portal is not None:
            # Return current portal
            return portal
        # Get remote
        fremote = self.get_lfc_remote_url(remote)
        # Get parts of remote
        host, path = shellutils.identify_host(fremote)
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
        self.lfc_portals[remote] = portal
        # Return it
        return portal

    def close_lfc_portal(self, remote=None):
        r"""Close large file transfer portal, if any

        :Call:
            >>> repo.close_lfc_portal(remote=None)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *remote*: {``None``} | :class:`str`
                Name of remote, or default
        :Versions:
            * 2022-12-20 ``@ddalle``: v1.0
            * 2023-10-26 ``@ddalle``: v1.1; multiple portals
        """
        # Resolve remote name
        remote = self.resolve_lfc_remote_name(remote)
        # Get current portal
        portal = self.lfc_portals.get(remote)
        # Close it
        if portal is not None:
            portal.close()
        # Reset LFC portal
        self.lfc_portals.pop(remote, None)

   # --- LFC replace-DVC ---
    @run_gitdir
    def lfc_replace_dvc(self):
        r"""Fully subsitute local large file control in place of DVC

        This command will move all ``.dvc`` metadata stub files to the
        same name but with ``.lfc`` as the extension. It will also move
        the ``.dvc/`` folder to ``.lfc/`` and remove the ``.dvc/plots/``
        folder and ``.dvcignore`` file.

        If both ``.dvc/`` and ``.lfc/`` exist, this function will merge
        the caches so that any files in ``.dvc/cache/`` are copied into
        ``.lfc/cache/``.

        It does not recompute any hashes as LFC can work with MD-5
        hashes. It does not compute any new ones, but it can still
        utilize the old ones and have the two intermixed.

        :Call:
            >>> repo.lfc_replace_dvc()
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
        :Versions:
            * 2022-12-28 ``@ddalle``: v1.0
            * 2023-03-17 ``@ddalle``: v1.1; delete .dvc/plots first
            * 2023-10-27 ``@ddalle``: v1.2; merge caches
        """
        # Only attempt in working repo
        self.assert_working()
        # Form expected folder names
        flfcdir = os.path.join(self.gitdir, ".lfc")
        fdvcdir = os.path.join(self.gitdir, ".dvc")
        fplotdir = os.path.join(fdvcdir, "plots")
        dvccache = os.path.join(fdvcdir, "cache")
        lfccache = os.path.join(flfcdir, "cache")
        # Check if .dvc/plots folder was there
        if os.path.isdir(fplotdir):
            # Remove it
            self.rm(os.path.join(".dvc", "plots"), r=True)
        # Make sure .dvc exists but not .lfc
        if os.path.isdir(fdvcdir) and not os.path.isdir(flfcdir):
            # Move the folder (using git)
            self.mv(".dvc", ".lfc")
        elif os.path.isdir(dvccache):
            # Combine the caches
            _merge_caches(dvccache, lfccache)
            # Remove anything left in the .dvc/ folder
            shutil.rmtree(fdvcdir)
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

   # --- LFC hooks ---
    def lfc_install_hooks(self, *a, **kw):
        r"""Install full set of git-hooks for this repo

        :Call:
            >>> repo.lfc_install_hooks()
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
        """
        self.lfc_install_post_merge(*a, **kw)
        self.lfc_install_pre_push(*a, **kw)

    def lfc_install_post_merge(self, *a, **kw):
        r"""Install ``post-merge`` hook to auto-pull mode=2 files

        :Call:
            >>> repo.lfc_install_post_merge()
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
        """
        # This should only be run on working repo
        self.assert_working()
        # Get location of configuration dir
        gitdir = self.get_configdir()
        # Location to hooks dir
        hooksdir = os.path.join(gitdir, "hooks")
        # Location to "post-merge" hook
        fhook = os.path.join(hooksdir, "post-merge")
        # Check for existing file
        if os.path.isfile(fhook):
            print("hooks/post-merge hook already exists; aborting")
            return
        # Write file
        with open(fhook, 'w') as fp:
            fp.write("#!/bin/bash\n\n")
            fp.write("lfc auto-pull\n")
        # Get current file's permissions
        fmod = os.stat(fhook).st_mode
        # Make it executable
        fmod = fmod | 0o100
        # Reset it
        os.chmod(fhook, fmod)

    def lfc_install_pre_push(self, *a, **kw):
        r"""Install ``pre-push`` hook to auto-push some files

        :Call:
            >>> repo.lfc_install_pre_push()
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
        """
        # This should only be run on working repo
        self.assert_working()
        # Get location of configuration dir
        gitdir = self.get_configdir()
        # Location to hooks dir
        hooksdir = os.path.join(gitdir, "hooks")
        # Location to "post-merge" hook
        fhook = os.path.join(hooksdir, "pre-push")
        # Check for existing file
        if os.path.isfile(fhook):
            print("hooks/pre-push hook already exists; aborting")
            return
        # Write file
        with open(fhook, 'w') as fp:
            fp.write("#!/bin/bash\n\n")
            fp.write("lfc auto-push\n")
        # Get current file's permissions
        fmod = os.stat(fhook).st_mode
        # Make it executable
        fmod = fmod | 0o100
        # Reset it
        os.chmod(fhook, fmod)

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
        # Get mode
        mode = kw.get("mode", 1)
        # Loop through files
        for fname in fnames:
            # Expand
            fglob = glob.glob(fname)
            # Loop through matches
            for fj in fglob:
                self._lfc_add(fj, mode)

    def lfc_set_mode(self, *fnames, **kw):
        r"""Set LFC mode for one or more files

        :Call:
            >>> repo.lfc_set_mode(*fnames, **kw)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *fnames*: :class:`tuple`\ [:class:`str`]
                Names or wildcard patterns of files to add using LFC
        """
        # Get mode
        mode = kw.get("mode", 1)
        # Loop through files
        for fname in fnames:
            # Expand
            fglob = glob.glob(fname)
            # Loop through matches
            for fj in fglob:
                self._lfc_set_mode(fj, mode)

    def _lfc_set_mode(self, fname: str, mode=1):
        # Only on working repos
        self.assert_working()
        # Validate mode
        _valid8_mode(mode)
        # Get .lfc file name
        flfc = self.genr8_lfc_filename(fname)
        # Open the file
        lfcinfo = self.read_lfc_file(flfc)
        # Set mode
        lfcinfo["mode"] = mode
        # Get stuff
        fhash = lfcinfo.get("sha256", lfcinfo.get("md5"))
        fsize = lfcinfo.get("size")
        fpath = lfcinfo.get("path")
        # Write LFC metadata stub file
        with open(flfc, "w") as fp:
            fp.write("outs:\n")
            fp.write(f"- sha256: {fhash}\n")
            fp.write(f"  size: {fsize}\n")
            fp.write(f"  path: {fpath}\n")
            fp.write(f"  mode: {mode}\n")

    def _lfc_add(self, fname: str, mode=1):
        # Validate mode
        _valid8_mode(mode)
        # Strip .dvc if necessary
        fname = self.genr8_lfc_ofilename(fname)
        flfc = self.genr8_lfc_filename(fname)
        # Check if it's a folder
        if os.path.isdir(fname):
            # Recurse
            for fj in os.listdir(fname):
                # Add individual files
                self._lfc_add(os.path.join(fname, fj))
            # Don't continue with original dir
            return
        # Make sure main file is ignored
        self._ignore(fname)
        # Current terminal width
        twidth = shutil.get_terminal_size().columns
        # Truncate file name
        fname8 = self._trunc8_fname(fname, 20)
        # Check cache status
        if os.path.isfile(flfc) and self._lfc_status(flfc):
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
            fp.write(f"- sha256: {fhash}\n")
            fp.write(f"  size: {fsize}\n")
            fp.write(f"  path: {os.path.basename(fname)}\n")
            fp.write(f"  mode: {mode}\n")
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
            # Truncate file name
            f1 = self._trunc8_fname(fname, 28)
            raise GitutilsFileNotFoundError(f"Can't hash '{f1}'; no such file")
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
        # Select mode to use
        mode = kw.get("mode")
        _valid8n_mode(mode)
        # Verbosity setting
        quiet = kw.get("quiet", kw.get("q", False))
        # Expand file list
        lfcfiles = self.genr8_lfc_glob(*fnames, mode=mode)
        # Loop through files
        for flfc in lfcfiles:
            # Push
            self._lfc_push(flfc, remote, quiet)

    def _lfc_push(self, fname: str, remote=None, quiet=False):
        # Resolve remote name
        remote = self.resolve_lfc_remote_name(remote)
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
        # Split host
        host, _ = shellutils.identify_host(fremote)
        # Check remote/local
        if host is None:
            self._lfc_push_local(fhash, remote, flarge, quiet)
        else:
            self._lfc_push_ssh(fhash, remote, flarge, quiet)

    def _lfc_push_ssh(self, fhash, remote, fname, quiet=False):
        # Get source file
        fsrc = os.path.join(self.get_cachedir(), fhash[:2], fhash[2:])
        # Expand remote
        remote = self.resolve_lfc_remote_name(remote)
        # Get remote location
        fremote = self.get_lfc_remote_url(remote)
        # Get parts of remote
        _, path = shellutils.identify_host(fremote)
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
            # Up-to-date
            if not quiet:
                # Truncate long file name
                f1 = self._trunc8_fname(fname, 6 + len(remote))
                # Status update
                print(f"{f1} [{remote}]")
        else:
            # Upload it
            portal.put(fsrc, ftarg, fprog=fname)

    def _lfc_push_local(self, fhash, remote, fname, quiet=False):
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
        if os.path.isfile(ftarg):
            # Up-to-date
            if not quiet:
                # Truncate long file name
                f1 = self._trunc8_fname(fname, 6 + len(remote))
                # Status update
                print(f"{f1} [{remote}]")
        else:
            # Truncate long file name
            f1 = self._trunc8_fname(fname, len(remote) + 14)
            # Status update
            print(f"{f1} [local -> {remote}]")
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
            *mode*: {``None``} | ``1`` | ``2``
                LFC file mode:
            *f*, *force*: ``True`` | {``False``}
                Delete uncached working file if present
        :Versions:
            * 2022-12-28 ``@ddalle``: v1.0
            * 2023-11-08 ``@ddalle``: v1.1; add *mode*
        """
        # Get remote
        remote = kw.get("remote", kw.get("r"))
        # Get mode
        mode = kw.get("mode")
        # Verbosity setting
        quiet = kw.get("quiet", kw.get("q", False))
        # Overwrite setting
        force = kw.get("force", kw.get("f", False))
        # Expand list of files
        lfcfiles = self.genr8_lfc_glob(*fnames, mode=mode)
        # Loop through matches
        for flfc in lfcfiles:
            # Pull
            self._lfc_pull(flfc, remote, quiet, force)

    def _lfc_pull(self, fname: str, remote=None, quiet=False, force=False):
        # Fetch (download/copy) file to local cache
        ierr = self._lfc_fetch(fname, remote, quiet)
        # Check it out
        if ierr == IERR_OK:
            self._lfc_checkout(fname, force=force)

    def _lfc_fetch(self, fname: str, remote=None, quiet=False):
        # Resolve remote name
        remote = self.resolve_lfc_remote_name(remote)
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
            # Status update
            f1 = self._trunc8_fname(flarge, 17)
            # Status update
            if not quiet:
                print(f"{f1} [local]")
            # Done
            return IERR_OK
        # Get remote location
        fremote = self.get_lfc_remote_url(remote)
        # Split host name and path
        host, _ = shellutils.identify_host(fremote)
        # Check remote/local
        if host is None:
            return self._lfc_fetch_local(fhash, remote, flarge)
        else:
            return self._lfc_fetch_ssh(fhash, remote, flarge)

    def _lfc_fetch_ssh(self, fhash, remote, fname: str):
        # Get remote location
        fremote = self.get_lfc_remote_url(remote)
        # Get parts of remote
        _, path = shellutils.identify_host(fremote)
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
            return IERR_FILE_NOT_FOUND
        # Copy file
        portal.get(fsrc, ftarg, fprog=fname)
        return IERR_OK

    def _lfc_fetch_local(self, fhash, remote, fname: str):
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
            # Truncate long file name
            f1 = self._trunc8_fname(fname, 30)
            # Status update and exit
            print("Remote cache missing file '%s'" % f1)
            return IERR_FILE_NOT_FOUND
        # Truncate long file name
        f1 = self._trunc8_fname(fname, len(remote) + 14)
        # Status update
        print(f"{f1} [{remote} -> local]")
        # Copy file
        shutil.copy(fsrc, ftarg)
        return IERR_OK

   # --- LFC checkout --
    def lfc_checkout(self, fname: str, *fnames, **kw):
        r"""Checkout one or more large files from current ``.lfc`` stub

        :Call:
            >>> repo.lfc_checkout(*fnames, **kw)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *fnames*: :class:`tuple`\ [:class:`str`]
                Names or wildcard patterns of files
            *f*, *force*: ``True`` | {``False``}
                Delete uncached working file if present
        :Versions:
            * 2023-10-24 ``@ddalle``: v1.0
        """
        # Expand list of files
        lfcfiles = self.genr8_lfc_glob(fname, *fnames)
        # Overwrite option
        force = kw.get("f", kw.get("force", False))
        # Loop through files
        for flfc in lfcfiles:
            # Checkout single file
            self._lfc_checkout(flfc, force=force)

    def _lfc_checkout(self, fname: str, force=False):
        # Only appropriate in working repos
        self.assert_working()
        # Strip .lfc if necessary
        fname = self.genr8_lfc_ofilename(fname)
        # Get info
        lfcinfo = self.read_lfc_file(fname)
        # Unpack MD5 hash
        fhash = lfcinfo.get("sha256", lfcinfo.get("md5"))
        # Get path to cache
        cachedir = self.get_cachedir()
        # Get cache file name
        fcache = os.path.join(cachedir, fhash[:2], fhash[2:])
        # Check if file is present in the cache
        if (not force) and (not os.path.isfile(fcache)):
            # Truncate long file name
            f1 = self._trunc8_fname(fname, 32)
            # Raise exception
            raise LFCCheckoutError(
                f"Can't checkout '{f1}'; not in cache")
        # Check status
        up_to_date = self._lfc_status(fname)
        # Exit if file is up-to-date
        if up_to_date:
            return
        # Check for existing file that's not up-to-date
        if os.path.isfile(fname):
            # Calculate hash of existing file
            try:
                hash1 = self.genr8_hash(fname)
            except MemoryError:  # pragma no cover
                # Too big to read; assume up-to-date for simplicity
                return
            # Check if it's the same hash
            up_to_date = (hash1 == fhash)
            # Get path to cached version of existing file
            fhash1 = os.path.join(cachedir, hash1[:2], hash1[2:])
            # Check if file is present
            if not os.path.isfile(fhash1):
                # Truncate file name
                f1 = self._trunc8_fname(fname, 42)
                # Raise exceptoin
                raise LFCCheckoutError(
                    f"Can't checkout '{f1}'; exsiting uncached file")
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
                # Truncate long file name
                f1 = self._trunc8_fname(forig, 20)
                print(f"No git/lfc file '{f1}'")
                return
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
            # Split parts
            host, path = shellutils.identify_host(url)
            # Check if SSH
            if host is None or _check_host(host):
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

    def read_lfc_file(self, fname: str, ref=None, ext=None):
        r"""Read status information from large file stub

        :Call:
            >>> info = repo.read_lfc_file(fname, ref=None, ext=None)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *fname*: :class:`str`
                Name of original file or large file stub
            *ref*: {``None``} | :class:`str`
                Optional git reference (default ``HEAD`` on bare repo)
            *ext*: {``None``} | ``".dvc"`` | ``".lfc"``
                Large file metadata stub file extension
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
        fname = self.genr8_lfc_filename(fname, ext=ext)
        # Check if bare repo
        if self.bare or ref is not None:
            # Make sure the file exists
            if len(self.ls_tree(fname, ref=ref)) == 0:
                f1 = self._trunc8_fname(fname, 20)
                raise GitutilsFileNotFoundError(f"No file '{f1}' in repo")
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

    def read_lfc_mode(self, fname: str, ref=None, ext=None) -> int:
        r"""Read LFC file mode for a tracked file

        :Call:
            >>> mode = repo.read_lfc_mode(fname, ref=None)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *fname*: :class:`str`
                Name of original file or large file stub
            *ref*: {``None``} | :class:`str`
                Optional git reference (default ``HEAD`` on bare repo)
        :Outputs:
            *mode*: ``1`` | ``2``
                LFC file mode:

                * ``1``: Only push/pull file on-demand
                * ``2``: Automatically push/pull most recent version
        :Versions:
            * 2023-11-08 ``@ddalle``: v1.0
        """
        # Read the file
        lfcinfo = self.read_lfc_file(fname, ref=ref, ext=ext)
        # Get mode
        return int(lfcinfo.get("mode", 1))

   # --- LFC search ---
    def find_lfc_files(self, pattern=None, ext=None, mode=None, **kw) -> list:
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
            * 2023-10-26 ``@ddalle``: v2.0
                - use ``ls_tree()`` instead of calling ``git ls-files``
                - works with ``lfc add data/`` or similar

            * 2023-11-08 ``@ddalle``: v2.1; add *mode*
        """
        # Get extension
        if ext is None:
            ext = self.get_lfc_ext()
        # Default: all .lfc files
        default_pattern = f"*{ext}"
        # Apply default pattern
        pat = default_pattern if pattern is None else pattern
        # If pattern does not end with extension, add it
        if not pat.endswith(ext[1:]):
            pat = pat.rstrip(".*") + default_pattern
        # Get all tracked files (relative to CWD if working repo)
        all_files = self.ls_tree(r=True)
        # Include files added but not committed
        if not self.bare:
            # Get status files
            statusdict = self.status()
            # Loop through files; potentially including each one
            for frel in statusdict:
                # Check if file is (a) in PWD and (b) not already found
                if not frel.startswith("..") and (frel not in all_files):
                    all_files.append(frel)
        # Filter against the pattern
        lfcmatches = fnmatch.filter(all_files, pat)
        lfcfiles = []
        # Loop through matches
        for flfc in lfcmatches:
            # Check file mode
            modej = self.read_lfc_mode(flfc, ext=ext)
            # Check if it matches target
            if (mode is None) or (mode == modej):
                lfcfiles.append(flfc)
        # Output
        return lfcfiles

    def genr8_lfc_glob(self, *fnames, mode=None):
        r"""Generate list of ``.lfc`` files matchin one or more pattern

        :Call:
            >>> lfcfiles = repo.genr8_lfc_glob(*fnames, mode=None)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *fnames*: :class:`tuple`\ [:class:`str`]
                List of file name patterns to search for
            *mode*: {``None``} | ``1`` | ``2``
                LFC file mode to search for
        :Outputs:
            *lfcfiles*: :class:`list`\ [:class:`str`]
                List of matching ``.lfc`` files
        """
        # Default to (None,) if no inputs
        patterns = (None,) if len(fnames) == 0 else fnames
        # Initialize glob
        fglob = []
        # Loop through patterns
        for pat in patterns:
            # Find matches
            fglobj = self.find_lfc_files(pat, mode=mode)
            # Append to overall list
            for fj in fglobj:
                # Check for duplicates from previous *pat*
                if fj not in fglob:
                    fglob.append(fj)
        # Output
        return fglob

   # --- LFC status ---
    def _lfc_status(self, flfc: str) -> bool:
        r"""Check if the LFC status of a large file is up-to-odate

        :Call:
            >>> status = repo._lfc_status(flfc)
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
            * 2023-10-30 ``@ddalle``: v2.0
                - recompute hash instead of comparing mod times
                - allow input to be original file name (not .lfc)
                - more generic
        """
        # Get metadata file names
        flfc = self.genr8_lfc_filename(flfc)
        # Check if there's no .lfc file
        if not os.path.isfile(flfc):
            return False
        # Get info
        lfcinfo = self.read_lfc_file(flfc)
        # Get file name
        fname = lfcinfo.get("path")
        # Check if file present
        if not os.path.isfile(fname):
            return False
        # Get anticipated file size
        lfcsize = lfcinfo.get("size", 0)
        # Get file infos
        finfo = os.stat(fname)
        # Check for matching size
        if finfo.st_size != lfcsize:
            return False
        # Check if file is in cache
        if not self._check_cache(lfcinfo):
            return False
        # Gemerate hash
        try:
            hash1 = self.genr8_hash(fname)
        except MemoryError:  # pragma no cover
            # File is too large
            return True
        # Hahs from info file
        hashinfo = lfcinfo.get("sha256", lfcinfo.get("md5"))
        # Check if file is the same
        return hash1 == hashinfo

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
    def genr8_lfc_filename(self, fname: str, ext=None) -> str:
        r"""Produce name of large file stub

        :Call:
            >>> flfc = repo.genr8_lfc_filename(fname)
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
            *fname*: :class:`str`
                Name of file, either original file or metadata stub
            *ext*: {``None``} | ``".dvc"`` | ``".lfc"``
                Large file metadata stub file extension
        :Outputs:
            *flfc*: :class:`str`
                Name of large file metadata stub file
        :Versions:
            * 2022-12-21 ``@ddalle``: v1.0
        """
        # Get working extension
        if ext is None:
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
        return trunc8_fname(fname, n)

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
    def lfc_config_get(self, fullopt: str, vdef=None) -> str:
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
            *vdef*: {``None``} | :class:`object`
                Default value
        :Outputs:
            *val*: :class:`str`
                Raw value of LCF config option
        :Raises:
            * :class:`GitutilsKeyError` if either *section* or *opt* is
              missing from the LFC config (unless *vdef* is set)
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
            # Check for default
            if vdef is not None:
                return vdef
            # Otherwise report an error
            raise GitutilsKeyError(
                "No option '%s' in large file config section '%s'" %
                (opt, section))
        # Get it
        return self._from_ini(config.get(section, opt))

    def get_lfc_autopull(self) -> int:
        r"""Get the LFC mode for auto-pull

        * ``0``: do not auto-pull files
        * ``1``: auto-pull all files
        * ``2``: auto-pull all mode-2 files (default)

        :Call:
            >>> mode = repo.get_lfc_autopull()
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
        :Outputs:
            *mode*: :class:`int`
                Files of LCF files to automatically push
        """
        return int(self.lfc_config_get("core.autopull", vdef=2))

    def get_lfc_autopush(self) -> int:
        r"""Get the LFC mode for auto-push

        * ``0``: do not auto-push files
        * ``1``: auto-push all files
        * ``2``: auto-push all mode-2 files (default)

        :Call:
            >>> mode = repo.get_lfc_autopush()
        :Inputs:
            *repo*: :class:`GitRepo`
                Interface to git repository
        :Outputs:
            *mode*: :class:`int`
                Files of LCF files to automatically push
        """
        return int(self.lfc_config_get("core.autopush", vdef=2))

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
        # Split into parts
        host, path = shellutils.identify_host(url)
        # LFC remotes always stored as POSIX; convert to system path
        if host is None:
            path = path.replace('/', os.sep)
        # Check for relative URL or remote host that matches current
        if host is None and not os.path.isabs(path):
            # This won't work on a bare repo
            path = os.path.join(self.gitdir, path)
            # Get rid of ../..
            url = os.path.realpath(path)
        elif host is not None and _check_host(host):
            # Apparent SSH, but host is current machine
            url = path.replace("/", os.sep)
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


def _check_host(host: str) -> bool:
    return socket.gethostname().startswith(host)


def _merge_caches(dvccache: str, lfccache: str):
    # Create new cache
    if not os.path.isdir(lfccache):
        os.mkdir(lfccache)
    # List the dvc cache
    cachesubs = os.listdir(dvccache)
    # Loop through those subs
    for p1 in cachesubs:
        # Construct .dvc/cache/{p1} and .lfc/cache/{p1}
        dvcpart = os.path.join(dvccache, p1)
        lfcpart = os.path.join(lfccache, p1)
        # Skip if it's a file (not a folder)
        if not os.path.isdir(dvcpart):
            continue
        # Check if destination exists
        if os.path.isdir(lfcpart):
            # In that case, loop through the contents of *p1* in .dvc
            for p2 in os.listdir(dvcpart):
                # Construct full paths
                p2dvc = os.path.join(dvcpart, p2)
                p2lfc = os.path.join(lfcpart, p2)
                # Move file if not already in .lfc/cache/
                if (not os.path.isfile(p2lfc)) and os.path.isfile(p2dvc):
                    # Status update
                    f1 = f"{p1}/{p2[:8]}"
                    print("{.dvc -> .lfc}/cache/" + f1)
                    # Move the file
                    os.rename(p2dvc, p2lfc)
        else:
            # Status update
            print("{.dvc -> .lfc}/cache/" + p1)
            # Move the whole folder if no conflict w/ .lfc/cache
            os.rename(dvcpart, lfcpart)


def _valid8n_mode(mode=None):
    # Allow mode=None
    if mode is None:
        return
    # Otherwise only 1 | 2
    _valid8_mode(mode)


def _valid8_mode(mode=1):
    # Check type
    assert_isinstance(mode, int, "LFC file mode")
    # Check value
    if mode not in (1, 2):
        raise LFCValueError(
            f"Unknown LFC file mode {mode}; accepted values are: 1 | 2")
