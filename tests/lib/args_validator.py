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
    """Test for Default Validator."""
    val, _ = self.validator.Validate('operand', {})
    self.assertTrue(val)


# pylint: disable=abstract-class-instantiated
# pytype: disable=not-instantiable
class CommaSeparatedValidatorTest(unittest.TestCase):
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
                           return_value=(True, '')) as mock_validatesingle:
      validator = args_validator.CommaSeparatedValidator()
      val, _ = validator.Validate('one,two,three', {'comma_separated': True})
      self.assertEqual(mock_validatesingle.call_count, 3)
      self.assertTrue(val)

    with mock.patch.object(args_validator.CommaSeparatedValidator,
                           'ValidateSingle',
                           return_value=(True, '')) as mock_validatesingle:
      validator = args_validator.CommaSeparatedValidator()
      val, _ = validator.Validate('one,two,three', {'comma_separated': False})
      self.assertEqual(mock_validatesingle.call_count, 1)
      self.assertTrue(val)

    with mock.patch.object(args_validator.CommaSeparatedValidator,
                           'ValidateSingle',
                           return_value=(True, '')):
      validator = args_validator.CommaSeparatedValidator()
      val, _ = validator.Validate('one,two,three', {})
      self.assertEqual(mock_validatesingle.call_count, 1)
      self.assertTrue(val)

  def test_ValidateFailure(self):
    """Tests validation failure."""
    with mock.patch.object(args_validator.CommaSeparatedValidator,
                           'ValidateSingle',
                           side_effect=[(True, ''),
                                        (False, 'Failure1'),
                                        (False, 'Failure2')]):
      validator = args_validator.CommaSeparatedValidator()
      val, msg = validator.Validate('one,two,three', {'comma_separated': True})
      self.assertFalse(val)
      self.assertEqual(msg, 'Failure1\nFailure2')
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
      val, _ = self.validator.Validate(r, {})
      self.assertTrue(val)

  def test_ValidateFailure(self):
    """Tests invalid values correctly throw an exception."""
    regions = ['invalid', '123456']

    for r in regions:
      val, msg = self.validator.Validate(r, {})
      self.assertFalse(val)
      self.assertEqual(msg, 'Invalid AWS Region name')


class AzureRegionValidatorTest(unittest.TestCase):
  """Tests AzureRegionValidator."""

  def setUp(self):
    """Setup."""
    self.validator = args_validator.AzureRegionValidator()

  def test_Init(self):
    """Tests initialisation."""
    self.assertEqual(self.validator.NAME, 'azure_region')

  def test_ValidateSuccess(self):
    """Test that correct values do not throw an exception."""
    regions = ['eastasia', 'norwaywest', 'westindia']

    for r in regions:
      val, _ = self.validator.Validate(r, {})
      self.assertTrue(val)

  def test_ValidateFailure(self):
    """Tests invalid values correctly throw an exception."""
    regions = ['invalid', '123456']

    for r in regions:
      val, msg = self.validator.Validate(r, {})
      self.assertFalse(val)
      self.assertEqual(msg, 'Invalid Azure Region name')


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
    zones = ['asia-east1-a', 'europe-west2-a', 'us-central1-f']

    for z in zones:
      val, _ = self.validator.Validate(z, {})
      self.assertTrue(val)

  def test_ValidateFailure(self):
    """Tests invalid values correctly throw an exception."""
    zones = ['nope', '123456']

    for z in zones:
      val, msg = self.validator.Validate(z, {})
      self.assertFalse(val)
      self.assertEqual(msg, 'Invalid GCP Zone name')


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
    values = ['abcdef', 'bcdefg', 'abcdef,bcdefg']
    params = {'comma_separated': True, 'regex': '.?bcdef.?'}
    for v in values:
      val, _ = self.validator.Validate(v, params)
      self.assertTrue(val)

  def test_ValidateFailure(self):
    """Test Regex test failure."""
    params = {'comma_separated': True, 'regex': '.?bcdef.?'}

    val, msg = self.validator.Validate('tuvwxy', params)
    self.assertFalse(val)
    self.assertEqual(msg, '"tuvwxy" does not match regex /.?bcdef.?/')

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
      val, _ = self.validator.Validate(v, params)
      self.assertTrue(val)

  def test_ValidateFailure(self):
    """Test Subnet test failure."""
    values = ['1.2.3.4/33', '267.0.0.1/32', 'text']
    params = {'comma_separated': True}

    for value in values:
      val, msg = self.validator.Validate(value, params)
      self.assertFalse(val)
      self.assertEqual(msg, f'{value} is not a valid subnet.')


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
    val, _ = self.validator.Validate(
        '2023-12-31 23:29:59', {'format_string': self.FORMAT_STRING})
    self.assertTrue(val)

  def test_ValidateSuccessWithOrder(self):
    """Tests validation success with order parameters."""
    first = '2023-01-01 00:00:00'
    second = '2023-01-02 00:00:00'
    third = '2023-01-03 00:00:00'
    fourth = '2023-01-04 00:00:00'
    fifth = '2023-01-05 00:00:00'

    params = {
      'format_string': self.FORMAT_STRING,
      'before': fourth,
      'after': second
    }

    val, _ = self.validator.Validate(third, params)
    self.assertTrue(val)

    val, msg = self.validator.Validate(first, params)
    self.assertFalse(val)
    self.assertEqual(
        msg,
        f'{first} is before {second} but it should be the other way around')

    val, msg = self.validator.Validate(fifth, params)
    self.assertFalse(val)
    self.assertEqual(
        msg,
        f'{fourth} is before {fifth} but it should be the other way around')

  def test_ValidateFailureInvalidFormat(self):
    """Tests invalid date formats correctly fail."""
    values = ['value', '2023-12-31', '2023-31-12 23:29:59']
    for v in values:
      val, msg = self.validator.Validate(
          v, {'format_string': self.FORMAT_STRING})
      self.assertFalse(val)
      self.assertEqual(
          msg,
          f"time data '{v}' does not match format '{self.FORMAT_STRING}'")

  # pylint: disable=protected-access
  def test_ValidateOrder(self):
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

  def test_Init(self):
    """Tests initialization."""
    self.assertEqual(self.validator.NAME, 'hostname')

  def test_ValidateSuccess(self):
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
      val, _ = self.validator.Validate(fqdn, {})
      self.assertTrue(val)

    val, _ = self.validator.Validate(','.join(fqdns), {'comma_separated': True})
    self.assertTrue(val)

  def test_ValidationFailure(self):
    """Tests validation failures."""
    fqdns = ['a-.com', '-a.com']
    for fqdn in fqdns:
      val, msg = self.validator.Validate(fqdn, {})
      self.assertFalse(val)
      self.assertEqual(msg, f"'{fqdn}' is an invalid hostname.")

    val, msg =self.validator.Validate(
        ','.join(fqdns), {'comma_separated': True})
    self.assertFalse(val)
    self.assertEqual(msg, ("'a-.com' is an invalid hostname.\n"
                           "'-a.com' is an invalid hostname."))

  def test_ValidationFailureWithFQDNOnly(self):
    """tests validation fails for flat names when FQDN_ONLY is set."""
    fqdns = ['localhost', 'grr-server']
    for fqdn in fqdns:
      val, msg = self.validator.Validate(fqdn, {'fqdn_only': True})
      self.assertFalse(val)
      self.assertEqual(msg, f"'{fqdn}' is an invalid hostname.")

    val, msg =self.validator.Validate(
        ','.join(fqdns), {'comma_separated': True, 'fqdn_only': True})
    self.assertFalse(val)
    self.assertEqual(msg, ("'localhost' is an invalid hostname.\n"
                           "'grr-server' is an invalid hostname."))


class GRRHostValidatorTest(unittest.TestCase):
  """Tests the GRRHostValidator class."""

  def setUp(self):
    """Setup."""
    self.validator = args_validator.GRRHostValidator()

  def test_Init(self):
    """Tests initialization."""
    self.assertEqual(self.validator.NAME, 'grr_host')

  def test_ValidateSuccess(self):
    """Test successful validation."""
    fqdns = ['C.1facf5562db006ad',
             'grr-client-ubuntu.c.ramoj-playground.internal',
             'grr-client']
    for fqdn in fqdns:
      val, _ = self.validator.Validate(fqdn, {})
      self.assertTrue(val)

    val, _ = self.validator.Validate(','.join(fqdns), {'comma_separated': True})
    self.assertTrue(val)

  def test_ValidationFailure(self):
    """Tests validation failures."""
    fqdns = ['a-.com', 'C.a', 'C.01234567890123456789']
    for fqdn in fqdns:
      val, msg = self.validator.Validate(fqdn, {})
      self.assertFalse(val)
      self.assertEqual(msg, f"'{fqdn}' is an invalid Grr host ID.")

    val, msg = self.validator.Validate(','.join(fqdns),
                                       {'comma_separated': True})
    self.assertFalse(val)
    self.assertEqual(msg,
                     ("'a-.com' is an invalid Grr host ID.\n"
                      "'C.a' is an invalid Grr host ID.\n"
                      "'C.01234567890123456789' is an invalid Grr host ID."))


class URLValidatorTest(unittest.TestCase):
  """Tests the URLValidator class."""

  def setUp(self):
    """Setup."""
    self.validator = args_validator.URLValidator()

  def test_Init(self):
    """Tests initialization."""
    self.assertEqual(self.validator.NAME, 'url')

  def test_ValidateSuccess(self):
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
      val, _ = self.validator.Validate(fqdn, {})
      self.assertTrue(val, f'{fqdn} failed validation')

    val, _ = self.validator.Validate(','.join(fqdns), {'comma_separated': True})
    self.assertTrue(val)

  def test_ValidationFailure(self):
    """Tests validation failures."""
    fqdns = [
        'value',
        '10.100.0.100',  # Needs scheme
        'http://one.*.com'
    ]
    for fqdn in fqdns:
      val, msg = self.validator.Validate(fqdn, {})
    self.assertFalse(val)
    self.assertEqual(msg, f"'{fqdn}' is an invalid URL.")

    val, msg = self.validator.Validate(','.join(fqdns),
                                       {'comma_separated': True})
    self.assertFalse(val)
    self.assertEqual(msg, ("'value' is an invalid URL.\n"
                           "'10.100.0.100' is an invalid URL.\n"
                           "'http://one.*.com' is an invalid URL."))


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

    self.assertEqual(len(self.vm._validators), 9)

    self.assertIn('aws_region', self.vm._validators)
    self.assertIn('azure_region', self.vm._validators)
    self.assertIn('datetime', self.vm._validators)
    self.assertIn('gcp_zone', self.vm._validators)
    self.assertIn('grr_host', self.vm._validators)
    self.assertIn('hostname', self.vm._validators)
    self.assertIn('regex', self.vm._validators)
    self.assertIn('subnet', self.vm._validators)
    self.assertIn('url', self.vm._validators)

    self.assertIsInstance(self.vm._validators['aws_region'],
                          args_validator.AWSRegionValidator)
    self.assertIsInstance(self.vm._validators['azure_region'],
                          args_validator.AzureRegionValidator)
    self.assertIsInstance(self.vm._validators['datetime'],
                          args_validator.DatetimeValidator)
    self.assertIsInstance(self.vm._validators['gcp_zone'],
                          args_validator.GCPZoneValidator)
    self.assertIsInstance(self.vm._validators['grr_host'],
                          args_validator.GRRHostValidator)
    self.assertIsInstance(self.vm._validators['hostname'],
                          args_validator.HostnameValidator)
    self.assertIsInstance(self.vm._validators['regex'],
                          args_validator.RegexValidator)
    self.assertIsInstance(self.vm._validators['subnet'],
                          args_validator.SubnetValidator)
    self.assertIsInstance(self.vm._validators['url'],
                          args_validator.URLValidator)

  def test_Validation(self):
    """Tests validation."""
    val, _ = self.vm.Validate(
        '192.168.0.0/24', {'format': 'subnet', 'comma_separated': False})
    self.assertTrue(val)

  def test_DefaultValidation(self):
    """Tests param validation with DefaultValidator."""
    val, _ = self.vm.Validate('operand', {})
    self.assertTrue(val)

  def test_ValidationFailure(self):
    """Tests validation failure."""
    val, msg = self.vm.Validate('invalid',
                                {'format': 'subnet', 'comma_separated': False})
    self.assertFalse(val)
    self.assertEqual(msg, 'invalid is not a valid subnet.')

  def test_InvalidValidator(self):
    """Tests an exception is thrown if an invalid validator is specified."""
    with self.assertRaisesRegex(
        errors.RecipeArgsValidatorError,
        'invalid is not a valid validator name'):
      self.vm.Validate('operand', {'format': 'invalid'})


if __name__ == '__main__':
  unittest.main()
