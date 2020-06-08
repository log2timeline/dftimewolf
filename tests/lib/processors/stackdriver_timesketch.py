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
        'insertId':
            '9g6l0dd4nlo',
        'severity':
            'NOTICE',
        'timestamp':
            '2019-06-06T09:00:41.797000Z',
        'operation': {
            'id': 'operation-1559811626986-58aa3f1f16a4c-6840f50a-8fab23b9',
            'producer': 'compute.googleapis.com',
            'last': True
        },
        'protoPayload': {
            '@type':
                'type.googleapis.com/google.cloud.audit.AuditLog',
            'authenticationInfo': {
                'principalEmail':
                    'heinz-57@ketchup-research.iam.gserviceaccount.com'
            },
            'requestMetadata': {
                'callerIp': 'gce-internal-ip',
                'callerSuppliedUserAgent': 'google-cloud-sdk gcloud/249.0.0'
            },
            'serviceName':
                'compute.googleapis.com',
            'methodName':
                'v1.compute.firewalls.insert',
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
            'on projects/ketchup-research/global/firewalls/deny-tomchop-access'
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
        'insertId':
            '329e1bd92jo',
        'severity':
            'NOTICE',
        'timestamp':
            '2019-06-06T09:00:27.066000Z',
        'operation': {
            'id': 'operation-1559811626986-58aa3f1f16a4c-6840f50a-8fab23b9',
            'producer': 'type.googleapis.com',
            'first': True
        },
        'protoPayload': {
            '@type':
                'type.googleapis.com/google.cloud.audit.AuditLog',
            'authenticationInfo': {
                'principalEmail':
                    'heinz-57@ketchup-research.iam.gserviceaccount.com'
            },
            'requestMetadata': {
                'callerIp': 'gce-internal-ip',
                'callerSuppliedUserAgent': 'google-cloud-sdk gcloud/249.0.0'
            },
            'serviceName':
                'compute.googleapis.com',
            'methodName':
                'v1.compute.firewalls.insert',
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
            'projects/ketchup-research/global/firewalls/deny-tomchop-access'
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
            'example-instance-2'
    }

    # pylint: disable=protected-access
    actual_timesketch_record = processor._ProcessLogLine(
        gce_creation, 'test_query', 'test_project')
    actual_timesketch_record = json.loads(actual_timesketch_record)
    self.assertDictEqual(expected_timesketch_record, actual_timesketch_record)
