"""Tests args_validator classes."""

import unittest
import mock

from dftimewolf.lib import args_validator
from dftimewolf.lib import resources
from dftimewolf.lib import errors


class DefaultValidatorTest(unittest.TestCase):
  """Tests the Default Validator."""

  def setUp(self):
    """Setup."""
    self.validator = args_validator.DefaultValidator()
    self.recipe_argument = resources.RecipeArgument()
    self.recipe_argument.switch = 'default'

  def testInit(self):
    """Tests initialisation."""
    self.assertEqual(self.validator.NAME, 'default')

  def testValidateSuccess(self):
    """Test for Default Validator."""
    val = self.validator.Validate('test', self.recipe_argument)
    self.assertEqual(val, 'test')


# pylint: disable=abstract-class-instantiated
# pytype: disable=not-instantiable
class CommaSeparatedValidatorTest(unittest.TestCase):
  """Tests CommaSeparatedValidator."""

  def testInit(self):
    """Tests initialization.

    Really, CommaSeparatedValidator is an abstract class so should never be
    instantiated, but we're doing this for unit tests, so we can test the
    non-abstract method."""
    args_validator.CommaSeparatedValidator.__abstractmethods__=set()

    # pylint: disable=unused-variable
    with mock.patch.object(args_validator.CommaSeparatedValidator,
                           '__init__',
                           return_value=None) as mock_init:
      validator = args_validator.CommaSeparatedValidator()
      mock_init.assert_called_once()
    # pylint: enable=unused-variable

  def testValidate(self):
    """Tests validation."""
    args_validator.CommaSeparatedValidator.__abstractmethods__=set()

    recipe_argument = resources.RecipeArgument()
    recipe_argument.switch = 'testcommaseparated'

    with mock.patch.object(args_validator.CommaSeparatedValidator,
                           'ValidateSingle',
                           side_effect=lambda x, y: x) as mock_validatesingle:
      validator = args_validator.CommaSeparatedValidator()
      recipe_argument.validation_params = {'comma_separated': True}
      val = validator.Validate('one,two,three', recipe_argument)
      self.assertEqual(mock_validatesingle.call_count, 3)
      self.assertEqual(val,'one,two,three')

    with mock.patch.object(args_validator.CommaSeparatedValidator,
                           'ValidateSingle',
                           side_effect=lambda x, y: x) as mock_validatesingle:
      validator = args_validator.CommaSeparatedValidator()
      recipe_argument.validation_params = {'comma_separated': False}
      val = validator.Validate('one,two,three', recipe_argument)
      self.assertEqual(mock_validatesingle.call_count, 1)
      self.assertEqual(val,'one,two,three')

    with mock.patch.object(args_validator.CommaSeparatedValidator,
                           'ValidateSingle',
                           side_effect=lambda x, y: x):
      validator = args_validator.CommaSeparatedValidator()
      recipe_argument.validation_params = {}
      val = validator.Validate('one,two,three', recipe_argument)
      self.assertEqual(mock_validatesingle.call_count, 1)
      self.assertEqual(val, 'one,two,three')

  def testValidateFailure(self):
    """Tests validation failure."""
    def FailingValidateSingle(argument_value, _):
      if argument_value == 'three':
        raise errors.RecipeArgsValidationFailure(
            'failingvalidatesingle',
            'three',
            'CommaSeperatedValidator',
            'TestDescription')
      return argument_value

    with (mock.patch.object(args_validator.CommaSeparatedValidator,
                           'ValidateSingle',
                           side_effect=FailingValidateSingle)):
      validator = args_validator.CommaSeparatedValidator()
      argument_definition = resources.RecipeArgument()
      argument_definition.validation_params = {'comma_separated': True}
      with self.assertRaises(errors.RecipeArgsValidationFailure):
        _ = validator.Validate('one,two,three', argument_definition)

# pylint: enable=abstract-class-instantiated
# pytype: enable=not-instantiable


class AWSRegionValidatorTest(unittest.TestCase):
  """Tests AWSRegionValidator."""

  def setUp(self):
    """Setup."""
    self.validator = args_validator.AWSRegionValidator()
    self.recipe_argument = resources.RecipeArgument()
    self.recipe_argument.switch = 'testawsregion'

  def testInit(self):
    """Tests initialisation."""
    self.assertEqual(self.validator.NAME, 'aws_region')

  def testValidateSuccess(self):
    """Test that correct values do not throw an exception."""
    regions = ['ap-southeast-2', 'us-east-1', 'me-central-1']

    for region in regions:
      val = self.validator.Validate(region, self.recipe_argument)
      self.assertEqual(val, region)

  def testValidateFailure(self):
    """Tests invalid values correctly throw an exception."""
    regions = ['invalid', '123456']

    for r in regions:
      with self.assertRaisesRegex(
          errors.RecipeArgsValidationFailure,
          'Invalid AWS Region name'):
        _ = self.validator.Validate(r, self.recipe_argument)


class AzureRegionValidatorTest(unittest.TestCase):
  """Tests AzureRegionValidator."""

  def setUp(self):
    """Setup."""
    self.validator = args_validator.AzureRegionValidator()
    self.recipe_argument = resources.RecipeArgument()
    self.recipe_argument.switch = 'testazureregion'

  def testInit(self):
    """Tests initialisation."""
    self.assertEqual(self.validator.NAME, 'azure_region')

  def testValidateSuccess(self):
    """Test that correct values do not throw an exception."""
    regions = ['eastasia', 'norwaywest', 'westindia']

    for region in regions:
      val  = self.validator.Validate(region, self.recipe_argument)
      self.assertEqual(val, region)

  def testValidateFailure(self):
    """Tests invalid values correctly throw an exception."""
    regions = ['invalid', '123456']

    for region in regions:
      with self.assertRaisesRegex(
          errors.RecipeArgsValidationFailure,
          'Invalid Azure Region name'):
        _ = self.validator.Validate(region, self.recipe_argument)


class GCPZoneValidatorTest(unittest.TestCase):
  """Tests GCPZoneValidator."""

  def setUp(self):
    """Setup."""
    self.validator = args_validator.GCPZoneValidator()
    self.recipe_argument = resources.RecipeArgument()
    self.recipe_argument.switch = 'testgcpzone'

  def testInit(self):
    """Tests initialisation."""
    self.assertEqual(self.validator.NAME, 'gcp_zone')

  def testValidateSuccess(self):
    """Test that correct values do not throw an exception."""
    zones = ['asia-east1-a', 'europe-west2-a', 'us-central1-f']

    for zone in zones:
      val = self.validator.Validate(zone, self.recipe_argument)
      self.assertEqual(val, zone)

  def testValidateFailure(self):
    """Tests invalid values correctly throw an exception."""
    zones = ['nope', '123456']

    for zone in zones:
      with self.assertRaisesRegex(
          errors.RecipeArgsValidationFailure, 'Invalid GCP Zone name'):
        _ = self.validator.Validate(zone, self.recipe_argument)


class RegexValidatorTest(unittest.TestCase):
  """Tests RegexValidator."""

  def setUp(self):
    """Setup."""
    self.validator = args_validator.RegexValidator()
    self.recipe_argument = resources.RecipeArgument()
    self.recipe_argument.switch = 'testregex'
    self.recipe_argument.validation_params = {'comma_separated': True}

  def testInit(self):
    """Tests initialisation."""
    self.assertEqual(self.validator.NAME, 'regex')

  def testValidateSuccess(self):
    """Test that correct values do not throw an exception."""
    values = ['abcdef', 'bcdefg', 'abcdef,bcdefg']
    self.recipe_argument.validation_params['regex'] = '.?bcdef.?'
    for value in values:
      valid_value = self.validator.Validate(value, self.recipe_argument)
      self.assertEqual(valid_value, value)

  def testValidateFailure(self):
    """Test Regex test failure."""
    self.recipe_argument.validation_params['regex'] = '.?bcdef.?'

    with self.assertRaisesRegex(
        errors.RecipeArgsValidationFailure,
        "does not match regex /.\?bcdef.\?"): # pylint: disable=anomalous-backslash-in-string
      _ = self.validator.Validate('tuvwxy', self.recipe_argument)

  def testRequiredParam(self):
    """Tests an error is thrown is the regex param is missing."""
    self.recipe_argument.validation_params['regex'] = None
    with self.assertRaisesRegex(
        errors.RecipeArgsValidatorError,
        'Missing validator parameter: regex'):
      self.validator.Validate('tuvwxy', self.recipe_argument)


class SubnetValidatorTest(unittest.TestCase):
  """Tests SubnetValidator."""

  def setUp(self):
    """Setup."""
    self.validator = args_validator.SubnetValidator()
    self.recipe_argument = resources.RecipeArgument()
    self.recipe_argument.switch = 'testsubnet'
    self.recipe_argument.validation_params = {'comma_separated': True}


  def testInit(self):
    """Tests initialisation."""
    self.assertEqual(self.validator.NAME, 'subnet')

  def testValidateSuccess(self):
    """Test that correct values do not throw an exception."""
    values = ['1.2.3.4/32','192.168.0.0/24','1.2.3.4/32,192.168.0.0/24']
    for value in values:
      valid_value = self.validator.Validate(value, self.recipe_argument)
      self.assertEqual(valid_value, value)

  def testValidateFailure(self):
    """Test Subnet test failure."""
    values = ['1.2.3.4/33', '267.0.0.1/32', 'text']

    for value in values:
      with self.assertRaisesRegex(
          errors.RecipeArgsValidationFailure,
          'Not a valid subnet'):
        _ = self.validator.Validate(value, self.recipe_argument)


class DatetimeValidatorTest(unittest.TestCase):
  """Tests the DatetimeValidator class."""

  FORMAT_STRING = '%Y-%m-%d %H:%M:%S'

  def setUp(self):
    """Setup."""
    self.validator = args_validator.DatetimeValidator()
    self.recipe_argument = resources.RecipeArgument()
    self.recipe_argument.switch = 'testdatetime'

  def testInit(self):
    """Tests initialisation."""
    self.assertEqual(self.validator.NAME, 'datetime')

  def testRequiredParam(self):
    """Tests an error is thrown if format_string is missing."""
    with self.assertRaisesRegex(
        errors.RecipeArgsValidatorError,
        'Missing validator parameter: format_string'):
      self.validator.Validate('value', self.recipe_argument)

  def testValidateSuccess(self):
    """Tests a successful validation."""
    self.recipe_argument.validation_params['format_string'] = self.FORMAT_STRING
    date = '2023-12-31 23:29:59'
    val = self.validator.Validate(date, self.recipe_argument)
    self.assertEqual(val, date)

  def testValidateSuccessWithOrder(self):
    """Tests validation success with order parameters."""
    first = '2023-01-01 00:00:00'
    second = '2023-01-02 00:00:00'
    third = '2023-01-03 00:00:00'
    fourth = '2023-01-04 00:00:00'
    fifth = '2023-01-05 00:00:00'

    self.recipe_argument.validation_params['format_string'] = self.FORMAT_STRING
    self.recipe_argument.validation_params['before'] = fourth
    self.recipe_argument.validation_params['after'] = second

    val = self.validator.Validate(third, self.recipe_argument)
    self.assertEqual(val, third)

    with self.assertRaisesRegex(
        errors.RecipeArgsValidationFailure,
        f'{first} is before {second} but it should be the other way around'):
      _ = self.validator.Validate(first, self.recipe_argument)

    with self.assertRaisesRegex(
        errors.RecipeArgsValidationFailure,
        f'{fourth} is before {fifth} but it should be the other way around'):
      _ = self.validator.Validate(fifth, self.recipe_argument)

  def testValidateFailureInvalidFormat(self):
    """Tests invalid date formats correctly fail."""
    values = ['value', '2023-12-31', '2023-31-12 23:29:59']
    self.recipe_argument.validation_params['format_string'] = self.FORMAT_STRING
    for value in values:
      with self.assertRaisesRegex(
          errors.RecipeArgsValidationFailure,
          f'does not match format {self.FORMAT_STRING}'):
        _ = self.validator.Validate(value, self.recipe_argument)

  # pylint: disable=protected-access
  def testValidateOrder(self):
    """Tests the _ValidateOrder method."""
    first = '2023-01-01 00:00:00'
    second = '2023-01-02 00:00:00'

    # Correct order passes
    val = self.validator._ValidateOrder(first, second, self.FORMAT_STRING)
    self.assertTrue(val)

    # Reverse order fails
    val = self.validator._ValidateOrder(second, first, self.FORMAT_STRING)
    self.assertFalse(val)


class HostnameValidatorTest(unittest.TestCase):
  """Tests the HostnameValidator class."""

  def setUp(self):
    """Setup."""
    self.validator = args_validator.HostnameValidator()
    self.recipe_argument = resources.RecipeArgument()
    self.recipe_argument.switch = 'testhostname'

  def testInit(self):
    """Tests initialization."""
    self.assertEqual(self.validator.NAME, 'hostname')

  def testValidateSuccess(self):
    """Test successful validation."""
    fqdns = [
      'github.com',
      'grr-client-ubuntu.c.ramoj-playground.internal',
      'www.google.com.au',
      'www.google.co.uk',
      'localhost',
      'grr-server'
    ]
    for fqdn in fqdns:
      val = self.validator.Validate(fqdn, self.recipe_argument)
      self.assertTrue(val)

    self.recipe_argument.validation_params['comma_separated'] = True
    val = self.validator.Validate(','.join(fqdns), self.recipe_argument)
    self.assertTrue(val)

  def testValidationFailure(self):
    """Tests validation failures."""
    fqdns = ['a-.com', '-a.com']
    for fqdn in fqdns:
      with self.assertRaisesRegex(errors.RecipeArgsValidationFailure,
                                  'Not a valid hostname'):
        _ = self.validator.Validate(fqdn, self.recipe_argument)

    self.recipe_argument.validation_params['comma_separated'] = True
    with self.assertRaisesRegex(
        errors.RecipeArgsValidationFailure,
        'Not a valid hostname'):
      _ = self.validator.Validate(','.join(fqdns), self.recipe_argument)


  def testValidationFailureWithFQDNOnly(self):
    """tests validation fails for flat names when FQDN_ONLY is set."""
    fqdns = ['localhost', 'grr-server']
    self.recipe_argument.validation_params['comma_separated'] = False
    self.recipe_argument.validation_params['fqdn_only'] = True
    for fqdn in fqdns:
      with self.assertRaisesRegex(
          errors.RecipeArgsValidationFailure,
          'Not a valid hostname'):
        _ = self.validator.Validate(fqdn, self.recipe_argument)

    self.recipe_argument.validation_params['comma_separated'] = True
    with self.assertRaisesRegex(
        errors.RecipeArgsValidationFailure,
        'Not a valid hostname'):
      _ = self.validator.Validate(','.join(fqdns), self.recipe_argument)


class GRRHostValidatorTest(unittest.TestCase):
  """Tests the GRRHostValidator class."""

  def setUp(self):
    """Setup."""
    self.validator = args_validator.GRRHostValidator()
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
        _ = self.validator.Validate(fqdn, self.recipe_argument)

    self.recipe_argument.validation_params['comma_separated'] = True
    with self.assertRaisesRegex(
        errors.RecipeArgsValidationFailure,
        'Not a GRR host identifier'):
      _ = self.validator.Validate(','.join(fqdns), self.recipe_argument)


class URLValidatorTest(unittest.TestCase):
  """Tests the URLValidator class."""

  def setUp(self):
    """Setup."""
    self.validator = args_validator.URLValidator()
    self.recipe_argument = resources.RecipeArgument()
    self.recipe_argument.switch = 'testurl'

  def testInit(self):
    """Tests initialization."""
    self.assertEqual(self.validator.NAME, 'url')

  def testValidateSuccess(self):
    """Test successful validation."""
    fqdns = [
        'http://10.100.0.100:8080',
        'http://10.100.0.100',
        'https://10.100.0.100',
        'http://localhost:8080',
        'http://grr-server:8080',
        'http://grr.ramoj-playground.internal:8080',
        'http://grr.ramoj-playground.internal',
        'https://grr.ramoj-playground.internal',
    ]
    for fqdn in fqdns:
      val = self.validator.Validate(fqdn, self.recipe_argument)
      self.assertTrue(val, f'{fqdn} failed validation')

    self.recipe_argument.validation_params['comma_separated'] = True
    val = self.validator.Validate(','.join(fqdns), self.recipe_argument)
    self.assertTrue(val)

  def testValidationFailure(self):
    """Tests validation failures."""
    fqdns = [
        'value',
        '10.100.0.100',  # Needs scheme
    ]
    for fqdn in fqdns:
      with self.assertRaisesRegex(
          errors.RecipeArgsValidationFailure,
          "Not a valid URL"):
        _ = self.validator.Validate(fqdn, self.recipe_argument)

    self.recipe_argument.validation_params['comma_separated'] = True
    with self.assertRaisesRegex(
        errors.RecipeArgsValidationFailure, "Error: Not a valid URL"):
      _ = self.validator.Validate(','.join(fqdns), self.recipe_argument)


class _TestValidator(args_validator.AbstractValidator):
  """Validator class for unit tests."""
  NAME = 'test'

  def Validate(self, argument_value, recipe_argument):
    return argument_value

class _TestValidator2(args_validator.AbstractValidator):
  """Validator class for unit tests."""
  NAME = 'test2'

  def Validate(self, argument_value, recipe_argument):
    return argument_value


# Tests for the ValidatorsManager class.
# pylint: disable=protected-access
class ValidatorsManagerTest(unittest.TestCase):
  """Tests for the modules manager."""

  # pylint: disable=protected-access
  def testModuleRegistration(self):
    """Tests the RegisterModule and DeregisterModule functions."""
    number_of_module_classes = len(
        args_validator.ValidatorsManager._validator_classes)

    args_validator.ValidatorsManager.RegisterValidator(_TestValidator)
    self.assertEqual(
        len(args_validator.ValidatorsManager._validator_classes),
        number_of_module_classes + 1)

    args_validator.ValidatorsManager.DeregisterValidator(_TestValidator)
    self.assertEqual(
        len(args_validator.ValidatorsManager._validator_classes),
        number_of_module_classes)


  def testRegisterModules(self):
    """Tests the RegisterModules function."""
    number_of_module_classes = len(
        args_validator.ValidatorsManager._validator_classes)

    args_validator.ValidatorsManager.RegisterValidators(
        [_TestValidator, _TestValidator2])
    self.assertEqual(
        len(args_validator.ValidatorsManager._validator_classes),
        number_of_module_classes + 2)

    args_validator.ValidatorsManager.DeregisterValidator(_TestValidator)
    args_validator.ValidatorsManager.DeregisterValidator(_TestValidator2)

    self.assertEqual(
        number_of_module_classes,
        len(args_validator.ValidatorsManager._validator_classes))


  def testValidate(self):
    """Tests the Validate function."""
    recipe_argument = resources.RecipeArgument()
    recipe_argument.validation_params = {'format': 'test'}

    args_validator.ValidatorsManager.RegisterValidator(_TestValidator)

    validation_result = args_validator.ValidatorsManager.Validate(
        'test', recipe_argument)
    self.assertEqual(validation_result, 'test')

    recipe_argument.validation_params['format'] = 'does_not_exist'
    with self.assertRaisesRegex(
        errors.RecipeArgsValidatorError, 'not a registered validator'):
      args_validator.ValidatorsManager.Validate('test', recipe_argument)


if __name__ == '__main__':
  unittest.main()
