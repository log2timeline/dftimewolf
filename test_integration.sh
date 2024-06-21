#!/bin/bash
# OSDFIR Infrastructure integration tests
# This script can be used to test the integration between dfTimewolf, Timesketch, and Turbinia
# Requirements:
# - have 'kubectl', 'jq' and 'expect' packages installed
# - have the OSDFIR Infrastructure Helm chart deployed and are authenticated to the GKE cluster
# - have the 'dfTimewolf', 'turbinia-client', and 'timesketch' CLI's installed

set -o posix

RELEASE="test"
DISK="disk-1"
SKETCH_ID="1"
FAILED=0
DATE=$(date -I)

if [ $# -ne  2 ]
then
  echo "Not enough arguments supplied, please provide GCP project and zone"
  echo "$0 [PROJECT] [ZONE]"
  exit 1
fi

GCP_PROJECT="$1"
GCP_ZONE="$2"

echo -n "Started at "
date -Iseconds

# Forward k8s services
echo "Forwarding k8s $RELEASE services"
kubectl --namespace default port-forward service/$RELEASE-timesketch 5000:5000 > /dev/null 2>&1 &
kubectl --namespace default port-forward service/$RELEASE-turbinia 8000:8000  > /dev/null 2>&1 &

# Back up existing Timesketch configs else script will attempt to connect to wrong Timesketch instance
if  [ -f ~/.timesketchrc ] && [ -f ~/.timesketch.token ] 
then
    echo "Backing up existing Timesketch configs to ~/.timesketchrc.$DATE and ~/.timesketch.token.$DATE"
    mv ~/.timesketchrc ~/.timesketchrc.$DATE
    mv ~/.timesketch.token ~/.timesketch.token.$DATE
fi

echo "Generating Timesketch config..."
TS_SECRET=$(kubectl get secret --namespace default $RELEASE-timesketch-secret -o jsonpath="{.data.timesketch-user}" | base64 -d)
if ! [ -f ~/.timesketchrc ] && ! [ -f ~/.timesketch.token ]; then
    expect <<END_EXPECT
    spawn timesketch config
    expect "What is the value for <host_uri>"
    send "http://127.0.0.1:5000\r"
    expect "What is the value for <auth_mode>"
    send "userpass\r"
    expect "What is the value for <username>"
    send "timesketch\r"
    expect "Password for user timesketch"
    send "$TS_SECRET\r"
    expect eof
END_EXPECT
fi

# Back up existing Turbinia config else script will attempt to connect to wrong Turbinia instance
if  [ -f ~/.turbinia_api_config.json ]
then
  echo "Backing up existing Turbinia config to ~/.turbinia_api_config.json.$DATE"
  mv ~/.turbinia_api_config.json ~/.turbinia_api_config.json.$DATE
fi

# Replace Turbinia config with test config
echo "Writing turbinia config to $HOME/.turbinia_api_config.json..."
cat > $HOME/.turbinia_api_config.json <<EOL
{
	"default": {
		"description": "Turbinia client test config",
		"API_SERVER_ADDRESS": "http://127.0.0.1",
		"API_SERVER_PORT": 8000,
		"API_AUTHENTICATION_ENABLED": false,
		"CLIENT_SECRETS_FILENAME": ".client_secrets.json",
		"CREDENTIALS_FILENAME": ".credentials_default.json"
	}
}
EOL

# Ensure connection is stable before running test
turbinia-client status summary
if [ $? != "0" ]
then
  echo "Connection to the Turbinia service failed. Retrying k8s port-forward..."
  kubectl --namespace default port-forward service/$RELEASE-turbinia 8000:8000  > /dev/null 2>&1 &
fi

timesketch timelines
if [ $? != "0" ]
then
  echo "Connection to the Timesketch service failed. Retrying k8s port-forward..."
  kubectl --namespace default port-forward service/$RELEASE-timesketch 5000:5000 > /dev/null 2>&1 &
fi

# Exit on any failures after this point
set -e

# Run dfTimewolf recipe
echo "Running dfTimewolf recipe: dftimewolf gcp_turbinia_ts $GCP_PROJECT $GCP_ZONE --disk_names $DISK --incident_id test213 --timesketch_username timesketch --timesketch_password TS_SECRET"
export DFTIMEWOLF_NO_CURSES=1
poetry run dftimewolf gcp_turbinia_ts $GCP_PROJECT $GCP_ZONE --disk_names $DISK --incident_id test213 --timesketch_username timesketch --timesketch_password $TS_SECRET
echo "dfTimewolf recipe succeeded!" 

# Turbinia integration test
echo "Starting integration test for Turbinia..."

# Grab all Turbinia request IDs
REQUEST_SUMMARY=$(turbinia-client status summary -j)
REQUEST_IDS=$(echo $REQUEST_SUMMARY | jq -r '.[] | .[].request_id')
for req in $REQUEST_IDS
do
	# Grab all PlasoParserTask or PlasoHasherTask where successful = false
  echo "Checking the status of Turbinia request: $req"
  status=$(turbinia-client status request $req -j)
	plaso_status=$(echo $status | jq '[.tasks[]] | map({name: .name, id: .id, successful: .successful, worker_name: .worker_name}) | map(select(.name == "PlasoParserTask" or .name == "PlasoHasherTask")) | map(select(.successful==false))')
	length=$(echo $plaso_status | jq '. | length')
	if [[ $length > 0 ]]
	then
	  echo "A failed Plaso Task for Turbinia request $req has been detected."
	  echo "Listing failed Tasks..."
    # Grab the Task ID
    tasks=$(echo $plaso_status | jq -r '.[] | .id')
	  FAILED=1
	  for task in $tasks
    do
	    echo "Failed Plaso Task ID: $task"
	    turbinia-client status task $task
	  done
    # Grab Turbinia worker logs from the server pod
    server=$(kubectl get pods -o name  | grep turbinia-server)
    workers=$(echo $plaso_status | jq -r '.[] | .worker_name')
    for worker in $workers
    do
      wlogs=$(kubectl exec $server -- find /mnt/turbiniavolume/logs -path "*$worker*")
      if [ -n $wlogs ] && [ -n  $server ]
      then
        echo "Grabbing logs for Turbinia worker $worker"
        kubectl exec $server -- cat $wlogs 
      fi
    done
  # If no failed Plaso Tasks were detected
  else
    echo "No failed Plaso Tasks detected for Turbinia request $req"
	fi
done

if [ "$FAILED" != "0" ]
then
  echo "Turbinia integration tests failed! Exiting..."
  exit 1
fi

echo "Turbinia integration tests succeeded!"

# Timesketch integration test

echo "Starting integration test for Timesketch..."

echo "Setting Timesketch Sketch ID to $SKETCH_ID"
timesketch config set sketch $SKETCH_ID
# Grab the error_message field in the sketch.timelines response
TIMESKETCH_STATUS=$(timesketch --output-format json sketch describe)
TIMESKETCH_ERR=$(echo $TIMESKETCH_STATUS | jq '.resource_data.objects | .[].timelines | .[].datasources | .[].error_message')
TIMESKETCH_ERR_LENGTH=$(echo $TIMESKETCH_STATUS | jq '.resource_data.objects | .[].timelines | .[].datasources | .[].error_message | length')

# Grab original filename for each timeline and total count of timelines
TIMESKETCH_FILENAME=$(echo $TIMESKETCH_STATUS | jq '.resource_data.objects | .[].timelines | .[].datasources | .[].original_filename' | tr '\n' ' ')
TIMESKETCH_TL=$(echo $TIMESKETCH_STATUS | jq '.resource_data.objects | .[].timelines | .[].datasources | .[].id' | wc -l)
echo "$TIMESKETCH_TL timelines found $TIMESKETCH_FILENAME"
timesketch timelines list

# Iterate through timelines for any populated error messages
echo "Checking for any failed timeline imports for Sketch ID $SKETCH_ID..."
for timeline_err in $TIMESKETCH_ERR_LENGTH
do
  # if error_message field is populated
  if [[ $timeline_err > 0 ]]
  then
    FAILED=1
  fi
done

if [[ $FAILED == 1 ]]
then
  echo "A failure in Timesketch importing timelines has been detected!"
  echo $TIMESKETCH_ERR

  worker=$(kubectl get pods -o name  | grep timesketch-worker)
  echo "Grabbing logs for Timesketch worker: $worker"
  kubectl exec $worker -- cat /var/log/timesketch/worker.log

  echo "Timesketch integration tests failed. Exiting!"
  exit 1
fi

echo "No failed Timesketch timeline imports detected!"
echo "Timesketch integration tests succeeded!"
echo -n "Ended at "
date -Iseconds

exit 0
