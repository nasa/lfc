#!/bin/bash

# Get package name (type manually if necessary)
PKG=$(python3 -c "from setuptools import find_packages
print(find_packages()[0])")

# Run tests
python3 -m pytest \
    --pdb \
    --report-log=test/log.json \
    --cov=$PKG \
    --cov-report html:test/htmlcov 

# Clear out .gitignore for coverage report
rm test/htmlcov/.gitignore

