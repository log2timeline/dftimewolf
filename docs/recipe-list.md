
# Recipe list

This is an auto-generated list of dfTimewolf recipes.

To regenerate this list, from the repository root, run:

```
pipenv install --dev
python docs/generate_recipe_doc.py data/recipes
```

---
## `aws_disk_to_gcp`

Copies EBS volumes from within AWS, and transfers them to GCP.

**Details:**

Copies EBS volumes from within AWS by pushing them to an AWS S3 bucket. The S3 bucket is then copied to a Google Cloud Storage bucket, from which a GCP Disk Image and fnially a GCP Persistend Disk are created. This operation happens in the cloud and doesn't touch the local workstation on which the recipe is run.

**CLI parameters:**

- `aws_region` *(default: None)*: AWS region containing the EBS volumes.
- `gcp_zone` *(default: None)*: Destination GCP zone in which to create the disks.
- `volumes` *(default: None)*: Comma separated list of EBS volume IDs (e.g. vol-xxxxxxxx).
- `aws_bucket` *(default: None)*: AWS bucket for image storage.
- `gcp_bucket` *(default: None)*: GCP bucket for image storage.
- `--subnet` *(default: None)*: AWS subnet to copy instances from, required if there is no default subnet in the volume region.
- `--gcp_project` *(default: None)*: Destination GCP project.
- `--aws_profile` *(default: None)*: Source AWS profile.
- `--incident_id` *(default: None)*: Incident ID (used for Timesketch description).
- `--run_all_jobs` *(default: False)*: Run all Turbinia processing jobs instead of a faster subset.
- `--sketch_id` *(default: None)*: Timesketch sketch to which the timeline should be added.
- `--token_password` *(default: '')*: Optional custom password to decrypt Timesketch credential file with.
- `--wait_for_timelines` *(default: True)*: Whether to wait for Timesketch to finish processing all timelines.


Modules: `AWSVolumeSnapshotCollector`, `AWSSnapshotS3CopyCollector`, `S3ToGCSCopy`, `GCSToGCEImage`, `GCEDiskFromImage`

**Module graph**

![aws_disk_to_gcp](/_static/graphviz/aws_disk_to_gcp.png)

----

## `aws_forensics`

Copies a volume from an AWS account to an analysis VM.

**Details:**

Copies a volume from an AWS account, creates an analysis VM in AWS (with a startup script containing installation instructions for basic forensics tooling), and attaches the copied volume to it.

**CLI parameters:**

- `remote_profile_name` *(default: None)*: Name of the AWS profile pointing to the AWS account where the volume(s) exist(s).
- `remote_zone` *(default: None)*: The AWS zone in which the source volume(s) exist(s).
- `incident_id` *(default: None)*: Incident ID to label the VM with.
- `--instance_id` *(default: None)*: Instance ID of the instance to analyze.
- `--volume_ids` *(default: None)*: Comma-separated list of volume IDs to copy.
- `--all_volumes` *(default: False)*: Copy all volumes in the designated instance. Overrides volume_ids if specified.
- `--boot_volume_size` *(default: 50)*: The size of the analysis VM boot volume (in GB).
- `--analysis_zone` *(default: None)*: The AWS zone in which to create the VM.
- `--analysis_profile_name` *(default: None)*: Name of the AWS profile to use when creating the analysis VM.


Modules: `AWSCollector`

**Module graph**

![aws_forensics](/_static/graphviz/aws_forensics.png)

----

## `aws_logging_collect`

Collects logs from an AWS account and dumps the results to the filesystem.

**Details:**

Collects logs from an AWS account using a specified query filter and date ranges, and dumps them on the filesystem.

**CLI parameters:**

- `zone` *(default: None)*: Default availability zone for API queries.
- `--profile_name` *(default: 'default')*: Name of the AWS profile to collect logs from.
- `--query_filter` *(default: None)*: Filter expression to use to query logs.
- `--start_time` *(default: None)*: Start time for the query.
- `--end_time` *(default: None)*: End time for the query.


Modules: `AWSLogsCollector`

**Module graph**

![aws_logging_collect](/_static/graphviz/aws_logging_collect.png)

----

## `aws_turbinia_ts`

Copies EBS volumes from within AWS, transfers them to GCP, analyses with Turbinia and exports the results to Timesketch.

**Details:**

Copies EBS volumes from within AWS, uses buckets and cloud-to-cloud operations to transfer the data to GCP. Once in GCP, a persistend disk is created and a job is added to the Turbinia queue to start analysis. The resulting Plaso file is then exported to Timesketch.

**CLI parameters:**

- `aws_region` *(default: None)*: AWS region containing the EBS volumes.
- `gcp_zone` *(default: None)*: Destination GCP zone in which to create the disks.
- `volumes` *(default: None)*: Comma separated list of EBS volume IDs (e.g. vol-xxxxxxxx).
- `aws_bucket` *(default: None)*: AWS bucket for image storage.
- `gcp_bucket` *(default: None)*: GCP bucket for image storage.
- `--subnet` *(default: None)*: AWS subnet to copy instances from, required if there is no default subnet in the volume region.
- `--gcp_project` *(default: None)*: Destination GCP project.
- `--aws_profile` *(default: None)*: Source AWS profile.
- `--incident_id` *(default: None)*: Incident ID (used for Timesketch description).
- `--run_all_jobs` *(default: False)*: Run all Turbinia processing jobs instead of a faster subset.
- `--sketch_id` *(default: None)*: Timesketch sketch to which the timeline should be added.
- `--token_password` *(default: '')*: Optional custom password to decrypt Timesketch credential file with.
- `--turbinia_zone` *(default: 'us-central1-f')*: Zone Turbinia is located in
- `--wait_for_timelines` *(default: True)*: Whether to wait for Timesketch to finish processing all timelines.


Modules: `AWSVolumeSnapshotCollector`, `AWSSnapshotS3CopyCollector`, `S3ToGCSCopy`, `GCSToGCEImage`, `GCEDiskFromImage`, `TurbiniaGCPProcessorThreaded`, `TimesketchExporterThreaded`

**Module graph**

![aws_turbinia_ts](/_static/graphviz/aws_turbinia_ts.png)

----

## `azure_forensics`

Copies a disk from an Azure account to an analysis VM.

**Details:**

Copies a disk from an Azure account, creates an analysis VM in Azure (with a startup script containing installation instructions for basic forensics tooling), and attaches the copied disk to it.

**CLI parameters:**

- `remote_profile_name` *(default: None)*: Name of the Azure profile pointing to the Azure account where the disk(s) exist(s).
- `analysis_resource_group_name` *(default: None)*: The Azure resource group name in which to create the VM.
- `incident_id` *(default: None)*: Incident ID to label the VM with.
- `ssh_public_key` *(default: None)*: A SSH public key string to add to the VM (e.g. `ssh-rsa AAAAB3NzaC1y...`).
- `--instance_name` *(default: None)*: Instance name of the instance to analyze.
- `--disk_names` *(default: None)*: Comma-separated list of disk names to copy.
- `--all_disks` *(default: False)*: Copy all disks in the designated instance. Overrides `disk_names` if specified.
- `--boot_disk_size` *(default: 50)*: The size of the analysis VM's boot disk (in GB).
- `--analysis_region` *(default: None)*: The Azure region in which to create the VM.
- `--analysis_profile_name` *(default: None)*: Name of the Azure profile to use when creating the analysis VM.


Modules: `AzureCollector`

**Module graph**

![azure_forensics](/_static/graphviz/azure_forensics.png)

----

## `bigquery_collect`

Collects results from BigQuery and dumps them on the filesystem.

**Details:**

Collects results from BigQuery in a GCP project and dumps them in JSONL on the local filesystem.

**CLI parameters:**

- `project_name` *(default: None)*: Name of GCP project to collect logs from.
- `query` *(default: None)*: Query to execute.
- `description` *(default: None)*: Human-readable description of the query.


Modules: `BigQueryCollector`

**Module graph**

![bigquery_collect](/_static/graphviz/bigquery_collect.png)

----

## `bigquery_ts`

Collects results from BigQuery and uploads them to Timesketch.

**Details:**

Collects results from BigQuery in JSONL form, dumps them to the filesystem, and uploads them to Timesketch.

**CLI parameters:**

- `project_name` *(default: None)*: Name of GCP project to collect logs from.
- `query` *(default: None)*: Query to execute.
- `description` *(default: None)*: Human-readable description of the query.
- `--incident_id` *(default: None)*: Incident ID (used for Timesketch description).
- `--sketch_id` *(default: None)*: Timesketch sketch to which the timeline should be added.
- `--token_password` *(default: '')*: Optional custom password to decrypt Timesketch credential file with.
- `--wait_for_timelines` *(default: True)*: Whether to wait for Timesketch to finish processing all timelines.


Modules: `BigQueryCollector`, `TimesketchExporter`

**Module graph**

![bigquery_ts](/_static/graphviz/bigquery_ts.png)

----

## `gce_disk_export`

Export a disk image from a GCP project to a Google Cloud Storage bucket.

**Details:**

Creates a disk image from Google Compute persistent disks, compresses the images, and exports them to Google Cloud Storage.

The exported images names are appended by `.tar.gz.`

As this export happens through a Cloud Build job, the default service account `[PROJECT-NUMBER]@cloudbuild.gserviceaccount.com` in the source or analysis project (if provided) must have the IAM role `[Storage Admin]` on their corresponding project's storage bucket/folder.

**CLI parameters:**

- `source_project_name` *(default: None)*: Source project containing the disk to export.
- `gcs_output_location` *(default: None)*: Google Cloud Storage parent bucket/folder to which to export the image.
- `--analysis_project_name` *(default: None)*: Project where the disk image is created then exported. If not provided, the image is exported to a bucket in the source project.
- `--source_disk_names` *(default: None)*: Comma-separated list of disk names to export. If not provided, disks attached to `remote_instance_name` will be used.
- `--remote_instance_name` *(default: None)*: Instance in source project to export its disks. If not provided, `disk_names` will be used.
- `--all_disks` *(default: False)*: If True, copy all disks attached to the `remote_instance_name` instance. If False and `remote_instance_name` is provided, it will select the instance's boot disk.
- `--exported_image_name` *(default: None)*: Name of the output file, must comply with `^[A-Za-z0-9-]*$` and `'.tar.gz'` will be appended to the name. If not provided or if more than one disk is selected, the exported image will be named `exported-image-{TIMESTAMP('%Y%m%d%H%M%S')}`.


Modules: `GoogleCloudDiskExport`

**Module graph**

![gce_disk_export](/_static/graphviz/gce_disk_export.png)

----

## `gcp_forensics`

Copies disk from a GCP project to an analysis VM.

**Details:**

Copies a persistend disk from a GCP project to another, creates an analysis VM (with a startup script containing installation instructions for basic forensics tooling) in the destiantion project, and attaches the copied GCP persistend disk to it.

**CLI parameters:**

- `remote_project_name` *(default: None)*: Name of the project containing the instance / disks to copy.
- `--analysis_project_name` *(default: None)*: Name of the project where the analysis VM will be created and disks copied to.
- `--incident_id` *(default: None)*: Incident ID to label the VM with.
- `--instance` *(default: None)*: Name of the instance to analyze.
- `--disks` *(default: None)*: Comma-separated list of disks to copy from the source GCP project (if `instance` not provided).
- `--all_disks` *(default: False)*: Copy all disks in the designated instance. Overrides `disk_names` if specified.
- `--stop_instance` *(default: False)*: Stop the designated instance after copying disks.
- `--create_analysis_vm` *(default: True)*: Create an analysis VM in the destination project.
- `--cpu_cores` *(default: 4)*: Number of CPU cores of the analysis VM.
- `--boot_disk_size` *(default: 50.0)*: The size of the analysis VM boot disk (in GB).
- `--boot_disk_type` *(default: 'pd-standard')*: Disk type to use [pd-standard, pd-ssd].
- `--zone` *(default: 'us-central1-f')*: The GCP zone where the Analysis VM and copied disks will be created.


Modules: `GoogleCloudCollector`

**Module graph**

![gcp_forensics](/_static/graphviz/gcp_forensics.png)

----

## `gcp_logging_cloudaudit_ts`

Collects GCP logs from a project and exports them to Timesketch.

**Details:**

Collects GCP logs from a project and exports them to Timesketch. Some light processing is made to translate the logs into something Timesketch can process.

**CLI parameters:**

- `project_name` *(default: None)*: Name of the GCP project to collect logs from.
- `start_date` *(default: None)*: Start date (yyyy-mm-ddTHH:MM:SSZ).
- `end_date` *(default: None)*: End date (yyyy-mm-ddTHH:MM:SSZ).
- `--incident_id` *(default: None)*: Incident ID (used for Timesketch description).
- `--sketch_id` *(default: None)*: Timesketch sketch to which the timeline should be added.
- `--token_password` *(default: '')*: Optional custom password to decrypt Timesketch credential file with.
- `--wait_for_timelines` *(default: True)*: Whether to wait for Timesketch to finish processing all timelines.


Modules: `GCPLogsCollector`, `GCPLoggingTimesketch`, `TimesketchExporter`

**Module graph**

![gcp_logging_cloudaudit_ts](/_static/graphviz/gcp_logging_cloudaudit_ts.png)

----

## `gcp_logging_cloudsql_ts`

Collects GCP related to Cloud SQL instances in a project and exports them to Timesketch.

**Details:**

Collects GCP related to Cloud SQL instances in a project and exports them to Timesketch. Some light processing is made to translate the logs into something Timesketch can process.

**CLI parameters:**

- `project_name` *(default: None)*: Name of the GCP project to collect logs from.
- `start_date` *(default: None)*: Start date (yyyy-mm-ddTHH:MM:SSZ).
- `end_date` *(default: None)*: End date (yyyy-mm-ddTHH:MM:SSZ).
- `--incident_id` *(default: None)*: Incident ID (used for Timesketch description).
- `--sketch_id` *(default: None)*: Timesketch sketch to which the timeline should be added.
- `--token_password` *(default: '')*: Optional custom password to decrypt Timesketch credential file with.
- `--wait_for_timelines` *(default: True)*: Whether to wait for Timesketch to finish processing all timelines.


Modules: `GCPLogsCollector`, `GCPLoggingTimesketch`, `TimesketchExporter`

**Module graph**

![gcp_logging_cloudsql_ts](/_static/graphviz/gcp_logging_cloudsql_ts.png)

----

## `gcp_logging_collect`

Collects logs from a GCP project and dumps on the filesystem (JSON). https://cloud.google.com/logging/docs/view/query-library for example queries.

**Details:**

Collects logs from a GCP project and dumps on the filesystem.

**CLI parameters:**

- `project_name` *(default: None)*: Name of the GCP project to collect logs from.
- `filter_expression` *(default: "resource.type = 'gce_instance'")*: Filter expression to use to query GCP logs. See https://cloud.google.com/logging/docs/view/query-library for examples.


Modules: `GCPLogsCollector`

**Module graph**

![gcp_logging_collect](/_static/graphviz/gcp_logging_collect.png)

----

## `gcp_logging_gce_instance_ts`

GCP Instance Cloud Audit logs to Timesketch

**Details:**

Collects GCP Cloud Audit Logs for a GCE instance and exports them to Timesketch. Some light processing is made to translate the logs into something Timesketch can process.

**CLI parameters:**

- `project_name` *(default: None)*: Name of the GCP project to collect logs from.
- `instance_id` *(default: None)*: Identifier for GCE instance (Instance ID).
- `--incident_id` *(default: None)*: Incident ID (used for Timesketch description).
- `--sketch_id` *(default: None)*: Timesketch sketch to which the timeline should be added.
- `--token_password` *(default: '')*: Optional custom password to decrypt Timesketch credential file with.
- `--wait_for_timelines` *(default: True)*: Whether to wait for Timesketch to finish processing all timelines.


Modules: `GCPLogsCollector`, `GCPLoggingTimesketch`, `TimesketchExporter`

**Module graph**

![gcp_logging_gce_instance_ts](/_static/graphviz/gcp_logging_gce_instance_ts.png)

----

## `gcp_logging_gce_ts`

Loads all GCE Cloud Audit Logs in a GCP project into Timesketch.

**Details:**

Loads all GCE Cloud Audit Logs for all instances in a GCP project into Timesketch. Some light processing is made to translate the logs into something Timesketch can process.

**CLI parameters:**

- `project_name` *(default: None)*: Name of the GCP project to collect logs from.
- `start_date` *(default: None)*: Start date (yyyy-mm-ddTHH:MM:SSZ).
- `end_date` *(default: None)*: End date (yyyy-mm-ddTHH:MM:SSZ).
- `--incident_id` *(default: None)*: Incident ID (used for Timesketch description).
- `--sketch_id` *(default: None)*: Timesketch sketch to which the timeline should be added.
- `--token_password` *(default: '')*: Optional custom password to decrypt Timesketch credential file with.
- `--wait_for_timelines` *(default: True)*: Whether to wait for Timesketch to finish processing all timelines.


Modules: `GCPLogsCollector`, `GCPLoggingTimesketch`, `TimesketchExporter`

**Module graph**

![gcp_logging_gce_ts](/_static/graphviz/gcp_logging_gce_ts.png)

----

## `gcp_turbinia_disk_copy_ts`

Imports a remote GCP persistent disk, processes it with Turbinia and sends results to Timesketch.

**Details:**

Imports a remote GCP persistent disk into an analysis GCP project and sends the result of Turbinia processing to Timesketch.

- Copies a disk from a remote GCP project into an analysis project
- Creates Turbinia processing request to process the imported disk
- Downloads and sends results of the Turbinia processing to Timesketch.

This recipe will also start an analysis VM in the destination project with the attached disk (the same one that Turbinia will have processed). If the target disk is already in the same project as Turbinia, you can use the `gcp_turbinia_ts` recipe.

**CLI parameters:**

- `remote_project_name` *(default: None)*: Name of the project containing the instance / disks to copy.
- `analysis_project_name` *(default: None)*: Name of the project containing the Turbinia instance.
- `--turbinia_zone` *(default: None)*: The GCP zone the disk to process and Turbinia workers are in.
- `--incident_id` *(default: None)*: Incident ID (used for Timesketch description and to label the VM with).
- `--run_all_jobs` *(default: False)*: Run all Turbinia processing jobs instead of a faster subset.
- `--sketch_id` *(default: None)*: Timesketch sketch to which the timeline should be added.
- `--token_password` *(default: '')*: Optional custom password to decrypt Timesketch credential file with.
- `--analysis_vm` *(default: True)*: Create an analysis VM in the destination project.
- `--wait_for_timelines` *(default: True)*: Whether to wait for Timesketch to finish processing all timelines.
- `--instance` *(default: None)*: Name of the instance to analyze.
- `--disks` *(default: None)*: Comma-separated list of disks to copy from the source GCP project (if `instance` not provided).
- `--all_disks` *(default: False)*: Copy all disks in the designated instance. Overrides disk_names if specified.
- `--stop_instance` *(default: False)*: Stop the designated instance after copying disks.
- `--cpu_cores` *(default: 4)*: Number of CPU cores of the analysis VM.
- `--boot_disk_size` *(default: 50.0)*: The size of the analysis VM boot disk (in GB).
- `--boot_disk_type` *(default: 'pd-standard')*: Disk type to use [pd-standard, pd-ssd]
- `--image_project` *(default: 'ubuntu-os-cloud')*: Name of the project where the analysis VM image is hosted.
- `--image_family` *(default: 'ubuntu-1804-lts')*: Name of the image to use to create the analysis VM.


Modules: `GoogleCloudCollector`, `TurbiniaGCPProcessor`, `TimesketchExporter`

**Module graph**

![gcp_turbinia_disk_copy_ts](/_static/graphviz/gcp_turbinia_disk_copy_ts.png)

----

## `gcp_turbinia_ts`

Processes an existing GCP persistent disks with Turbinia project and sends results to Timesketch.

**Details:**

Process GCP persistent disks with Turbinia and send output to Timesketch.

This processes disks that are already in the project where Turbinia exists. If you want to copy disks from another project, use the `gcp_turbinia_disk_copy_ts` recipe.

**CLI parameters:**

- `analysis_project_name` *(default: None)*: Name of GCP project the disk exists in.
- `turbinia_zone` *(default: None)*: The GCP zone the disk to process (and Turbinia workers) are in.
- `disk_name` *(default: None)*: Name of GCP persistent disk to process.
- `--incident_id` *(default: None)*: Incident ID (used for Timesketch description).
- `--run_all_jobs` *(default: False)*: Run all Turbinia processing jobs instead of a faster subset.
- `--sketch_id` *(default: None)*: Timesketch sketch to which the timeline should be added.
- `--token_password` *(default: '')*: Optional custom password to decrypt Timesketch credential file with.
- `--wait_for_timelines` *(default: True)*: Whether to wait for Timesketch to finish processing all timelines.


Modules: `TurbiniaGCPProcessor`, `TimesketchExporter`

**Module graph**

![gcp_turbinia_ts](/_static/graphviz/gcp_turbinia_ts.png)

----

## `gcp_turbinia_ts_threaded`

Processes an existing GCP persistent disks with Turbinia project and sends results to Timesketch.

**Details:**

This is the threaded version of `gcp_turbinia_ts`.

Process GCP persistent disks with Turbinia and send output to Timesketch.

This processes disks that are already in the project where Turbinia exists. If you want to copy disks from another project, use the `gcp_turbinia_disk_copy_ts` recipe.

**CLI parameters:**

- `analysis_project_name` *(default: None)*: Name of GCP project the disk(s) and Turbinia are in.
- `turbinia_zone` *(default: None)*: The GCP zone the disk(s) to process and Turbinia workers are in.
- `disks` *(default: None)*: Comma separated names of GCP persistent disks to process.
- `--incident_id` *(default: None)*: Incident ID (used for Timesketch description).
- `--run_all_jobs` *(default: False)*: Run all Turbinia processing jobs instead of a faster subset.
- `--sketch_id` *(default: None)*: Timesketch sketch to which the timeline should be added.
- `--token_password` *(default: '')*: Optional custom password to decrypt Timesketch credential file with.
- `--wait_for_timelines` *(default: True)*: Whether to wait for Timesketch to finish processing all timelines.


Modules: `TurbiniaGCPProcessorThreaded`, `TimesketchExporterThreaded`

**Module graph**

![gcp_turbinia_ts_threaded](/_static/graphviz/gcp_turbinia_ts_threaded.png)

----

## `grr_artifact_grep`

Fetches ForensicArtifacts from GRR hosts and runs grep with a list of keywords on them.

**Details:**

Collect ForensicArtifacts from hosts using GRR.

- Collect a predefined list of artifacts from hosts using GRR
- Process them locally with grep to extract keywords.

**CLI parameters:**

- `hostnames` *(default: None)*: Comma-separated list of hostnames or GRR client IDs to process.
- `reason` *(default: None)*: Reason for collection.
- `keywords` *(default: None)*: Pipe-separated list of keywords to search for (e.g. key1|key2|key3.
- `--artifacts` *(default: None)*: Comma-separated list of artifacts to fetch (override default artifacts).
- `--extra_artifacts` *(default: None)*: Comma-separated list of artifacts to append to the default artifact list.
- `--use_tsk` *(default: False)*: Use TSK to fetch artifacts.
- `--approvers` *(default: None)*: Emails for GRR approval request.
- `--grr_server_url` *(default: 'http://localhost:8000')*: GRR endpoint.
- `--verify` *(default: True)*: Whether to verify the GRR TLS certificate.
- `--skip_offline_clients` *(default: False)*: Whether to skip clients that are offline.
- `--grr_username` *(default: 'admin')*: GRR username.
- `--grr_password` *(default: 'admin')*: GRR password.
- `--max_file_size` *(default: 5368709120)*: Maximum size of files to collect (in bytes).


Modules: `GRRArtifactCollector`, `GrepperSearch`

**Module graph**

![grr_artifact_grep](/_static/graphviz/grr_artifact_grep.png)

----

## `grr_artifact_ts`

Fetches default ForensicArtifacts from a sequence of GRR hosts, processes them with plaso, and sends the results to Timesketch.

**Details:**

Collect artifacts from hosts using GRR.

- Collect a predefined list of artifacts from hosts using GRR
- Process them with a local install of plaso
- Export them to a Timesketch sketch.

The default set of artifacts is defined in the GRRArtifactCollector module (see the `_DEFAULT_ARTIFACTS_*` class attributes in `grr_hosts.py`), and varies per platform.

**CLI parameters:**

- `hostnames` *(default: None)*: Comma-separated list of hostnames or GRR client IDs to process.
- `reason` *(default: None)*: Reason for collection.
- `--artifacts` *(default: None)*: Comma-separated list of artifacts to fetch (override default artifacts).
- `--extra_artifacts` *(default: None)*: Comma-separated list of artifacts to append to the default artifact list.
- `--use_tsk` *(default: False)*: Use TSK to fetch artifacts.
- `--approvers` *(default: None)*: Emails for GRR approval request.
- `--sketch_id` *(default: None)*: Timesketch sketch to which the timeline should be added.
- `--wait_for_timelines` *(default: True)*: Whether to wait for Timesketch to finish processing all timelines.
- `--token_password` *(default: '')*: Optional custom password to decrypt Timesketch credential file with.
- `--incident_id` *(default: None)*: Incident ID (used for Timesketch description).
- `--grr_server_url` *(default: 'http://localhost:8000')*: GRR endpoint.
- `--verify` *(default: True)*: Whether to verify the GRR TLS certificate.
- `--skip_offline_clients` *(default: False)*: Whether to skip clients that are offline.
- `--grr_username` *(default: 'admin')*: GRR username
- `--grr_password` *(default: 'admin')*: GRR password
- `--max_file_size` *(default: 5368709120)*: Maximum size of files to collect (in bytes).


Modules: `GRRArtifactCollector`, `LocalPlasoProcessor`, `TimesketchExporter`

**Module graph**

![grr_artifact_ts](/_static/graphviz/grr_artifact_ts.png)

----

## `grr_files_collect`

Collects specific files from one or more GRR hosts.

**Details:**

Collects specific files from one or more GRR hosts. Files can be a glob pattern (e.g. `/tmp/*.so`) and support GRR variable interpolation (e.g. `%%users.localappdata%%/Directory/`) 

**CLI parameters:**

- `hostnames` *(default: None)*: Comma-separated list of hostnames or GRR client IDs to process.
- `reason` *(default: None)*: Reason for collection.
- `files` *(default: None)*: Comma-separated list of files to fetch (supports globs and GRR variable interpolation).
- `directory` *(default: None)*: Directory in which to export files.
- `--use_tsk` *(default: False)*: Use TSK to fetch artifacts.
- `--approvers` *(default: None)*: Emails for GRR approval request.
- `--verify` *(default: True)*: Whether to verify the GRR TLS certificate.
- `--skip_offline_clients` *(default: False)*: Whether to skip clients that are offline.
- `--action` *(default: 'download')*: String denoting action (download/hash/stat) to take
- `--grr_server_url` *(default: 'http://localhost:8000')*: GRR endpoint
- `--grr_username` *(default: 'admin')*: GRR username
- `--grr_password` *(default: 'admin')*: GRR password
- `--max_file_size` *(default: 5368709120)*: Maximum size of files to collect (in bytes).


Modules: `GRRFileCollector`, `LocalFilesystemCopy`

**Module graph**

![grr_files_collect](/_static/graphviz/grr_files_collect.png)

----

## `grr_flow_collect`

Download the result of a GRR flow to the local filesystem.

**Details:**

Download the result of a GRR flow to the local filesystem. Flow IDs are unique *per client*, so both need to be provided in sequence.

**CLI parameters:**

- `hostnames` *(default: None)*: Hostname(s) to collect the flow from.
- `flow_ids` *(default: None)*: Flow ID(s) to download.
- `reason` *(default: None)*: Reason for collection.
- `directory` *(default: None)*: Directory in which to export files.
- `--approvers` *(default: None)*: Emails for GRR approval request.
- `--grr_server_url` *(default: 'http://localhost:8000')*: GRR endpoint
- `--verify` *(default: True)*: Whether to verify the GRR TLS certificate.
- `--skip_offline_clients` *(default: False)*: Whether to skip clients that are offline.
- `--grr_username` *(default: 'admin')*: GRR username
- `--grr_password` *(default: 'admin')*: GRR password


Modules: `GRRFlowCollector`, `LocalFilesystemCopy`

**Module graph**

![grr_flow_collect](/_static/graphviz/grr_flow_collect.png)

----

## `grr_hunt_artifacts`

Starts a GRR hunt for the default set of artifacts.

**Details:**

Starts a GRR artifact hunt and provides the Hunt ID to the user. Feed the Hunt ID to `grr_huntresults_ts` to process results through Plaso and export them to Timesketch.

**CLI parameters:**

- `artifacts` *(default: None)*: Comma-separated list of artifacts to hunt for.
- `reason` *(default: None)*: Reason for collection.
- `--use_tsk` *(default: False)*: Use TSK to fetch artifacts.
- `--approvers` *(default: None)*: Emails for GRR approval request.
- `--grr_server_url` *(default: 'http://localhost:8000')*: GRR endpoint
- `--verify` *(default: True)*: Whether to verify the GRR TLS certificate.
- `--grr_username` *(default: 'admin')*: GRR username
- `--grr_password` *(default: 'admin')*: GRR password
- `--max_file_size` *(default: 5368709120)*: Maximum size of files to collect (in bytes).


Modules: `GRRHuntArtifactCollector`

**Module graph**

![grr_hunt_artifacts](/_static/graphviz/grr_hunt_artifacts.png)

----

## `grr_hunt_file`

Starts a GRR hunt for a list of files.

**Details:**

Starts a GRR hunt for a list of files and provides a Hunt ID to the user. Feed the Hunt ID to `grr_huntresults_ts` to process results through Plaso and export them to Timesketch.

Like in `grr_files_collect`, files can be globs and support variable interpolation.

**CLI parameters:**

- `file_path_list` *(default: None)*: Comma-separated list of file paths to hunt for.
- `reason` *(default: None)*: Reason for collection.
- `--approvers` *(default: None)*: Emails for GRR approval request.
- `--grr_server_url` *(default: 'http://localhost:8000')*: GRR endpoint
- `--verify` *(default: True)*: Whether to verify the GRR TLS certificate.
- `--grr_username` *(default: 'admin')*: GRR username
- `--grr_password` *(default: 'admin')*: GRR password
- `--max_file_size` *(default: 5368709120)*: Maximum size of files to collect (in bytes).


Modules: `GRRHuntFileCollector`

**Module graph**

![grr_hunt_file](/_static/graphviz/grr_hunt_file.png)

----

## `grr_huntresults_ts`

Fetches the ersults of a GRR hunt, processes them with Plaso, and exports the results to Timesketch.

**Details:**

Download the results of a GRR hunt and process them.

- Collect results of a hunt given its Hunt ID
- Processes results with a local install of Plaso
- Exports processed items to a new Timesketch sketch

**CLI parameters:**

- `hunt_id` *(default: None)*: ID of GRR Hunt results to fetch.
- `reason` *(default: None)*: Reason for exporting hunt (used for Timesketch description).
- `--sketch_id` *(default: None)*: Timesketch sketch to which the timeline should be added.
- `--token_password` *(default: '')*: Optional custom password to decrypt Timesketch credential file with.
- `--wait_for_timelines` *(default: True)*: Whether to wait for Timesketch to finish processing all timelines.
- `--approvers` *(default: None)*: Emails for GRR approval request.
- `--grr_server_url` *(default: 'http://localhost:8000')*: GRR endpoint
- `--verify` *(default: True)*: Whether to verify the GRR TLS certificate.
- `--grr_username` *(default: 'admin')*: GRR username
- `--grr_password` *(default: 'admin')*: GRR password


Modules: `GRRHuntDownloader`, `LocalPlasoProcessor`, `TimesketchExporter`

**Module graph**

![grr_huntresults_ts](/_static/graphviz/grr_huntresults_ts.png)

----

## `grr_timeline_ts`

Runs a TimelineFlow on a set of GRR hosts, generating a filesystem bodyfile for each host. These bodyfiles are processed results with Plaso, and the resulting plaso files are exported to Timesketch.

**Details:**

Uses the GRR TimelineFlow to generate a filesystem timeline and exports it to Timesketch..

**CLI parameters:**

- `hostnames` *(default: None)*: Comma-separated list of hostnames or GRR client IDs to process.
- `root_path` *(default: '/')*: Root path for timeline generation.
- `reason` *(default: None)*: Reason for collection.
- `--skip_offline_clients` *(default: False)*: Whether to skip clients that are offline.
- `--approvers` *(default: None)*: Comma-separated list of usernames to ask for approval.
- `--sketch_id` *(default: None)*: Timesketch sketch to which the timeline should be added.
- `--grr_server_url` *(default: 'http://localhost:8000')*: GRR endpoint.
- `--token_password` *(default: '')*: Optional custom password to decrypt Timesketch credential file with.
- `--timesketch_quick` *(default: False)*: Skip waiting for analyzers to complete their run.
- `--wait_for_timelines` *(default: True)*: Whether to wait for Timesketch to finish processing all timelines.
- `--grr_username` *(default: 'admin')*: GRR username.
- `--grr_password` *(default: 'admin')*: GRR password.


Modules: `GRRTimelineCollector`, `LocalPlasoProcessor`, `TimesketchExporter`, `TimesketchEnhancer`

**Module graph**

![grr_timeline_ts](/_static/graphviz/grr_timeline_ts.png)

----

## `plaso_ts`

Processes a list of file paths using a Plaso and epxort results to Timesketch.

**Details:**

Processes a list of file paths using Plaso and sends results to Timesketch.

- Collectors collect from a path in the FS
- Processes them with a local install of plaso
- Exports them to a new Timesketch sketch

**CLI parameters:**

- `paths` *(default: None)*: Comma-separated list of paths to process.
- `--incident_id` *(default: None)*: Incident ID (used for Timesketch description).
- `--sketch_id` *(default: None)*: Timesketch sketch to which the timeline should be added.
- `--token_password` *(default: '')*: Optional custom password to decrypt Timesketch credential file with.
- `--wait_for_timelines` *(default: True)*: Whether to wait for Timesketch to finish processing all timelines.


Modules: `FilesystemCollector`, `LocalPlasoProcessor`, `TimesketchExporter`

**Module graph**

![plaso_ts](/_static/graphviz/plaso_ts.png)

----

## `upload_ts`

Uploads a local CSV or Plaso file to Timesketch.

**Details:**

Uploads a CSV or Plaso file to Timesketch.

**CLI parameters:**

- `files` *(default: None)*: Comma-separated list of paths to CSV files or Plaso storage files.
- `--sketch_id` *(default: None)*: Timesketch sketch to which the timeline should be added.
- `--token_password` *(default: '')*: Optional custom password to decrypt Timesketch credential file with.
- `--incident_id` *(default: None)*: Incident ID (used for Timesketch description).
- `--wait_for_timelines` *(default: True)*: Whether to wait for Timesketch to finish processing all timelines.


Modules: `FilesystemCollector`, `TimesketchExporter`

**Module graph**

![upload_ts](/_static/graphviz/upload_ts.png)

----

## `upload_turbinia`

Uploads arbitrary files to Turbinia and downloads results.

**Details:**

Uploads arbitrary files to Turbinia for processing. The recipe will wait for Turbinia to return with results and will download them back to the filesystem. The Turbinia system needs to be accesible via SSH.

**CLI parameters:**

- `files` *(default: None)*: Paths to process.
- `--destination_turbinia_dir` *(default: None)*: Destination path in Turbinia host to write the files to.
- `--hostname` *(default: None)*: Remote host.
- `--directory` *(default: None)*: Directory in which to copy and compress files.
- `--turbinia_config` *(default: None)*: Turbinia config file to use.
- `--local_turbinia_results` *(default: None)*: Directory where Turbinia results will be downloaded to.
- `--sketch_id` *(default: None)*: Timesketch sketch ID.


Modules: `FilesystemCollector`, `LocalFilesystemCopy`, `SCP-Upload`, `TurbiniaArtifactProcessor`, `SCP-Download`

**Module graph**

![upload_turbinia](/_static/graphviz/upload_turbinia.png)

----

## `upload_web_ts`

Uploads a CSV/JSONL or Plaso file to Timesketch and runs web-related Timesketch analyzers.

**Details:**

Uploads a CSV or Plaso file to Timesketch and runs a series of web-related analyzers on the uploaded data.

The following analyzers will run on the processed timeline: `browser_search,browser_timeframe,account_finder,phishy_domains,evtx_gap,login,win_crash,safebrowsing,chain`.

**CLI parameters:**

- `files` *(default: None)*: Comma-separated list of paths to CSV files or Plaso storage files.
- `--sketch_id` *(default: None)*: Timesketch sketch to which the timeline should be added.
- `--token_password` *(default: '')*: Optional custom password to decrypt Timesketch credential file with.
- `--incident_id` *(default: None)*: Incident ID (used for Timesketch description).
- `--wait_for_analyzers` *(default: True)*: Wait for analyzers until they complete their run, if set to False the TS enhancer will be skipped.
- `--timesketch_include_stories` *(default: False)*: Include story dumps in reports.
- `--searches_to_skip` *(default: None)*: A comma separated list of saved searches that should not be uploaded.
- `--analyzer_max_checks` *(default: 0)*: Number of wait cycles (per cycle is 3 seconds) before terminating wait for analyzers to complete.
- `--aggregations_to_skip` *(default: None)*: A comma separated list of aggregation names that should not be uploaded.


Modules: `FilesystemCollector`, `TimesketchExporter`, `TimesketchEnhancer`

**Module graph**

![upload_web_ts](/_static/graphviz/upload_web_ts.png)

----

## `vt_evtx`

Downloads the EVTX files from VirusTotal for a specific hash.

**Details:**

Downloads the EVTX files from VirusTotal sandbox run for a specific hash, processes it with Plaso.

**CLI parameters:**

- `hashes` *(default: None)*: Comma-separated list of hashes to process.
- `directory` *(default: None)*: Directory in which to export files.
- `--vt_api_key` *(default: 'admin')*: Virustotal API key


Modules: `VTCollector`, `LocalPlasoProcessor`

**Module graph**

![vt_evtx](/_static/graphviz/vt_evtx.png)

----

## `vt_evtx_ts`

Downloads the EVTX from VirusTotal sandbox runs for a specific hash and uploads the corresponding timeline to Timesketch.

**Details:**

Downloads the EVTX file generated by VirusTotal during the sandbox runs for a specific hash, processes the EVTX files with Plaso and uploads the resulting Plaso file to Timesketch.

**CLI parameters:**

- `hashes` *(default: None)*: Comma-separated list of hashes to process.
- `directory` *(default: None)*: Directory in which to export files.
- `--vt_api_key` *(default: 'admin')*: Virustotal API key
- `--incident_id` *(default: None)*: Incident ID (used for Timesketch description).
- `--sketch_id` *(default: None)*: Timesketch sketch to which the timeline should be added.
- `--token_password` *(default: '')*: Optional custom password to decrypt Timesketch credential file with
- `--wait_for_timelines` *(default: True)*: Whether to wait for Timesketch to finish processing all timelines.


Modules: `VTCollector`, `LocalPlasoProcessor`, `TimesketchExporter`

**Module graph**

![vt_evtx_ts](/_static/graphviz/vt_evtx_ts.png)

----

## `vt_pcap`

Downloads the PCAP from VirusTotal for a specific hash.

**Details:**

Downloads the PCAP files generated from VirusTotal sandboxs run for a specific hash.

**CLI parameters:**

- `hashes` *(default: None)*: Comma-separated list of hashes to process.
- `directory` *(default: None)*: Directory in which to export files.
- `--vt_api_key` *(default: 'admin')*: Virustotal API key


Modules: `VTCollector`, `LocalFilesystemCopy`

**Module graph**

![vt_pcap](/_static/graphviz/vt_pcap.png)

----

## `workspace_logging_collect`

Collects Workspace Audit logs and dumps them on the filesystem.

**Details:**

Collects logs from Workspace Audit log and dumps them on the filesystem.

See https://developers.google.com/admin-sdk/reports/reference/rest/v1/activities/list#ApplicationName for a list of application mames.

For filters, see https://developers.google.com/admin-sdk/reports/reference/rest/v1/activities/list.

**CLI parameters:**

- `application_name` *(default: None)*: Name of application to to collect logs for. See https://developers.google.com/admin-sdk/reports/reference/rest/v1/activities/list#ApplicationName for a list of possible values.
- `--user` *(default: 'all')*: email address of the user to query logs for
- `--start_time` *(default: None)*: Start time (yyyy-mm-ddTHH:MM:SSZ).
- `--end_time` *(default: None)*: End time (yyyy-mm-ddTHH:MM:SSZ).
- `--filter_expression` *(default: '')*: Filter expression to use to query Workspace logs. See https://developers.google.com/admin-sdk/reports/reference/rest/v1/activities/list.


Modules: `WorkspaceAuditCollector`

**Module graph**

![workspace_logging_collect](/_static/graphviz/workspace_logging_collect.png)

----

## `workspace_meet_ts`

Collects Meet records and adds them to Timesketch

**Details:**

Collects Google Workspace audit records for a Google Meet and adds them to Timesketch.

**CLI parameters:**

- `meeting_id` *(default: None)*: ID for the Meeting to look up.
- `--start_time` *(default: None)*: Start time (yyyy-mm-ddTHH:MM:SSZ).
- `--end_time` *(default: None)*: End time (yyyy-mm-ddTHH:MM:SSZ).
- `--incident_id` *(default: None)*: Incident ID (used for Timesketch description).
- `--sketch_id` *(default: None)*: Timesketch sketch to which the timeline should be added.
- `--token_password` *(default: '')*: Optional custom password to decrypt Timesketch credential file with.
- `--wait_for_timelines` *(default: True)*: Whether to wait for Timesketch to finish processing all timelines.


Modules: `WorkspaceAuditCollector`, `WorkspaceAuditTimesketch`, `TimesketchExporter`

**Module graph**

![workspace_meet_ts](/_static/graphviz/workspace_meet_ts.png)

----

## `workspace_user_activity_ts`

Collects records for a Google Workspace user and adds them to Timesketch

**Details:**

Collects records for a Google Workspace user and adds them to Timesketch.

Collects logs for the following apps: `Login`, `Drive`, `Token`, `Chrome`, `CAA`, `DataStudio`, `GroupsEnterprise`, `Calendar`, `Chat`, `Groups`, `Meet`, `UserAccounts`.

**CLI parameters:**

- `user` *(default: '')*: email address of the user to query logs for
- `--start_time` *(default: None)*: Start time (yyyy-mm-ddTHH:MM:SSZ).
- `--end_time` *(default: None)*: End time (yyyy-mm-ddTHH:MM:SSZ).
- `--filter_expression` *(default: '')*: Filter expression to use to query Workspace logs. See https://developers.google.com/admin-sdk/reports/reference/rest/v1/activities/list
- `--incident_id` *(default: None)*: Incident ID (used for Timesketch description).
- `--sketch_id` *(default: None)*: Timesketch sketch to which the timeline should be added.
- `--token_password` *(default: '')*: Optional custom password to decrypt Timesketch credential file with.
- `--wait_for_timelines` *(default: True)*: Whether to wait for Timesketch to finish processing all timelines.


Modules: `WorkspaceAuditCollector-Login`, `WorkspaceAuditCollector-Drive`, `WorkspaceAuditCollector-Token`, `WorkspaceAuditCollector-Chrome`, `WorkspaceAuditCollector-CAA`, `WorkspaceAuditCollector-DataStudio`, `WorkspaceAuditCollector-GroupsEnterprise`, `WorkspaceAuditCollector-Calendar`, `WorkspaceAuditCollector-Chat`, `WorkspaceAuditCollector-GCP`, `WorkspaceAuditCollector-Groups`, `WorkspaceAuditCollector-Meet`, `WorkspaceAuditCollector-UserAccounts`, `WorkspaceAuditTimesketch`, `TimesketchExporter`

**Module graph**

![workspace_user_activity_ts](/_static/graphviz/workspace_user_activity_ts.png)

----

## `workspace_user_drive_ts`

Collects Drive records for a Workspace user and adds them to Timesketch

**Details:**

Collects Drive records for a Workspace user and adds them to Timesketch.

**CLI parameters:**

- `user` *(default: '')*: email address of the user to query logs for
- `--start_time` *(default: None)*: Start time (yyyy-mm-ddTHH:MM:SSZ).
- `--end_time` *(default: None)*: End time (yyyy-mm-ddTHH:MM:SSZ).
- `--filter_expression` *(default: '')*: Filter expression to use to query Workspace logs. See https://developers.google.com/admin-sdk/reports/reference/rest/v1/activities/list
- `--incident_id` *(default: None)*: Incident ID (used for Timesketch description).
- `--sketch_id` *(default: None)*: Timesketch sketch to which the timeline should be added.
- `--token_password` *(default: '')*: Optional custom password to decrypt Timesketch credential file with.
- `--wait_for_timelines` *(default: True)*: Whether to wait for Timesketch to finish processing all timelines.


Modules: `WorkspaceAuditCollector`, `WorkspaceAuditTimesketch`, `TimesketchExporter`

**Module graph**

![workspace_user_drive_ts](/_static/graphviz/workspace_user_drive_ts.png)

----

## `workspace_user_login_ts`

Collects login records and adds to Timesketch

**Details:**

Collects login records for a Workspace user and adds them to Timesketch.

**CLI parameters:**

- `user` *(default: '')*: email address of the user to query logs for
- `--start_time` *(default: None)*: Start time (yyyy-mm-ddTHH:MM:SSZ).
- `--end_time` *(default: None)*: End time (yyyy-mm-ddTHH:MM:SSZ).
- `--filter_expression` *(default: '')*: Filter expression to use to query Workspace logs. See https://developers.google.com/admin-sdk/reports/reference/rest/v1/activities/list
- `--incident_id` *(default: None)*: Incident ID (used for Timesketch description).
- `--sketch_id` *(default: None)*: Timesketch sketch to which the timeline should be added.
- `--token_password` *(default: '')*: Optional custom password to decrypt Timesketch credential file with.
- `--wait_for_timelines` *(default: True)*: Whether to wait for Timesketch to finish processing all timelines.


Modules: `WorkspaceAuditCollector`, `WorkspaceAuditTimesketch`, `TimesketchExporter`

**Module graph**

![workspace_user_login_ts](/_static/graphviz/workspace_user_login_ts.png)

----

