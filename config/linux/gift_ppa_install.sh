#!/usr/bin/env bash
set -e

# Dependencies for running dftimewolf, alphabetized, one per line.
# This should not include packages only required for testing or development.
PYTHON2_DEPENDENCIES="python-bs4
                      python-certifi
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

# Pending resolution of https://github.com/log2timeline/l2tdevtools/issues/233.
sudo apt-get install -y python-pip
sudo pip install grr-api-client

if [[ "$*" =~ "include-development" ]]; then
    sudo apt-get install -y ${DEVELOPMENT_DEPENDENCIES}
fi

if [[ "$*" =~ "include-test" ]]; then
    sudo apt-get install -y ${TEST_DEPENDENCIES}
fi

if [[ "$*" =~ "include-docker" ]]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
    sudo add-apt-repository \
       "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
       $(lsb_release -cs) \
       stable"
    sudo apt-get update -q
    sudo apt-get install -y docker-ce
    curl -L https://github.com/docker/compose/releases/download/1.21.0/docker-compose-$(uname -s)-$(uname -m) -o docker-compose
    sudo cp docker-compose /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

if [[ "$*" =~ "include-grr" ]]; then
    # Start the GRR server container.
    mkdir ~/grr-docker
    sudo docker run \
      --name grr-server -v ~/grr-docker/db:/var/grr-datastore \
      -v ~/grr-docker/logs:/var/log \
      -e EXTERNAL_HOSTNAME="localhost" \
      -e ADMIN_PASSWORD="demo" \
      --ulimit nofile=1048576:1048576 \
      -p 0.0.0.0:8000:8000 -p 0.0.0.0:8080:8080 \
      -d grrdocker/grr:v3.2.2.0 grr

    # Wait for GRR to initialize.
    /bin/sleep 120

    # Install the client.
    sudo docker cp grr-server:/usr/share/grr-server/executables/installers .
    sudo dpkg -i installers/*amd64.deb
fi

if [[ "$*" =~ "include-timesketch" ]]; then
    # Start the Timesketch server container.
     TIMESKETCH_PASSWORD="dftimewolf_test"
     git clone https://github.com/google/timesketch.git
     cd timesketch/docker
     sudo docker-compose up
fi

if [[ "$*" =~ "include-plaso" ]]; then
    sudo apt-get -y install plaso-tools
fi