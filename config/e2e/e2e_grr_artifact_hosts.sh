#!/usr/bin/env bash
#
# This file is meant to be used by e2e test runners

# Exit on error.
set -e
sudo sysctl -w vm.max_map_count=262144
bash ./config/e2e/jenkins_dftimewolf_install.sh include-docker include-grr include-timesketch include-plaso
export DFTIMEWOLF_NO_RAINBOW=true
export DFTIMEWOLF_DEBUG=true
PYTHONPATH=. poetry run python tests/test_dftimewolf.py
PYTHONPATH=. poetry run python dftimewolf/cli/dftimewolf_recipes.py --help
PYTHONPATH=. poetry run python dftimewolf/cli/dftimewolf_recipes.py grr_artifact_ts $NODE_NAME test --artifacts LinuxAuditLogs --timesketch_endpoint http://localhost:80/ --timesketch_username test --timesketch_password test
