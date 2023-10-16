#!/bin/bash
set -e

PYTHONPATH="/app"

echo "Running entrypoint.sh"
echo "PYTHONPATH: $PYTHONPATH"
echo "arg passed: $1"

# Pass all args to dftimewolf
if [[ "$1" =~ 'dftimewolf' ]]; then
    poetry run dftimewolf "$@"
fi

# Run a custom command on container start
exec "$@"
