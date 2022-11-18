#!/bin/bash
set -e

PYTHONPATH="/app"

# Run the container the default way
if [[ "$1" =~ 'envshell' ]]; then
    poetry shell
fi

if [[ "$1" =~ 'tests' ]]; then
    poetry run python -m unittest discover -s tests -p '*.py'
fi

# Run a custom command on container start
exec "$@"
