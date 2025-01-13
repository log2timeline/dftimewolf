#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the GCEForensicsVM generator."""

# pytype: disable=attribute-error


from absl.testing import absltest
from absl.testing import parameterized

import mock
from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.gcp.internal import compute
from libcloudforensics import errors as lcf_errors

from dftimewolf.lib import errors
from dftimewolf.lib.containers import containers
from dftimewolf.lib.processors.gce_forensics_vm import GCEForensicsVM
from tests.lib import modules_test_base

FAKE_PROJECT = gcp_project.GoogleCloudProject(
    'test-target-project-name',
    'fake_zone')
FAKE_ANALYSIS_VM = compute.GoogleComputeInstance(
    FAKE_PROJECT.project_id,
    'fake_zone',
    'fake-analysis-vm')


class GCEForensicsVMTest(modules_test_base.ModuleTestBase):
  """Tests for the Forensics VM creator."""

  def setUp(self):
    self._InitModule(GCEForensicsVM)
    super().setUp()

  # pylint: disable=invalid-name,line-too-long
  def testSetUp(self):
    """Tests SetUp of the processor."""
    self._module.SetUp(
        'test-analysis-project-name',
        'test-incident-id',
        'test-zone',
        120,
        'pd-standard',
        64,
        'test-image-project',
        'test-image-family',
        True,
        'gcp-forensics-vm'
    )
    self.assertEqual(self._module.project.project_id,
                     'test-analysis-project-name')
    self.assertEqual(self._module.incident_id, 'test-incident-id')
    self.assertEqual(self._module.project.default_zone, 'test-zone')
    self.assertEqual(self._module.boot_disk_size, 120)
    self.assertEqual(self._module.cpu_cores, 64)
    self.assertEqual(self._module.image_project, 'test-image-project')
    self.assertEqual(self._module.image_family, 'test-image-family')

  # pylint: disable=line-too-long
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeDisk')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeInstance.GetBootDisk')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute_base_resource.GoogleComputeBaseResource.AddLabels')
  @mock.patch('libcloudforensics.providers.gcp.forensics.StartAnalysisVm')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeInstance.AttachDisk')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeInstance.GetPowerState')
  @mock.patch('time.sleep')
  # pylint: enable=line-too-long
  def testProcess(self,
                  mock_sleep,
                  mock_GetPowerState,
                  mock_AttachDisk,
                  mock_StartAnalysisVm,
                  mock_AddLabels,
                  mock_GetBootDisk,
                  mock_DiskInit):
    """Tests the collector's Process() function."""
    mock_sleep.return_value = None
    mock_GetPowerState.return_value = 'RUNNING'
    mock_StartAnalysisVm.return_value = (FAKE_ANALYSIS_VM, None)
    FAKE_ANALYSIS_VM.AddLabels = mock_AddLabels
    FAKE_ANALYSIS_VM.GetBootDisk = mock_GetBootDisk

    disk1 = compute.GoogleComputeDisk(
        'test-analysis-project-name', 'test-zone', 'test-disk-1')
    disk2 = compute.GoogleComputeDisk(
        'test-analysis-project-name', 'test-zone', 'test-disk-2')
    disk3 = compute.GoogleComputeDisk(
        'test-analysis-project-name', 'test-zone', 'test-disk-3')
    mock_DiskInit.side_effect = [disk1, disk2, disk3]

    self._module.StoreContainer(containers.GCEDisk(
        'test-disk-1', 'test-analysis-project-name'))
    self._module.StoreContainer(containers.GCEDisk(
        'test-disk-2', 'test-analysis-project-name'))
    self._module.StoreContainer(containers.GCEDisk(
        'test-disk-3', 'test-analysis-project-name'))

    self._module.SetUp(
        'test-analysis-project-name',
        'test-incident-id',
        'test-zone',
        120,
        'pd-standard',
        64,
        'test-image-project',
        'test-image-family',
        True,
        'gcp-forensics-vm'
    )
    self._module.Process()

    mock_StartAnalysisVm.assert_called_with(
        'test-analysis-project-name',
        'gcp-forensics-vm-test-incident-id',
        'test-zone',
        120,
        'pd-standard',
        64,
        image_project='test-image-project',
        image_family='test-image-family'
    )
    mock_AddLabels.assert_has_calls([
        mock.call({'incident_id': 'test-incident-id'})])

    self.assertEqual(1, len(self._module.GetContainers(containers.ForensicsVM)))
    forensics_vm = self._module.GetContainers(containers.ForensicsVM)[0]
    self.assertEqual(forensics_vm.name, 'fake-analysis-vm')

    self.assertEqual(mock_AttachDisk.call_count, 3)
    mock_AttachDisk.assert_has_calls([
      mock.call(disk1),
      mock.call(disk2),
      mock.call(disk3),
    ])

    actual_disks = self._module.GetContainers(containers.GCEDisk)
    actual_disk_names = [d.name for d in actual_disks]

    self.assertEqual(3, len(actual_disks))
    expected_disk_names = ['test-disk-1', 'test-disk-2', 'test-disk-3']
    self.assertEqual(expected_disk_names, actual_disk_names)

  @mock.patch('libcloudforensics.providers.gcp.forensics.StartAnalysisVm')
  def testProcessResourceCreationFailure(self, mock_StartAnalysisVM):
    """Tests correct handling of a failure to create the forensics VM."""
    mock_StartAnalysisVM.side_effect = lcf_errors.ResourceCreationError(
      'Permission denied', 'name')

    self._module.SetUp(
        'test-analysis-project-name',
        'test-incident-id',
        'test-zone',
        120,
        'pd-standard',
        64,
        'test-image-project',
        'test-image-family',
        True,
        'gcp-forensics-vm'
    )
    with self.assertRaises(errors.DFTimewolfError) as error:
      self._module.Process()
    self.assertEqual(error.exception.message, 'Permission denied')

  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeInstance.AttachDisk')
  @mock.patch('libcloudforensics.providers.gcp.forensics.StartAnalysisVm')
  def testNoCreateVMFlag(self, mock_StartAnalysisVM, mock_AttachDisk):
    """Tests that nothing happens when create_analysis_vm is false."""
    for d in ['test-disk-1', 'test-disk-2', 'test-disk-3']:
      self._module.StoreContainer(
          containers.GCEDisk(d, 'test-analysis-project-name'))

    self._module.SetUp(
        'test-analysis-project-name',
        'test-incident-id',
        'test-zone',
        120,
        'pd-standard',
        64,
        'test-image-project',
        'test-image-family',
        False,
        'gcp-forensics-vm'
    )
    self._module.Process()

    self.assertIsNone(self._module.project)
    mock_StartAnalysisVM.assert_not_called()
    mock_AttachDisk.assert_not_called()

    self.assertEqual(3, len(self._module.GetContainers(containers.GCEDisk)))
    expected_disks = ['test-disk-1', 'test-disk-2', 'test-disk-3']
    actual_disks = [
        d.name for d in self._module.GetContainers(containers.GCEDisk)]
    self.assertEqual(expected_disks, actual_disks)

  # pylint: disable=line-too-long
  @parameterized.named_parameters(
      ('id_and_empty', '12345', '', 'gcp-forensics-vm-12345'),
      ('id_and_name', '12345', 'vm_name', 'vm_name-12345'),
      ('empty_and_name', '', 'vm_name', 'vm_name-abcd'),
      ('id_in_name', '12345', 'vm_12345_name', 'vm_12345_name'),
  )
  @mock.patch('libcloudforensics.providers.gcp.forensics.StartAnalysisVm')
  @mock.patch('libcloudforensics.providers.gcp.internal.common.GenerateUniqueInstanceName')
  @mock.patch('time.sleep')
  # pylint: enable=line-too-long
  def testVMNames(self,
                  incident_id,
                  vm_name,
                  expected_vm_name_result,
                  mock_sleep,
                  mock_GenerateUniqueInstanceName,
                  mock_StartAnalysisVm):
    """Tests naming the created VM."""
    mock_sleep.return_value = None
    mock_StartAnalysisVm.return_value = (FAKE_ANALYSIS_VM, None)
    mock_GenerateUniqueInstanceName.return_value = f'{vm_name}-abcd'

    self._module.SetUp(
        'test-analysis-project-name',
        incident_id,
        'test-zone',
        120,
        'pd-standard',
        64,
        'test-image-project',
        'test-image-family',
        True,
        vm_name
    )
    self._module.Process()

    mock_StartAnalysisVm.assert_called_with(
        mock.ANY,
        expected_vm_name_result,
        mock.ANY,
        mock.ANY,
        mock.ANY,
        mock.ANY,
        image_project=mock.ANY,
        image_family=mock.ANY
    )


if __name__ == '__main__':
  absltest.main()
