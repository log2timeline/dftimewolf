#!/usr/bin/env bash
mkdir ~/grr-docker

docker run \
  --name sqlitedb -v ~/grr-docker/db:/var/grr-datastore \
  --name logs -v ~/grr-docker/logs:/var/log \
  -e EXTERNAL_HOSTNAME="localhost" \
  -e ADMIN_PASSWORD="demo" \
  --ulimit nofile=1048576:1048576 \
  -p 0.0.0.0:8000:8000 -p 0.0.0.0:8080:8080 \
  -d grrdocker/grr:latest grr

# Need to grab container name here

docker cp {container name} /usr/share/grr-server/executables/installers .

dpkg -i installers/*amd64.deb
