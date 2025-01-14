#!/usr/bin/env python
"""Tests the GRR hunt collectors."""

# pytype: disable=attribute-error


import unittest
import zipfile
import mock

from grr_response_proto import flows_pb2
from grr_response_proto import osquery_pb2 as osquery_flows

from dftimewolf.lib import errors
from dftimewolf.lib.collectors import grr_hunt
from dftimewolf.lib.containers import containers
from tests.lib.collectors.test_data import mock_grr_hosts
from tests.lib import modules_test_base


# pylint: disable=invalid-name,arguments-differ
class GRRHuntArtifactCollectorTest(modules_test_base.ModuleTestBase):
  """Tests for the GRR artifact collector."""

  # For pytype
  mock_grr_api: mock.Mock

  @mock.patch('grr_api_client.api.InitHttp')
  def setUp(self, mock_InitHttp):
    self._InitModule(grr_hunt.GRRHuntArtifactCollector)
    self.mock_grr_api = mock.Mock()
    mock_InitHttp.return_value = self.mock_grr_api
    self._module.SetUp(
        artifacts='RandomArtifact',
        use_raw_filesystem_access=True,
        reason='random reason',
        grr_server_url='http://fake/endpoint',
        grr_username='admin',
        grr_password='admin',
        approvers='approver1,approver2',
        max_file_size='1234',
        verify=False,
        match_mode=None,
        client_operating_systems=None,
        client_labels=None
    )

  def testProcess(self):
    """Tests that the process function issues correct GRR API calls."""
    self._ProcessModule()
    # extract call kwargs
    call_kwargs = self.mock_grr_api.CreateHunt.call_args[1]
    self.assertEqual(call_kwargs['flow_args'].artifact_list,
                     ['RandomArtifact'])
    self.assertEqual(call_kwargs['flow_args'].use_raw_filesystem_access, True)
    self.assertEqual(call_kwargs['flow_name'], 'ArtifactCollectorFlow')
    self.assertEqual(call_kwargs['hunt_runner_args'].description,
                     'random reason')


class GRRHuntFileCollectorTest(modules_test_base.ModuleTestBase):
  """Tests for the GRR file collector."""

  # For pytype
  mock_grr_api: mock.Mock

  @mock.patch('grr_api_client.api.InitHttp')
  def setUp(self, mock_InitHttp):
    self._InitModule(grr_hunt.GRRHuntFileCollector)
    self.mock_grr_api = mock.Mock()
    mock_InitHttp.return_value = self.mock_grr_api
    self._module.StoreContainer(
        containers.FSPath(path='/etc/hosts'))
    self._module.SetUp(
        file_path_list='/etc/passwd,/etc/shadow',
        reason='random reason',
        grr_server_url='http://fake/endpoint',
        grr_username='admin',
        grr_password='admin',
        approvers='approver1,approver2',
        max_file_size='1234',
        verify=False,
        match_mode=None,
        client_operating_systems=None,
        client_labels=None
    )

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    self.assertEqual(
        self._module.file_path_list,
        ['/etc/passwd', '/etc/shadow']
    )

  def testPreProcess(self):
    """Tests the preprocess method."""
    self._module.PreProcess()
    self.assertEqual(
        self._module.file_path_list,
        ['/etc/passwd', '/etc/shadow', '/etc/hosts'])

  def testProcess(self):
    """Tests that the process method invokes the correct GRR API calls."""
    self._module.PreProcess()
    self._ProcessModule()
    # extract call kwargs
    call_kwargs = self.mock_grr_api.CreateHunt.call_args[1]
    self.assertEqual(call_kwargs['flow_args'].paths,
                     ['/etc/passwd', '/etc/shadow', '/etc/hosts'])
    self.assertEqual(call_kwargs['flow_args'].action.action_type,
                     flows_pb2.FileFinderAction.DOWNLOAD)
    self.assertEqual(call_kwargs['flow_name'], 'FileFinder')
    self.assertEqual(call_kwargs['hunt_runner_args'].description,
                     'random reason')


class GRRHuntOsqueryCollectorTest(modules_test_base.ModuleTestBase):
  """Tests for the GRR osquery collector."""

  # For pytype
  _module: grr_hunt.GRRHuntOsqueryCollector
  mock_grr_api: mock.Mock

  @mock.patch('grr_api_client.api.InitHttp')
  def setUp(self, mock_InitHttp):
    self._InitModule(grr_hunt.GRRHuntOsqueryCollector)
    self.mock_grr_api = mock.Mock()
    mock_InitHttp.return_value = self.mock_grr_api
    self._module.StoreContainer(
        containers.OsqueryQuery(
            query='SELECT * FROM processes',
            configuration_path='/test/path',
            file_collection_columns=['path']))
    self._module.SetUp(
        reason='random reason',
        timeout_millis=300000,
        ignore_stderr_errors=False,
        grr_server_url='http://fake/endpoint',
        grr_username='admin',
        grr_password='admin',
        approvers='approver1,approver2',
        verify=False,
        match_mode=None,
        client_operating_systems=None,
        client_labels=None)

  def testProcess(self):
    """Tests that the process method invokes the correct GRR API calls."""
    self._ProcessModule()
    # extract call kwargs
    call_kwargs = self.mock_grr_api.CreateHunt.call_args[1]
    self.assertEqual(call_kwargs['flow_args'].query,
                     'SELECT * FROM processes;')
    self.assertEqual(call_kwargs['flow_args'].timeout_millis,
                     300000)
    self.assertEqual(call_kwargs['flow_args'].ignore_stderr_errors, False)
    self.assertEqual(call_kwargs['flow_args'].configuration_path, '/test/path')
    self.assertEqual(call_kwargs['flow_args'].file_collection_columns, ['path'])
    self.assertEqual(call_kwargs['flow_name'], 'OsqueryFlow')
    self.assertEqual(call_kwargs['hunt_runner_args'].description,
                     'random reason')


class GRRHuntDownloader(modules_test_base.ModuleTestBase):
  """Tests for the GRR hunt downloader."""

  # For pytype
  _module: grr_hunt.GRRHuntDownloader
  mock_grr_api: mock.Mock

  @mock.patch('grr_api_client.api.InitHttp')
  def setUp(self, mock_InitHttp):
    self._InitModule(grr_hunt.GRRHuntDownloader)
    self.mock_grr_api = mock.Mock()
    mock_InitHttp.return_value = self.mock_grr_api
    self._module.SetUp(
        hunt_id='H:12345',
        reason='random reason',
        grr_server_url='http://fake/endpoint',
        grr_username='admin',
        grr_password='admin',
        approvers='approver1,approver2',
        verify=False
    )
    self._module.output_path = '/tmp/test'

  def testInitialization(self):
    """Tests that the collector is correctly initialized."""
    self.assertEqual(self._module.hunt_id, 'H:12345')

  @mock.patch('dftimewolf.lib.collectors.grr_hunt.GRRHuntDownloader._ExtractHuntResults')  # pylint: disable=line-too-long
  @mock.patch('dftimewolf.lib.collectors.grr_hunt.GRRHuntDownloader._GetAndWriteArchive')  # pylint: disable=line-too-long
  def testCollectHuntResults(self,
                             mock_get_write_archive,
                             mock_ExtractHuntResults):
    """Tests that hunt results are downloaded to the correct file."""
    self.mock_grr_api.Hunt.return_value.Get.return_value = \
        mock_grr_hosts.MOCK_HUNT
    self._ProcessModule()
    mock_get_write_archive.assert_called_with(mock_grr_hosts.MOCK_HUNT,
                                              '/tmp/test/H:12345.zip')
    mock_ExtractHuntResults.assert_called_with('/tmp/test/H:12345.zip')

  @mock.patch('os.remove')
  @mock.patch('zipfile.ZipFile.extract')
  def testExtractHuntResults(self, _, mock_remove):
    """Tests that hunt results are correctly extracted."""
    self._module.output_path = '/directory'
    expected = sorted([
        ('greendale-student04.c.greendale.internal',
         '/directory/hunt_H_A43ABF9D/C.4c4223a2ea9cf6f1'),
        ('greendale-admin.c.greendale.internal',
         '/directory/hunt_H_A43ABF9D/C.ba6b63df5d330589'),
        ('greendale-student05.c.greendale.internal',
         '/directory/hunt_H_A43ABF9D/C.fc693a148af801d5')
    ])
    test_zip = 'tests/lib/collectors/test_data/hunt.zip'
    # pylint: disable=protected-access
    result = sorted(self._module._ExtractHuntResults(test_zip))
    self.assertEqual(result, expected)
    mock_remove.assert_called_with('tests/lib/collectors/test_data/hunt.zip')

  @mock.patch('os.remove')
  @mock.patch('zipfile.ZipFile.extract')
  def testOSErrorExtractHuntResults(self, mock_extract, mock_remove):
    """Tests that an OSError when reading files generate errors."""
    self._module.output_path = '/directory'
    test_zip = 'tests/lib/collectors/test_data/hunt.zip'
    mock_extract.side_effect = OSError
    # pylint: disable=protected-access

    with self.assertRaises(errors.DFTimewolfError) as error:
      self._module._ExtractHuntResults(test_zip)
    self.assertEqual(
        error.exception.message,
        'Error manipulating file tests/lib/collectors/test_data/hunt.zip: ')
    self.assertTrue(error.exception.critical)
    mock_remove.assert_not_called()

  @mock.patch('os.remove')
  @mock.patch('zipfile.ZipFile.extract')
  def testBadZipFileExtractHuntResults(self, mock_extract, mock_remove):
    """Tests that a BadZipFile error when reading files generate errors."""
    self._module.output_path = '/directory'
    test_zip = 'tests/lib/collectors/test_data/hunt.zip'

    mock_extract.side_effect = zipfile.BadZipfile
    # pylint: disable=protected-access
    with self.assertRaises(errors.DFTimewolfError) as error:
      self._module._ExtractHuntResults(test_zip)

    self.assertEqual(
        error.exception.message,
        'Bad zipfile tests/lib/collectors/test_data/hunt.zip: ')
    self.assertTrue(error.exception.critical)
    mock_remove.assert_not_called()


class GRRHuntOsqueryDownloader(modules_test_base.ModuleTestBase):
  """Tests for the GRR Osquery hunt downloader."""

  @mock.patch('grr_api_client.api.InitHttp')
  def setUp(self, mock_InitHttp):
    self._InitModule(grr_hunt.GRRHuntOsqueryDownloader)
    self.mock_grr_api = mock.Mock()
    mock_InitHttp.return_value = self.mock_grr_api
    self._module.SetUp(
        hunt_id='H:12345',
        reason='random reason',
        grr_server_url='http://fake/endpoint',
        grr_username='admin',
        grr_password='admin',
        approvers='approver1,approver2',
        verify=False
    )
    self._module.output_path = '/tmp/test'

  def testInitialization(self):
    """Tests that the collector is correctly initialized."""
    # pytype: disable=attribute-error
    self.assertEqual(self._module.hunt_id, 'H:12345')
    # pytype: enable=attribute-error

  @mock.patch('dftimewolf.lib.collectors.grr_hunt.GRRHuntOsqueryDownloader._GetAndWriteResults')  # pylint: disable=line-too-long
  def testProcess(self, mock_get_write_results):
    """Tests that hunt results are downloaded to the correct path."""
    self.mock_grr_api.Hunt.return_value.Get.return_value = \
        mock_grr_hosts.MOCK_HUNT
    self._ProcessModule()
    mock_get_write_results.assert_called_with(mock_grr_hosts.MOCK_HUNT,
                                              '/tmp/test')

  @mock.patch('grr_api_client.hunt.Hunt.ListResults')
  def testGetAndWriteResults(self, mock_list_results):
    """Tests the GetAndWriteReslts function."""
    mock_result = mock.MagicMock()
    mock_result.payload = mock.MagicMock(spec=osquery_flows.OsqueryResult)
    mock_list_results.return_value = [mock_result]
    mock_client = mock.MagicMock()
    mock_client.data.os_info.fqdn = 'TEST'
    self.mock_grr_api.SearchClients.return_value = [mock_client]

    results = self._module._GetAndWriteResults(  # pylint: disable=protected-access
        mock_grr_hosts.MOCK_HUNT, '/tmp/test')

    self.assertEqual(len(results), 1)
    self.assertEqual(results[0][0], 'test')
    self.assertEqual(results[0][1], '/tmp/test/test.csv')

  @mock.patch('grr_api_client.hunt.Hunt.ListResults')
  def testGetAndWriteWrongResults(self, mock_list_results):
    """Tests the GetAndWriteReslts function with wrong results."""
    mock_result = mock.MagicMock()
    mock_result.payload = mock.MagicMock(spec=flows_pb2.FileFinderResult)
    mock_list_results.return_value = [mock_result]
    mock_client = mock.MagicMock()
    mock_client.data.os_info.fqdn = 'TEST'
    self.mock_grr_api.SearchClients.return_value = [mock_client]

    # pylint: disable=protected-access
    with self.assertRaises(errors.DFTimewolfError) as error:
      self._module._GetAndWriteResults(
          mock_grr_hosts.MOCK_HUNT, '/tmp/test')

    self.assertIn('Incorrect results format from', error.exception.message)
    self.assertIn('Possibly not an osquery hunt.', error.exception.message)
    self.assertTrue(error.exception.critical)


class GRRHuntYara(modules_test_base.ModuleTestBase):
  """Tests for the GRR Osquery hunt downloader."""

  mock_grr_api = None

  @mock.patch('grr_api_client.connectors.HttpConnector')
  def setUp(self, mock_InitHttp):
    self._InitModule(grr_hunt.GRRHuntYaraScanner)
    self.mock_grr_api = mock.Mock()
    mock_InitHttp.return_value = self.mock_grr_api

  @mock.patch('grr_api_client.connectors.HttpConnector')
  def testInitialization(self, mock_InitHttp):
    """Tests that the collector is correctly initialized."""
    mock_InitHttp.return_value = self.mock_grr_api

    self._module.SetUp(
        reason='random reason',
        hunt_description='random description',
        grr_server_url='http://fake/endpoint',
        grr_username='admin',
        grr_password='admin',
        approvers='approver1,approver2',
        verify=False,
        match_mode='all',
        client_operating_systems='win,linux',
        client_labels='label1',
        client_limit='999',
        process_ignorelist=['\\.exe', 'ignore1'],
        cmdline_ignorelist=None,
        dump_process_on_match=False
    )

    runner_args = self._module.hunt_runner_args
    assert runner_args is not None
    self.assertEqual(
      runner_args.client_rule_set.match_mode,
      runner_args.client_rule_set.MATCH_ALL)
    self.assertTrue(runner_args.client_rule_set.rules[0].os.os_windows)
    self.assertEqual(
      runner_args.client_rule_set.rules[1].label.label_names, ['label1'])
    self.assertEqual(runner_args.client_limit, 999)
    self.assertEqual(runner_args.avg_cpu_seconds_per_client_limit, 2000)

  @mock.patch('grr_api_client.connectors.HttpConnector')
  @mock.patch('grr_api_client.api.GrrApi.CreateHunt')
  def testProcess(self, mock_CreateHunt, mock_InitHttp):
    """Tests that the Process function is correctly called."""
    mock_InitHttp.return_value = self.mock_grr_api
    self._module.SetUp(
        reason='random reason',
        hunt_description='random description',
        grr_server_url='http://fake/endpoint',
        grr_username='admin',
        grr_password='admin',
        approvers='approver1,approver2',
        verify=False,
        match_mode='all',
        client_operating_systems='win,linux',
        client_labels='label1',
        client_limit='999',
        process_ignorelist=['\\.exe', 'ignore1'],
        cmdline_ignorelist=None,
        dump_process_on_match=False
    )

    self._module.StoreContainer(
      containers.YaraRule(
        name='test',
        rule_text=('rule test { strings: $a = "abcdefg" condition: '
                   '$a and pe.DLL }')))

    self._module.StoreContainer(
      containers.YaraRule(
        name='test2',
        rule_text=('rule test { strings: $a = "0123456" condition: '
                   '$a and math.entropy($a) }')))

    expected_runner_args = flows_pb2.HuntRunnerArgs(
      description='random description'
    )
    expected_runner_args.client_rule_set.match_mode = \
        expected_runner_args.client_rule_set.MATCH_ALL
    rule = expected_runner_args.client_rule_set.rules.add()
    rule.rule_type = rule.OS
    rule.os.os_windows = True
    rule.os.os_linux = True
    rule.os.os_darwin = False

    rule = expected_runner_args.client_rule_set.rules.add()
    rule.rule_type = rule.LABEL
    rule.label.label_names.append('label1')

    expected_runner_args.client_limit = 999
    expected_runner_args.client_rate= 1000
    expected_runner_args.crash_limit = 1000
    expected_runner_args.per_client_cpu_limit = 2000
    expected_runner_args.avg_cpu_seconds_per_client_limit = 2000
    expected_runner_args.network_bytes_limit = 10_737_418_240

    self._ProcessModule()
    mock_CreateHunt.assert_called_with(
      flow_name='YaraProcessScan',
      flow_args=flows_pb2.YaraProcessScanRequest(
          yara_signature=('import "math"\nimport "pe"\n\nrule test { '
                          'strings: $a = "abcdefg" condition: $a and pe.DLL }'
                          '\n\nrule test { strings: $a = "0123456" condition:'
                          ' $a and math.entropy($a) }'),
          ignore_grr_process=True,
          process_regex=r"(?i)^(?!.*(\.exe|ignore1)).*",
          cmdline_regex=None,
          skip_mapped_files=False,
          dump_process_on_match=False,
          process_dump_size_limit= 268_435_456,
      ),
      hunt_runner_args=expected_runner_args
    )

  @mock.patch('grr_api_client.connectors.HttpConnector')
  @mock.patch('grr_api_client.api.GrrApi.CreateHunt')
  def testSetupProcessIgnorelists(self,
                                  unused_mock_CreateHunt,
                                  unused_mock_http_connector):
    """Tests that the Process function is correctly called."""
    self._module.SetUp(
        reason='random reason',
        hunt_description='random description',
        grr_server_url='http://fake/endpoint',
        grr_username='admin',
        grr_password='admin',
        approvers='approver1,approver2',
        verify=False,
        match_mode='all',
        client_operating_systems='win,linux',
        client_labels='label1',
        client_limit='999',
        process_ignorelist=['\\.exe', 'onlyprocesses'],
        cmdline_ignorelist=None,
        dump_process_on_match=False
    )

    self.assertEqual(self._module.cmdline_ignorelist_regex, None)
    self.assertEqual(
      self._module.process_ignorelist_regex,
      r'(?i)^(?!.*(\.exe|onlyprocesses)).*')

  @mock.patch('grr_api_client.connectors.HttpConnector')
  @mock.patch('grr_api_client.api.GrrApi.CreateHunt')
  def testSetupCMDIgnorelists(self,
                              unused_mock_CreateHunt,
                              unused_mock_http_connector):
    """Tests applying a command line ignore list."""
    self._module.SetUp(
        reason='random reason',
        hunt_description='random description',
        grr_server_url='http://fake/endpoint',
        grr_username='admin',
        grr_password='admin',
        approvers='approver1,approver2',
        verify=False,
        match_mode='all',
        client_operating_systems='win,linux',
        client_labels='label1',
        client_limit='999',
        process_ignorelist=None,
        cmdline_ignorelist=['my cmd --line', 'onlycmdlines'],
        dump_process_on_match=False
    )

    self.assertEqual(
      self._module.cmdline_ignorelist_regex,
      '(?i)^(?!.*(my cmd --line|onlycmdlines)).*')
    self.assertEqual(self._module.process_ignorelist_regex, None)

  @mock.patch('grr_api_client.connectors.HttpConnector')
  @mock.patch('grr_api_client.api.GrrApi.CreateHunt')
  def testSetupIgnorelistsError(self,
                                unused_mock_CreateHunt,
                                unused_mock_http_connector):
    """Tests setting both process and cmd ignore lists raises an error."""
    with self.assertRaises(errors.DFTimewolfError) as error:
      self._module.SetUp(
          reason='random reason',
          hunt_description='random description',
          grr_server_url='http://fake/endpoint',
          grr_username='admin',
          grr_password='admin',
          approvers='approver1,approver2',
          verify=False,
          match_mode='all',
          client_operating_systems='win,linux',
          client_labels='label1',
          client_limit='999',
          process_ignorelist=['explorer.exe'],
          cmdline_ignorelist=['my cmd --line', 'onlycmdlines'],
          dump_process_on_match=False,
      )
    self.assertEqual(
        error.exception.message,
        'Only one of process_ignorelist or cmd_ignorelist can be specified')

if __name__ == '__main__':
  unittest.main()
