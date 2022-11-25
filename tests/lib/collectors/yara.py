#!/usr/bin/env python
"""Tests the Yeti YaraCollector collectors (YetiYaraCollector)."""

from unittest import mock
import unittest

from dftimewolf.lib import state
from dftimewolf.lib.collectors import yara
from dftimewolf.lib.containers import containers

from dftimewolf import config

MOCK_RESPONSE = [{
    'created': '2022-11-18T10:54:12.039366Z',
    'description': 'rule description',
    'id': 'x-yara--2a2c4c6c-1797-4add-9787-19890ac35fc3',
    'labels': ['label1', 'label2'],
    'modified': '2022-11-18T10:58:36.970528Z',
    'name': 'Some random rule',
    'pattern': 'rule test {\n'
                '  meta:\n'
                '    author = "tomchop"\n'
                '  strings:\n'
                '    $s = "r4nd0m"\n'
                '  condition:\n'
                '    any of them\n'
                '}',
    'spec_version': '2.1',
    'type': 'x-yara',
    'valid_from': '2022-11-17T23:00:00Z'
}]

class YetiYaraCollectorTest(unittest.TestCase):
  """Tests for the Yeti Yara collector."""

  def setUp(self):
    test_state = state.DFTimewolfState(config.Config)
    self.yara_collector = yara.YetiYaraCollector(test_state, name='test')

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    self.assertIsNotNone(self.yara_collector)

  @mock.patch('requests.post')
  def testProcess(self, mock_post):
    """Tests that Process() runs as expected."""
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = MOCK_RESPONSE

    self.yara_collector.SetUp(
        rule_name_filter='rulefilter',
        api_key='d34db33f',
        api_root='http://localhost:8080/api/'
    )
    self.yara_collector.Process()

    mock_post.assert_called_with(
        'http://localhost:8080/api/indicators/filter/',
        json={'name': 'rulefilter', 'type': 'x-yara'},
        headers={'X-Yeti-API': 'd34db33f'},
    )
    yara_containers = self.yara_collector.state.GetContainers(
      containers.YaraRule)
    self.assertEqual(len(yara_containers), 1)
    self.assertEqual(yara_containers[0].name, 'Some random rule')
    self.assertEqual(
        yara_containers[0].rule_text,
        'rule test {\n'
        '  meta:\n'
        '    author = "tomchop"\n'
        '  strings:\n'
        '    $s = "r4nd0m"\n'
        '  condition:\n'
        '    any of them\n'
        '}'
    )

if __name__ == '__main__':
  unittest.main()
