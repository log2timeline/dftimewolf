# Development Docker container

This compose file is meant to be used to develop dftimewolf using a contained environment.
It's useful if e.g. you don't want to pollute your system with various Python version installs or packages.

## Running tests

Make sure you have Docker installed (sudoless) and run:

```bash
cd docker/dev
docker-compose run --rm dftw tests
```

This will build the dfTimewolf Docker image using `docker/dev/Dockerfile`, and
run the dfTimewolf tests aginst the verison of the code that lives on the host
filesystem.

The `docker-compose` scripts mounts the top-level directory of the dftimewofl
code repo on `/app` in the container, and tests are run from there.
