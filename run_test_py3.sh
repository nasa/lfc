#!/bin/bash

# Get package name (type manually if necessary)
PKG=lfc

# Run tests
python3 -m pytest \
    --junitxml=test/junit.xml \
    --cov=$PKG \
    --cov-report html:test/htmlcov 

# Save result
IERR=$?

# Create Sphinx docs of results
python3 -m testutils write-rst

# Return pytest's status
exit $IERR

