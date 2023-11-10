#!/bin/bash

# Get package name (type manually if necessary)
PKG=lfc

# Run tests
python3 -m pytest \
    test/10_lfc \
    --junitxml=test/junit.xml \
    --cov=$PKG \
    --pdb \
    --cov-report html:test/htmlcov 

