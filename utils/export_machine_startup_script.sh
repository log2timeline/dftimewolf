#!/bin/bash
#
# A GCE startup script to start a VM that loops on all disks attached to it and stream all the
# non-boot disks to a GCS bucket. After the export is done the script calculates the hash of 
# each disk and compares it to the hash of the export in GCS and updates the instance
# metadata and labels as well as the disks labels to reflect the export progress and
# integrity. The script installs all the required tools.

export CLOUDSDK_PYTHON=python3;
LOCKDIR="/tmp/add_label.lock";
if [[ -e "${{LOCKDIR}}" ]]
  then
     /bin/rm -r ${{LOCKDIR}}
  fi

function add_label(){{
  until ($( /bin/mkdir ${{LOCKDIR}}));
  do
    sleep_period=$(shuf -i 5-15 -n 1);
    logger "Updating labels is busy, re-trying in ${{sleep_period}} seconds."
    sleep ${{sleep_period}};
  done;
  /usr/bin/gcloud compute $1 -q \
  --project {project_id}  add-labels $2 --labels=$3 --zone={zone};
   /bin/rm -r ${{LOCKDIR}}
}}


LOCKDIR_2="/tmp/set_metadata.lock";
if [[ -e "${{LOCKDIR_2}}" ]]
  then
     /bin/rm -r ${{LOCKDIR_2}}
  fi

function set_metadata(){{
  until ($( /bin/mkdir ${{LOCKDIR_2}}));
  do
    sleep_period=$(shuf -i 5-15 -n 1);
    logger "Updating setting metadata is busy, re-trying in ${{sleep_period}} seconds."
    sleep ${{sleep_period}};
  done;
  /usr/bin/gcloud compute instances -q --project {project_id} add-metadata {instance_name} \
  --metadata=$1="$2\n$3" --zone={zone};
   /bin/rm -r ${{LOCKDIR_2}}
}}


function start_startup_prep(){{
  add_label instances {instance_name}  startup_script="started";
  add_label instances {instance_name}  startup_prep_starts=0;

  until startup_prep;
  do
     logger "startup_prep failed, re-trying in 3 seconds."
     sleep 3
  done;

  add_label instances {instance_name} startup_prep_starts=1;
}}

function startup_prep(){{
  tmp_dir=$( /bin/mktemp -d);
  cd ${{tmp_dir}};
  /usr/bin/apt -y update;
  /usr/bin/apt -y install google-cloud-sdk;
  /usr/bin/apt -y install dcfldd pv;
}}

function start_archive_disks(){{
  IFS=$'\n' read -d '' -r -a disk_array < <(/bin/lsblk  -nd -e 1 -o  SERIAL,NAME|awk '$2 != "sda" {{print $2}}');
  IFS=$'\n' read -d '' -r -a compute_disk_array < <(/bin/lsblk  -nd -e 1 -o  SERIAL,NAME|awk '$2 != "sda" {{print $1}}');

  incident_dir=$(mktemp -d);
  stamp_utc=$(date -u '+%Y%m%d%H%M%S')
  current_zone_batch_path="{archive_bucket}${{stamp_utc}}-{zone}/"

  for ((i=0;i<${{#disk_array[@]}};i++));
    do
      disk_name=${{disk_array[$i]}};
      compute_disk_name=${{compute_disk_array[$i]}};
      add_label instances {instance_name} ${{compute_disk_name}}="archive_starting_check_disk_labels";
      (archive_disk ${{disk_name}} ${{compute_disk_name}} ${{incident_dir}} ${{current_zone_batch_path}})&
    done;
}}

function archive_disk(){{
  disk_name=$1;
  compute_disk_name=$2;
  incident_dir=$3;
  current_zone_batch_path=$4;

  incident_id=$(/usr/bin/gcloud compute disks describe ${{compute_disk_name}} \
  --zone={zone} --project={project_id} --format json|python3 -c "import sys, json; print(json.load(sys.stdin).get('labels',{{}}).get('incident_id','NO_INCIDENT_ID_FOUND'))");
  incident_file_path="${{incident_dir}}/${{incident_id}}.txt";
  if ! [[ -e "${{incident_file_path}}" ]]
  then
    touch ${{incident_file_path}}
  fi

  base_path="${{current_zone_batch_path}}${{incident_id}}/${{compute_disk_name}}/";
  disk_path="${{base_path}}disk.image";
  hash_path="${{base_path}}disk_hash.txt";
  set_metadata "archive_path_${{compute_disk_name}}" "${{incident_id}}" "${{disk_path}}";

  (/usr/bin/dcfldd if="/dev/${{disk_name}}" \
  hashlog=${{disk_name}}.hash hash=md5,sha1 bs=2M  conv=noerror hashwindow=128M |\
  /usr/bin/pv | /usr/bin/gsutil cp - ${{disk_path}}) 2>&1 | logger;
  /usr/bin/gsutil cp ${{disk_name}}.hash ${{hash_path}};

  verify_archive ${{compute_disk_name}} ${{incident_file_path}} ${{base_path}} \
  ${{disk_path}} ${{hash_path}};
}}

function verify_archive(){{
  compute_disk_name=$1
  incident_file_path=$2
  base_path=$3
  disk_path=$4
  hash_path=$5

  if [[ $(/usr/bin/gsutil ls ${{disk_path}}) ]];
  then

    gcs_object_hash=$(/usr/bin/gsutil hash -mh ${{disk_path}}|grep md5|cut -d ":" -f 2|tr -d " \t");
    dcfldd_total_hash=$(/usr/bin/gsutil cat ${{hash_path}}|grep md5|cut -d " " -f 3);
    if [[ ${{gcs_object_hash}} == ${{dcfldd_total_hash}} ]];
    then

      add_label disks ${{compute_disk_name}} "archive_hash_verified"="true";
      add_label disks ${{compute_disk_name}} "gcs_object_hash"=${{gcs_object_hash}};
      add_label disks ${{compute_disk_name}} "dcfldd_total_hash"=${{dcfldd_total_hash}};
      add_label instances {instance_name} ${{compute_disk_name}}="archive_hash_verified";

      echo "Time Stamp (UTC):  $(date -u '+%Y_%m_%d_%H_%M_%S')">${{incident_file_path}};
      echo "Compute Disk: ${{compute_disk_name}}">>${{incident_file_path}};
      echo "Incident ID: ${{incident_id}}">>${{incident_file_path}};
      echo "GCS MD5 Hash: ${{gcs_object_hash}}">>${{incident_file_path}};
      echo "DCFLDD MD5 Hash: ${{dcfldd_total_hash}}">>${{incident_file_path}};
      echo "Disk full path: ${{disk_path}}">>${{incident_file_path}};
      echo "">>${{incident_file_path}};
      echo "">>${{incident_file_path}};
      /usr/bin/gsutil cp "${{incident_file_path}}" "${{base_path}}DISK_INFO.txt";
    else

      add_label instances {instance_name} ${{compute_disk_name}}="archive_hash_not_verified";
      add_label disks ${{compute_disk_name}} "archive_hash_verified"="false";
    fi;
  else
    add_label instances {instance_name} ${{compute_disk_name}}="archived_disk_not_found_check_logs";
    add_label disks ${{compute_disk_name}} ${{compute_disk_name}}="archived_disk_not_found_check_logs";
  fi;
  add_label instances {instance_name} startup_script="ended";
}}

start_startup_prep;
start_archive_disks;