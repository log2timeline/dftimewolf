#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for Metawolf output utilities."""

import unittest
from unittest import mock
from unittest.mock import mock_open

import typing

from dftimewolf.lib import resources
from dftimewolf.metawolf import session
from dftimewolf.metawolf import utils


MOCK_SESSION_SETTABLE = session.SessionSettable(
    session_id='session_test',
    recipe='recipe_test',
    name='name_test',
    description='I am a mock!',
    value_type=str,
    optional=False
)
MOCK_SESSION_SETTABLE.SetValue('value_test')

MOCK_NO_VALUE_SETTABLE = session.SessionSettable(
    session_id='session_test',
    recipe='recipe_test',
    name='argument_1_test',
    description='I am another mock!',
    value_type=str,
    optional=False
)

MOCK_OPTIONAL_SETTABLE = session.SessionSettable(
    session_id='session_test',
    recipe='recipe_test',
    name='argument_2_test',
    description='I am yet another mock!',
    value_type=int,
    optional=True
)
MOCK_OPTIONAL_SETTABLE.SetValue(1)

MOCK_SESSION_SETTABLES = {
    'settable_1': MOCK_SESSION_SETTABLE,
    'settable_2': MOCK_OPTIONAL_SETTABLE,
    'settable_3': MOCK_NO_VALUE_SETTABLE
}

MOCK_SESSION_SETTABLE_JSON = {
    'session_id': 'session_test',
    'recipe': 'recipe_test',
    'name': 'name_test',
    'description': 'I am a mock!',
    'value': 'value_test',
    'type': 'str',
    'optional': False
}

MOCK_SESSION_JSON = {
    'last_active_session': 'session_test',
    'session_test': {
        'last_active_recipe': 'recipe_test',
        'recipe_test': {
            'session_test-recipe_test-param_name': MOCK_SESSION_SETTABLE_JSON
        }
    }
}

MOCK_DFTIMEWOLF_RECIPE = {
    'recipe_test': resources.Recipe(
        description='foo',
        contents={'name': 'recipe_test'},
        args=[('argument_1_test', '', None), ('--argument_2_test', '', None)]
    )
}


class MetawolfUtilsTest(unittest.TestCase):
  """Test utils.py"""
  # pylint: disable=unused-argument

  def testIsInt(self) -> None:
    """That whether or not a string is an int."""
    self.assertTrue(utils.MetawolfUtils().IsInt('1'))
    self.assertFalse(utils.MetawolfUtils().IsInt('1.4'))
    self.assertFalse(utils.MetawolfUtils().IsInt('string'))

  def testIsFloat(self) -> None:
    """That whether or not a string is a float."""
    self.assertTrue(utils.MetawolfUtils().IsFloat('1'))
    self.assertTrue(utils.MetawolfUtils().IsFloat('1.4'))
    self.assertFalse(utils.MetawolfUtils().IsFloat('string'))

  def testStr2Bool(self) -> None:
    """That whether or not a string can be represented as a boolean."""
    for s in ['YeS', 'tRue', 'T', 'y']:
      self.assertTrue(utils.MetawolfUtils().Str2Bool(s))
    for s in ['nO', 'fAlsE', 'f', 'N']:
      self.assertFalse(utils.MetawolfUtils().Str2Bool(s))
    self.assertIsNone(utils.MetawolfUtils().Str2Bool('foo'))

  def testGetType(self) -> None:
    """Test that the type of a string is inferred correctly."""
    self.assertEqual(bool, utils.MetawolfUtils().GetType('y'))
    self.assertEqual(int, utils.MetawolfUtils().GetType('0'))
    self.assertEqual(float, utils.MetawolfUtils().GetType('1.'))

  def testCastToType(self) -> None:
    """Test that a string can be cast to the desired type."""
    self.assertTrue(utils.MetawolfUtils().CastToType('y', bool))
    self.assertEqual(0, utils.MetawolfUtils().CastToType('0', int))
    self.assertEqual(1., utils.MetawolfUtils().CastToType('1.', float))

  def testMarshal(self) -> None:
    """Test that a session settable object marshals correctly."""
    self.assertEqual(MOCK_SESSION_SETTABLE_JSON,
                     utils.MetawolfUtils().Marshal(MOCK_SESSION_SETTABLE))

  def testUnmarshal(self) -> None:
    """Test that a JSON dict of a session settable unmarshalls correctly."""
    unmarshalled = utils.MetawolfUtils().Unmarshal(MOCK_SESSION_SETTABLE_JSON)
    self.assertEqual(
        MOCK_SESSION_SETTABLE.session_id,
        unmarshalled.session_id)
    self.assertEqual(
        MOCK_SESSION_SETTABLE.description,
        unmarshalled.description)
    self.assertEqual(
        MOCK_SESSION_SETTABLE.GetValue(),
        unmarshalled.GetValue())

  @mock.patch('json.loads')
  @mock.patch(
      'builtins.open', new_callable=mock_open, read_data=str(MOCK_SESSION_JSON))
  @mock.patch('os.path.exists')
  @typing.no_type_check
  def testReadSessionFromFile(self, mock_exists, m_open, mock_json) -> None:
    """Test that the session file is read correctly."""
    mock_exists.return_value = True
    mock_json.return_value = MOCK_SESSION_JSON
    s = utils.MetawolfUtils().ReadSessionFromFile()
    self.assertIn('session_test', s)
    json_session_settable = s['session_test']['recipe_test'][
      'session_test-recipe_test-param_name']
    # Check a few fields for equality
    self.assertEqual(MOCK_SESSION_SETTABLE.session_id,
                     json_session_settable.session_id)
    self.assertEqual(MOCK_SESSION_SETTABLE.description,
                     json_session_settable.description)
    self.assertEqual(MOCK_SESSION_SETTABLE.GetValue(),
                     json_session_settable.GetValue())

    s = utils.MetawolfUtils().ReadSessionFromFile(unmarshal=False)
    self.assertIn('session_test', s)
    self.assertEqual(
        MOCK_SESSION_SETTABLE_JSON,
        s['session_test']['recipe_test']['session_test-recipe_test-param_name'])

  @mock.patch('dftimewolf.lib.recipes.manager.RecipesManager.Recipes')
  @typing.no_type_check
  def testPrepareDFTimewolfCommand(self, mock_recipes) -> None:
    """Test that the DFTimewolf command is constructed correctly."""
    # If a non-optional settable has no value, the command should be empty
    cmd = utils.MetawolfUtils().PrepareDFTimewolfCommand(
        'recipe_test', MOCK_SESSION_SETTABLES)
    self.assertEqual([], cmd)

    # Mock DFTimewolf's recipe call
    mock_recipes.return_value = MOCK_DFTIMEWOLF_RECIPE
    # Assign values to non-optional settables
    MOCK_NO_VALUE_SETTABLE.SetValue('non_optional_param_value')
    # Prepare the command
    cmd = utils.MetawolfUtils().PrepareDFTimewolfCommand(
        'recipe_test', MOCK_SESSION_SETTABLES)
    self.assertEqual(
        ['dftimewolf', 'recipe_test', 'non_optional_param_value',
         '--argument_2_test=1'], cmd)
