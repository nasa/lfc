#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Standard library
from setuptools import setup, find_packages


# Local software hub
hub = "git+ssh://pfe/nobackupp16/ddalle/cape/hub/src/"

# Create the build
setup(
    name="lfc",
    packages=find_packages(),
    install_requires=[
        "PyYAML",
    ],
    description="Git add-on for large file control",
    entry_points={
        "console_scripts": [
            "lfc=lfc.cli:main"
        ]
    },
    version="1.0.0b6")

