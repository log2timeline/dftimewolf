#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the GCP logging timesketch processor."""

import json
import unittest

from dftimewolf.lib import state
from dftimewolf.lib.processors import gcp_logging_timesketch

from dftimewolf import config


class GCPLoggingTimesketchTest(unittest.TestCase):
  """Tests for the GCP logging Timesketch processor."""

  maxDiff = None

  def testInitialization(self):
    """Tests that the processor can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    processor = gcp_logging_timesketch.GCPLoggingTimesketch(test_state)
    self.assertIsNotNone(processor)

  def testGCEFirewallLog(self):
    """Tests that a firewall log is transformed correctly."""
    test_state = state.DFTimewolfState(config.Config)
    processor = gcp_logging_timesketch.GCPLoggingTimesketch(test_state)

    firewall_addition = {
        'logName':
            'projects/ketchup-research/logs/'
            'cloudaudit.googleapis.com%2Factivity',
        'resource': {
            'type': 'gce_firewall_rule',
            'labels': {
                'firewall_rule_id': '2527368186053355716',
                'project_id': 'ketchup-research'
            }
        },
        'insertId': '9g6l0dd4nlo',
        'severity': 'NOTICE',
        'timestamp': '2019-06-06T09:00:41.797000Z',
        'operation': {
            'id': 'operation-1559811626986-58aa3f1f16a4c-6840f50a-8fab23b9',
            'producer': 'compute.googleapis.com',
            'last': True
        },
        'protoPayload': {
            '@type': 'type.googleapis.com/google.cloud.audit.AuditLog',
            'authenticationInfo': {
                'principalEmail':
                    'heinz-57@ketchup-research.iam.gserviceaccount.com'
            },
            'requestMetadata': {
                'callerIp': 'gce-internal-ip',
                'callerSuppliedUserAgent': 'google-cloud-sdk gcloud/249.0.0'
            },
            'serviceName': 'compute.googleapis.com',
            'methodName': 'v1.compute.firewalls.insert',
            'resourceName':
                'projects/ketchup-research/global/firewalls/'
                'deny-tomchop-access',
            'request': {
                '@type': 'type.googleapis.com/compute.firewalls.insert'
            }
        }
    }
    firewall_addition_json = json.dumps(firewall_addition)

    expected_addition_record = {
        'query':
            'test_query',
        'project_name':
            'test_project',
        'data_type':
            'gcp:log:json',
        'datetime':
            '2019-06-06T09:00:41.797000Z',
        'timestamp_desc':
            'Event Recorded',
        'resource_label_firewall_rule_id':
            '2527368186053355716',
        'resource_label_project_id':
            'ketchup-research',
        'principalEmail':
            'heinz-57@ketchup-research.iam.gserviceaccount.com',
        'requestMetadata_callerIp':
            'gce-internal-ip',
        'requestMetadata_callerSuppliedUserAgent':
            'google-cloud-sdk gcloud/249.0.0',
        'serviceName':
            'compute.googleapis.com',
        'methodName':
            'v1.compute.firewalls.insert',
        'resourceName':
            'projects/ketchup-research/global/firewalls/deny-tomchop-access',
        'message':
            'User heinz-57@ketchup-research.iam.gserviceaccount.com '
            'performed v1.compute.firewalls.insert '
            'on projects/ketchup-research/global/firewalls/deny-tomchop-access',
        'severity': 'NOTICE'
    }

    # pylint: disable=protected-access
    actual_timesketch_record = processor._ProcessLogLine(
        firewall_addition_json, 'test_query', 'test_project')
    actual_timesketch_record = json.loads(actual_timesketch_record)
    self.assertDictEqual(expected_addition_record, actual_timesketch_record)

    firewall_creation = {
        'logName':
            'projects/ketchup-research/logs/'
            'cloudaudit.googleapis.com%2Factivity',
        'resource': {
            'type': 'gce_firewall_rule',
            'labels': {
                'firewall_rule_id': '2527368186053355716',
                'project_id': 'ketchup-research'
            }
        },
        'insertId': '329e1bd92jo',
        'severity': 'NOTICE',
        'timestamp': '2019-06-06T09:00:27.066000Z',
        'operation': {
            'id': 'operation-1559811626986-58aa3f1f16a4c-6840f50a-8fab23b9',
            'producer': 'type.googleapis.com',
            'first': True
        },
        'protoPayload': {
            '@type': 'type.googleapis.com/google.cloud.audit.AuditLog',
            'authenticationInfo': {
                'principalEmail':
                    'heinz-57@ketchup-research.iam.gserviceaccount.com'
            },
            'requestMetadata': {
                'callerIp': 'gce-internal-ip',
                'callerSuppliedUserAgent': 'google-cloud-sdk gcloud/249.0.0'
            },
            'serviceName': 'compute.googleapis.com',
            'methodName': 'v1.compute.firewalls.insert',
            'authorizationInfo': [{
                'permission': 'compute.firewalls.create',
                'granted': True
            }, {
                'permission': 'compute.networks.updatePolicy',
                'granted': True
            }],
            'resourceName':
                'projects/ketchup-research/global/firewalls/'
                'deny-tomchop-access',
            'request': {
                '@type': 'type.googleapis.com/compute.firewalls.insert',
                'targetTags': ['webserver'],
                'network':
                    'https://www.googleapis.com/compute/v1/projects/'
                    'ketchup-research/global/networks/ketchup-exfil',
                'denieds': [{
                    'IPProtocol': 'tcp'
                }],
                'name': 'deny-tomchop-access',
                'direction': 'INGRESS',
                'priority': '1000',
                'sourceRanges': ['0.0.0.0/0']
            },
            'response': {
                'insertTime':
                    '2019-06-06T02:00:28.013-07:00',
                'startTime':
                    '2019-06-06T02:00:28.029-07:00',
                'targetLink':
                    'https://www.googleapis.com/compute/v1/projects'
                    '/ketchup-research/global/firewalls/deny-tomchop'
                    '-access',
                'progress':
                    '0',
                'user':
                    'heinz-57@ketchup-research.iam.gserviceaccount.com',
                '@type':
                    'type.googleapis.com/operation',
                'selfLinkWithId':
                    'https://www.googleapis.com/compute/v1/projects/'
                    'ketchup-research/global/operations/7407667996112808132',
                'operationType':
                    'insert',
                'status':
                    'RUNNING',
                'id':
                    '7407667996112808132',
                'targetId':
                    '2527368186053355716',
                'selfLink':
                    'https://www.googleapis.com/compute/v1/removed',
                'name':
                    'operation-1559811626986-58aa3f1f16a4c-6840f50a-8fab23b9'
            }
        }
    }

    firewall_creation_json = json.dumps(firewall_creation)

    expected_creation_record = {
        'query':
            'test_query',
        'project_name':
            'test_project',
        'data_type':
            'gcp:log:json',
        'datetime':
            '2019-06-06T09:00:27.066000Z',
        'timestamp_desc':
            'Event Recorded',
        'resource_label_firewall_rule_id':
            '2527368186053355716',
        'resource_label_project_id':
            'ketchup-research',
        'principalEmail':
            'heinz-57@ketchup-research.iam.gserviceaccount.com',
        'requestMetadata_callerIp':
            'gce-internal-ip',
        'requestMetadata_callerSuppliedUserAgent':
            'google-cloud-sdk gcloud/249.0.0',
        'serviceName':
            'compute.googleapis.com',
        'methodName':
            'v1.compute.firewalls.insert',
        'resourceName':
            'projects/ketchup-research/global/firewalls/deny-tomchop-access',
        'request_name':
            'deny-tomchop-access',
        'request_direction':
            'INGRESS',
        'request_targetTags': ['webserver'],
        'source_ranges':
            '0.0.0.0/0',
        'denied_tcp_ports':
            'all',
        'message':
            'User heinz-57@ketchup-research.iam.gserviceaccount.com '
            'performed v1.compute.firewalls.insert on '
            'projects/ketchup-research/global/firewalls/deny-tomchop-access',
        'severity': 'NOTICE'
    }

    actual_timesketch_record = processor._ProcessLogLine(
        firewall_creation_json, 'test_query', 'test_project')
    actual_timesketch_record = json.loads(actual_timesketch_record)
    self.assertDictEqual(expected_creation_record, actual_timesketch_record)

  def testGCECreateLog(self):
    """Tests that a GCE instance creation log is transformed correctly."""
    test_state = state.DFTimewolfState(config.Config)
    processor = gcp_logging_timesketch.GCPLoggingTimesketch(test_state)

    gce_creation = {
        'logName':
            'projects/ketchup-research/logs/'
            'cloudaudit.googleapis.com%2Factivity',
        'resource': {
            'type': 'gce_instance',
            'labels': {
                'zone': 'europe-west1-c',
                'project_id': 'ketchup-research',
                'instance_id': '6662286141402997301'
            }
        },
        'insertId': '-3vn1nsd4wgu',
        'severity': 'NOTICE',
        'timestamp': '2019-06-06T09:29:04.499000Z',
        'operation': {
            'id': 'operation-1559813338033-58aa457edecaa-437db0e5-08683c6e',
            'producer': 'compute.googleapis.com',
            'last': True
        },
        'protoPayload': {
            '@type': 'type.googleapis.com/google.cloud.audit.AuditLog',
            'authenticationInfo': {
                'principalEmail':
                    'heinz-57@ketchup-research.iam.gserviceaccount.com'
            },
            'requestMetadata': {
                'callerIp': 'gce-internal-ip',
                'callerSuppliedUserAgent': 'google-cloud-sdk gcloud/249.0.0'
            },
            'serviceName': 'compute.googleapis.com',
            'methodName': 'v1.compute.instances.insert',
            'resourceName':
                'projects/ketchup-research/zones/europe-west1-c/instances/'
                'example-instance-2',
            'request': {
                '@type': 'type.googleapis.com/compute.instances.insert'
            }
        }
    }
    gce_creation = json.dumps(gce_creation)

    expected_timesketch_record = {
        'query':
            'test_query',
        'project_name':
            'test_project',
        'data_type':
            'gcp:log:json',
        'datetime':
            '2019-06-06T09:29:04.499000Z',
        'timestamp_desc':
            'Event Recorded',
        'resource_label_zone':
            'europe-west1-c',
        'resource_label_project_id':
            'ketchup-research',
        'resource_label_instance_id':
            '6662286141402997301',
        'principalEmail':
            'heinz-57@ketchup-research.iam.gserviceaccount.com',
        'requestMetadata_callerIp':
            'gce-internal-ip',
        'requestMetadata_callerSuppliedUserAgent':
            'google-cloud-sdk gcloud/249.0.0',
        'serviceName':
            'compute.googleapis.com',
        'methodName':
            'v1.compute.instances.insert',
        'resourceName':
            'projects/ketchup-research/zones/europe-west1-c/instances/'
            'example-instance-2',
        'message':
            'User heinz-57@ketchup-research.iam.gserviceaccount.com '
            'performed v1.compute.instances.insert '
            'on projects/ketchup-research/zones/europe-west1-c/instances/'
            'example-instance-2',
        'severity': 'NOTICE'
    }

    # pylint: disable=protected-access
    actual_timesketch_record = processor._ProcessLogLine(
        gce_creation, 'test_query', 'test_project')
    actual_timesketch_record = json.loads(actual_timesketch_record)
    self.assertDictEqual(expected_timesketch_record, actual_timesketch_record)

  def testGCSCreateLog(self):
    """Tests that a GCS bucket creation log is transformed correctly."""
    test_state = state.DFTimewolfState(config.Config)
    processor = gcp_logging_timesketch.GCPLoggingTimesketch(test_state)

    gcs_creation = {
        'protoPayload': {
            '@type': 'type.googleapis.com/google.cloud.audit.AuditLog',
            'status': {},
            'authenticationInfo': {
                'principalEmail':
                    'heinz-57@ketchup-research.iam.gserviceaccount.com'
            },
            'requestMetadata': {
                'callerIp': '100.100.100.100',
                'callerSuppliedUserAgent': 'google-cloud-sdk gcloud/249.0.0',
                'requestAttributes': {
                    'time': '2020-06-16T05:09:57.437288734Z',
                    'auth': {}
                },
                'destinationAttributes': {}
            },
            'serviceName': 'storage.googleapis.com',
            'methodName': 'storage.buckets.create',
            'authorizationInfo': [{
                'resource': 'projects/_/buckets/test_bucket_1',
                'permission': 'storage.buckets.create',
                'granted': 'true',
                'resourceAttributes': {}
            }],
            'resourceName': 'projects/_/buckets/test_bucket_1',
            'serviceData': {
                '@type': 'type.googleapis.com/google.iam.v1.logging.AuditData',
                'policyDelta': {
                    'bindingDeltas': [{
                        'action': 'ADD',
                        'role': 'roles/storage.legacyBucketOwner',
                        'member': 'projectEditor:ketchup-research'
                    }, {
                        'action': 'ADD',
                        'role': 'roles/storage.legacyBucketOwner',
                        'member': 'projectOwner:ketchup-research'
                    }, {
                        'action': 'ADD',
                        'role': 'roles/storage.legacyBucketReader',
                        'member': 'projectViewer:ketchup-research'
                    }]
                }
            },
            'request': {
                'defaultObjectAcl': {
                    'bindings': [{
                        'role': 'roles/storage.legacyObjectReader',
                        'members': ['projectViewer:ketchup-research']
                    }, {
                        'role':
                            'roles/storage.legacyObjectOwner',
                        'members': [
                            'projectOwner:ketchup-research',
                            'projectEditor:ketchup-research'
                        ]
                    }],
                    '@type': 'type.googleapis.com/google.iam.v1.Policy'
                }
            },
            'resourceLocation': {
                'currentLocations': ['us-east1']
            }
        },
        'insertId': '10329k5e3miwp',
        'resource': {
            'type': 'gcs_bucket',
            'labels': {
                'location': 'us-east1',
                'project_id': 'ketchup-research',
                'bucket_name': 'test_bucket_1'
            }
        },
        'timestamp': '2020-06-16T05:09:57.427874505Z',
        'severity': 'NOTICE',
        'logName':
            'projects/ketchup-research/logs/'
            'cloudaudit.googleapis.com%2Factivity',
        'receiveTimestamp': '2020-06-16T05:09:58.131439936Z'
    }

    gcs_creation = json.dumps(gcs_creation)

    expected_timesketch_record = {
        'query':
            'test_query',
        'project_name':
            'test_project',
        'data_type':
            'gcp:log:json',
        'datetime':
            '2020-06-16T05:09:57.427874505Z',
        'timestamp_desc':
            'Event Recorded',
        'resource_label_location':
            'us-east1',
        'resource_label_project_id':
            'ketchup-research',
        'principalEmail':
            'heinz-57@ketchup-research.iam.gserviceaccount.com',
        'requestMetadata_callerIp':
            '100.100.100.100',
        'requestMetadata_callerSuppliedUserAgent':
            'google-cloud-sdk gcloud/249.0.0',
        'requestMetadata_destinationAttributes': {},
        'requestMetadata_requestAttributes': {
            'auth': {},
            'time': '2020-06-16T05:09:57.437288734Z',
        },
        'serviceName':
            'storage.googleapis.com',
        'methodName':
            'storage.buckets.create',
        'resourceName':
            'projects/_/buckets/test_bucket_1',
        'resource_label_bucket_name':
            'test_bucket_1',
        'policyDelta':
            'ADD projectEditor:ketchup-research with role '
            'roles/storage.legacyBucketOwner, ADD '
            'projectOwner:ketchup-research with role '
            'roles/storage.legacyBucketOwner, ADD '
            'projectViewer:ketchup-research with role '
            'roles/storage.legacyBucketReader',
        'message':
            'User heinz-57@ketchup-research.iam.gserviceaccount.com '
            'performed storage.buckets.create on '
            'projects/_/buckets/test_bucket_1',
        'severity': 'NOTICE'
    }

    # pylint: disable=protected-access
    actual_timesketch_record = processor._ProcessLogLine(
        gcs_creation, 'test_query', 'test_project')
    actual_timesketch_record = json.loads(actual_timesketch_record)
    self.assertDictEqual(expected_timesketch_record, actual_timesketch_record)

  def testDataProcYarn(self):
    """Tests that a Yarn dataproc log is transformed correctly."""
    test_state = state.DFTimewolfState(config.Config)
    processor = gcp_logging_timesketch.GCPLoggingTimesketch(test_state)

    yarn_log = {
        "logName":
            "projects/test-project-name/logs/yarn-userlogs",
        "resource": {
            "type": "cloud_dataproc_cluster",
            "labels": {
                    "project_id": "metastore-playground",
                    "cluster_name": "cluster-ca8b",
                    "cluster_uuid": "44444-444444-444-4444-4444",
                    "region": "us-central1"
            }
        },
        "labels": {
            "compute.googleapis.com/resource_id": "400",
            "compute.googleapis.com/resource_name": "cluster-ca8b-w-0",
            "compute.googleapis.com/zone": "us-central1-a"
        },
        "insertId": "j44cqu11aqckveeeo",
        "timestamp": "2021-05-24T08:18:46.299359Z",
        "jsonPayload": {
            "container_logname": "prelaunch.err",
            "message": "line 470: /etc/selinux/config: Permission denied",
            "application": "application_000004_0005",
            "container": "container_0004_0005_0006_000001",
            "filename": "application_000004_0005.container_113_05_1833_01."
                        "prelaunch.err"
        }
    }

    yarn_log = json.dumps(yarn_log)

    expected_timesketch_record = {
        'container': 'container_0004_0005_0006_000001',
        'datetime': '2021-05-24T08:18:46.299359Z',
        'filename': 'application_000004_0005.container_113_05_1833_01.'
                    'prelaunch.err',
        'message': 'line 470: /etc/selinux/config: Permission denied',
        'project_name': 'test_project',
        'query': 'test_query',
        'data_type': 'gcp:log:json',
        'resource_label_cluster_name': 'cluster-ca8b',
        'resource_label_cluster_uuid': '44444-444444-444-4444-4444',
        'resource_label_project_id': 'metastore-playground',
        'resource_label_region': 'us-central1',
        'timestamp_desc': 'Event Recorded'}

    # pylint: disable=protected-access
    actual_timesketch_record = processor._ProcessLogLine(
        yarn_log, 'test_query', 'test_project')
    actual_timesketch_record = json.loads(actual_timesketch_record)
    self.assertDictEqual(expected_timesketch_record, actual_timesketch_record)


if __name__ == '__main__':
  unittest.main()
