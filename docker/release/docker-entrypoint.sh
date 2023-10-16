#!/bin/bash
set -e

PYTHONPATH="/app"

# Pass all args to dftimewolf
if [[ "$1" =~ 'dftimewolf' ]]; then
    # poetry run is a bit slower than using the virtualenv directly
    $PYBIN -m dftimewolf.cli.dftimewolf_recipes "${@:2}"
fi

# Run a custom command on container start
exec "$@"
