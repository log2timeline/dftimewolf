#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the SkipOnResumeIfComplete decorator of the base module."""

import unittest
from unittest import mock

from dftimewolf.lib import errors
from dftimewolf.lib import module
from tests.lib import modules_test_base


class _Copier(module.BaseModule):
  """A module with one decorated step, which counts its runs."""

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.runs = 0
    self.valid = True
    self.undone: list[str] = []

  def SetUp(self, *args, **kwargs) -> None:
    """Needs no set up."""

  def Process(self) -> None:
    """Has no process."""

  def _StillValid(self, result: str, name: str) -> bool:
    del result, name  # Unused.
    return self.valid

  def _Undo(self, result: str, name: str) -> None:
    del name  # Unused.
    self.undone.append(result)

  @module.SkipOnResumeIfComplete(still_valid=_StillValid, undo=_Undo)
  def Copy(self, name: str) -> str:
    """Returns the name of a new copy, or '' if the name is empty."""
    self.runs += 1
    return f'{name}-copy-{self.runs}' if name else ''


class SkipOnResumeIfCompleteTest(modules_test_base.ModuleTestBase):
  """Tests the SkipOnResumeIfComplete decorator."""

  _module: _Copier

  def setUp(self):
    super().setUp()
    self._InitModule(_Copier)

  def testCliRunsEachCall(self):
    """Tests that a cache that keeps no resume keys runs each call."""
    self.assertEqual(self._module.Copy('disk'), 'disk-copy-1')
    self.assertEqual(self._module.Copy('disk'), 'disk-copy-2')

    self._ResumeModule()
    self.assertEqual(self._module.Copy('disk'), 'disk-copy-1')

  def testResumeSkipsACompleteCall(self):
    """Tests that a resumed run skips a complete call while it is valid."""
    self._KeepResumeKeys()
    self.assertEqual(self._module.Copy('disk'), 'disk-copy-1')

    self._ResumeModule()
    self.assertEqual(self._module.Copy('disk'), 'disk-copy-1')
    self.assertEqual(self._module.Copy('other'), 'other-copy-1')
    self.assertEqual(self._module.runs, 1)

    self._module.valid = False
    self.assertEqual(self._module.Copy('disk'), 'disk-copy-2')

  def testFalseResultIsNotRecorded(self):
    """Tests that a resumed run repeats a call that returned a false result."""
    self._KeepResumeKeys()
    self.assertEqual(self._module.Copy(''), '')

    self._ResumeModule()
    self.assertEqual(self._module.Copy(''), '')
    self.assertEqual(self._module.runs, 1)

  def testFailedRecordUndoesTheCall(self):
    """Tests that a failed record undoes the call and stops the module."""
    self._KeepResumeKeys()
    self.enter_context(
        mock.patch.object(self._cache, 'AddToCache',
                          side_effect=errors.DFTimewolfError('No record')))

    with self.assertRaisesRegex(errors.DFTimewolfError, 'No record'):
      self._module.Copy('disk')
    self.assertEqual(self._module.undone, ['disk-copy-1'])


if __name__ == '__main__':
  unittest.main()
