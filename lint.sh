#!/usr/bin/env bash
echo "#### ruff"
ruff check --config ./ruff.toml .
echo "#### mypy"
mypy --show-column-numbers --config-file ./mypy.ini .
