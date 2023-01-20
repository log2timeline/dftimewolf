
# Recipe list

This is an auto-generated list of dfTimewolf recipes.

To regenerate this list, from the repository root, run:

```
poetry install -d
python docs/generate_recipe_doc.py data/recipes
```

---
## `aws_disk_to_gcp`

Copies EBS volumes from within AWS, and transfers them to GCP.

**Details:**

Copies EBS volumes from within AWS by pushing them to an AWS S3 bucket. The S3 bucket is then copied to a Google Cloud Storage bucket, from which a GCP Disk Image and finally a GCP Persistent Disk are created. This operation happens in the cloud and doesn't touch the local workstation on which the recipe is run.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['aws_region', 'AWS region containing the EBS volumes.', None, {'format': 'aws_region'}]`|`None`|
`['gcp_zone', 'Destination GCP zone in which to create the disks.', None]`|`None`|
`['volumes', 'Comma separated list of EBS volume IDs (e.g. vol-xxxxxxxx).', None]`|`None`|
`['aws_bucket', 'AWS bucket for image storage.', None]`|`None`|
`['gcp_bucket', 'GCP bucket for image storage.', None]`|`None`|
`['--subnet', 'AWS subnet to copy instances from, required if there is no default subnet in the volume region.', None]`|`None`|
`['--gcp_project', 'Destination GCP project.', None]`|`None`|
`['--aws_profile', 'Source AWS profile.', None]`|`None`|
`['--incident_id', 'Incident ID (used for Timesketch description).', None]`|`None`|
`['--run_all_jobs', 'Run all Turbinia processing jobs instead of a faster subset.', False]`|`None`|
`['--sketch_id', 'Timesketch sketch to which the timeline should be added.', None]`|`None`|
`['--token_password', 'Optional custom password to decrypt Timesketch credential file with.', '']`|`None`|
`['--wait_for_timelines', 'Whether to wait for Timesketch to finish processing all timelines.', True]`|`None`|




Modules: `AWSVolumeSnapshotCollector`, `AWSSnapshotS3CopyCollector`, `S3ToGCSCopy`, `GCSToGCEImage`, `GCEDiskFromImage`

**Module graph**

![aws_disk_to_gcp](_static/graphviz/aws_disk_to_gcp.png)

----

## `aws_forensics`

Copies a volume from an AWS account to an analysis VM.

**Details:**

Copies a volume from an AWS account, creates an analysis VM in AWS (with a startup script containing installation instructions for basic forensics tooling), and attaches the copied volume to it.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['remote_profile_name', 'Name of the AWS profile pointing to the AWS account where the volume(s) exist(s).', None]`|`None`|
`['remote_zone', 'The AWS zone in which the source volume(s) exist(s).', None]`|`None`|
`['incident_id', 'Incident ID to label the VM with.', None]`|`None`|
`['--instance_id', 'Instance ID of the instance to analyze.', None]`|`None`|
`['--volume_ids', 'Comma-separated list of volume IDs to copy.', None]`|`None`|
`['--all_volumes', 'Copy all volumes in the designated instance. Overrides volume_ids if specified.', False]`|`None`|
`['--boot_volume_size', 'The size of the analysis VM boot volume (in GB).', 50]`|`None`|
`['--analysis_zone', 'The AWS zone in which to create the VM.', None]`|`None`|
`['--analysis_profile_name', 'Name of the AWS profile to use when creating the analysis VM.', None]`|`None`|




Modules: `AWSCollector`

**Module graph**

![aws_forensics](_static/graphviz/aws_forensics.png)

----

## `aws_logging_collect`

Collects logs from an AWS account and dumps the results to the filesystem.

**Details:**

Collects logs from an AWS account using a specified query filter and date ranges, and dumps them on the filesystem. If no args are provided this recipe will collect 90 days of logs for the default AWS profile.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['--profile_name', 'Name of the AWS profile to collect logs from.', 'default']`|`None`|
`['--query_filter', 'Filter expression to use to query logs.', None]`|`None`|
`['--start_time', 'Start time for the query.', None]`|`None`|
`['--end_time', 'End time for the query.', None]`|`None`|




Modules: `AWSLogsCollector`

**Module graph**

![aws_logging_collect](_static/graphviz/aws_logging_collect.png)

----

## `aws_logging_ts`

Collects logs from an AWS account, processes the logs with Plaso and uploads the result to Timesketch.

**Details:**

Collects logs from an AWS account using a specified query filter and date ranges, processes the logs with plaso and uploads the result to Timesketch. If no args are provided this recipe will collect 90 days of logs for the default AWS profile.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['--profile_name', 'Name of the AWS profile to collect logs from.', 'default']`|`None`|
`['--query_filter', 'Filter expression to use to query logs.', None]`|`None`|
`['--start_time', 'Start time for the query.', None]`|`None`|
`['--end_time', 'End time for the query.', None]`|`None`|
`['--incident_id', 'Incident ID (used for Timesketch description).', None]`|`None`|
`['--sketch_id', 'Timesketch sketch to which the timeline should be added.', None]`|`None`|
`['--token_password', 'Optional custom password to decrypt Timesketch credential file with.', '']`|`None`|
`['--wait_for_timelines', 'Whether to wait for Timesketch to finish processing all timelines.', True]`|`None`|




Modules: `AWSLogsCollector`, `LocalPlasoProcessor`, `TimesketchExporter`

**Module graph**

![aws_logging_ts](_static/graphviz/aws_logging_ts.png)

----

## `aws_turbinia_ts`

Copies EBS volumes from within AWS, transfers them to GCP, analyses with Turbinia and exports the results to Timesketch.

**Details:**

Copies EBS volumes from within AWS, uses buckets and cloud-to-cloud operations to transfer the data to GCP. Once in GCP, a persistent disk is created and a job is added to the Turbinia queue to start analysis. The resulting Plaso file is then exported to Timesketch.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['aws_region', 'AWS region containing the EBS volumes.', None]`|`None`|
`['gcp_zone', 'Destination GCP zone in which to create the disks.', None]`|`None`|
`['volumes', 'Comma separated list of EBS volume IDs (e.g. vol-xxxxxxxx).', None]`|`None`|
`['aws_bucket', 'AWS bucket for image storage.', None]`|`None`|
`['gcp_bucket', 'GCP bucket for image storage.', None]`|`None`|
`['--subnet', 'AWS subnet to copy instances from, required if there is no default subnet in the volume region.', None]`|`None`|
`['--gcp_project', 'Destination GCP project.', None]`|`None`|
`['--aws_profile', 'Source AWS profile.', None]`|`None`|
`['--incident_id', 'Incident ID (used for Timesketch description).', None]`|`None`|
`['--sketch_id', 'Timesketch sketch to which the timeline should be added.', None]`|`None`|
`['--token_password', 'Optional custom password to decrypt Timesketch credential file with.', '']`|`None`|
`['--turbinia_recipe', 'The Turbinia recipe name to use for evidence processing.', None]`|`None`|
`['--turbinia_zone', 'Zone Turbinia is located in', 'us-central1-f']`|`None`|
`['--wait_for_timelines', 'Whether to wait for Timesketch to finish processing all timelines.', True]`|`None`|




Modules: `AWSVolumeSnapshotCollector`, `AWSSnapshotS3CopyCollector`, `S3ToGCSCopy`, `GCSToGCEImage`, `GCEDiskFromImage`, `TurbiniaGCPProcessor`, `TimesketchExporter`

**Module graph**

![aws_turbinia_ts](_static/graphviz/aws_turbinia_ts.png)

----

## `azure_forensics`

Copies a disk from an Azure account to an analysis VM.

**Details:**

Copies a disk from an Azure account, creates an analysis VM in Azure (with a startup script containing installation instructions for basic forensics tooling), and attaches the copied disk to it.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['remote_profile_name', 'Name of the Azure profile pointing to the Azure account where the disk(s) exist(s).', None]`|`None`|
`['analysis_resource_group_name', 'The Azure resource group name in which to create the VM.', None]`|`None`|
`['incident_id', 'Incident ID to label the VM with.', None]`|`None`|
`['ssh_public_key', 'A SSH public key string to add to the VM (e.g. `ssh-rsa AAAAB3NzaC1y...`).', None]`|`None`|
`['--instance_name', 'Instance name of the instance to analyze.', None]`|`None`|
`['--disk_names', 'Comma-separated list of disk names to copy.', None]`|`None`|
`['--all_disks', 'Copy all disks in the designated instance. Overrides `disk_names` if specified.', False]`|`None`|
`['--boot_disk_size', "The size of the analysis VM's boot disk (in GB).", 50]`|`None`|
`['--analysis_region', 'The Azure region in which to create the VM.', None]`|`None`|
`['--analysis_profile_name', 'Name of the Azure profile to use when creating the analysis VM.', None]`|`None`|




Modules: `AzureCollector`

**Module graph**

![azure_forensics](_static/graphviz/azure_forensics.png)

----

## `azure_logging_collect`

Collects logs from an Azure subscription and dumps the results to the filesystem.

**Details:**

Collects logs from an Azure subscription using a specified filter, and dumps them on the filesystem.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['subscription_id', 'Subscription ID for the subscription to collect logs from.', None]`|`None`|
`['filter_expression', 'A filter expression to use for the log query, must specify at least a start date like "eventTimestamp ge \'2022-02-01\'"', None]`|`None`|
`['--profile_name', 'A profile name to use when looking for Azure credentials.', None]`|`None`|




Modules: `AzureLogsCollector`

**Module graph**

![azure_logging_collect](_static/graphviz/azure_logging_collect.png)

----

## `azure_logging_ts`

Collects logs from an Azure subscription, processes the logs with Plaso and uploads the result to Timesketch.

**Details:**

Collects logs from an Azure subscription using a specified query filter and date ranges, processes the logs with plaso and uploads the result to Timesketch.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['subscription_id', 'Subscription ID for the subscription to collect logs from.', None]`|`None`|
`['filter_expression', 'A filter expression to use for the log query, must specify at least a start date like "eventTimestamp ge \'2022-02-01\'"', None]`|`None`|
`['--profile_name', 'A profile name to use when looking for Azure credentials.', None]`|`None`|
`['--incident_id', 'Incident ID (used for Timesketch description).', None]`|`None`|
`['--sketch_id', 'Timesketch sketch to which the timeline should be added.', None]`|`None`|
`['--token_password', 'Optional custom password to decrypt Timesketch credential file with.', '']`|`None`|
`['--wait_for_timelines', 'Whether to wait for Timesketch to finish processing all timelines.', True]`|`None`|




Modules: `AzureLogsCollector`, `LocalPlasoProcessor`, `TimesketchExporter`

**Module graph**

![azure_logging_ts](_static/graphviz/azure_logging_ts.png)

----

## `bigquery_collect`

Collects results from BigQuery and dumps them on the filesystem.

**Details:**

Collects results from BigQuery in a GCP project and dumps them in JSONL on the local filesystem.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['project_name', 'Name of GCP project to collect logs from.', None]`|`None`|
`['query', 'Query to execute.', None]`|`None`|
`['description', 'Human-readable description of the query.', None]`|`None`|




Modules: `BigQueryCollector`

**Module graph**

![bigquery_collect](_static/graphviz/bigquery_collect.png)

----

## `bigquery_ts`

Collects results from BigQuery and uploads them to Timesketch.

**Details:**

Collects results from BigQuery in JSONL form, dumps them to the filesystem, and uploads them to Timesketch.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['project_name', 'Name of GCP project to collect logs from.', None]`|`None`|
`['query', 'Query to execute.', None]`|`None`|
`['description', 'Human-readable description of the query.', None]`|`None`|
`['--incident_id', 'Incident ID (used for Timesketch description).', None]`|`None`|
`['--sketch_id', 'Timesketch sketch to which the timeline should be added.', None]`|`None`|
`['--token_password', 'Optional custom password to decrypt Timesketch credential file with.', '']`|`None`|
`['--wait_for_timelines', 'Whether to wait for Timesketch to finish processing all timelines.', True]`|`None`|




Modules: `BigQueryCollector`, `TimesketchExporter`

**Module graph**

![bigquery_ts](_static/graphviz/bigquery_ts.png)

----

## `gce_disk_copy`

Copy disks from one project to another.

**Details:**

Copies disks from one project to another. The disks can be specified individually, or instances can be specified, to copy all their disks or boot disks.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['source_project_name', 'Source project containing the disks to export.', None]`|`None`|
`['--destination_project_name', 'Project to where the disk images are exported. If not provided, source_project_name is used.', None]`|`None`|
`['--source_disk_names', 'Comma-separated list of disk names to export. If not provided, disks attached to `remote_instance_name` will be used.', None]`|`None`|
`['--remote_instance_names', 'Comma-separated list of instances in source project from which to copy disks. If not provided, `disk_names` will be used.', None]`|`None`|
`['--all_disks', "If True, copy all disks attached to the `remote_instance_names` instances. If False and `remote_instance_name` is provided, it will select the instance's boot disk.", False]`|`None`|
`['--zone', 'Destination zone for the disks to be copied to.', 'us-central1-f']`|`None`|
`['--stop_instances', 'Stop instances after disks have been copied', False]`|`None`|




Modules: `GCEDiskCopy`

**Module graph**

![gce_disk_copy](_static/graphviz/gce_disk_copy.png)

----

## `gce_disk_export`

Export a disk image from a GCP project to a Google Cloud Storage bucket.

**Details:**

Creates a disk image from Google Compute persistent disks, compresses the images, and exports them to Google Cloud Storage.

The exported images names are appended by `.tar.gz.`

As this export happens through a Cloud Build job, the default service account `[PROJECT-NUMBER]@cloudbuild.gserviceaccount.com` in the source or analysis project (if provided) must have the IAM role `[Storage Admin]` on their corresponding project's storage bucket/folder.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['source_project_name', 'Source project containing the disk to export.', None]`|`None`|
`['gcs_output_location', 'Google Cloud Storage parent bucket/folder to which to export the image.', None]`|`None`|
`['--analysis_project_name', 'Project where the disk image is created then exported. If not provided, the image is exported to a bucket in the source project.', None]`|`None`|
`['--source_disk_names', 'Comma-separated list of disk names to export. If not provided, disks attached to `remote_instance_name` will be used.', None]`|`None`|
`['--remote_instance_name', 'Instance in source project to export its disks. If not provided, `disk_names` will be used.', None]`|`None`|
`['--all_disks', "If True, copy all disks attached to the `remote_instance_name` instance. If False and `remote_instance_name` is provided, it will select the instance's boot disk.", False]`|`None`|
`['--exported_image_name', "Name of the output file, must comply with `^[A-Za-z0-9-]*$` and `'.tar.gz'` will be appended to the name. If not provided or if more than one disk is selected, the exported image will be named `exported-image-{TIMESTAMP('%Y%m%d%H%M%S')}`.", None]`|`None`|




Modules: `GoogleCloudDiskExport`

**Module graph**

![gce_disk_export](_static/graphviz/gce_disk_export.png)

----

## `gce_disk_export_dd`

Stream the disk bytes from a GCP project to a Google Cloud Storage bucket.

**Details:**

The export is performed via bit streaming the the disk bytes to GCS. This will allow getting a disk image out of the project in case both organization policies `constraints/compute.storageResourceUseRestrictions` and `constraints/compute.trustedImageProjects` are enforced and in case OsLogin is allowed only for the organization users while the analyst is an external user with no roles/`compute.osLoginExternalUser` role.

The exported images names are appended by `.tar.gz.`

The compute engine default service account in the source project must have sufficient permissions to Create and List Storage objects on the corresponding storage bucket/folder. 

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['source_project_name', 'Source project containing the disk to export.', None]`|`None`|
`['gcs_output_location', 'Google Cloud Storage parent bucket/folder to which to export the image.', None]`|`None`|
`['--source_disk_names', 'Comma-separated list of disk names to export. If not provided, disks attached to `remote_instance_name` will be used.', None]`|`None`|
`['--remote_instance_name', 'Instance in source project to export its disks. If not provided, `source_disk_names ` will be used.', None]`|`None`|
`['--all_disks', "If True, copy all disks attached to the `remote_instance_name` instance. If False and `remote_instance_name` is provided, it will select the instance's boot disk.", False]`|`None`|
`['--boot_image_project', 'Name of the project where the boot disk image of the export VM is stored.', 'debian-cloud']`|`None`|
`['--boot_image_family', 'Name of the image to use to create the boot disk of the export VM.', 'debian-10']`|`None`|




Modules: `GoogleCloudDiskExportStream`

**Module graph**

![gce_disk_export_dd](_static/graphviz/gce_disk_export_dd.png)

----

## `gcp_cloud_resource_tree`

Generates a parent/children tree for given GCP resource.

**Details:**

Generates a parent/children tree for given GCP resource by enumerating all the currently available resources. It also will attempt to fill any gaps identified in the tree through querying the GCP logs

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['project_id', 'ID of the project where the resource is located', None]`|`None`|
`['location', "Resource location (zone/region) or 'global'", None]`|`None`|
`['resource_type', 'Resource type (currently supported types: gce_instance, gce_disk, gce_image, gce_machine_image, gce_instance_template, gce_snapshot)', None]`|`None`|
`['--resource_id', 'Resource id', None]`|`None`|
`['--resource_name', 'Resource name', None]`|`None`|




Modules: `GCPCloudResourceTree`

**Module graph**

![gcp_cloud_resource_tree](_static/graphviz/gcp_cloud_resource_tree.png)

----

## `gcp_cloud_resource_tree_offline`

Generates a parent/children tree for given GCP resource using the supplied exported GCP logs

**Details:**

Generates a parent/children tree for given GCP resource using the supplied exported GCP logs

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['project_id', 'ID of the project where the resource is located', None]`|`None`|
`['location', "Resource location (zone/region) or 'global'", None]`|`None`|
`['resource_type', 'Resource type (currently supported types: gce_instance, gce_disk, gce_image, gce_machine_image, gce_instance_template, gce_snapshot)', None]`|`None`|
`['paths', 'Comma-separated paths to GCP log files. Log files should contain log entiries in json format.', None]`|`None`|
`['--resource_id', 'Resource id', None]`|`None`|
`['--resource_name', 'Resource name', None]`|`None`|




Modules: `FilesystemCollector`, `GCPCloudResourceTree`

**Module graph**

![gcp_cloud_resource_tree_offline](_static/graphviz/gcp_cloud_resource_tree_offline.png)

----

## `gcp_forensics`

Copies disk from a GCP project to an analysis VM.

**Details:**

Copies a persistent disk from a GCP project to another, creates an analysis VM (with a startup script containing installation instructions for basic forensics tooling) in the destination project, and attaches the copied GCP persistent disk to it.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['source_project_name', 'Name of the project containing the instance / disks to copy.', None]`|`None`|
`['analysis_project_name', 'Name of the project where the analysis VM will be created and disks copied to.', None]`|`None`|
`['--incident_id', 'Incident ID to label the VM with.', None]`|`None`|
`['--instances', 'Name of the instance to analyze.', None]`|`None`|
`['--disks', 'Comma-separated list of disks to copy from the source GCP project (if `instance` not provided).', None]`|`None`|
`['--all_disks', 'Copy all disks in the designated instance. Overrides `disk_names` if specified.', False]`|`None`|
`['--stop_instances', 'Stop the designated instance after copying disks.', False]`|`None`|
`['--create_analysis_vm', 'Create an analysis VM in the destination project.', True]`|`None`|
`['--cpu_cores', 'Number of CPU cores of the analysis VM.', 4]`|`None`|
`['--boot_disk_size', 'The size of the analysis VM boot disk (in GB).', 50.0]`|`None`|
`['--boot_disk_type', 'Disk type to use [pd-standard, pd-ssd].', 'pd-standard']`|`None`|
`['--zone', 'The GCP zone where the Analysis VM and copied disks will be created.', 'us-central1-f']`|`None`|




Modules: `GCEDiskCopy`, `GCEForensicsVM`

**Module graph**

![gcp_forensics](_static/graphviz/gcp_forensics.png)

----

## `gcp_logging_cloudaudit_ts`

Collects GCP logs from a project and exports them to Timesketch.

**Details:**

Collects GCP logs from a project and exports them to Timesketch. Some light processing is made to translate the logs into something Timesketch can process.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['project_name', 'Name of the GCP project to collect logs from.', None]`|`None`|
`['start_date', 'Start date (yyyy-mm-ddTHH:MM:SSZ).', None]`|`None`|
`['end_date', 'End date (yyyy-mm-ddTHH:MM:SSZ).', None]`|`None`|
`['--incident_id', 'Incident ID (used for Timesketch description).', None]`|`None`|
`['--sketch_id', 'Timesketch sketch to which the timeline should be added.', None]`|`None`|
`['--token_password', 'Optional custom password to decrypt Timesketch credential file with.', '']`|`None`|
`['--wait_for_timelines', 'Whether to wait for Timesketch to finish processing all timelines.', True]`|`None`|
`['--backoff', 'If GCP Cloud Logging API query limits are exceeded, retry with an increased delay between each query to try complete the query at a slower rate.', False]`|`None`|
`['--delay', 'Number of seconds to wait between each GCP Cloud Logging query to avoid hitting API query limits', 0]`|`None`|




Modules: `GCPLogsCollector`, `LocalPlasoProcessor`, `TimesketchExporter`

**Module graph**

![gcp_logging_cloudaudit_ts](_static/graphviz/gcp_logging_cloudaudit_ts.png)

----

## `gcp_logging_cloudsql_ts`

Collects GCP related to Cloud SQL instances in a project and exports them to Timesketch.

**Details:**

Collects GCP related to Cloud SQL instances in a project and exports them to Timesketch. Some light processing is made to translate the logs into something Timesketch can process.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['project_name', 'Name of the GCP project to collect logs from.', None]`|`None`|
`['start_date', 'Start date (yyyy-mm-ddTHH:MM:SSZ).', None]`|`None`|
`['end_date', 'End date (yyyy-mm-ddTHH:MM:SSZ).', None]`|`None`|
`['--incident_id', 'Incident ID (used for Timesketch description).', None]`|`None`|
`['--sketch_id', 'Timesketch sketch to which the timeline should be added.', None]`|`None`|
`['--token_password', 'Optional custom password to decrypt Timesketch credential file with.', '']`|`None`|
`['--wait_for_timelines', 'Whether to wait for Timesketch to finish processing all timelines.', True]`|`None`|
`['--backoff', 'If GCP Cloud Logging API query limits are exceeded, retry with an increased delay between each query to try complete the query at a slower rate.', False]`|`None`|
`['--delay', 'Number of seconds to wait between each GCP Cloud Logging query to avoid hitting API query limits', 0]`|`None`|




Modules: `GCPLogsCollector`, `LocalPlasoProcessor`, `TimesketchExporter`

**Module graph**

![gcp_logging_cloudsql_ts](_static/graphviz/gcp_logging_cloudsql_ts.png)

----

## `gcp_logging_collect`

Collects logs from a GCP project and dumps on the filesystem (JSON). https://cloud.google.com/logging/docs/view/query-library for example queries.

**Details:**

Collects logs from a GCP project and dumps on the filesystem.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['project_name', 'Name of the GCP project to collect logs from.', None]`|`None`|
`['filter_expression', 'Filter expression to use to query GCP logs. See https://cloud.google.com/logging/docs/view/query-library for examples.', "resource.type = 'gce_instance'"]`|`None`|
`['--backoff', 'If GCP Cloud Logging API query limits are exceeded, retry with an increased delay between each query to try complete the query at a slower rate.', False]`|`None`|
`['--delay', 'Number of seconds to wait between each GCP Cloud Logging query to avoid hitting API query limits', 0]`|`None`|




Modules: `GCPLogsCollector`

**Module graph**

![gcp_logging_collect](_static/graphviz/gcp_logging_collect.png)

----

## `gcp_logging_gce_instance_ts`

GCP Instance Cloud Audit logs to Timesketch

**Details:**

Collects GCP Cloud Audit Logs for a GCE instance and exports them to Timesketch. Some light processing is made to translate the logs into something Timesketch can process.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['project_name', 'Name of the GCP project to collect logs from.', None]`|`None`|
`['instance_id', 'Identifier for GCE instance (Instance ID).', None]`|`None`|
`['--incident_id', 'Incident ID (used for Timesketch description).', None]`|`None`|
`['--sketch_id', 'Timesketch sketch to which the timeline should be added.', None]`|`None`|
`['--token_password', 'Optional custom password to decrypt Timesketch credential file with.', '']`|`None`|
`['--wait_for_timelines', 'Whether to wait for Timesketch to finish processing all timelines.', True]`|`None`|
`['--backoff', 'If GCP Cloud Logging API query limits are exceeded, retry with an increased delay between each query to try complete the query at a slower rate.', False]`|`None`|
`['--delay', 'Number of seconds to wait between each GCP Cloud Logging query to avoid hitting API query limits', 0]`|`None`|




Modules: `GCPLogsCollector`, `LocalPlasoProcessor`, `TimesketchExporter`

**Module graph**

![gcp_logging_gce_instance_ts](_static/graphviz/gcp_logging_gce_instance_ts.png)

----

## `gcp_logging_gce_ts`

Loads all GCE Cloud Audit Logs in a GCP project into Timesketch.

**Details:**

Loads all GCE Cloud Audit Logs for all instances in a GCP project into Timesketch. Some light processing is made to translate the logs into something Timesketch can process.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['project_name', 'Name of the GCP project to collect logs from.', None]`|`None`|
`['start_date', 'Start date (yyyy-mm-ddTHH:MM:SSZ).', None]`|`None`|
`['end_date', 'End date (yyyy-mm-ddTHH:MM:SSZ).', None]`|`None`|
`['--incident_id', 'Incident ID (used for Timesketch description).', None]`|`None`|
`['--sketch_id', 'Timesketch sketch to which the timeline should be added.', None]`|`None`|
`['--token_password', 'Optional custom password to decrypt Timesketch credential file with.', '']`|`None`|
`['--wait_for_timelines', 'Whether to wait for Timesketch to finish processing all timelines.', True]`|`None`|
`['--backoff', 'If GCP Cloud Logging API query limits are exceeded, retry with an increased delay between each query to try complete the query at a slower rate.', False]`|`None`|
`['--delay', 'Number of seconds to wait between each GCP Cloud Logging query to avoid hitting API query limits', 0]`|`None`|




Modules: `GCPLogsCollector`, `LocalPlasoProcessor`, `TimesketchExporter`

**Module graph**

![gcp_logging_gce_ts](_static/graphviz/gcp_logging_gce_ts.png)

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

Parameter|Default value|Description
---------|-------------|-----------
`['source_project_name', 'Name of the project containing the instance / disks to copy.', None]`|`None`|
`['analysis_project_name', 'Name of the project containing the Turbinia instance.', None]`|`None`|
`['--turbinia_recipe', 'The Turbinia recipe name to use for evidence processing.', None]`|`None`|
`['--turbinia_zone', 'The GCP zone the disk to process and Turbinia workers are in.', 'us-central1-f']`|`None`|
`['--incident_id', 'Incident ID (used for Timesketch description and to label the VM with).', None]`|`None`|
`['--sketch_id', 'Timesketch sketch to which the timeline should be added.', None]`|`None`|
`['--token_password', 'Optional custom password to decrypt Timesketch credential file with.', '']`|`None`|
`['--create_analysis_vm', 'Create an analysis VM in the destination project.', True]`|`None`|
`['--wait_for_timelines', 'Whether to wait for Timesketch to finish processing all timelines.', True]`|`None`|
`['--instances', 'Name of the instances to analyze.', None]`|`None`|
`['--disks', 'Comma-separated list of disks to copy from the source GCP project (if `instance` not provided).', None]`|`None`|
`['--all_disks', 'Copy all disks in the designated instance. Overrides disk_names if specified.', False]`|`None`|
`['--stop_instances', 'Stop the designated instances after copying disks.', False]`|`None`|
`['--cpu_cores', 'Number of CPU cores of the analysis VM.', 4]`|`None`|
`['--boot_disk_size', 'The size of the analysis VM boot disk (in GB).', 50.0]`|`None`|
`['--boot_disk_type', 'Disk type to use [pd-standard, pd-ssd]', 'pd-standard']`|`None`|
`['--image_project', 'Name of the project where the analysis VM image is hosted.', 'ubuntu-os-cloud']`|`None`|
`['--image_family', 'Name of the image to use to create the analysis VM.', 'ubuntu-1804-lts']`|`None`|




Modules: `GCEDiskCopy`, `GCEForensicsVM`, `TurbiniaGCPProcessor`, `TimesketchExporter`

**Module graph**

![gcp_turbinia_disk_copy_ts](_static/graphviz/gcp_turbinia_disk_copy_ts.png)

----

## `gcp_turbinia_ts`

Processes existing GCP persistent disks with Turbinia project and sends results to Timesketch.

**Details:**

Process GCP persistent disks with Turbinia and send output to Timesketch.

This processes disks that are already in the project where Turbinia exists. If you want to copy disks from another project, use the `gcp_turbinia_disk_copy_ts` recipe.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['analysis_project_name', 'Name of GCP project the disk exists in.', None]`|`None`|
`['turbinia_zone', 'The GCP zone the disk to process (and Turbinia workers) are in.', None]`|`None`|
`['disk_names', 'Names of GCP persistent disks to process.', None]`|`None`|
`['--incident_id', 'Incident ID (used for Timesketch description).', None]`|`None`|
`['--sketch_id', 'Timesketch sketch to which the timeline should be added.', None]`|`None`|
`['--token_password', 'Optional custom password to decrypt Timesketch credential file with.', '']`|`None`|
`['--turbinia_recipe', 'The Turbinia recipe name to use for evidence processing.', None]`|`None`|
`['--wait_for_timelines', 'Whether to wait for Timesketch to finish processing all timelines.', True]`|`None`|




Modules: `TurbiniaGCPProcessor`, `TimesketchExporter`

**Module graph**

![gcp_turbinia_ts](_static/graphviz/gcp_turbinia_ts.png)

----

## `grr_artifact_grep`

Fetches ForensicArtifacts from GRR hosts and runs grep with a list of keywords on them.

**Details:**

Collect ForensicArtifacts from hosts using GRR.

- Collect a predefined list of artifacts from hosts using GRR
- Process them locally with grep to extract keywords.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['hostnames', 'Comma-separated list of hostnames or GRR client IDs to process.', None]`|`None`|
`['reason', 'Reason for collection.', None]`|`None`|
`['keywords', 'Pipe-separated list of keywords to search for (e.g. key1|key2|key3.', None]`|`None`|
`['--artifacts', 'Comma-separated list of artifacts to fetch (override default artifacts).', None]`|`None`|
`['--extra_artifacts', 'Comma-separated list of artifacts to append to the default artifact list.', None]`|`None`|
`['--use_raw_filesystem_access', 'Use raw disk access to fetch artifacts.', False]`|`None`|
`['--approvers', 'Emails for GRR approval request.', None]`|`None`|
`['--grr_server_url', 'GRR endpoint.', 'http://localhost:8000']`|`None`|
`['--verify', 'Whether to verify the GRR TLS certificate.', True]`|`None`|
`['--skip_offline_clients', 'Whether to skip clients that are offline.', False]`|`None`|
`['--grr_username', 'GRR username.', 'admin']`|`None`|
`['--grr_password', 'GRR password.', 'admin']`|`None`|
`['--max_file_size', 'Maximum size of files to collect (in bytes).', 5368709120]`|`None`|




Modules: `GRRArtifactCollector`, `GrepperSearch`

**Module graph**

![grr_artifact_grep](_static/graphviz/grr_artifact_grep.png)

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

Parameter|Default value|Description
---------|-------------|-----------
`['hostnames', 'Comma-separated list of hostnames or GRR client IDs to process.', None]`|`None`|
`['reason', 'Reason for collection.', None]`|`None`|
`['--artifacts', 'Comma-separated list of artifacts to fetch (override default artifacts).', None]`|`None`|
`['--extra_artifacts', 'Comma-separated list of artifacts to append to the default artifact list.', None]`|`None`|
`['--use_raw_filesystem_access', 'Use raw disk access to fetch artifacts.', False]`|`None`|
`['--approvers', 'Emails for GRR approval request.', None]`|`None`|
`['--sketch_id', 'Timesketch sketch to which the timeline should be added.', None]`|`None`|
`['--wait_for_timelines', 'Whether to wait for Timesketch to finish processing all timelines.', True]`|`None`|
`['--analyzers', 'Timesketch analyzers to run', None]`|`None`|
`['--token_password', 'Optional custom password to decrypt Timesketch credential file with.', '']`|`None`|
`['--incident_id', 'Incident ID (used for Timesketch description).', None]`|`None`|
`['--grr_server_url', 'GRR endpoint.', 'http://localhost:8000']`|`None`|
`['--verify', 'Whether to verify the GRR TLS certificate.', True]`|`None`|
`['--skip_offline_clients', 'Whether to skip clients that are offline.', False]`|`None`|
`['--grr_username', 'GRR username', 'admin']`|`None`|
`['--grr_password', 'GRR password', 'admin']`|`None`|
`['--max_file_size', 'Maximum size of files to collect (in bytes).', 5368709120]`|`None`|




Modules: `GRRArtifactCollector`, `LocalPlasoProcessor`, `TimesketchExporter`

**Module graph**

![grr_artifact_ts](_static/graphviz/grr_artifact_ts.png)

----

## `grr_files_collect`

Collects specific files from one or more GRR hosts.

**Details:**

Collects specific files from one or more GRR hosts. Files can be a glob pattern (e.g. `/tmp/*.so`) and support GRR variable interpolation (e.g. `%%users.localappdata%%/Directory/`) 

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['hostnames', 'Comma-separated list of hostnames or GRR client IDs to process.', None]`|`None`|
`['reason', 'Reason for collection.', None]`|`None`|
`['files', 'Comma-separated list of files to fetch (supports globs and GRR variable interpolation).', None]`|`None`|
`['directory', 'Directory in which to export files.', None]`|`None`|
`['--use_raw_filesystem_access', 'Use raw disk access to fetch artifacts.', False]`|`None`|
`['--approvers', 'Emails for GRR approval request.', None]`|`None`|
`['--verify', 'Whether to verify the GRR TLS certificate.', True]`|`None`|
`['--skip_offline_clients', 'Whether to skip clients that are offline.', False]`|`None`|
`['--action', 'String denoting action (download/hash/stat) to take', 'download']`|`None`|
`['--grr_server_url', 'GRR endpoint', 'http://localhost:8000']`|`None`|
`['--grr_username', 'GRR username', 'admin']`|`None`|
`['--grr_password', 'GRR password', 'admin']`|`None`|
`['--max_file_size', 'Maximum size of files to collect (in bytes).', 5368709120]`|`None`|




Modules: `GRRFileCollector`, `LocalFilesystemCopy`

**Module graph**

![grr_files_collect](_static/graphviz/grr_files_collect.png)

----

## `grr_flow_collect`

Download the result of a GRR flow to the local filesystem.

**Details:**

Download the result of a GRR flow to the local filesystem. Flow IDs are unique *per client*, so both need to be provided in sequence.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['hostnames', 'Hostname(s) to collect the flow from.', None]`|`None`|
`['flow_ids', 'Flow ID(s) to download.', None]`|`None`|
`['reason', 'Reason for collection.', None]`|`None`|
`['directory', 'Directory in which to export files.', None]`|`None`|
`['--approvers', 'Emails for GRR approval request.', None]`|`None`|
`['--grr_server_url', 'GRR endpoint', 'http://localhost:8000']`|`None`|
`['--verify', 'Whether to verify the GRR TLS certificate.', True]`|`None`|
`['--skip_offline_clients', 'Whether to skip clients that are offline.', False]`|`None`|
`['--grr_username', 'GRR username', 'admin']`|`None`|
`['--grr_password', 'GRR password', 'admin']`|`None`|




Modules: `GRRFlowCollector`, `LocalFilesystemCopy`

**Module graph**

![grr_flow_collect](_static/graphviz/grr_flow_collect.png)

----

## `grr_hunt_artifacts`

Starts a GRR hunt for the default set of artifacts.

**Details:**

Starts a GRR artifact hunt and provides the Hunt ID to the user. Feed the Hunt ID to `grr_huntresults_ts` to process results through Plaso and export them to Timesketch.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['artifacts', 'Comma-separated list of artifacts to hunt for.', None]`|`None`|
`['reason', 'Reason for collection.', None]`|`None`|
`['--use_raw_filesystem_access', 'Use raw disk access to fetch artifacts.', False]`|`None`|
`['--approvers', 'Emails for GRR approval request.', None]`|`None`|
`['--grr_server_url', 'GRR endpoint', 'http://localhost:8000']`|`None`|
`['--verify', 'Whether to verify the GRR TLS certificate.', True]`|`None`|
`['--grr_username', 'GRR username', 'admin']`|`None`|
`['--grr_password', 'GRR password', 'admin']`|`None`|
`['--max_file_size', 'Maximum size of files to collect (in bytes).', 5368709120]`|`None`|
`['--match_mode', 'Match mode of the client rule set (ANY or ALL)', None]`|`None`|
`['--client_operating_systems', 'Comma-separated list of client operating systems to filter hosts on (linux, osx, win).', None]`|`None`|
`['--client_labels', 'Comma-separated list of client labels to filter GRR hosts on.', None]`|`None`|




Modules: `GRRHuntArtifactCollector`

**Module graph**

![grr_hunt_artifacts](_static/graphviz/grr_hunt_artifacts.png)

----

## `grr_hunt_file`

Starts a GRR hunt for a list of files.

**Details:**

Starts a GRR hunt for a list of files and provides a Hunt ID to the user. Feed the Hunt ID to `grr_huntresults_ts` to process results through Plaso and export them to Timesketch.

Like in `grr_files_collect`, files can be globs and support variable interpolation.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['file_path_list', 'Comma-separated list of file paths to hunt for.', None]`|`None`|
`['reason', 'Reason for collection.', None]`|`None`|
`['--approvers', 'Emails for GRR approval request.', None]`|`None`|
`['--grr_server_url', 'GRR endpoint', 'http://localhost:8000']`|`None`|
`['--verify', 'Whether to verify the GRR TLS certificate.', True]`|`None`|
`['--grr_username', 'GRR username', 'admin']`|`None`|
`['--grr_password', 'GRR password', 'admin']`|`None`|
`['--max_file_size', 'Maximum size of files to collect (in bytes).', 5368709120]`|`None`|
`['--match_mode', 'Match mode of the client rule set (ANY or ALL)', None]`|`None`|
`['--client_operating_systems', 'Comma-separated list of client operating systems to filter hosts on (linux, osx, win).', None]`|`None`|
`['--client_labels', 'Comma-separated list of client labels to filter GRR hosts on.', None]`|`None`|




Modules: `GRRHuntFileCollector`

**Module graph**

![grr_hunt_file](_static/graphviz/grr_hunt_file.png)

----

## `grr_hunt_osquery`

Starts a GRR hunt for an Osquery flow.

**Details:**

Starts a GRR osquery hunt and provides the Hunt ID to the user.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['reason', 'Reason for collection.', None]`|`None`|
`['--osquery_query', 'Osquery query to hunt for.', None]`|`None`|
`['--osquery_paths', 'Path(s) to text file containing one osquery query per line.', None]`|`None`|
`['--timeout_millis', 'Osquery timeout in milliseconds', 300000]`|`None`|
`['--ignore_stderr_errors', 'Ignore osquery stderr errors', False]`|`None`|
`['--approvers', 'Emails for GRR approval request.', None]`|`None`|
`['--grr_server_url', 'GRR endpoint', 'http://localhost:8000']`|`None`|
`['--verify', 'Whether to verify the GRR TLS certificate.', True]`|`None`|
`['--grr_username', 'GRR username', 'admin']`|`None`|
`['--grr_password', 'GRR password', 'admin']`|`None`|
`['--match_mode', 'Match mode of the client rule set (ANY or ALL)', None]`|`None`|
`['--client_operating_systems', 'Comma-separated list of client operating systems to filter hosts on (linux, osx, win).', None]`|`None`|
`['--client_labels', 'Comma-separated list of client labels to filter GRR hosts on.', None]`|`None`|




Modules: `OsqueryCollector`, `GRRHuntOsqueryCollector`

**Module graph**

![grr_hunt_osquery](_static/graphviz/grr_hunt_osquery.png)

----

## `grr_huntresults_ts`

Fetches the results of a GRR hunt, processes them with Plaso, and exports the results to Timesketch.

**Details:**

Download the results of a GRR hunt and process them.

- Collect results of a hunt given its Hunt ID
- Processes results with a local install of Plaso
- Exports processed items to a new Timesketch sketch

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['hunt_id', 'ID of GRR Hunt results to fetch.', None]`|`None`|
`['reason', 'Reason for exporting hunt (used for Timesketch description).', None]`|`None`|
`['--sketch_id', 'Timesketch sketch to which the timeline should be added.', None]`|`None`|
`['--token_password', 'Optional custom password to decrypt Timesketch credential file with.', '']`|`None`|
`['--wait_for_timelines', 'Whether to wait for Timesketch to finish processing all timelines.', True]`|`None`|
`['--approvers', 'Emails for GRR approval request.', None]`|`None`|
`['--grr_server_url', 'GRR endpoint', 'http://localhost:8000']`|`None`|
`['--verify', 'Whether to verify the GRR TLS certificate.', True]`|`None`|
`['--grr_username', 'GRR username', 'admin']`|`None`|
`['--grr_password', 'GRR password', 'admin']`|`None`|




Modules: `GRRHuntDownloader`, `LocalPlasoProcessor`, `TimesketchExporter`

**Module graph**

![grr_huntresults_ts](_static/graphviz/grr_huntresults_ts.png)

----

## `grr_osquery_flow`

Runs osquery on GRR hosts and save any results to local CSV files.

**Details:**

Runs osquery on GRR hosts and save any results to local CSV files.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['reason', 'Reason for collection.', None]`|`None`|
`['hostnames', 'Hostname(s) to collect the osquery flow from.', None]`|`None`|
`['--osquery_query', 'Osquery query to hunt for.', None]`|`None`|
`['--osquery_paths', 'Path(s) to text file containing one osquery query per line.', None]`|`None`|
`['--timeout_millis', 'Osquery timeout in milliseconds', 300000]`|`None`|
`['--ignore_stderr_errors', 'Ignore osquery stderr errors', False]`|`None`|
`['--directory', 'Directory in which to export results.', None]`|`None`|
`['--approvers', 'Emails for GRR approval request.', None]`|`None`|
`['--grr_server_url', 'GRR endpoint', 'http://localhost:8000']`|`None`|
`['--verify', 'Whether to verify the GRR TLS certificate.', True]`|`None`|
`['--skip_offline_clients', 'Whether to skip clients that are offline.', False]`|`None`|
`['--grr_username', 'GRR username', 'admin']`|`None`|
`['--grr_password', 'GRR password', 'admin']`|`None`|




Modules: `OsqueryCollector`, `GRROsqueryCollector`

**Module graph**

![grr_osquery_flow](_static/graphviz/grr_osquery_flow.png)

----

## `grr_timeline_ts`

Runs a TimelineFlow on a set of GRR hosts, generating a filesystem bodyfile for each host. These bodyfiles are processed results with Plaso, and the resulting plaso files are exported to Timesketch.

**Details:**

Uses the GRR TimelineFlow to generate a filesystem timeline and exports it to Timesketch..

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['hostnames', 'Comma-separated list of hostnames or GRR client IDs to process.', None]`|`None`|
`['root_path', 'Root path for timeline generation.', '/']`|`None`|
`['reason', 'Reason for collection.', None]`|`None`|
`['--skip_offline_clients', 'Whether to skip clients that are offline.', False]`|`None`|
`['--approvers', 'Comma-separated list of usernames to ask for approval.', None]`|`None`|
`['--sketch_id', 'Timesketch sketch to which the timeline should be added.', None]`|`None`|
`['--grr_server_url', 'GRR endpoint.', 'http://localhost:8000']`|`None`|
`['--token_password', 'Optional custom password to decrypt Timesketch credential file with.', '']`|`None`|
`['--timesketch_quick', 'Skip waiting for analyzers to complete their run.', False]`|`None`|
`['--wait_for_timelines', 'Whether to wait for Timesketch to finish processing all timelines.', True]`|`None`|
`['--grr_username', 'GRR username.', 'admin']`|`None`|
`['--grr_password', 'GRR password.', 'admin']`|`None`|




Modules: `GRRTimelineCollector`, `LocalPlasoProcessor`, `TimesketchExporter`, `TimesketchEnhancer`

**Module graph**

![grr_timeline_ts](_static/graphviz/grr_timeline_ts.png)

----

## `grr_yarascan`

Run Yara rules on hosts memory.

**Details:**

Run Yara rules on hosts memory.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['reason', 'Reason for collection.', None]`|`None`|
`['hostnames', 'Hostname(s) to collect the flow from.', None]`|`None`|
`['--yara_name_filter', 'Filter to filter Yara sigs by.', None]`|`None`|
`['--api_key', 'API Key to the Yeti instance', None]`|`None`|
`['--api_root', 'API root of the Yeti instance (e.g. http://localhost/api/)', 'http://localhost/api/']`|`None`|
`['--approvers', 'Emails for GRR approval request.', None]`|`None`|
`['--grr_server_url', 'GRR endpoint', 'http://localhost:8000']`|`None`|
`['--verify', 'Whether to verify the GRR TLS certificate.', True]`|`None`|
`['--skip_offline_clients', 'Whether to skip clients that are offline.', False]`|`None`|
`['--grr_username', 'GRR username', 'admin']`|`None`|
`['--grr_password', 'GRR password', 'demo']`|`None`|




Modules: `YetiYaraCollector`, `GRRYaraScanner`

**Module graph**

![grr_yarascan](_static/graphviz/grr_yarascan.png)

----

## `gsheets_ts`

Collects data from google sheets and outputs them to Timesketch.

**Details:**

Collects data from google sheets and outputs them to Timesketch.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['spreadsheet', 'ID or URL of the Google Sheet spreadsheet to collect data from.', None]`|`None`|
`['--sheet_names', 'Comma-separated list sheet names to collect date from. If not set all sheets in the spreadsheet will be parsed.', []]`|`None`|
`['--validate_columns', 'Set to True to check for mandatory columns required by Timesketch while extracting data. Set to False to ignore validation. Default is True.', True]`|`None`|
`['--sketch_id', 'Sketch to which the timeline should be added', None]`|`None`|
`['--token_password', 'Optional custom password to decrypt Timesketch credential file with', '']`|`None`|
`['--incident_id', 'Incident ID (used for Timesketch description)', None]`|`None`|
`['--wait_for_timelines', 'Whether to wait for timelines to finish processing.', True]`|`None`|




Modules: `GoogleSheetsCollector`, `TimesketchExporter`

**Module graph**

![gsheets_ts](_static/graphviz/gsheets_ts.png)

----

## `plaso_ts`

Processes a list of file paths using a Plaso and export results to Timesketch.

**Details:**

Processes a list of file paths using Plaso and sends results to Timesketch.

- Collectors collect from a path in the FS
- Processes them with a local install of plaso
- Exports them to a new Timesketch sketch

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['paths', 'Comma-separated list of paths to process.', None]`|`None`|
`['--incident_id', 'Incident ID (used for Timesketch description).', None]`|`None`|
`['--sketch_id', 'Timesketch sketch to which the timeline should be added.', None]`|`None`|
`['--token_password', 'Optional custom password to decrypt Timesketch credential file with.', '']`|`None`|
`['--wait_for_timelines', 'Whether to wait for Timesketch to finish processing all timelines.', True]`|`None`|




Modules: `FilesystemCollector`, `LocalPlasoProcessor`, `TimesketchExporter`

**Module graph**

![plaso_ts](_static/graphviz/plaso_ts.png)

----

## `upload_ts`

Uploads a local CSV or Plaso file to Timesketch.

**Details:**

Uploads a CSV or Plaso file to Timesketch.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['files', 'Comma-separated list of paths to CSV files or Plaso storage files.', None]`|`None`|
`['--analyzers', 'Timesketch analyzers to run.', None]`|`None`|
`['--sketch_id', 'Timesketch sketch to which the timeline should be added.', None]`|`None`|
`['--token_password', 'Optional custom password to decrypt Timesketch credential file with.', '']`|`None`|
`['--incident_id', 'Incident ID (used for Timesketch description).', None]`|`None`|
`['--wait_for_timelines', 'Whether to wait for Timesketch to finish processing all timelines.', True]`|`None`|




Modules: `FilesystemCollector`, `TimesketchExporter`

**Module graph**

![upload_ts](_static/graphviz/upload_ts.png)

----

## `upload_turbinia`

Uploads arbitrary files to Turbinia and downloads results.

**Details:**

Uploads arbitrary files to Turbinia for processing. The recipe will wait for Turbinia to return with results and will download them back to the filesystem. The Turbinia system needs to be accessible via SSH.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['files', 'Paths to process.', None]`|`None`|
`['--turbinia_recipe', 'The Turbinia recipe name to use for evidence processing.', None]`|`None`|
`['--destination_turbinia_dir', 'Destination path in Turbinia host to write the files to.', None]`|`None`|
`['--hostname', 'Remote host.', None]`|`None`|
`['--directory', 'Directory in which to copy and compress files.', None]`|`None`|
`['--turbinia_config', 'Turbinia config file to use.', None]`|`None`|
`['--local_turbinia_results', 'Directory where Turbinia results will be downloaded to.', None]`|`None`|
`['--sketch_id', 'Timesketch sketch ID.', None]`|`None`|




Modules: `FilesystemCollector`, `LocalFilesystemCopy`, `SCP-Upload`, `TurbiniaArtifactProcessor`, `SCP-Download`

**Module graph**

![upload_turbinia](_static/graphviz/upload_turbinia.png)

----

## `upload_web_ts`

Uploads a CSV/JSONL or Plaso file to Timesketch and runs web-related Timesketch analyzers.

**Details:**

Uploads a CSV or Plaso file to Timesketch and runs a series of web-related analyzers on the uploaded data.

The following analyzers will run on the processed timeline: `browser_search,browser_timeframe,account_finder,phishy_domains,evtx_gap,login,win_crash,safebrowsing,chain`.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['files', 'Comma-separated list of paths to CSV files or Plaso storage files.', None]`|`None`|
`['--sketch_id', 'Timesketch sketch to which the timeline should be added.', None]`|`None`|
`['--token_password', 'Optional custom password to decrypt Timesketch credential file with.', '']`|`None`|
`['--incident_id', 'Incident ID (used for Timesketch description).', None]`|`None`|
`['--wait_for_analyzers', 'Wait for analyzers until they complete their run, if set to False the TS enhancer will be skipped.', True]`|`None`|
`['--timesketch_include_stories', 'Include story dumps in reports.', False]`|`None`|
`['--searches_to_skip', 'A comma separated list of saved searches that should not be uploaded.', None]`|`None`|
`['--analyzer_max_checks', 'Number of wait cycles (per cycle is 3 seconds) before terminating wait for analyzers to complete.', 0]`|`None`|
`['--aggregations_to_skip', 'A comma separated list of aggregation names that should not be uploaded.', None]`|`None`|




Modules: `FilesystemCollector`, `TimesketchExporter`, `TimesketchEnhancer`

**Module graph**

![upload_web_ts](_static/graphviz/upload_web_ts.png)

----

## `vt_evtx`

Downloads the EVTX files from VirusTotal for a specific hash.

**Details:**

Downloads the EVTX files from VirusTotal sandbox run for a specific hash, processes it with Plaso.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['hashes', 'Comma-separated list of hashes to process.', None]`|`None`|
`['directory', 'Directory in which to export files.', None]`|`None`|
`['--vt_api_key', 'Virustotal API key', 'admin']`|`None`|




Modules: `VTCollector`, `LocalPlasoProcessor`

**Module graph**

![vt_evtx](_static/graphviz/vt_evtx.png)

----

## `vt_evtx_ts`

Downloads the EVTX from VirusTotal sandbox runs for a specific hash and uploads the corresponding timeline to Timesketch.

**Details:**

Downloads the EVTX file generated by VirusTotal during the sandbox runs for a specific hash, processes the EVTX files with Plaso and uploads the resulting Plaso file to Timesketch.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['hashes', 'Comma-separated list of hashes to process.', None]`|`None`|
`['directory', 'Directory in which to export files.', None]`|`None`|
`['--vt_api_key', 'Virustotal API key', 'admin']`|`None`|
`['--incident_id', 'Incident ID (used for Timesketch description).', None]`|`None`|
`['--sketch_id', 'Timesketch sketch to which the timeline should be added.', None]`|`None`|
`['--token_password', 'Optional custom password to decrypt Timesketch credential file with', '']`|`None`|
`['--wait_for_timelines', 'Whether to wait for Timesketch to finish processing all timelines.', True]`|`None`|




Modules: `VTCollector`, `LocalPlasoProcessor`, `TimesketchExporter`

**Module graph**

![vt_evtx_ts](_static/graphviz/vt_evtx_ts.png)

----

## `vt_pcap`

Downloads the PCAP from VirusTotal for a specific hash.

**Details:**

Downloads the PCAP files generated from VirusTotal sandbox's run for a specific hash.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['hashes', 'Comma-separated list of hashes to process.', None]`|`None`|
`['directory', 'Directory in which to export files.', None]`|`None`|
`['--vt_api_key', 'Virustotal API key', 'admin']`|`None`|




Modules: `VTCollector`, `LocalFilesystemCopy`

**Module graph**

![vt_pcap](_static/graphviz/vt_pcap.png)

----

## `workspace_logging_collect`

Collects Workspace Audit logs and dumps them on the filesystem.

**Details:**

Collects logs from Workspace Audit log and dumps them on the filesystem.

See https://developers.google.com/admin-sdk/reports/reference/rest/v1/activities/list#ApplicationName for a list of application names.

For filters, see https://developers.google.com/admin-sdk/reports/reference/rest/v1/activities/list.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['application_name', 'Name of application to to collect logs for. See https://developers.google.com/admin-sdk/reports/reference/rest/v1/activities/list#ApplicationName for a list of possible values.', None]`|`None`|
`['--user', 'email address of the user to query logs for', 'all']`|`None`|
`['--start_time', 'Start time (yyyy-mm-ddTHH:MM:SSZ).', None]`|`None`|
`['--end_time', 'End time (yyyy-mm-ddTHH:MM:SSZ).', None]`|`None`|
`['--filter_expression', 'Filter expression to use to query Workspace logs. See https://developers.google.com/admin-sdk/reports/reference/rest/v1/activities/list.', '']`|`None`|




Modules: `WorkspaceAuditCollector`

**Module graph**

![workspace_logging_collect](_static/graphviz/workspace_logging_collect.png)

----

## `workspace_meet_ts`

Collects Meet records and adds them to Timesketch

**Details:**

Collects Google Workspace audit records for a Google Meet and adds them to Timesketch.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['meeting_id', "ID for the Meeting to look up. (Without the '-' delimiter)", None]`|`None`|
`['--start_time', 'Start time (yyyy-mm-ddTHH:MM:SSZ).', None]`|`None`|
`['--end_time', 'End time (yyyy-mm-ddTHH:MM:SSZ).', None]`|`None`|
`['--incident_id', 'Incident ID (used for Timesketch description).', None]`|`None`|
`['--sketch_id', 'Timesketch sketch to which the timeline should be added.', None]`|`None`|
`['--token_password', 'Optional custom password to decrypt Timesketch credential file with.', '']`|`None`|
`['--wait_for_timelines', 'Whether to wait for Timesketch to finish processing all timelines.', True]`|`None`|




Modules: `WorkspaceAuditCollector`, `WorkspaceAuditTimesketch`, `TimesketchExporter`

**Module graph**

![workspace_meet_ts](_static/graphviz/workspace_meet_ts.png)

----

## `workspace_user_activity_ts`

Collects records for a Google Workspace user and adds them to Timesketch

**Details:**

Collects records for a Google Workspace user and adds them to Timesketch.

Collects logs for the following apps: `Login`, `Drive`, `Token`, `Chrome`, `CAA`, `DataStudio`, `GroupsEnterprise`, `Calendar`, `Chat`, `Groups`, `Meet`, `UserAccounts`.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['user', 'email address of the user to query logs for', '']`|`None`|
`['--start_time', 'Start time (yyyy-mm-ddTHH:MM:SSZ).', None]`|`None`|
`['--end_time', 'End time (yyyy-mm-ddTHH:MM:SSZ).', None]`|`None`|
`['--filter_expression', 'Filter expression to use to query Workspace logs. See https://developers.google.com/admin-sdk/reports/reference/rest/v1/activities/list', '']`|`None`|
`['--incident_id', 'Incident ID (used for Timesketch description).', None]`|`None`|
`['--sketch_id', 'Timesketch sketch to which the timeline should be added.', None]`|`None`|
`['--token_password', 'Optional custom password to decrypt Timesketch credential file with.', '']`|`None`|
`['--wait_for_timelines', 'Whether to wait for Timesketch to finish processing all timelines.', True]`|`None`|




Modules: `WorkspaceAuditCollector-Login`, `WorkspaceAuditCollector-Drive`, `WorkspaceAuditCollector-Token`, `WorkspaceAuditCollector-Chrome`, `WorkspaceAuditCollector-CAA`, `WorkspaceAuditCollector-DataStudio`, `WorkspaceAuditCollector-GroupsEnterprise`, `WorkspaceAuditCollector-Calendar`, `WorkspaceAuditCollector-Chat`, `WorkspaceAuditCollector-GCP`, `WorkspaceAuditCollector-Groups`, `WorkspaceAuditCollector-Meet`, `WorkspaceAuditCollector-UserAccounts`, `WorkspaceAuditTimesketch`, `TimesketchExporter`

**Module graph**

![workspace_user_activity_ts](_static/graphviz/workspace_user_activity_ts.png)

----

## `workspace_user_drive_ts`

Collects Drive records for a Workspace user and adds them to Timesketch

**Details:**

Collects Drive records for a Workspace user and adds them to Timesketch.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['user', 'email address of the user to query logs for', '']`|`None`|
`['--start_time', 'Start time (yyyy-mm-ddTHH:MM:SSZ).', None]`|`None`|
`['--end_time', 'End time (yyyy-mm-ddTHH:MM:SSZ).', None]`|`None`|
`['--filter_expression', 'Filter expression to use to query Workspace logs. See https://developers.google.com/admin-sdk/reports/reference/rest/v1/activities/list', '']`|`None`|
`['--incident_id', 'Incident ID (used for Timesketch description).', None]`|`None`|
`['--sketch_id', 'Timesketch sketch to which the timeline should be added.', None]`|`None`|
`['--token_password', 'Optional custom password to decrypt Timesketch credential file with.', '']`|`None`|
`['--wait_for_timelines', 'Whether to wait for Timesketch to finish processing all timelines.', True]`|`None`|




Modules: `WorkspaceAuditCollector`, `WorkspaceAuditTimesketch`, `TimesketchExporter`

**Module graph**

![workspace_user_drive_ts](_static/graphviz/workspace_user_drive_ts.png)

----

## `workspace_user_login_ts`

Collects login records and adds to Timesketch

**Details:**

Collects login records for a Workspace user and adds them to Timesketch.

**CLI parameters:**

Parameter|Default value|Description
---------|-------------|-----------
`['user', 'email address of the user to query logs for', '']`|`None`|
`['--start_time', 'Start time (yyyy-mm-ddTHH:MM:SSZ).', None]`|`None`|
`['--end_time', 'End time (yyyy-mm-ddTHH:MM:SSZ).', None]`|`None`|
`['--filter_expression', 'Filter expression to use to query Workspace logs. See https://developers.google.com/admin-sdk/reports/reference/rest/v1/activities/list', '']`|`None`|
`['--incident_id', 'Incident ID (used for Timesketch description).', None]`|`None`|
`['--sketch_id', 'Timesketch sketch to which the timeline should be added.', None]`|`None`|
`['--token_password', 'Optional custom password to decrypt Timesketch credential file with.', '']`|`None`|
`['--wait_for_timelines', 'Whether to wait for Timesketch to finish processing all timelines.', True]`|`None`|




Modules: `WorkspaceAuditCollector`, `WorkspaceAuditTimesketch`, `TimesketchExporter`

**Module graph**

![workspace_user_login_ts](_static/graphviz/workspace_user_login_ts.png)

----

