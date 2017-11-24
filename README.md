## DFTimewolf

A framework for orchestrating forensic collection, processing and data export.

dfTimewolf consists of collectors, processors and exporters (modules) that pass
data on to one another. How modules are orchestrated is defined in predefined
"recipes".

<p align="center">
  <img src="https://cloud.githubusercontent.com/assets/13300571/17257013/0065185c-5575-11e6-957d-5e662ec78d8c.png" width="300"/>
</p>


### Quick how-to

dfTimewolf is typically run by specifying a recipe name and any argument the
recipe defines. For example:

```
$ dftimewolf local_plaso /tmp/path1,/tmp/path2 --incident_id 12345
```
This will launch the local_plaso against `path1` and `path2` in `/tmp`.
`--incident_id` is used by Timesketch as a sketch description.

Details on a recipe can be obtained using the standard python help flags:

```
$ dftimewolf -h
usage: dftimewolf [-h]
                             {local_plaso,grr_artifact_hosts,...}

optional arguments:
  -h, --help            show this help message and exit

Available recipes:
  "dftimewolf <recipe_name> help" for help on a specific recipe

  {local_plaso,grr_artifact_hosts,...}
```

To get more help on a recipe's specific flags, specify a recipe name before
the `-h` flag:

```
$ dftimewolf local_plaso -h
usage: dftimewolf local_plaso [-h] [--incident_id INCIDENT_ID] paths

DFTimewolf recipe for collecting data from the filesystem. - Collectors collect
from a path in the FS - Processes them with a local install of plaso - Exports
them to a new Timesketch sketch

positional arguments:
  paths                 Paths to process

optional arguments:
  -h, --help            show this help message and exit
  --incident_id INCIDENT_ID
                        Incident ID (used for Timesketch description)
```


### Recipes

Recipes are pre-defined sequences of collectors, processors and exporters. They
can be minimally configured to take specific command-line arguments or flags.

* grr_artifact_hosts - Launches an ArtifactCollectorFlow on specific hosts,
  processes them with Plaso, and exports results to Timesketch.
* grr_hunt_artifacts - Launches a fleet-wide GRR Artifact hunt and returns a
  hunt ID.
* grr_hunt_file - Launches a fleet-wide GRR FileFinder hunt and returns a
  hunt ID.
* grr_huntresults_plaso_timesketch - Fetches hunt results given a Hunt ID,
  processes them with Plaso, sends results to Timesketch
* local_plaso - Launches log2timeline on a local file path and exports results
  to timesketch.

### Existing Modules

#### Collectors

* FilesystemCollector - a simple collector that just passes a local path on to
the processors.
* GRR hunts - launch and fetch results from fleet-wide GRR hunts.
 * GRRHuntArtifactCollector - Launches a fleet-wide GRR ArtifactCollectorFlow
 * GRRHuntFileCollector - Launches a fleet-wide GRR FileFinder
 * GRRHuntDownloader - Downloads results from a GRR hunt.
* GRR targeted collectors - launch and fetch flows on targeted hosts.
 * GRRArtifactCollector - Launches a GRR ArtifactCollectorFlow on specific
   hosts.
 * GRRFileCollector - Launches a FileFinder flow on specific hosts.
 * GRRFlowCollector - Downloads the results of an arbitrary flow.

As a general rule, GRRHuntArtifactCollector and GRRHuntFileCollector collectors
are asynchronous. They will create a hunt and return the hunt ID that should be
used with GRRHuntDownloader once the hunt is complete. GRRArtifactCollector,
GRRFileCollector and GRRFlowCollector will wait for results before exiting.

#### processors

* LocalPlasoProcessor - processes a list of file paths with a local plaso
(log2timeline.py) instance.

#### Exporters

* TimesketchExporter - exports the result of a processor to a remote Timesketch
instance.
* LocalFileSystemExporter - exports the results of a processor to the local
filesystem.



### Configuration

DFTimewolf has a minimal configuration file. DFTimewolf looks for a
`config.json` file in its directory and loads parameters from there.

See `/dftimewolf/config.json` for an example configuration file and
edit as you see fit.
