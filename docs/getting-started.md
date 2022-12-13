# Getting started

## Installation

Ideally you'll want to install dftimewolf in its own virtual environment.

```
git clone https://github.com/log2timeline/dftimewolf.git && cd dftimewolf
pip install poetry
poetry install
```

<div class="admonition note">
  <p class="first admonition-title">Attention</p>
  <p class="last">If you want to leverage other modules such as log2timeline, you'll have
  to install them separately and make them available in your virtual environment.</p>
</div>

If you want to run dftimewolf from any other directory, activate the virtualenv
by doing `poetry shell` in the main dfTimewolf directory.

## Quick how-to

dfTimewolf is typically run by specifying a recipe name and any arguments the
recipe defines. For example:

```code
dftimewolf plaso_ts /tmp/path1,/tmp/path2 --incident_id 12345
```

This will launch the `plaso_ts` recipe against `path1` and `path2` in `/tmp`.
In this recipe `--incident_id` is used by Timesketch as a sketch description.

Details on a recipe can be obtained using the standard python help flags:

```code
$ dftimewolf -h
[2020-10-06 14:29:42,111] [dftimewolf          ] INFO     Logging to stdout and /tmp/dftimewolf.log
[2020-10-06 14:29:42,111] [dftimewolf          ] DEBUG    Recipe data path: /Users/tomchop/code/dftimewolf/data
[2020-10-06 14:29:42,112] [dftimewolf          ] DEBUG    Configuration loaded from: /Users/tomchop/code/dftimewolf/data/config.json
usage: dftimewolf [-h]
                             {aws_forensics,gce_disk_export,gcp_forensics,gcp_logging_cloudaudit_ts,gcp_logging_cloudsql_ts,...}

Available recipes:

 aws_forensics                      Copies a volume from an AWS account to an analysis VM.
 gce_disk_export                    Export disk image from a GCP project to Google Cloud Storage.
 gcp_forensics                      Copies disk from a GCP project to an analysis VM.
 gcp_logging_cloudaudit_ts          Collects GCP logs from a project and exports them to Timesketch.
 [...]

positional arguments:
  {aws_forensics,gce_disk_export,gcp_forensics,gcp_logging_cloudaudit_ts,...}

optional arguments:
  -h, --help            show this help message and exit
```

To get details on an individual recipe, call the recipe with the `-h` flag.

```code
$ dftimewolf gcp_forensics -h
[...]
usage: dftimewolf gcp_forensics [-h] [--instance INSTANCE]
                                           [--disks DISKS] [--all_disks]
                                           [--analysis_project_name ANALYSIS_PROJECT_NAME]
                                           [--boot_disk_size BOOT_DISK_SIZE]
                                           [--boot_disk_type BOOT_DISK_TYPE]
                                           [--zone ZONE]
                                           remote_project_name incident_id

Copies a disk from a project to another, creates an analysis VM, and attaches the copied disk to it.

positional arguments:
  remote_project_name   Name of the project containing the instance / disks to
                        copy
  incident_id           Incident ID to label the VM with.

optional arguments:
  -h, --help            show this help message and exit
  --instance INSTANCE   Name of the instance to analyze. (default: None)
  --disks DISKS         Comma-separated list of disks to copy. (default: None)
  --all_disks           Copy all disks in the designated instance. Overrides
                        disk_names if specified (default: False)
  --analysis_project_name ANALYSIS_PROJECT_NAME
                        Name of the project where the analysis VM will be
                        created (default: None)
  --boot_disk_size BOOT_DISK_SIZE
                        The size of the analysis VM boot disk (in GB)
                        (default: 50.0)
  --boot_disk_type BOOT_DISK_TYPE
                        Disk type to use [pd-standard, pd-ssd] (default: pd-
                        standard)
  --zone ZONE           The GCP zone where the Analysis VM and copied disks
                        will be created (default: us-central1-f)
```
