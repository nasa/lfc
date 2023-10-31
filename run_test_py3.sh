#!/bin/bash

# Get package name (type manually if necessary)
PKG=lfc

# Run tests
python3 -m pytest \
    "test/10_lfc/01_lfcrepo" \
    "test/10_lfc/03_lfccli" \
    --junitxml=test/junit.xml \
    --cov=$PKG \
    --pdb \
    --cov-report html:test/htmlcov 

