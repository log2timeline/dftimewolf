# Development Docker container

This compose file is meant to be used to develop dfTimewolf using a contained
environment. It's useful if e.g. you don't want to pollute your system with
various Python version installs or packages.

## Building the image

```bash
cd docker/dev
docker compose build
```

Then to get it running:

```
docker compose up -d
```

## Running tests

Make sure you have Docker installed (sudoless) and run:

```bash
cd docker/dev
docker-compose run --rm dftw tests
```

This will build the dfTimewolf Docker image using `docker/dev/Dockerfile`, and
run the dfTimewolf tests against the version of the code that lives on the host
filesystem.

The `docker-compose` scripts mounts the top-level directory of the dfTimewolf
code repo on `/app` in the container, and tests are run from there.

## Shell access

```bash
$ cd docker/dev
$ docker-compose run --rm dftw envshell
(dftimewolf-py3.10) root@f3a2cc77dc3e:/app# python -m unittest discover -s tests -p '*.py'
```

## vscode

- Follow the steps at [building the image](#building-the-image)
- Open VScode, and optionally connect to your remote host
- In the command pallette, choose "attach to running container", and pick the
  container that you just created.

You might have to select your Python interpreter for all tests to be
discoverable.
