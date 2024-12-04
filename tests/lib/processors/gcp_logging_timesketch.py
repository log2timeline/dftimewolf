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
        'data_type':
            'gcp:log:json',
        'datetime':
            '2019-06-06T09:00:41.797000Z',
        'timestamp_desc':
            'Event Recorded',
        'firewall_rule_id':
            '2527368186053355716',
        'project_id':
            'ketchup-research',
        'principal_email':
            'heinz-57@ketchup-research.iam.gserviceaccount.com',
        'caller_ip':
            'gce-internal-ip',
        'user_agent':
            'google-cloud-sdk gcloud/249.0.0',
        'service_name':
            'compute.googleapis.com',
        'method_name':
            'v1.compute.firewalls.insert',
        'resource_name':
            'projects/ketchup-research/global/firewalls/deny-tomchop-access',
        'status_code': '',
        'status_message': '',
        'message':
            'User heinz-57@ketchup-research.iam.gserviceaccount.com '
            'performed v1.compute.firewalls.insert '
            'on projects/ketchup-research/global/firewalls/deny-tomchop-access',
        'severity': 'NOTICE'
    }

    # pylint: disable=protected-access
    actual_timesketch_record = processor._ProcessLogLine(
        firewall_addition_json, 'test_query')
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
        'data_type':
            'gcp:log:json',
        'datetime':
            '2019-06-06T09:00:27.066000Z',
        'timestamp_desc':
            'Event Recorded',
        'firewall_rule_id':
            '2527368186053355716',
        'permissions': [
            'compute.firewalls.create', 'compute.networks.updatePolicy'],
        'project_id':
            'ketchup-research',
        'principal_email':
            'heinz-57@ketchup-research.iam.gserviceaccount.com',
        'caller_ip':
            'gce-internal-ip',
        'user_agent':
            'google-cloud-sdk gcloud/249.0.0',
        'service_name':
            'compute.googleapis.com',
        'method_name':
            'v1.compute.firewalls.insert',
        'resource_name':
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
        'status_code': '',
        'status_message': '',
        'message':
            'User heinz-57@ketchup-research.iam.gserviceaccount.com '
            'performed v1.compute.firewalls.insert on '
            'projects/ketchup-research/global/firewalls/deny-tomchop-access',
        'severity': 'NOTICE'
    }

    actual_timesketch_record = processor._ProcessLogLine(
        firewall_creation_json, 'test_query')
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
              "@type": "type.googleapis.com/compute.instances.insert",
              "description": "GCE instance created for training.",
              "disks": [
                {
                  "autoDelete": 'true',
                  "boot": 'true',
                  "initializeParams": {
                    "diskSizeGb": "100",
                    "diskType": "zones/europe-west1-c/diskTypes/pd-ssd",
                    "sourceImage": 'projects/ketchup-research/global/images/'
                        'my-custom-os'
                  }
                }
              ],
              "labels": [],
              "machineType": "zones/europe-west1-c/machineTypes/n1-highmem-8",
              "name": "training-instance",
              "networkInterfaces": [
                {
                  "accessConfigs": [
                    {
                      "name": "External NAT",
                      "type": "ONE_TO_ONE_NAT"
                    }
                  ],
                  "network": "global/networks/default"
                }
              ],
              "scheduling": {
                "automaticRestart": 'true'
              },
              "serviceAccounts": [
                {
                  "email": "my-sa2@ketchup-research.iam.gserviceaccount.com",
                  "scopes": [
                    "https://www.googleapis.com/auth/devstorage.full_control",
                    "https://www.googleapis.com/auth/logging.read",
                    "https://www.googleapis.com/auth/logging.write",
                    "https://www.googleapis.com/auth/monitoring.write",
                  ]
                }
              ]
            }
        }
    }

    gce_creation = json.dumps(gce_creation)

    expected_timesketch_record = {
        'query':
            'test_query',
        'data_type':
            'gcp:log:json',
        'datetime':
            '2019-06-06T09:29:04.499000Z',
        'timestamp_desc':
            'Event Recorded',
        'dcsa_emails': ['my-sa2@ketchup-research.iam.gserviceaccount.com'],
        'dcsa_scopes': [
          'https://www.googleapis.com/auth/devstorage.full_control',
          'https://www.googleapis.com/auth/logging.read',
           'https://www.googleapis.com/auth/logging.write',
            'https://www.googleapis.com/auth/monitoring.write',
        ],
        'zone':
            'europe-west1-c',
        'project_id':
            'ketchup-research',
        'instance_id':
            '6662286141402997301',
        'principal_email':
            'heinz-57@ketchup-research.iam.gserviceaccount.com',
        'caller_ip':
            'gce-internal-ip',
        'user_agent':
            'google-cloud-sdk gcloud/249.0.0',
        'service_name':
            'compute.googleapis.com',
        'method_name':
            'v1.compute.instances.insert',
        'request_description': 'GCE instance created for training.',
        'request_name': 'training-instance',
        'resource_name':
            'projects/ketchup-research/zones/europe-west1-c/instances/'
            'example-instance-2',
        'message':
            'User heinz-57@ketchup-research.iam.gserviceaccount.com '
            'performed v1.compute.instances.insert '
            'on projects/ketchup-research/zones/europe-west1-c/instances/'
            'example-instance-2',
        'severity': 'NOTICE',
        'source_images': [
          'projects/ketchup-research/global/images/my-custom-os'],
        'status_code': '',
        'status_message': ''
    }

    # pylint: disable=protected-access
    actual_timesketch_record = processor._ProcessLogLine(
        gce_creation, 'test_query')
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
        'data_type':
            'gcp:log:json',
        'datetime':
            '2020-06-16T05:09:57.427874505Z',
        'timestamp_desc':
            'Event Recorded',
        'location':
            'us-east1',
        'permissions': ['storage.buckets.create'],
        'project_id':
            'ketchup-research',
        'principal_email':
            'heinz-57@ketchup-research.iam.gserviceaccount.com',
        'caller_ip':
            '100.100.100.100',
        'user_agent':
            'google-cloud-sdk gcloud/249.0.0',
        'service_name':
            'storage.googleapis.com',
        'method_name':
            'storage.buckets.create',
        'resource_name':
            'projects/_/buckets/test_bucket_1',
        'bucket_name':
            'test_bucket_1',
        'policy_delta':
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
        'severity': 'NOTICE',
        'status_code': '',
        'status_message': ''
    }

    # pylint: disable=protected-access
    actual_timesketch_record = processor._ProcessLogLine(
        gcs_creation, 'test_query')
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
        'query': 'test_query',
        'data_type': 'gcp:log:json',
        'cluster_name': 'cluster-ca8b',
        'cluster_uuid': '44444-444444-444-4444-4444',
        'project_id': 'metastore-playground',
        'region': 'us-central1',
        'timestamp_desc': 'Event Recorded'}

    # pylint: disable=protected-access
    actual_timesketch_record = processor._ProcessLogLine(
        yarn_log, 'test_query')
    actual_timesketch_record = json.loads(actual_timesketch_record)
    self.assertDictEqual(expected_timesketch_record, actual_timesketch_record)

  def testComputeInstancesInsert(self):
    """Tests `type.googleapis.com/compute.instances.insert` is parsed
        correctly.
    """
    test_state = state.DFTimewolfState(config.Config)
    processor = gcp_logging_timesketch.GCPLoggingTimesketch(test_state)

    compute_instance_insert_log = {
      'insertId':'-ft34ekedkmxm',
      'labels': {
        'compute.googleapis.com/root_trigger_id':
            'bcbc8a09-25db-4183-ab94-43d53ab987ca'
      },
      'logName':'projects/ketchup/logs/cloudaudit.googleapis.com%2F'
          'data_access',
      'protoPayload': {
        '@type':'type.googleapis.com/google.cloud.audit.AuditLog',
        'authenticationInfo': {
          'principalEmail': 'service-account123@ketchup.iam.'
              'gserviceaccount.com',
          'principalSubject': 'serviceAccount:service-account123'
              '@ketchup.iam.gserviceaccount.com',
          'serviceAccountDelegationInfo': [
            {
              'firstPartyPrincipal':{
                'principalEmail': 'my-sa@ketchup.iam.gserviceaccount.com'
              }
            }
          ]
        },
        'authorizationInfo': [
          {
            'granted': 'true',
            'permission': 'compute.instances.get',
            'permissionType': 'ADMIN_READ',
            'resource': 'projects/ketchup/zones/us-central1-a/instances/'
                'my-cluster',
            'resourceAttributes': {
              'name': 'projects/ketchup/zones/us-central1-a/instances/'
                  'my-cluster',
              'service': 'compute',
              'type': 'compute.instances'
            }
          }
        ],
      'methodName': 'v1.compute.instances.get',
      'request': {
        '@type': 'type.googleapis.com/compute.instances.get'
      },
      'requestMetadata': {
        'callerIp': '34.X.Y.Z',
        'callerNetwork': '//compute.googleapis.com/projects/ketchup/global/'
            'networks/__unknown__',
        'callerSuppliedUserAgent': 'special-user-agent-string',
        'destinationAttributes': {},
        'requestAttributes': {
          'auth': {},
          'time': '2024-10-26T19:55:40.930578Z'
        }
      },
      'resourceLocation': {
        'currentLocations': ['us-central1-a']
      },
      'resourceName': 'projects/1234567890/zones/us-central1-a/instances/'
          'my-cluster',
      'serviceName': 'compute.googleapis.com'
      },
      'receiveTimestamp': '2024-10-26T19:55:41.937084378Z',
      'resource': {
        'labels': {
          'instance_id': '9876543210',
          'project_id': 'ketchup',
          'zone': 'us-central1-a'
        },
        'type': 'gce_instance'
      },
      'severity': 'INFO',
      'timestamp': '2024-10-26T19:55:40.876410Z'
    }

    expected_timesketch_record = {
      'query': 'test_query',
      'data_type': 'gcp:log:json',
      'datetime': '2024-10-26T19:55:40.876410Z',
      'timestamp_desc': 'Event Recorded',
      'caller_ip': '34.X.Y.Z',
      'delegation_chain': 'my-sa@ketchup.iam.gserviceaccount.com',
      'instance_id': '9876543210',
      'method_name': 'v1.compute.instances.get',
      'message': 'User service-account123@ketchup.iam.gserviceaccount.com '
          'performed v1.compute.instances.get on projects/1234567890/zones/'
          'us-central1-a/instances/my-cluster',
      'permissions': ['compute.instances.get'],
      'principal_email': 'service-account123@ketchup.iam.gserviceaccount.com',
      'principal_subject': 'serviceAccount:service-account123@ketchup.iam.'
          'gserviceaccount.com',
      'project_id': 'ketchup',
      'resource_name': 'projects/1234567890/zones/us-central1-a/instances/'
          'my-cluster',
      'service_name': 'compute.googleapis.com',
      'service_account_delegation': ['my-sa@ketchup.iam.gserviceaccount.com'],
      'severity': 'INFO',
      'status_code': '',
      'status_message': '',
      'user_agent': 'special-user-agent-string',
      'zone': 'us-central1-a'
    }

    compute_instance_insert_log = json.dumps(compute_instance_insert_log)

    # pylint: disable=protected-access
    actual_timesketch_record = processor._ProcessLogLine(
        compute_instance_insert_log, 'test_query')
    actual_timesketch_record = json.loads(actual_timesketch_record)
    self.assertDictEqual(expected_timesketch_record, actual_timesketch_record)

  def testServiceAccountCreateFailed(self):
    """Test the failed service account create logs with reasons."""
    test_state = state.DFTimewolfState(config.Config)
    processor = gcp_logging_timesketch.GCPLoggingTimesketch(test_state)

    service_create_log = {
      'protoPayload': {
        '@type': 'type.googleapis.com/google.cloud.audit.AuditLog',
        'status': {
          'code': 7,
          'message': ('Permission \'iam.serviceAccounts.create\' denied on '
              'resource (or it may not exist).'),
          'details': [
            {
              '@type': 'type.googleapis.com/google.rpc.ErrorInfo',
              'reason': 'IAM_PERMISSION_DENIED',
              'domain': 'iam.googleapis.com',
              'metadata': {
                'permission': 'iam.serviceAccounts.create'
              }
            }
          ]
        },
        'authenticationInfo': {
          'principalEmail': ('dvwa-service-account@ketchup'
              '.iam.gserviceaccount.com'),
          'serviceAccountDelegationInfo': [
            {
              'firstPartyPrincipal': {
                'principalEmail': ('service-1234567890@compute-system.iam.'
                    'gserviceaccount.com')
              }
            }
          ],
          'principalSubject': ('serviceAccount:dvwa-service-account@'
              'ketchup.iam.gserviceaccount.com')
        },
        'requestMetadata': {
          'callerIp': '34.72.217.225',
          'callerSuppliedUserAgent': '(gzip),gzip(gfe)',
          'requestAttributes': {
            'time': '2024-12-03T17:58:45.019694350Z',
            'auth': {}
          },
          'destinationAttributes': {}
        },
        'serviceName': 'iam.googleapis.com',
        'methodName': 'google.iam.admin.v1.CreateServiceAccount',
        'authorizationInfo': [
          {
            'resource': 'projects/ketchup',
            'permission': 'iam.serviceAccounts.create',
            'resourceAttributes': {
              'type': 'iam.googleapis.com/ServiceAccount'
            },
            'permissionType': 'ADMIN_WRITE'
          }
        ],
        'resourceName': 'projects/ketchup',
        'request': {
          'service_account': {
            'display_name': 'This is the attacker account'
          },
          'account_id': 'theattacker',
          'name': 'projects/ketchup',
          '@type': ('type.googleapis.com/google.iam.admin.v1.'
              'CreateServiceAccountRequest')
        },
        'response': {
          '@type': 'type.googleapis.com/google.iam.admin.v1.ServiceAccount'
        }
      },
      'insertId': '1awjxggeaxqgz',
      'resource': {
        'type': 'service_account',
        'labels': {
          'unique_id': '',
          'project_id': 'ketchup',
          'email_id': ''
        }
      },
      'timestamp': '2024-12-03T17:58:44.882119699Z',
      'severity': 'ERROR',
      'logName': ('projects/ketchup/logs/cloudaudit.'
          'googleapis.com%2Factivity'),
      'receiveTimestamp': '2024-12-03T17:58:45.716564605Z'
    }

    expected_timesketch_record = {
      'query': 'test_query',
      'data_type': 'gcp:log:json',
      'datetime': '2024-12-03T17:58:44.882119699Z',
      'timestamp_desc': 'Event Recorded',
      'caller_ip': '34.72.217.225',
      'delegation_chain': ('service-1234567890@compute-system.iam.'
          'gserviceaccount.com'),
      'email_id': '',
      'message': ('User dvwa-service-account@ketchup.iam.'
          'gserviceaccount.com performed google.iam.admin.v1.'
          'CreateServiceAccount on projects/ketchup'),
      'method_name': 'google.iam.admin.v1.CreateServiceAccount',
     'permissions': ['iam.serviceAccounts.create'],
      'principal_email': ('dvwa-service-account@ketchup.'
          'iam.gserviceaccount.com'),
      'principal_subject': ('serviceAccount:dvwa-service-account@'
          'ketchup.iam.gserviceaccount.com'),
      'project_id': 'ketchup',
      'request_account_id': 'theattacker',
      'request_name': 'projects/ketchup',
      'resource_name': 'projects/ketchup',
      'service_account_delegation': [
          'service-1234567890@compute-system.iam.gserviceaccount.com'],
      'service_account_display_name': 'This is the attacker account',
      'service_name': 'iam.googleapis.com',
      'severity': 'ERROR',
      'status_code': '7',
      'status_message': ('Permission \'iam.serviceAccounts.create\' denied on'
          ' resource (or it may not exist).'),
      'status_reasons': ['IAM_PERMISSION_DENIED'],
      'unique_id': '',
      'user_agent': '(gzip),gzip(gfe)'
    }

    failed_service_account_create_log = json.dumps(service_create_log)

    # pylint: disable=protected-access
    actual_timesketch_record = processor._ProcessLogLine(
        failed_service_account_create_log, 'test_query')

    actual_timesketch_record = json.loads(actual_timesketch_record)
    self.assertDictEqual(expected_timesketch_record, actual_timesketch_record)

if __name__ == '__main__':
  unittest.main()
