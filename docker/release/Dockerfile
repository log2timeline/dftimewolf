# Use the official Docker Hub Ubuntu 22.04 base image
FROM ubuntu:22.04

RUN apt-get update
RUN apt-get install -y --no-install-recommends \
    software-properties-common \
    gpg-agent

RUN add-apt-repository ppa:gift/stable -y
RUN apt-get update
RUN apt-get -y install plaso-tools --no-install-recommends

RUN apt install -y --no-install-recommends \
    python3-dev \
    python3-pip \
    libmagic1 \
    ssh \
    git \
    && apt-get clean && rm -rf /var/cache/apt/* /var/lib/apt/lists/*

RUN pip install --upgrade pip
RUN pip install poetry
RUN git clone https://github.com/tomchop/dftimewolf.git /app && cd /app && git checkout docker --
WORKDIR /app
RUN poetry install --with dev

# replace by git clone, or pip install, when script stabilizes
ADD . .

# Copy the entrypoint script into the container
COPY ./docker/release/docker-entrypoint.sh /
RUN chmod a+x /docker-entrypoint.sh

RUN PYBIN=$(poetry env info --executable)

# Load the entrypoint script to be run later
ENTRYPOINT ["/docker-entrypoint.sh"]
