#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script to run the tests."""

from __future__ import unicode_literals

import unittest
import sys


if __name__ == '__main__':
  test_suite = unittest.TestLoader().discover('tests', pattern='*.py')
  test_results = unittest.TextTestRunner(verbosity=2).run(test_suite)
  if not test_results.wasSuccessful():
    sys.exit(1)
