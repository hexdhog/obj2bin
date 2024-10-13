#!/usr/bin/env python3

from pathlib import Path
from setuptools import setup
from obj2bin.__version__ import __version__

directory = Path(__file__).resolve().parent
with Path.open(directory / "README.md", encoding="utf-8") as f:
  long_description = f.read()

setup(
  name="obj2bin",
  version=__version__,
  description="A simple object serialization library",
  author="hexdhog",
  license="MIT",
  long_description=long_description,
  long_description_content_type="text/markdown",
  packages = ["obj2bin"],
  classifiers=[
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License"
  ],
  python_requires=">=3.7",
  extras_require={
    "linting": [
      "mypy",
      "ruff"
    ]
  },
  include_package_data=True
)
