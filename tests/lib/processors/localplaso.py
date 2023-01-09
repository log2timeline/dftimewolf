#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the localplaso processor."""

import unittest
import re
import mock
import docker

from dftimewolf.lib import state
from dftimewolf.lib import errors
from dftimewolf.lib.processors import localplaso
from dftimewolf.lib.containers import containers

from dftimewolf import config


class LocalPlasoTest(unittest.TestCase):
  """Tests for the local Plaso processor."""

  def testInitialization(self):
    """Tests that the processor can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    local_plaso_processor = localplaso.LocalPlasoProcessor(test_state)
    self.assertIsNotNone(local_plaso_processor)

  # pylint: disable=invalid-name
  @mock.patch('os.path.isfile')
  @mock.patch('subprocess.Popen')
  @mock.patch('docker.from_env')
  def testProcessing(self, mock_docker, mock_Popen, mock_exists):
    """Tests that the correct number of containers is added."""
    test_state = state.DFTimewolfState(config.Config)
    mock_popen_object = mock.Mock()
    mock_popen_object.communicate.return_value = (None, None)
    mock_popen_object.wait.return_value = False
    mock_Popen.return_value = mock_popen_object
    mock_exists.return_value = True
    mock_docker().images.get.side_effect = docker.errors.ImageNotFound(
        message="")

    local_plaso_processor = localplaso.LocalPlasoProcessor(test_state)
    local_plaso_processor.StoreContainer(
        containers.File(name='test', path='/notexist/test'))
    local_plaso_processor.SetUp()
    local_plaso_processor.Process()
    mock_Popen.assert_called_once()
    args = mock_Popen.call_args[0][0]  # Get positional arguments of first call
    self.assertEqual(args[10], '/notexist/test')
    plaso_path = args[9]  # Dynamically generated path to the plaso file
    self.assertEqual(
        local_plaso_processor.GetContainers(containers.File)[0].path,
        plaso_path)

  @mock.patch('docker.from_env')
  def testProcessingDockerized(self, mock_docker):
    """Tests that plaso processing is called using Docker."""
    test_state = state.DFTimewolfState(config.Config)
    mock_docker.return_value = mock.Mock()
    local_plaso_processor = localplaso.LocalPlasoProcessor(test_state)
    local_plaso_processor.StoreContainer(
        containers.File(name='test', path='/notexist/test'))
    local_plaso_processor.SetUp()
    local_plaso_processor.Process()
    mock_docker().containers.run.assert_called_once()
    args = mock_docker().containers.run.call_args[1]
    # Get the plaso output file name, which was dynamically generated
    match = re.match(r".*/([a-z0-9]+\.plaso).*", args['command'])
    self.assertIsNotNone(match)
    self.assertRegex(
        local_plaso_processor.GetContainers(containers.File)[0].path,
        f".*/{match.group(1)}")  # pytype: disable=attribute-error

  @mock.patch.dict('os.environ', {'PATH': '/fake/path:/fake/path/2'})
  @mock.patch('os.path.isfile')
  def testPlasoCheck(self, mock_exists):
    """Tests that a plaso executable is correctly located."""
    test_state = state.DFTimewolfState(config.Config)
    mock_exists.return_value = True
    local_plaso_processor = localplaso.LocalPlasoProcessor(test_state)
    # We're testing module internals here.
    # pylint: disable=protected-access
    local_plaso_processor._DeterminePlasoPath()
    self.assertEqual(
        local_plaso_processor._plaso_path, '/fake/path/log2timeline.py')

  @mock.patch('os.path.isfile')
  @mock.patch('docker.from_env')
  def testPlasoCheckFail(self, mock_docker, mock_exists):
    """Tests that SetUp fails when no plaso executable is found."""
    test_state = state.DFTimewolfState(config.Config)
    mock_exists.return_value = False
    mock_docker().images.get.side_effect = docker.errors.ImageNotFound(
        message="")
    local_plaso_processor = localplaso.LocalPlasoProcessor(test_state)
    with self.assertRaises(errors.DFTimewolfError) as error:
      local_plaso_processor.SetUp()
    self.assertEqual((
        'Could not run log2timeline.py from PATH or a local Docker image. '
        'To fix: \n'
        '  "apt install plaso-tools" or "docker pull log2timeline/plaso"'),
                     error.exception.message)

  @mock.patch('os.path.isfile')
  @mock.patch('docker.from_env')
  def testPlasoPreferredInstallation(self, mock_docker, mock_exists):
    """Tests that SetUp prefers Docker plaso installation over native."""
    test_state = state.DFTimewolfState(config.Config)
    mock_exists.return_value = True
    mock_docker.return_value = mock.MagicMock()
    local_plaso_processor = localplaso.LocalPlasoProcessor(test_state)
    local_plaso_processor.SetUp()
    # pylint: disable=protected-access
    self.assertTrue(local_plaso_processor._use_docker)

  @mock.patch('os.path.isfile')
  @mock.patch('docker.from_env')
  def testNativePlasoSetup(self, mock_docker, mock_exists):
    """Tests that SetUp chooses native plaso if no Dockerized installation."""
    test_state = state.DFTimewolfState(config.Config)
    mock_exists.return_value = True
    mock_docker().images.get.side_effect = docker.errors.ImageNotFound(
        message="")
    local_plaso_processor = localplaso.LocalPlasoProcessor(test_state)
    local_plaso_processor.SetUp()
    # pylint: disable=protected-access
    self.assertFalse(local_plaso_processor._use_docker)


if __name__ == '__main__':
  unittest.main()
