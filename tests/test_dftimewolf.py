"""Tests for DFTimewolf functions."""
import argparse
from unittest import TestCase
import os
import shutil

from dftimewolf.cli import dftimewolf_recipes

parser = argparse.ArgumentParser()
parser.add_argument('parameterone')
parser.add_argument('--optional_param')
parser.add_argument('--spaces_param')
parser.add_argument('explosion')


class DFTimewolfTest(TestCase):
  """Tests for timeflow_recipes functions."""

  backup_config = None
  user_config_dir = None

  def setUp(self):
    # Copy user_config.py.sample to an actual user_config.py filesystem
    current_path = os.getcwd()
    user_config_dir = os.path.join(current_path, "dftimewolf")
    self.user_config_path = os.path.join(user_config_dir, "user_config.py")

    # If a config file exists, make a backup
    if os.path.isfile(self.user_config_path):
      backup_config = os.path.join(user_config_dir, "backup")
      shutil.move(self.user_config_path, backup_config)
      self.backup_config = backup_config

    # Move sample config to user config
    sample_config = os.path.join(user_config_dir, "user_config.py.sample")
    shutil.copy(sample_config, self.user_config_path)

  def tearDown(self):
    # Restore backup config if there was one
    if self.backup_config:
      shutil.move(self.backup_config, self.user_config_path)
    # Or delete dummy config
    else:
      os.remove(self.user_config_path)


  def test_import_args_from_cli(self):
    """Tries parsing the CLI arguments and updating a recipe dictionary."""

    recipe_args = {
        'recipe_arg1': 'This should remain intact',
        'recipe_arg2': 'This should be replaced: @parameterone',
        'recipe_arg3': 'This should be replaced by @optional_param',
        'recipe_arg4': 'This includes spaces: @spaces_param',
        'recipe_arg5': 'Characters after param: @explosion!',
    }

    expected_args = {
        'recipe_arg1': 'This should remain intact',
        'recipe_arg2': 'This should be replaced: value_for_param_one',
        'recipe_arg3': 'This should be replaced by 3',
        'recipe_arg4': 'This includes spaces: S P A C E',
        'recipe_arg5': 'Characters after param: BOOM!',
    }

    args = parser.parse_args([
        'value_for_param_one',
        '--optional_param', '3',
        '--spaces_param', 'S P A C E',
        'BOOM',
    ])

    imported_args = dftimewolf_recipes.import_args_from_cli(recipe_args, args)
    self.assertEqual(imported_args, expected_args)

  def test_nonexistent_arg(self):
    """Makes sure that an exception is raised for unknown @ variables.

    A recipe writer needs to define a parsing tuple for each @ variable used by
    the recipe.
    """

    recipe_args = {
        'recipe_arg1': 'This should be replaced: @parameterone',
        'recipe_arg2': 'This arg cannot be replaced @nonexistent',
    }

    args = parser.parse_args([
        'value_for_param_one',
        '--optional_param', '3',
        '--spaces_param', 'So unique!',
        'BOOM',
    ])

    with self.assertRaises(AttributeError):
      dftimewolf_recipes.import_args_from_cli(recipe_args, args)
