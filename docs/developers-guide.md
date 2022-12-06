# Developer's guide

This page gives a few hints on how to develop new recipes and modules for
dftimewolf. Start with the [architecture](architecture.md) page if you haven't
read it already.

## Installation

To be able to develop you need a local installation of dfTimewolf. To install it locally, a venv is recommended. We use poetry:

```bash
pip install poetry
poetry install
```

Now you are ready to run dfTimewolf in your local environment:

```bash
poetry run dftimewolf -h
```

## Docker container

We also provide a dev Docker container that you can use to install dftimewolf's
dependencies in.

```bash
cd docker/dev
docker-compose run --rm dftw tests
```

It will pick up changes from your current working directory, so tests will run
with the version of the code present on your filesystem. See `docker/dev/README.md`
for more details.

## Code review

As for other Log2Timeline projects, all contributions to dfTimewolf undergo code
review. The process is documented
[here](https://github.com/log2timeline/l2tdocs/blob/main/process/Code%20review%20process.md).

## Code style

dfTimewolf follows the
[Log2Timeline style guide](https://github.com/log2timeline/l2tdocs/blob/main/process/Style-guide.md).

## Creating a recipe

If you're not satisfied with the way modules are chained, or default arguments
that are passed to some of the recipes, then you can create your own. See
[existing recipes](https://github.com/log2timeline/dftimewolf/tree/main/data/recipes)
for simple examples like
[plaso_ts](https://github.com/log2timeline/dftimewolf/blob/main/data/recipes/plaso_ts.json).
Details on recipe keys are given [here](architecture.md#recipes).

### Recipe location

A new recipe needs to be added to `data/recipes` as a JSON file.

### Recipe arguments

Recipes launch Modules with a given set of arguments. Arguments can be specified
in different ways:

- Hardcoded values in the recipe's Python code
- `@` parameters that are dynamically changed, either:
  - Through a `~/.dftimewolfrc` file
  - Through the command line

Parameters are declared for each Module in a recipe's `recipe` variable in the
form of `@parameter` placeholders. How these are populated is then specified in
the `args` variable right after, as a list of
`(argument, help_text, default_value)` tuples that will be passed to `argparse`.
For example, the public version of the
[grr_artifact_hosts.py](https://github.com/log2timeline/dftimewolf/blob/main/data/recipes/gcp_forensics.json)
recipe specifies arguments in the following way:

    "args": [
      ["remote_project_name", "Name of the project containing the instance / disks to copy ", null],
      ["incident_id", "Incident ID to label the VM with.", null],
      ["--instance", "Name of the instance to analyze.", null],
      ["--disks", "Comma-separated list of disks to copy.", null],
      ["--all_disks", "Copy all disks in the designated instance. Overrides disk_names if specified", false],
      ["--analysis_project_name", "Name of the project where the analysis VM will be created", null],
      ["--boot_disk_size", "The size of the analysis VM boot disk (in GB)", 50.0],
      ["--boot_disk_type", "Disk type to use [pd-standard, pd-ssd]", "pd-standard"],
      ["--zone", "The GCP zone where the Analysis VM and copied disks will be created", "us-central1-f"]
    ]

`remote_project_name` and `incident_id` are positional arguments - they **must** be provided
through the command line. `instance`, `disks`, `all_disks`, and all other arguments starting with `--` are optional. If they are not specified through the command line, the default argument will be used. `null` will be translated to a Python `None`, and `false` will be the python `False` boolean.

## Modules

If dftimewolf lacks the actual processing logic, you need to create a new
module. If you can achieve your goal in Python, then you can include it in
dfTimewolf. "There is no learning curve™".

Check out the [Module architecture](architecture#modules) and read up on simple
existing modules such as the
[LocalPlasoProcessor](https://github.com/log2timeline/dftimewolf/blob/main/dftimewolf/lib/processors/localplaso.py)
module for an example of simple Module.

Additionally, a guide on implementing a module exists [here](module-writing-basics)

### Register a new module

There are two locations to register new modules:

- registering it at the end of the module file
- adding it to the big dict where in the main entry point script `dftimewolf_recipes.py`

## Run tests

It is recommended to run tests locally to discover issues early in the development lifecycle.

```bash
pip install poetry
poetry install
poetry run python -m unittest discover -s tests -p '*.py'
```
