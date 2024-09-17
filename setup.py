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
            "git-lfc-clone=lfc.lfcclone:main",
        ]
    },
    version="1.0.0")

