#!/usr/bin/env bash
set -e

# Dependencies for running dftimewolf, alphabetized, one per line.
# This should not include packages only required for testing or development.
PYTHON2_DEPENDENCIES="python-certifi
                      python-chardet
                      python-idna
                      python-requests
                      python-tz
                      python-urllib3";

# Additional dependencies for running dftimewolf tests, alphabetized,
# one per line.
TEST_DEPENDENCIES="python-mock";

# Additional dependencies for doing dftimewolf development, alphabetized,
# one per line.
DEVELOPMENT_DEPENDENCIES="python-sphinx
                          pylint";

sudo add-apt-repository ppa:gift/dev -y
sudo apt-get update -q
sudo apt-get install -y ${PYTHON2_DEPENDENCIES}

if [[ "$*" =~ "include-development" ]]; then
    sudo apt-get install -y ${DEVELOPMENT_DEPENDENCIES}
fi

if [[ "$*" =~ "include-test" ]]; then
    sudo apt-get install -y ${TEST_DEPENDENCIES}
fi
