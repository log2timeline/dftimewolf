
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

Modules: `AWSVolumeSnapshotCollector`, `AWSSnapshotS3CopyCollector`, `S3ToGCSCopy`, `GCSToGCEImage`, `GCEDiskFromImage`

**Module graph**

![aws_disk_to_gcp](/_static/graphviz/aws_disk_to_gcp.png)

----

## `aws_forensics`

Copies a volume from an AWS account to an analysis VM.

**Details:**

Copies a volume from an AWS account, creates an analysis VM in AWS (with a startup script containing installation instructions for basic forensics tooling), and attaches the copied volume to it.

Modules: `AWSCollector`

**Module graph**

![aws_forensics](/_static/graphviz/aws_forensics.png)

----

## `aws_logging_collect`

Collects logs from an AWS account and dumps the results to the filesystem.

**Details:**

Collects logs from an AWS account using a specified query filter and date ranges, and dumps them on the filesystem.

Modules: `AWSLogsCollector`

**Module graph**

![aws_logging_collect](/_static/graphviz/aws_logging_collect.png)

----

## `aws_turbinia_ts`

Copies EBS volumes from within AWS, transfers them to GCP, analyses with Turbinia and exports the results to Timesketch.

**Details:**

Copies EBS volumes from within AWS, uses buckets and cloud-to-cloud operations to transfer the data to GCP. Once in GCP, a persistend disk is created and a job is added to the Turbinia queue to start analysis. The resulting Plaso file is then exported to Timesketch.

Modules: `AWSVolumeSnapshotCollector`, `AWSSnapshotS3CopyCollector`, `S3ToGCSCopy`, `GCSToGCEImage`, `GCEDiskFromImage`, `TurbiniaGCPProcessorThreaded`, `TimesketchExporterThreaded`

**Module graph**

![aws_turbinia_ts](/_static/graphviz/aws_turbinia_ts.png)

----

## `azure_forensics`

Copies a disk from an Azure account to an analysis VM.

**Details:**

Copies a disk from an Azure account, creates an analysis VM in Azure (with a startup script containing installation instructions for basic forensics tooling), and attaches the copied disk to it.

Modules: `AzureCollector`

**Module graph**

![azure_forensics](/_static/graphviz/azure_forensics.png)

----

## `bigquery_collect`

Collects results from BigQuery and dumps them on the filesystem.

**Details:**

Collects results from BigQuery in a GCP project and dumps them in JSONL on the local filesystem.

Modules: `BigQueryCollector`

**Module graph**

![bigquery_collect](/_static/graphviz/bigquery_collect.png)

----

## `bigquery_ts`

Collects results from BigQuery and uploads them to Timesketch.

**Details:**

Collects results from BigQuery in JSONL form, dumps them to the filesystem, and uploads them to Timesketch.

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

Modules: `GoogleCloudDiskExport`

**Module graph**

![gce_disk_export](/_static/graphviz/gce_disk_export.png)

----

## `gcp_forensics`

Copies disk from a GCP project to an analysis VM.

**Details:**

Copies a persistend disk from a GCP project to another, creates an analysis VM (with a startup script containing installation instructions for basic forensics tooling) in the destiantion project, and attaches the copied GCP persistend disk to it.

Modules: `GoogleCloudCollector`

**Module graph**

![gcp_forensics](/_static/graphviz/gcp_forensics.png)

----

## `gcp_logging_cloudaudit_ts`

Collects GCP logs from a project and exports them to Timesketch.

**Details:**

Collects GCP logs from a project and exports them to Timesketch. Some light processing is made to translate the logs into something Timesketch can process.

Modules: `GCPLogsCollector`, `GCPLoggingTimesketch`, `TimesketchExporter`

**Module graph**

![gcp_logging_cloudaudit_ts](/_static/graphviz/gcp_logging_cloudaudit_ts.png)

----

## `gcp_logging_cloudsql_ts`

Collects GCP related to Cloud SQL instances in a project and exports them to Timesketch.

**Details:**

Collects GCP related to Cloud SQL instances in a project and exports them to Timesketch. Some light processing is made to translate the logs into something Timesketch can process.

Modules: `GCPLogsCollector`, `GCPLoggingTimesketch`, `TimesketchExporter`

**Module graph**

![gcp_logging_cloudsql_ts](/_static/graphviz/gcp_logging_cloudsql_ts.png)

----

## `gcp_logging_collect`

Collects logs from a GCP project and dumps on the filesystem (JSON). https://cloud.google.com/logging/docs/view/query-library for example queries.

**Details:**

Collects logs from a GCP project and dumps on the filesystem.

Modules: `GCPLogsCollector`

**Module graph**

![gcp_logging_collect](/_static/graphviz/gcp_logging_collect.png)

----

## `gcp_logging_gce_instance_ts`

GCP Instance Cloud Audit logs to Timesketch

**Details:**

Collects GCP Cloud Audit Logs for a GCE instance and exports them to Timesketch. Some light processing is made to translate the logs into something Timesketch can process.

Modules: `GCPLogsCollector`, `GCPLoggingTimesketch`, `TimesketchExporter`

**Module graph**

![gcp_logging_gce_instance_ts](/_static/graphviz/gcp_logging_gce_instance_ts.png)

----

## `gcp_logging_gce_ts`

Loads all GCE Cloud Audit Logs in a GCP project into Timesketch.

**Details:**

Loads all GCE Cloud Audit Logs for all instances in a GCP project into Timesketch. Some light processing is made to translate the logs into something Timesketch can process.

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

Modules: `GoogleCloudCollector`, `TurbiniaGCPProcessor`, `TimesketchExporter`

**Module graph**

![gcp_turbinia_disk_copy_ts](/_static/graphviz/gcp_turbinia_disk_copy_ts.png)

----

## `gcp_turbinia_ts`

Processes an existing GCP persistent disks with Turbinia project and sends results to Timesketch.

**Details:**

Process GCP persistent disks with Turbinia and send output to Timesketch.

This processes disks that are already in the project where Turbinia exists. If you want to copy disks from another project, use the `gcp_turbinia_disk_copy_ts` recipe.

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

Modules: `GRRArtifactCollector`, `LocalPlasoProcessor`, `TimesketchExporter`

**Module graph**

![grr_artifact_ts](/_static/graphviz/grr_artifact_ts.png)

----

## `grr_files_collect`

Collects specific files from one or more GRR hosts.

**Details:**

Collects specific files from one or more GRR hosts. Files can be a glob pattern (e.g. `/tmp/*.so`) and support GRR variable interpolation (e.g. `%%users.localappdata%%/Directory/`) 

Modules: `GRRFileCollector`, `LocalFilesystemCopy`

**Module graph**

![grr_files_collect](/_static/graphviz/grr_files_collect.png)

----

## `grr_flow_collect`

Download the result of a GRR flow to the local filesystem.

**Details:**

Download the result of a GRR flow to the local filesystem. Flow IDs are unique *per client*, so both need to be provided in sequence.

Modules: `GRRFlowCollector`, `LocalFilesystemCopy`

**Module graph**

![grr_flow_collect](/_static/graphviz/grr_flow_collect.png)

----

## `grr_hunt_artifacts`

Starts a GRR hunt for the default set of artifacts.

**Details:**

Starts a GRR artifact hunt and provides the Hunt ID to the user. Feed the Hunt ID to `grr_huntresults_ts` to process results through Plaso and export them to Timesketch.

Modules: `GRRHuntArtifactCollector`

**Module graph**

![grr_hunt_artifacts](/_static/graphviz/grr_hunt_artifacts.png)

----

## `grr_hunt_file`

Starts a GRR hunt for a list of files.

**Details:**

Starts a GRR hunt for a list of files and provides a Hunt ID to the user. Feed the Hunt ID to `grr_huntresults_ts` to process results through Plaso and export them to Timesketch.

Like in `grr_files_collect`, files can be globs and support variable interpolation.

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

Modules: `GRRHuntDownloader`, `LocalPlasoProcessor`, `TimesketchExporter`

**Module graph**

![grr_huntresults_ts](/_static/graphviz/grr_huntresults_ts.png)

----

## `grr_timeline_ts`

Runs a TimelineFlow on a set of GRR hosts, generating a filesystem bodyfile for each host. These bodyfiles are processed results with Plaso, and the resulting plaso files are exported to Timesketch.

**Details:**

Uses the GRR TimelineFlow to generate a filesystem timeline and exports it to Timesketch..

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

Modules: `FilesystemCollector`, `LocalPlasoProcessor`, `TimesketchExporter`

**Module graph**

![plaso_ts](/_static/graphviz/plaso_ts.png)

----

## `upload_ts`

Uploads a local CSV or Plaso file to Timesketch.

**Details:**

Uploads a CSV or Plaso file to Timesketch.

Modules: `FilesystemCollector`, `TimesketchExporter`

**Module graph**

![upload_ts](/_static/graphviz/upload_ts.png)

----

## `upload_turbinia`

Uploads arbitrary files to Turbinia and downloads results.

**Details:**

Uploads arbitrary files to Turbinia for processing. The recipe will wait for Turbinia to return with results and will download them back to the filesystem. The Turbinia system needs to be accesible via SSH.

Modules: `FilesystemCollector`, `LocalFilesystemCopy`, `SCP-Upload`, `TurbiniaArtifactProcessor`, `SCP-Download`

**Module graph**

![upload_turbinia](/_static/graphviz/upload_turbinia.png)

----

## `upload_web_ts`

Uploads a CSV/JSONL or Plaso file to Timesketch and runs web-related Timesketch analyzers.

**Details:**

Uploads a CSV or Plaso file to Timesketch and runs a series of web-related analyzers on the uploaded data.

The following analyzers will run on the processed timeline: `browser_search,browser_timeframe,account_finder,phishy_domains,evtx_gap,login,win_crash,safebrowsing,chain`.

Modules: `FilesystemCollector`, `TimesketchExporter`, `TimesketchEnhancer`

**Module graph**

![upload_web_ts](/_static/graphviz/upload_web_ts.png)

----

## `vt_evtx`

Downloads the EVTX files from VirusTotal for a specific hash.

**Details:**

Downloads the EVTX files from VirusTotal sandbox run for a specific hash, processes it with Plaso.

Modules: `VTCollector`, `LocalPlasoProcessor`

**Module graph**

![vt_evtx](/_static/graphviz/vt_evtx.png)

----

## `vt_evtx_ts`

Downloads the EVTX from VirusTotal sandbox runs for a specific hash and uploads the corresponding timeline to Timesketch.

**Details:**

Downloads the EVTX file generated by VirusTotal during the sandbox runs for a specific hash, processes the EVTX files with Plaso and uploads the resulting Plaso file to Timesketch.

Modules: `VTCollector`, `LocalPlasoProcessor`, `TimesketchExporter`

**Module graph**

![vt_evtx_ts](/_static/graphviz/vt_evtx_ts.png)

----

## `vt_pcap`

Downloads the PCAP from VirusTotal for a specific hash.

**Details:**

Downloads the PCAP files generated from VirusTotal sandboxs run for a specific hash.

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

Modules: `WorkspaceAuditCollector`

**Module graph**

![workspace_logging_collect](/_static/graphviz/workspace_logging_collect.png)

----

## `workspace_meet_ts`

Collects Meet records and adds them to Timesketch

**Details:**

Collects Google Workspace audit records for a Google Meet and adds them to Timesketch.

Modules: `WorkspaceAuditCollector`, `WorkspaceAuditTimesketch`, `TimesketchExporter`

**Module graph**

![workspace_meet_ts](/_static/graphviz/workspace_meet_ts.png)

----

## `workspace_user_activity_ts`

Collects records for a Google Workspace user and adds them to Timesketch

**Details:**

Collects records for a Google Workspace user and adds them to Timesketch.

Collects logs for the following apps: `Login`, `Drive`, `Token`, `Chrome`, `CAA`, `DataStudio`, `GroupsEnterprise`, `Calendar`, `Chat`, `Groups`, `Meet`, `UserAccounts`.

Modules: `WorkspaceAuditCollector-Login`, `WorkspaceAuditCollector-Drive`, `WorkspaceAuditCollector-Token`, `WorkspaceAuditCollector-Chrome`, `WorkspaceAuditCollector-CAA`, `WorkspaceAuditCollector-DataStudio`, `WorkspaceAuditCollector-GroupsEnterprise`, `WorkspaceAuditCollector-Calendar`, `WorkspaceAuditCollector-Chat`, `WorkspaceAuditCollector-GCP`, `WorkspaceAuditCollector-Groups`, `WorkspaceAuditCollector-Meet`, `WorkspaceAuditCollector-UserAccounts`, `WorkspaceAuditTimesketch`, `TimesketchExporter`

**Module graph**

![workspace_user_activity_ts](/_static/graphviz/workspace_user_activity_ts.png)

----

## `workspace_user_drive_ts`

Collects Drive records for a Workspace user and adds them to Timesketch

**Details:**

Collects Drive records for a Workspace user and adds them to Timesketch.

Modules: `WorkspaceAuditCollector`, `WorkspaceAuditTimesketch`, `TimesketchExporter`

**Module graph**

![workspace_user_drive_ts](/_static/graphviz/workspace_user_drive_ts.png)

----

## `workspace_user_login_ts`

Collects login records and adds to Timesketch

**Details:**

Collects login records for a Workspace user and adds them to Timesketch.

Modules: `WorkspaceAuditCollector`, `WorkspaceAuditTimesketch`, `TimesketchExporter`

**Module graph**

![workspace_user_login_ts](/_static/graphviz/workspace_user_login_ts.png)

----

