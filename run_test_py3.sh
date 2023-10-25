#!/bin/bash

# Get package name (type manually if necessary)
PKG=lfc

# Run tests
python3 -m pytest \
    --junitxml=test/junit.xml \
    --cov=$PKG \
    --cov-report html:test/htmlcov 

