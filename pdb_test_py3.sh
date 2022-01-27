#!/bin/bash

# Get package name (type manually if necessary)
PKG=$(python3 -c "from setuptools import find_packages
print(find_packages()[0])")

# Run tests
python3 -m pytest \
    --pdb \
    --junitxml=test/junit.xml \
    --cov=$PKG \
    --cov-report html:test/htmlcov 

# Save result
IERR=$?

# Allow tracking of coverage report
rm test/htmlcov/.gitignore

# Create Sphinx docs of results
python3 -m testutils write-rst

# Return pytest's status
exit $IERR

