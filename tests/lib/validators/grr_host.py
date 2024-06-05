# -*- coding: utf-8 -*-
"""Tests for the GRR host validator."""

import unittest

from dftimewolf.lib import errors, resources
from dftimewolf.lib.validators import grr_host


class GRRHostValidatorTest(unittest.TestCase):
  """Tests the GRRHostValidator class."""

  def setUp(self):
    """Setup."""
    self.validator = grr_host.GRRHostValidator()
    self.recipe_argument = resources.RecipeArgument()
    self.recipe_argument.switch = 'testgrrhost'

  def testInit(self):
    """Tests initialization."""
    self.assertEqual(self.validator.NAME, 'grr_host')

  def testValidateSuccess(self):
    """Test successful validation."""
    client_ids = ['C.1facf5562db006ad',
             'grr-client-ubuntu.c.ramoj-playground.internal',
             'grr-client']
    for client_id in client_ids:
      val = self.validator.Validate(client_id, self.recipe_argument)
      self.assertEqual(val, client_id)

    self.recipe_argument.validation_params['comma_separated'] = True
    val = self.validator.Validate(','.join(client_ids), self.recipe_argument)
    self.assertEqual(val, ','.join(client_ids))

  def testValidationFailure(self):
    """Tests validation failures."""
    fqdns = ['a-.com', 'C.a', 'C.01234567890123456789']
    for fqdn in fqdns:
      with self.assertRaisesRegex(
          errors.RecipeArgsValidationFailure,
          'Not a GRR host identifier'):
        self.validator.Validate(fqdn, self.recipe_argument)

    self.recipe_argument.validation_params['comma_separated'] = True
    with self.assertRaisesRegex(
        errors.RecipeArgsValidationFailure,
        'Not a GRR host identifier'):
      self.validator.Validate(','.join(fqdns), self.recipe_argument)


if __name__ == '__main__':
  unittest.main()
