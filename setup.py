#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Standard library
from setuptools import setup, find_packages


# Local software hub
hub = "git+ssh://pfe/nobackupnfs1/ddalle/cape/hub/src/"

# List of packages
pkgs = find_packages()
pkgs.remove("lfc.clidoc")

# Create the build
setup(
    name="lfc",
    packages=pkgs,
    install_requires=[
        "PyYAML",
        "numpy",
    ],
    description="Git add-on for large file control",
    entry_points={
        "console_scripts": [
            "lfc=lfc.cli:main",
            "lfc-add=lfc.cli:lfc_add",
            "lfc-auto-pull=lfc.cli:lfc_autopull",
            "lfc-auto-push=lfc.cli:lfc_autopush",
            "lfc-checkout=lfc.cli:lfc_checkout",
            "lfc-clone=lfc.cli:lfc_clone",
            "lfc-config=lfc.cli:lfc_config",
            "lfc-init=lfc.cli:lfc_init",
            "lfc-install-hooks=lfc.cli:lfc_install_hooks",
            "lfc-ls-files=lfc.cli:lfc_ls_files",
            "lfc-pull=lfc.cli:lfc_pull",
            "lfc-purge=lfc.cli:lfc_purge",
            "lfc-push=lfc.cli:lfc_push",
            "lfc-remote=lfc.cli:lfc_remote",
            "lfc-replace-dev=lfc.cli:lfc_replace_dvc",
            "lfc-set-mode=lfc.cli:lfc_set_mode",
            "lfc-show=lfc.cli:lfc_show",
        ]
    },
    version="1.1.1")

