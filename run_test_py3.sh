#!/bin/bash

python3 -m pytest \
    --junitxml=test/junit.xml \
    --report-log=test/log.json \
    --cov=mypkg \
    --cov-report html:doc/_build/html/cov
