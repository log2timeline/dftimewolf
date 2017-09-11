#!/usr/bin/env bash
set -e

# Dependencies for running dftimewolf, alphabetized, one per line.
# This should not include packages only required for testing or development.
PYTHON2_DEPENDENCIES="python-bs4
                      python-requests
                      python-tz";

PYTHON2_DEPENDENCIES="python-bs4
                      python-requests
                      python-tz";

sudo add-apt-repository ppa:gift/dev -y
sudo apt-get update -q
sudo apt-get install -y ${PYTHON2_DEPENDENCIES}
sudo apt-get install -y ${PYTHON2_DEPENDENCIES}
