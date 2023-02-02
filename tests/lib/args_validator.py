"""Tests args_validator classes."""

import unittest
import mock

from dftimewolf.lib import args_validator
from dftimewolf.lib import errors


class DefaultValidatorTest(unittest.TestCase):
  """Tests the Default Validator."""

  def setUp(self):
    """Setup."""
    self.validator = args_validator.DefaultValidator()

  def test_Init(self):
    """Tests initialisation."""
    self.assertEqual(self.validator.NAME, 'default')

  def test_ValidateSuccess(self):
    """Test that correct values do not throw an exception."""
    self.validator.Validate('operand', {})


# pylint: disable=abstract-class-instantiated
# pytype: disable=not-instantiable
class CommaSeparatedValidatorTester(unittest.TestCase):
  """Tests CommaSeparatedValidator."""

  def test_Init(self):
    """Tests initialisation.

    Really, CommaSeparatedValidator is an abstract class so should never be
    instantiated, but we're doing this for unit tests so we can test the
    non-abstract method."""
    args_validator.CommaSeparatedValidator.__abstractmethods__=set()

    # pylint: disable=unused-variable
    with mock.patch.object(args_validator.CommaSeparatedValidator,
                           '__init__',
                           return_value=None) as mock_init:
      validator = args_validator.CommaSeparatedValidator()
      mock_init.assert_called_once()
    # pylint: enable=unused-variable

  def test_Validate(self):
    """Tests validation."""
    args_validator.CommaSeparatedValidator.__abstractmethods__=set()

    with mock.patch.object(args_validator.CommaSeparatedValidator,
                           'ValidateSingle',
                           return_value=None) as mock_validatesingle:
      validator = args_validator.CommaSeparatedValidator()
      validator.Validate('one,two,three', {'comma_separated': True})
      self.assertEqual(mock_validatesingle.call_count, 3)

    with mock.patch.object(args_validator.CommaSeparatedValidator,
                           'ValidateSingle',
                           return_value=None) as mock_validatesingle:
      validator = args_validator.CommaSeparatedValidator()
      validator.Validate('one,two,three', {'comma_separated': False})
      self.assertEqual(mock_validatesingle.call_count, 1)

    with mock.patch.object(args_validator.CommaSeparatedValidator,
                           'ValidateSingle',
                           return_value=None):
      validator = args_validator.CommaSeparatedValidator()
      validator.Validate('one,two,three', {})
      self.assertEqual(mock_validatesingle.call_count, 1)
# pylint: enable=abstract-class-instantiated
# pytype: enable=not-instantiable


class AWSRegionValidatorTest(unittest.TestCase):
  """Tests AWSRegionValidator."""

  def setUp(self):
    """Setup."""
    self.validator = args_validator.AWSRegionValidator()

  def test_Init(self):
    """Tests initialisation."""
    self.assertEqual(self.validator.NAME, 'aws_region')

  def test_ValidateSuccess(self):
    """Test that correct values do not throw an exception."""
    regions = ['ap-southeast-2', 'us-east-1', 'me-central-1']

    for r in regions:
      self.validator.Validate(r, {})

  def test_ValidateFailure(self):
    """Tests invalid values correctly throw an exeption."""
    regions = ['invalid', '123456']

    for r in regions:
      with self.assertRaisesRegex(
          errors.RecipeArgsValidatorError, 'Invalid AWS Region name'):
        self.validator.Validate(r, {})


class GCPZoneValidatorTest(unittest.TestCase):
  """Tests GCPZoneValidator."""

  def setUp(self):
    """Setup."""
    self.validator = args_validator.GCPZoneValidator()

  def test_Init(self):
    """Tests initialisation."""
    self.assertEqual(self.validator.NAME, 'gcp_zone')

  def test_ValidateSuccess(self):
    """Test that correct values do not throw an exception."""
    regions = ['asia-east1-a', 'europe-west2-a', 'us-central1-f']

    for r in regions:
      self.validator.Validate(r, None)

  def test_ValidateFailure(self):
    """Tests invalid values correctly throw an exeption."""
    regions = ['nope', '123456']

    for r in regions:
      with self.assertRaisesRegex(
          errors.RecipeArgsValidatorError, 'Invalid GCP zone name'):
        self.validator.Validate(r, None)


class RegexValidatorTest(unittest.TestCase):
  """Tests RegexValidator."""

  def setUp(self):
    """Setup."""
    self.validator = args_validator.RegexValidator()

  def test_Init(self):
    """Tests initialisation."""
    self.assertEqual(self.validator.NAME, 'regex')

  def test_ValidateSuccess(self):
    """Test that correct values do not throw an exception."""
    values = ['abcdef','bcdefg','abcdef,bcdefg']
    params = {'comma_separated': True, 'regex': '.?bcdef.?'}
    for v in values:
      self.validator.Validate(v, params)

  def test_ValidateFailure(self):
    """Test Regex test failure."""
    params = {'comma_separated': True, 'regex': '.?bcdef.?'}
    with self.assertRaisesRegex(
        errors.RecipeArgsValidatorError,
        r'"tuvwxy" does not match regex \/\.\?bcdef\.\?\/'):
      self.validator.Validate('tuvwxy', params)

  def test_RequiredParam(self):
    """Tests an error is thrown is the regex param is missing."""
    params = {'comma_separated': True}
    with self.assertRaisesRegex(
        errors.RecipeArgsValidatorError,
        'Missing validator parameter: regex'):
      self.validator.Validate('tuvwxy', params)


class SubnetValidatorTest(unittest.TestCase):
  """Tests SubnetValidator."""

  def setUp(self):
    """Setup."""
    self.validator = args_validator.SubnetValidator()

  def test_Init(self):
    """Tests initialisation."""
    self.assertEqual(self.validator.NAME, 'subnet')

  def test_ValidateSuccess(self):
    """Test that correct values do not throw an exception."""
    values = ['1.2.3.4/32','192.168.0.0/24','1.2.3.4/32,192.168.0.0/24']
    params = {'comma_separated': True}
    for v in values:
      self.validator.Validate(v, params)

  def test_ValidateFailure(self):
    """Test Subnet test failure."""
    values = ['1.2.3.4/33', '267.0.0.1/32', 'text']
    params = {'comma_separated': True}
    for value in values:
      with self.assertRaisesRegex(
          errors.RecipeArgsValidatorError,
          f'{value} is not a valid subnet.'):
        self.validator.Validate(value, params)


class DatetimeValidatorTest(unittest.TestCase):
  """Tests the DatetimeValidator class."""

  FORMAT_STRING = '%Y-%m-%d %H:%M:%S'

  def setUp(self):
    """Setup."""
    self.validator = args_validator.DatetimeValidator()

  def test_Init(self):
    """Tests initialisation."""
    self.assertEqual(self.validator.NAME, 'datetime')

  def test_RequiredParam(self):
    """Tests an error is thrown if format_string is missing."""
    with self.assertRaisesRegex(
        errors.RecipeArgsValidatorError,
        'Missing validator parameter: format_string'):
      self.validator.Validate('value', {})

  def test_ValidateSuccess(self):
    """Tests a successful validation."""
    self.validator.Validate(
        '2023-12-31 23:29:59', {'format_string': self.FORMAT_STRING})

  def test_ValidateSuccessWithOrder(self):
    """Tests validation success with order parameters."""
    first = '2023-01-01 00:00:00'
    second = '2023-01-02 00:00:00'
    third = '2023-01-03 00:00:00'

    params = {
      'format_string': self.FORMAT_STRING,
      'before': third,
      'after': first
    }

    self.validator.Validate(second, params)


  def test_ValidateFailureInvalidFormat(self):
    """Tests invalid date formats correctly fail."""
    values = ['value', '2023-12-31', '2023-31-12 23:29:59']
    for v in values:
      with self.assertRaisesRegex(
          errors.RecipeArgsValidatorError,
          f"time data '{v}' does not match format '{self.FORMAT_STRING}'"):
        self.validator.Validate(v, {'format_string': self.FORMAT_STRING})

  # pylint: disable=protected-access
  def test_ValidateOrder(self):
    """Tests the _ValidateOrder method."""
    first = '2023-01-01 00:00:00'
    second = '2023-01-02 00:00:00'

    # Correct order passes without exception
    self.validator._ValidateOrder(first, second, self.FORMAT_STRING)

    # Reverse order raises exeption
    with self.assertRaisesRegex(
        errors.RecipeArgsValidatorError,
        f"{second} is after {first} but it should be the other way around"):
      self.validator._ValidateOrder(second, first, self.FORMAT_STRING)


# pylint: disable=protected-access
class ValidatorManagerTest(unittest.TestCase):
  """Tests the validatorManager class."""

  def setUp(self):
    """SetUp."""
    self.vm = args_validator.ValidatorManager()

  def test_Init(self):
    """Tests initialisation."""
    self.assertIsInstance(self.vm._default_validator,
                          args_validator.DefaultValidator)

    self.assertEqual(len(self.vm._validators), 5)

    self.assertIn('aws_region', self.vm._validators)
    self.assertIn('datetime', self.vm._validators)
    self.assertIn('gcp_zone', self.vm._validators)
    self.assertIn('regex', self.vm._validators)
    self.assertIn('subnet', self.vm._validators)

    self.assertIsInstance(self.vm._validators['aws_region'],
                          args_validator.AWSRegionValidator)
    self.assertIsInstance(self.vm._validators['datetime'],
                          args_validator.DatetimeValidator)
    self.assertIsInstance(self.vm._validators['gcp_zone'],
                          args_validator.GCPZoneValidator)
    self.assertIsInstance(self.vm._validators['regex'],
                          args_validator.RegexValidator)
    self.assertIsInstance(self.vm._validators['subnet'],
                          args_validator.SubnetValidator)

  def test_Validation(self):
    """Tests validation."""
    self.vm.Validate('192.168.0.0/24',
                     {'format': 'subnet', 'comma_separated': False})

  def test_DefaultValidation(self):
    """Tests param validation with DefaultValidator."""
    self.vm.Validate('operand')

  def test_ValidationFailure(self):
    """Tests validation failure."""
    with self.assertRaisesRegex(
        errors.RecipeArgsValidatorError,
        'invalid is not a valid subnet.'):
      self.vm.Validate('invalid',
                       {'format': 'subnet', 'comma_separated': False})

  def test_InvalidValidator(self):
    """Tests an exception is thrown if an invalid validator is specified."""
    with self.assertRaisesRegex(
        errors.RecipeArgsValidatorError,
        'invalid is not a valid validator name'):
      self.vm.Validate('operand', {'format': 'invalid'})


if __name__ == '__main__':
  unittest.main()
