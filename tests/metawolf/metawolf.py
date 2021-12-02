#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for Metawolf."""

import os
import unittest
import typing
from unittest import mock

from dftimewolf.metawolf import metawolf


class MetawolfTest(unittest.TestCase):
  """Integration tests for Metawolf."""

  @typing.no_type_check
  def RunTranscript(self, path_to_transcript: str) -> int:
    """Run a test in cmd2 using the transcript stored at path_to_transcript.

    Args:
      path_to_transcript (str): The path to the transcript to test.

    Returns:
      int: 0 if the test succeeded, 1 otherwise.
    """
    self.m = metawolf.Metawolf(
        session_path=self.session_file,
        transcript_files=[path_to_transcript])
    self.m.metawolf_utils.session_path = self.tmp_file
    return self.m.cmdloop()

  @typing.no_type_check
  def setUp(self) -> None:
    """Setup test cases."""
    self.m = None
    self.session_file = os.path.join(os.path.dirname(
        os.path.realpath(__file__)), 'metawolf-transcript-session.json')
    self.tmp_file = '/tmp/metawolf-test'

  @typing.no_type_check
  def testSet(self) -> None:
    """Test the `set` command."""
    return_code = self.RunTranscript(os.path.join(os.path.dirname(
        os.path.realpath(__file__)), './transcripts/set.txt'))
    self.assertEqual(0, return_code)

  @typing.no_type_check
  def testSetOnce(self) -> None:
    """Test the `set param value` command."""
    return_code = self.RunTranscript(os.path.join(os.path.dirname(
        os.path.realpath(__file__)), './transcripts/setOnce.txt'))
    self.assertEqual(0, return_code)

  @mock.patch('builtins.input')
  @typing.no_type_check
  def testSetAll(self, mock_input) -> None:
    """Test the `set all` command."""
    # These values will be sent to input() when looping on `set all`
    mock_input.side_effect = [
        'value_1', 'value_2', 'value_3', '', '', '', '', '', '']
    return_code = self.RunTranscript(os.path.join(os.path.dirname(
        os.path.realpath(__file__)), './transcripts/setAll.txt'))
    self.assertEqual(0, return_code)

  @typing.no_type_check
  def testShow(self) -> None:
    """Test the `show` command."""
    return_code = self.RunTranscript(os.path.join(os.path.dirname(
        os.path.realpath(__file__)), './transcripts/show.txt'))
    self.assertEqual(0, return_code)

  @typing.no_type_check
  def testShowRecipe(self) -> None:
    """Test the `show recipe recipe_name` command."""
    return_code = self.RunTranscript(os.path.join(os.path.dirname(
        os.path.realpath(__file__)), './transcripts/showRecipe.txt'))
    self.assertEqual(0, return_code)

  @typing.no_type_check
  def testShowRunning(self) -> None:
    """Test the `show running` command when there are no running processes."""
    return_code = self.RunTranscript(os.path.join(os.path.dirname(
        os.path.realpath(__file__)), './transcripts/showRunningEmpty.txt'))
    self.assertEqual(0, return_code)

  @typing.no_type_check
  def testPrepareSessionThenShow(self) -> None:
    """Test the `show sessions` command once a recipe has been set."""
    return_code = self.RunTranscript(os.path.join(os.path.dirname(
        os.path.realpath(
            __file__)), './transcripts/prepareSessionThenShow.txt'))
    self.assertEqual(0, return_code)

  @mock.patch('builtins.input')
  @typing.no_type_check
  def testPrepareProcessThenRun(self, mock_input) -> None:
    """Test the `run` command once recipe/parameters have been set."""
    # These values will be sent to input() when looping on `set all`. The last
    # input ('y') confirms the run.
    mock_input.side_effect = [
        'value_1', 'value_2', 'value_3', '', '', '', '', '', '', 'y']
    return_code = self.RunTranscript(os.path.join(os.path.dirname(
        os.path.realpath(__file__)), './transcripts/prepareProcessThenRun.txt'))
    self.assertEqual(0, return_code)

  @mock.patch('builtins.input')
  @typing.no_type_check
  def testSwitchRecipeNoCopyOver(self, mock_input) -> None:
    """Test that parameters stay in place when switching recipe back to back."""
    # These values will be sent to input() when looping on `set all`. The last
    # inputs ('N') deny the copy over option.
    mock_input.side_effect = [
        'value_1', 'value_2', 'value_3', '', '', '', '', '', '', 'N', 'N']
    return_code = self.RunTranscript(os.path.join(os.path.dirname(
        os.path.realpath(
            __file__)), './transcripts/switchRecipeNoCopyOver.txt'))
    self.assertEqual(0, return_code)

  @mock.patch('builtins.input')
  @typing.no_type_check
  def testSwitchRecipeCopyOver(self, mock_input) -> None:
    """Test that parameters are replaced when switching recipe back to back."""
    # These values will be sent to input() when looping on `set all`. The last
    # inputs ('y') accept the copy over option.
    mock_input.side_effect = [
        'value_1', 'value_2', 'value_3', '', '', '', '', '', '', 'y', 'y']
    return_code = self.RunTranscript(os.path.join(os.path.dirname(
        os.path.realpath(__file__)), './transcripts/switchRecipeCopyOver.txt'))
    self.assertEqual(0, return_code)

  @mock.patch('builtins.input')
  @typing.no_type_check
  def testClearThenReload(self, mock_input) -> None:
    """Test the `clear` and `reload` command."""
    # These values will be sent to input() when looping on `set all`
    mock_input.side_effect = [
        'value_1', 'value_2', 'value_3', '', '', '', '', '', '']
    return_code = self.RunTranscript(os.path.join(os.path.dirname(
        os.path.realpath(__file__)), './transcripts/clearThenReload.txt'))
    self.assertEqual(0, return_code)

  @typing.no_type_check
  def tearDown(self) -> None:
    for recipe in self.m.metawolf_utils.recipe_manager.GetRecipes():
      self.m.metawolf_utils.recipe_manager.DeregisterRecipe(recipe)
    try:
      os.remove(self.tmp_file)
    except IOError:
      pass
