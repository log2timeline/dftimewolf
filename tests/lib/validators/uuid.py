"""Tests for the UUID validator."""

from absl.testing import absltest
from absl.testing import parameterized
from dftimewolf.lib import errors, resources
from dftimewolf.lib.validators import uuid


class UUIIDValidatorTest(parameterized.TestCase):
  """Tests for the UUID validator."""

  def setUp(self):
    """Set Up."""
    super().setUp()
    self._validator = uuid.UUIDValidator()
    self._recipe_argument = resources.RecipeArgument(
        switch='testuuid', validation_params={'comma_separated': False})

  @parameterized.named_parameters(
      ('v1', '054d1b3e-dc70-11f0-91fb-42010a980fcc'),
      ('v3', '1f708c85-f15f-39c6-96fa-37843ce413a4'),
      ('v4', 'e1ec5248-68c9-41da-ad3b-0fa1fb53af17'),
      ('v5', 'eb037852-665d-5167-9c41-e612983f236d'),
  )
  def test_ValidateSuccess(self, uuid_):
    """Tests validation succeeds on a valid UUID."""
    valid = self._validator.Validate(uuid_, self._recipe_argument)
    self.assertEqual(valid, uuid_)

  @parameterized.named_parameters(
      ('short', '054d1b3e-dc70-11f0-91fb-42010a980fc'),
      ('long', '054d1b3e-dc70-11f0-91fb-42010a980fcc0'),
      ('invalid_char', '054d1b3e-dc70-11f0-91fb-42010a980fcz'),
  )
  def test_ValidateFailure(self, uuid_):
    """Tests validation failures."""
    with self.assertRaisesRegex(errors.RecipeArgsValidationFailure,
                                'does not match regex'):
      self._validator.Validate(uuid_, self._recipe_argument)


if __name__ == '__main__':
  absltest.main()
