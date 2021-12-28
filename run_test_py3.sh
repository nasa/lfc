#!/bin/bash

PKG=$(python3 -c "from setuptools import find_packages
print(find_packages()[0])")

python3 -m pytest \
    --pdb \
    --junitxml=test/junit.xml \
    --report-log=test/log.json \
    --cov=$PKG \
    --cov-report html:test/htmlcov 
