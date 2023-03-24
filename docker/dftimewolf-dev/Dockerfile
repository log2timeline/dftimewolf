# Use the official Docker Hub Ubuntu 20.04 base image
FROM ubuntu:22.04


RUN apt update && apt install -y --no-install-recommends \
    python3-dev \
    python3-pip \
    build-essential \
    libmagic1 \
    git

RUN pip install --upgrade pip
RUN pip install poetry

# /app is defined as the mount in the docker-compose.yaml file and should
# point to the root of the dftimewolf install
ADD . /app
WORKDIR /app

RUN poetry install

# Copy the entrypoint script into the container
COPY ./docker/dftimewolf-dev/docker-entrypoint.sh /
RUN chmod a+x /docker-entrypoint.sh

# Load the entrypoint script to be run later
ENTRYPOINT ["/docker-entrypoint.sh"]
