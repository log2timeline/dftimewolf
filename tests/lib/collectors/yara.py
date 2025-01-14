#!/usr/bin/env python
"""Tests the Yeti YaraCollector collectors (YetiYaraCollector)."""

from unittest import mock
import unittest

from dftimewolf.lib.collectors import yara
from dftimewolf.lib.containers import containers
from tests.lib import modules_test_base


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

class YetiYaraCollectorTest(modules_test_base.ModuleTestBase):
  """Tests for the Yeti Yara collector."""

  def setUp(self):
    self._InitModule(yara.YetiYaraCollector)
    super().setUp()

  @mock.patch('requests.post')
  def testProcess(self, mock_post):
    """Tests that Process() runs as expected."""
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = MOCK_RESPONSE

    self._module.SetUp(
        rule_name_filter='rulefilter',
        api_key='d34db33f',
        api_root='http://localhost:8080/api/'
    )
    self._module.Process()

    mock_post.assert_called_with(
        'http://localhost:8080/api/indicators/filter/',
        json={'name': 'rulefilter', 'type': 'x-yara'},
        headers={'X-Yeti-API': 'd34db33f'},
    )
    yara_containers = self._module.GetContainers(
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

  @mock.patch('requests.post')
  def testProcessBadRequest(self, mock_post):
    """Tests that Process() handles errors correctly."""
    mock_post.return_value.status_code = 519
    mock_post.return_value.json.return_value = 'BAD_RESPONSE'

    self._module.SetUp(
        rule_name_filter='rulefilter',
        api_key='d34db33f',
        api_root='http://localhost:8080/api/'
    )
    with self.assertLogs(self._module.logger, level='ERROR') as lc:
      self._module.Process()

      # Confirm that the error message was logged
      log_messages = [record.getMessage() for record in lc.records]
      self.assertEqual(
        'Error (HTTP 519) retrieving indicators from Yeti: BAD_RESPONSE',
        log_messages[0])

      # No containers should have been stored
      yara_containers = self._module.GetContainers(
        containers.YaraRule)
      self.assertEqual(len(yara_containers), 0)

if __name__ == '__main__':
  unittest.main()
