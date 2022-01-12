#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the Workspace logging timesketch processor."""

import json
import os
import unittest

from dftimewolf.lib.containers import containers
from dftimewolf.lib import state
from dftimewolf.lib.processors import workspace_audit_timesketch

from dftimewolf import config

current_dir = os.path.dirname(os.path.realpath(__file__))


class WorkspaceAuditTimesketchTest(unittest.TestCase):
  """Tests for the Workspace Audit logging Timesketch processor."""

  maxDiff = None

  def testInitialization(self):
    """Tests that the processor can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    processor = workspace_audit_timesketch.WorkspaceAuditTimesketch(test_state)
    self.assertIsNotNone(processor)

  def testTimelineName(self):
    """Tests that the timeline name is set correctly."""
    test_state = state.DFTimewolfState(config.Config)
    processor = workspace_audit_timesketch.WorkspaceAuditTimesketch(test_state)
    file_path = os.path.join(current_dir, 'test_data', 'empty_file.jsonl')
    workspace_container = containers.WorkspaceLogs(
        application_name='chrome', filter_expression='', path=file_path,
        user_key='testuser@example.com', start_time='2021-08-10T14:21Z',
        end_time='2021-09-10T14:21Z')

    test_state.StoreContainer(workspace_container)
    processor.Process()
    stored_containers = test_state.GetContainers(containers.File)

    self.assertEqual(1, len(stored_containers))

    timesketch_container = stored_containers[0]

    self.assertEqual(
        timesketch_container.name,
        'Workspace chrome logs for testuser@example.com from'
        ' 2021-08-10T14:21Z to 2021-09-10T14:21Z')

  def testNonExistingEventType(self):
    """Tests that a log with an unknown type is transformed correctly."""
    test_state = state.DFTimewolfState(config.Config)
    processor = workspace_audit_timesketch.WorkspaceAuditTimesketch(test_state)

    event = {
        "kind": "admin#reports#activity",
        "id": {
            "time": "2021-03-27T05:40:53.778Z",
            "uniqueQualifier": "8345464995891889991",
            "applicationName": "non_existent",
            "customerId": "C45gio"
        },
        "etag": "\"GhzOL-ck1v0ExCrJW7SfmvCq0dO_zUCDIDtcE-k9ub0"
                "/tQ3f2j2b4brrW332IF1-Gab3x7E\"",
        "actor": {
            "email": "text@example.com",
            "profileId": "42"
        },
        "ownerDomain": "example.com",
        "events": [
            {
                "type": "non_existent2",
                "name": "non_existent2",
                "parameters": [
                    {
                        "name": "event_id",
                        "value": "r718rbj583q2jp3mga1f5d2ibh"
                    },
                    {
                        "name": "organizer_id",
                        "value": "onager@example.com"
                    }
                ]
            }
        ]
    }

    event_json = json.dumps(event)

    expected_event_record = {
        'actor_email': 'text@example.com',
        'actor_profileId': '42',
        'actor_callerType': None,
        'actor_key': None,
        'applicationName': 'non_existent',
        'customerId': 'C45gio',
        'datetime': '2021-03-27T05:40:53.778Z',
        'etag': '"GhzOL-ck1v0ExCrJW7SfmvCq0dO_zUCDIDtcE-k9ub0'
                '/tQ3f2j2b4brrW332IF1-Gab3x7E"',
        'event_id': 'r718rbj583q2jp3mga1f5d2ibh',
        '_event_name': 'non_existent2',
        '_event_type': 'non_existent2',
        'kind': 'admin#reports#activity',
        'message': 'non_existent2 non_existent2 '
                   'text@example.com 42   8345464995891889991 non_existent '
                   'C45gio admin#reports#activity '
                   '"GhzOL-ck1v0ExCrJW7SfmvCq0dO_zUCDIDtcE-k9ub0'
                   '/tQ3f2j2b4brrW332IF1-Gab3x7E" example.com '
                   'r718rbj583q2jp3mga1f5d2ibh onager@example.com',
        'ownerDomain': 'example.com',
        'organizer_id': 'onager@example.com',
        'timestamp_desc': 'Event Recorded',
        'uniqueQualifier': '8345464995891889991'}

    # pylint: disable=protected-access
    actual_timesketch_records = processor._ProcessLogLine(event_json)

    self.assertEqual(len(actual_timesketch_records), 1)
    actual_timesketch_record = actual_timesketch_records[0]
    actual_timesketch_record = json.loads(actual_timesketch_record)
    self.assertDictEqual(expected_event_record, actual_timesketch_record)

  def testCalendarEvent(self):
    """Tests that a calendar log is transformed correctly."""
    test_state = state.DFTimewolfState(config.Config)
    processor = workspace_audit_timesketch.WorkspaceAuditTimesketch(test_state)

    calendar_event = {
        "kind": "admin#reports#activity",
        "id": {
            "time": "2021-03-27T05:49:53.778Z",
            "uniqueQualifier": "8345464995891889990",
            "applicationName": "calendar",
            "customerId": "C45gio"
        },
        "etag": "\"GhzOL-ck1v0ExCrJW7SfmvCq0dO_zUCDIDtcE-k9ub0"
                "/tQ3f2j2b4brrW332IF1-Gab3x7E\"",
        "actor": {
            "email": "text@example.com",
            "profileId": "42"
        },
        "ownerDomain": "example.com",
        "events": [
            {
                "type": "event_change",
                "name": "change_event_guest_response",
                "parameters": [
                    {
                        "name": "event_id",
                        "value": "r718rbj583q2jp3mga1f5d2ibh"
                    },
                    {
                        "name": "organizer_calendar_id",
                        "value": "onager@example.com"
                    },
                    {
                        "name": "calendar_id",
                        "value": "onager@example.com"
                    },
                    {
                        "name": "target_calendar_id",
                        "value": "onager@example.com"
                    },
                    {
                        "name": "event_title",
                        "value": "Test event title"
                    },
                    {
                        "name": "event_guest",
                        "value": "text@example.com"
                    },
                    {
                        "name": "event_response_status",
                        "value": "accepted"
                    }
                ]
            }
        ]
    }

    calendar_event_json = json.dumps(calendar_event)

    expected_calendar_record = {'actor_email': 'text@example.com',
        'actor_profileId': '42',
        'actor_callerType': None,
        'actor_key': None,
        'applicationName': 'calendar',
        'calendar_id': 'onager@example.com',
        'customerId': 'C45gio',
        'datetime': '2021-03-27T05:49:53.778Z',
        'etag': '"GhzOL-ck1v0ExCrJW7SfmvCq0dO_zUCDIDtcE-k9ub0'
                '/tQ3f2j2b4brrW332IF1-Gab3x7E"',
        'event_guest': 'text@example.com',
        'event_id': 'r718rbj583q2jp3mga1f5d2ibh',
        '_event_name': 'change_event_guest_response',
        'event_response_status': 'accepted',
        'event_title': 'Test event title',
        '_event_type': 'event_change',
        'kind': 'admin#reports#activity',
        'message': 'text@example.com changed the response of guest '
                   'text@example.com for the event Test event title to '
                   'accepted',
        'organizer_calendar_id': 'onager@example.com',
        'ownerDomain': 'example.com',
        'target_calendar_id': 'onager@example.com',
        'timestamp_desc': 'Event Recorded',
        'uniqueQualifier': '8345464995891889990'}

    # pylint: disable=protected-access
    actual_timesketch_records = processor._ProcessLogLine(
        calendar_event_json)
    self.assertEqual(len(actual_timesketch_records), 1)
    actual_timesketch_record = actual_timesketch_records[0]
    actual_timesketch_record = json.loads(actual_timesketch_record)
    self.assertDictEqual(expected_calendar_record, actual_timesketch_record)
