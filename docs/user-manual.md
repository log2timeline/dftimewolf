# User manual

dfTimewolf ships with *recipes*, which are essentially instructions on how to
launch and chain modules.

```eval_rst
.. toctree::

    user-manual
```
## Listing all recipes

Since you won't know all the recipe names off the top of your head, start with:

```
$ dftimewolf -h
usage: dftimewolf [-h]
                  {grr_huntresults_plaso_timesketch,local_plaso,timesketch_upload,grr_artifact_hosts,grr_hunt_artifacts,grr_flow_download,grr_hunt_file}
                  ...

Available recipes:

 grr_artifact_hosts                 Fetches default artifacts from a list of GRR hosts, processes them with plaso, and sends the results to Timesketch.
 grr_flow_download                  Downloads the contents of a specific GRR flow to the filesystem.
 grr_hunt_artifacts                 Starts a GRR hunt for the default set of artifacts.
 grr_hunt_file                      Starts a GRR hunt for a list of files.
 grr_huntresults_plaso_timesketch   Fetches the findings of a GRR hunt, processes them with plaso, and sends the results to Timesketch.
 local_plaso                        Processes a list of file paths using plaso and sends results to Timesketch.
 timesketch_upload                  Uploads a .plaso file to Timesketch.

positional arguments:
  {grr_huntresults_plaso_timesketch,local_plaso,timesketch_upload,grr_artifact_hosts,grr_hunt_artifacts,grr_flow_download,grr_hunt_file}

optional arguments:
  -h, --help            show this help message and exit
```

## Get detailed help for a specific recipe

To get more details on a specific recipe:

    $ dftimewolf grr_artifact_hosts -h
    usage: dftimewolf grr_artifact_hosts [-h] [--artifacts ARTIFACTS]
                                     [--extra_artifacts EXTRA_ARTIFACTS]
                                     [--use_tsk USE_TSK]
                                     [--approvers APPROVERS]
                                     [--sketch_id SKETCH_ID]
                                     [--incident_id INCIDENT_ID]
                                     [--grr_server_url GRR_SERVER_URL]
                                     hosts reason

    Collect artifacts from hosts using GRR.

    - Collect a predefined list of artifacts from hosts using GRR
    - Process them with a local install of plaso
    - Export them to a Timesketch sketch

    positional arguments:
    hosts                 Comma-separated list of hosts to process
    reason                Reason for collection

    optional arguments:
    -h, --help            show this help message and exit
    --artifacts ARTIFACTS
                        Comma-separated list of artifacts to fetch (override
                        default artifacts) (default: None)
    --extra_artifacts EXTRA_ARTIFACTS
                        Comma-separated list of artifacts to append to the
                        default artifact list (default: None)
    --use_tsk USE_TSK     Use TSK to fetch artifacts (default: False)
    --approvers APPROVERS
                        Emails for GRR approval request (default: None)
    --sketch_id SKETCH_ID
                        Sketch to which the timeline should be added (default:
                        None)
    --incident_id INCIDENT_ID
                        Incident ID (used for Timesketch description)
                        (default: None)
    --grr_server_url GRR_SERVER_URL
                        GRR endpoint (default: http://localhost:8000/)


## Running a recipe

One typically invokes dftimewolf with a recipe name and a few arguments. For
example:

    $ dftimewolf <RECIPE_NAME> arg1 arg2 --optarg1 optvalue1

Given the help output above, you can then use the recipe like this:

    $ dftimewolf grr_artifact_hosts tomchop.greendale.edu collection_reason

If you only want to collect browser activity:

    $ dftimewolf grr_artifact_hosts tomchop.greendale.edu collection_reason --artifact_list=BrowserHistory

In the same way, if you want to specify one (or more) approver(s):

    $ dftimewolf grr_artifact_hosts tomchop.greendale.edu collection_reason --artifact_list=BrowserHistory --approvers=admin
    $ dftimewolf grr_artifact_hosts tomchop.greendale.edu collection_reason --artifact_list=BrowserHistory --approvers=admin,tomchop

### ~/.dftimewolfrc

If you want to set recipe arguments to specific values without typing them in
the command-line (e.g. your development Timesketch server, or your favorite set
of GRR approvers), you can use a `.dftimewolfrc` file. Just create a
`~/.dftimewolfrc` file containing a JSON dump of parameters to replace:

    $ cat ~/.dftimewolfrc
    {
      "approvers": "approver@greendale.edu",
      "timesketch_endpoint": "http://timesketch.greendale.edu/"
    }

This will set your `timesketch_endpoint` and `approvers` parameters for all
subsequent dftimewolf runs. You can still override these settings for one-shot
usages by manually specifying the argument in the command-line.
