# Getting started

## Installation

Ideally you'll want to install dftimewolf in its own virtual environment. We
leverage `pipenv` for that.

```
$ pip install pipenv
$ git clone https://github.com/log2timeline/dftimewolf.git && cd dftimewolf
$ pipenv install -e .
```

<div class="admonition note">
  <p class="first admonition-title">Attention</p>
  <p class="last">If you want to leverage other modules such as log2timeline, you'll have
  to install them separately and make them available in your virtual environment.</p>
</div>

Then use `pipenv shell` to activate your freshly created virtual environment.
You can then invoke the `dftimewolf` command from any directory.

You can still use `python setup.py install` or `pip install -e .` if you'd rather
install dftimewolf this way.


## Quick how-to

dfTimewolf is typically run by specifying a recipe name and any arguments the
recipe defines. For example:

```
$ dftimewolf local_plaso /tmp/path1,/tmp/path2 --incident_id 12345
```
This will launch the local_plaso recipe against `path1` and `path2` in `/tmp`. In this
recipe `--incident_id` is used by Timesketch as a sketch description.

Details on a recipe can be obtained using the standard python help flags:

```
$ dftimewolf -h      
usage: dftimewolf [-h]
                  {grr_huntresults_plaso_timesketch,local_plaso,...}

Available recipes:

 local_plaso                        Processes a list of file paths using plaso and sends results to Timesketch.

positional arguments:
  {grr_huntresults_plaso_timesketch,local_plaso,...}

optional arguments:
  -h, --help            show this help message and exit
```

To get more help on a recipe's specific flags, specify a recipe name before
the `-h` flag:

```
$ dftimewolf local_plaso -h
usage: dftimewolf local_plaso [-h] [--incident_id INCIDENT_ID]
                              [--sketch_id SKETCH_ID]
                              paths

Analyze local file paths with plaso and send results to Timesketch.

- Collectors collect from a path in the FS
- Processes them with a local install of plaso
- Exports them to a new Timesketch sketch

positional arguments:
  paths                 Paths to process

optional arguments:
  -h, --help            show this help message and exit
  --incident_id INCIDENT_ID
                        Incident ID (used for Timesketch description)
                        (default: None)
  --sketch_id SKETCH_ID
                        Sketch to which the timeline should be added (default:
                        None)

```
