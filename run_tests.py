#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script to run the tests."""

import sys
import unittest

# Change PYTHONPATH to include dependencies.
sys.path.insert(0, '.')

import utils.dependencies  # pylint: disable=wrong-import-position


if __name__ == '__main__':
  version_tuple = (sys.version_info[0], sys.version_info[1])

  if version_tuple[0] != 3 or version_tuple < (3, 6):
    print(('Unsupported Python version: {0:s}, version 3.6 or higher '
           'required.').format(sys.version))
    sys.exit(1)

  print('Using Python version {0!s}'.format(sys.version))

  dependency_helper = utils.dependencies.DependencyHelper()

  if not dependency_helper.CheckTestDependencies():
    sys.exit(1)

  test_suite = unittest.TestLoader().discover('tests', pattern='*.py')
  test_results = unittest.TextTestRunner(verbosity=2).run(test_suite)
  if not test_results.wasSuccessful():
    sys.exit(1)
