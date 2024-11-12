"""Tests for filesystem export of Dataframe containers module."""

import tempfile

from absl.testing import absltest
from absl.testing import parameterized

import pandas as pd

from dftimewolf import config
from dftimewolf.lib.containers import containers
from dftimewolf.lib import state, errors
from dftimewolf.lib.exporters import df_to_filesystem


# pylint: disable=line-too-long
_INPUT_DF = pd.DataFrame(
    data=[['2024-11-01T00:00:01', 'value_1', 'value_2', 'value_3'],
          ['2024-11-01T00:00:02', 'value_4', None, True],
          ['2024-11-01T00:00:03', 1, 1.1, 1.11111111111],
          ['2024-11-01T00:00:04',
           {'key_4': 'value_5', 'key_5': 'value_6'},
           ['value_7', 'value_8', 'Value_9'],
           '']],
    columns=['datetime', 'key_1', 'key_2', 'key_3'])

_EXPECTED_JSONL = """{"datetime":"2024-11-01T00:00:01","key_1":"value_1","key_2":"value_2","key_3":"value_3"}
{"datetime":"2024-11-01T00:00:02","key_1":"value_4","key_2":null,"key_3":true}
{"datetime":"2024-11-01T00:00:03","key_1":1,"key_2":1.1,"key_3":1.1111111111}
{"datetime":"2024-11-01T00:00:04","key_1":{"key_4":"value_5","key_5":"value_6"},"key_2":["value_7","value_8","Value_9"],"key_3":""}
"""

_EXPECTED_CSV = """datetime,key_1,key_2,key_3
2024-11-01T00:00:01,value_1,value_2,value_3
2024-11-01T00:00:02,value_4,,True
2024-11-01T00:00:03,1,1.1,1.11111111111
2024-11-01T00:00:04,"{'key_4': 'value_5', 'key_5': 'value_6'}","['value_7', 'value_8', 'Value_9']",
"""

_EXPECTED_MD = """| datetime            | key_1                                    | key_2                             | key_3         |
|:--------------------|:-----------------------------------------|:----------------------------------|:--------------|
| 2024-11-01T00:00:01 | value_1                                  | value_2                           | value_3       |
| 2024-11-01T00:00:02 | value_4                                  |                                   | True          |
| 2024-11-01T00:00:03 | 1                                        | 1.1                               | 1.11111111111 |
| 2024-11-01T00:00:04 | {'key_4': 'value_5', 'key_5': 'value_6'} | ['value_7', 'value_8', 'Value_9'] |               |"""
# pylint: enable=line-too-long


class DataFrameToDiskExporterTest(parameterized.TestCase):
  """Tests DataFrameToDiskExporter."""

  def setUp(self):
    """Setup."""
    self._test_state = state.DFTimewolfState(config.Config)
    self._module = df_to_filesystem.DataFrameToDiskExporter(self._test_state)
    self._out_dir = tempfile.mkdtemp()

    self._module.StoreContainer(container=containers.DataFrame(
      data_frame=_INPUT_DF,
      description='A test dataframe',
      name='test_dataframe'))

  def test_Defaults(self):
    """Tests operation with no params specified."""
    self._module.SetUp(output_formats='',
                       output_directory='')
    self._module.Process()

    out_containers = self._test_state.GetContainers(containers.File)
    self.assertLen(out_containers, 1)

    with open(out_containers[0].path, 'r') as f:
      self.assertEqual(f.read(), _EXPECTED_JSONL)

  def test_JSONL(self):
    """Tests outputting JSONL."""
    self._module.SetUp(output_formats='jsonl',
                       output_directory=self._out_dir)
    self._module.Process()

    out_containers = self._test_state.GetContainers(containers.File)
    self.assertLen(out_containers, 1)

    self.assertEndsWith(out_containers[0].path, '.jsonl')
    with open(out_containers[0].path, 'r') as f:
      self.assertEqual(f.read(), _EXPECTED_JSONL)

  def test_CSV(self):
    """Tests outputting CSV."""
    self._module.SetUp(output_formats='csv',
                       output_directory=self._out_dir)
    self._module.Process()

    out_containers = self._test_state.GetContainers(containers.File)
    self.assertLen(out_containers, 1)

    self.assertEndsWith(out_containers[0].path, '.csv')
    with open(out_containers[0].path, 'r') as f:
      self.assertEqual(f.read(), _EXPECTED_CSV)

  def test_Markdown(self):
    """Tests outputting markdown."""
    self._module.SetUp(output_formats='markdown',
                       output_directory=self._out_dir)
    self._module.Process()

    out_containers = self._test_state.GetContainers(containers.File)
    self.assertLen(out_containers, 1)

    self.assertEndsWith(out_containers[0].path, '.md')
    with open(out_containers[0].path, 'r') as f:
      self.assertEqual(f.read(), _EXPECTED_MD)

  def test_Multiple(self):
    """Tests that multiple outputs are generated when specified."""
    self._module.SetUp(output_formats='jsonl,csv,markdown',
                       output_directory=self._out_dir)
    self._module.Process()

    out_containers = self._test_state.GetContainers(containers.File)
    self.assertLen(out_containers, 3)

    actual_results = []
    expected_results = (_EXPECTED_JSONL, _EXPECTED_CSV, _EXPECTED_MD)

    for c in out_containers:
      with open(c.path, 'r') as f:
        actual_results.append(f.read())

    for r in actual_results:
      self.assertIn(r, expected_results)
    for e in expected_results:
      self.assertIn(e, actual_results)

  def test_InvalidFormat(self):
    """Tests an error is thrown when an invalid format is selected."""
    with self.assertRaisesRegex(
        errors.DFTimewolfError, r'Invalid format\(s\) specified: foobar'):
      self._module.SetUp(output_formats='jsonl,foobar',
                         output_directory=self._out_dir)


if __name__ == '__main__':
  absltest.main()
