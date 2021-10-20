# User manual

dfTimewolf ships with _recipes_, which are essentially instructions on how to
launch and chain modules.

```eval_rst
.. toctree::

    user-manual
```

## Listing all recipes

Since you won't know all the recipe names off the top of your head, start with:

```code
$ dftimewolf -h
[2020-10-06 14:29:42,111] [dftimewolf          ] INFO     Logging to stdout and /tmp/dftimewolf.log
[2020-10-06 14:29:42,111] [dftimewolf          ] DEBUG    Recipe data path: /Users/tomchop/code/dftimewolf/data
[2020-10-06 14:29:42,112] [dftimewolf          ] DEBUG    Configuration loaded from: /Users/tomchop/code/dftimewolf/data/config.json
usage: dftimewolf [-h]
                  {aws_forensics,gce_disk_export,gcp_forensics,gcp_logging_cloudaudit_ts,gcp_logging_cloudsql_ts,gcp_logging_collect,gcp_logging_gce_instance_ts,gcp_logging_gce_ts,gcp_turbinia_disk_copy_ts,gcp_turbinia_ts,grr_artifact_grep,grr_artifact_ts,grr_files_collect,grr_flow_collect,grr_hunt_artifacts,grr_hunt_file,grr_huntresults_ts,plaso_ts,upload_ts,upload_turbinia,upload_web_ts,vt_pcap_ts}
                  ...

Available recipes:

 aws_forensics                      Copies a volume from an AWS account to an analysis VM.
 aws_logging_collect                Collects logs from an AWS account and dumps on the filesystem.
 azure_forensics                    Copies a disk from an Azure account to an analysis VM.
 gce_disk_export                    Export disk image from a GCP project to Google Cloud Storage.
 gcp_forensics                      Copies disk from a GCP project to an analysis VM.
 gcp_logging_cloudaudit_ts          Collects GCP logs from a project and exports them to Timesketch.
 gcp_logging_cloudsql_ts            Collects GCP logs from Cloud SQL instances for a project and exports them to Timesketch.
 gcp_logging_collect                Collects logs from a GCP project and dumps on the filesystem.
 gcp_logging_gce_instance_ts        GCP Instance Cloud Audit to Timesketch
 gcp_logging_gce_ts                 Loads GCP Cloud Audit Logs for GCE into Timesketch
 gcp_turbinia_disk_copy_ts          Imports a remote GCP persistent disk, processes it with Turbinia and sends results to Timesketch.
 gcp_turbinia_ts                    Processes an existing GCP persistent disk in the Turbinia project and sends results to Timesketch.
 gcp_turbinia_ts_threaded           Processes existing GCP persistent disks in the Turbinia project and sends results to Timesketch.
 grr_artifact_grep                  Fetches ForensicArtifacts from GRR hosts and runs grep with a list of keywords on them.
 grr_artifact_ts                    Fetches default artifacts from a list of GRR hosts, processes them with plaso, and sends the results to Timesketch.
 grr_files_collect                  Fetches specific files from one or more GRR hosts.
 grr_flow_collect                   Download GRR flows. Download a GRR flow's results to the local filesystem.
 grr_hunt_artifacts                 Starts a GRR hunt for the default set of artifacts.
 grr_hunt_file                      Starts a GRR hunt for a list of files.
 grr_huntresults_ts                 Fetches the findings of a GRR hunt, processes them with plaso, and sends the results to Timesketch.
 grr_timeline_ts                    Runs a TimelineFlow on a set of GRR hosts, processes results with plaso, and sends the timeline to Timesketch
 plaso_ts                           Processes a list of file paths using plaso and sends results to Timesketch.
 upload_ts                          Uploads a CSV or Plaso file to Timesketch.
 upload_turbinia                    Uploads arbitrary files to Turbinia.
 upload_web_ts                      Uploads a CSV/JSONL or Plaso file to Timesketch.
 vt_evtx                            Fetches the EVTX from VirusTotal sandbox run for a specific hash.
 vt_evtx_ts                         Fetches the EVTX from VirusTotal sandbox run for a specific hash and upload it to Timesketch.
 vt_pcap                            Fetches the PCAP from VirusTotal sandbox run for a specific hash
 workspace_logging_collect          Collects Workspace Audit logs and dumps them on the filesystem.
 workspace_meet_ts                  Collects Meet records and adds to Timesketch
 workspace_user_activity_ts         Collects records and adds to Timesketch
 workspace_user_drive_ts            Collects Drive records and adds to Timesketch
 workspace_user_login_ts            Collects login records and adds to Timesketch

positional arguments:
  {aws_forensics,gce_disk_export,gcp_forensics,gcp_logging_cloudaudit_ts,gcp_logging_cloudsql_ts,gcp_logging_collect,gcp_logging_gce_instance_ts,gcp_logging_gce_ts,gcp_turbinia_disk_copy_ts,gcp_turbinia_ts,grr_artifact_grep,grr_artifact_ts,grr_files_collect,grr_flow_collect,grr_hunt_artifacts,grr_hunt_file,grr_huntresults_ts,plaso_ts,upload_ts,upload_turbinia,upload_web_ts,vt_pcap_ts}

optional arguments:
  -h, --help            show this help message and exit
```

## Get detailed help for a specific recipe

To get more details on a specific recipe:

```code
$ dftimewolf grr_artifact_hosts -h
[2020-10-06 14:31:40,553] [dftimewolf          ] INFO     Logging to stdout and /tmp/dftimewolf.log
[2020-10-06 14:31:40,553] [dftimewolf          ] DEBUG    Recipe data path: /Users/tomchop/code/dftimewolf/data
[2020-10-06 14:31:40,553] [dftimewolf          ] DEBUG    Configuration loaded from: /Users/tomchop/code/dftimewolf/data/config.json
usage: dftimewolf_recipes.py plaso_ts [-h] [--incident_id INCIDENT_ID]
                                      [--sketch_id SKETCH_ID]
                                      [--token_password TOKEN_PASSWORD]
                                      paths

Processes a list of file paths using plaso and sends results to Timesketch.

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
  --token_password TOKEN_PASSWORD
                        Optional custom password to decrypt Timesketch
                        credential file with (default: )
```

### vt_pcap_ts

This recipe will take a list of hashes (md5, sha256...) and check if they are known to Virustotal.
If a hash is known to Virustotal, the recipe will check if there is one or more pcaps available for that hash from a sandbox run.
Each available pcap will be downloaded and parsed. After the parsing, the data will be passed to Timesketch.

Be careful, large pcap files might take a long time to process.

To use this recipe, the user needs to provide an [Virustotal Premium API key](https://developers.virustotal.com/v3.0/reference#public-vs-premium-api) either via argument or in `~/.dftimewolfrc` as `vt_api_key` Each parsed pcap will generate a new timeline in Timesketch in a given sketch.

## Running a recipe

One typically invokes dftimewolf with a recipe name and a few arguments. For
example:

    $ dftimewolf <RECIPE_NAME> arg1 arg2 --optarg1 optvalue1

Given the help output above, you can then use the recipe like this:

    $ dftimewolf grr_artifacts_ts tomchop.greendale.xyz collection_reason

If you only want to collect browser activity:

    $ dftimewolf grr_artifacts_ts tomchop.greendale.xyz collection_reason --artifact_list=BrowserHistory

In the same way, if you want to specify one (or more) approver(s):

    $ dftimewolf grr_artifacts_ts tomchop.greendale.xyz collection_reason --artifact_list=BrowserHistory --approvers=admin
    $ dftimewolf grr_artifacts_ts tomchop.greendale.xyz collection_reason --artifact_list=BrowserHistory --approvers=admin,tomchop

### ~/.dftimewolfrc

If you want to set recipe arguments to specific values without typing them in
the command-line (e.g. your development Timesketch server, or your favorite set
of GRR approvers), you can use a `.dftimewolfrc` file. Just create a
`~/.dftimewolfrc` file containing a JSON dump of parameters to replace:

    $ cat ~/.dftimewolfrc
    {
      "approvers": "approver@greendale.xyz",
      "ts_endpoint": "http://timesketch.greendale.xyz/"
    }

This will set your `ts_endpoint` and `approvers` parameters for all subsequent
dftimewolf runs. You can still override these settings for one-shot usages by
manually specifying the argument in the command-line.

## Remove colorization

dfTimewolf output will not be colorized if the environment variable ```DFTIMEWOLF_NO_RAINBOW``` is set.
