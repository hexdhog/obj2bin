#!/usr/bin/env bash
rm -rf dist
./setup.py sdist bdist_wheel
twine upload dist/*
