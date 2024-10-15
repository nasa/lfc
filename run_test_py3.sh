#!/bin/bash

# Get package name (type manually if necessary)
PKG=lfc

# Run tests
python3 -m coverage run \
    --omit="lfc/clidoc/*.py" \
    -m pytest \
    --junitxml=test/junit.xml \
    --cov=$PKG \
    --pdb \
    --cov-report html:test/htmlcov 

