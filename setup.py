#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Installation and deployment script."""

from __future__ import print_function
import sys

try:
  from setuptools import find_packages, setup
except ImportError:
  from distutils.core import find_packages, setup

try:
  from distutils.command.bdist_rpm import bdist_rpm
except ImportError:
  bdist_rpm = None

if sys.version < '2.7':
  print('Unsupported Python version: {0:s}.'.format(sys.version))
  print('Supported Python versions are 2.7 or a later 2.x version.')
  sys.exit(1)

# Change PYTHONPATH to include dftimewolf so that we can get the version.
sys.path.insert(0, '.')

import dftimewolf  # pylint: disable=wrong-import-position


if not bdist_rpm:
  BdistRPMCommand = None
else:
  class BdistRPMCommand(bdist_rpm):
    """Custom handler for the bdist_rpm command."""

    def _make_spec_file(self):
      """Generates the text of an RPM spec file.

      Returns:
        list[str]: lines of the RPM spec file.
      """
      # Note that bdist_rpm can be an old style class.
      if issubclass(BdistRPMCommand, object):
        spec_file = super(BdistRPMCommand, self)._make_spec_file()
      else:
        spec_file = bdist_rpm._make_spec_file(self)

      if sys.version_info[0] < 3:
        python_package = 'python'
      else:
        python_package = 'python3'

      description = []
      summary = ''
      in_description = False

      python_spec_file = []
      for line in iter(spec_file):
        if line.startswith('Summary: '):
          summary = line

        elif line.startswith('BuildRequires: '):
          line = 'BuildRequires: {0:s}-setuptools'.format(python_package)

        elif line.startswith('Requires: '):
          if python_package == 'python3':
            line = line.replace('python', 'python3')

        elif line.startswith('%description'):
          in_description = True

        elif line.startswith('%files'):
          # Cannot use %{_libdir} here since it can expand to "lib64".
          lines = [
              '%files',
              '%defattr(644,root,root,755)',
              '%doc ACKNOWLEDGEMENTS AUTHORS LICENSE README',
              '%{_prefix}/lib/python*/site-packages/dftimewolf/*.py',
              '%{_prefix}/lib/python*/site-packages/dftimewolf*.egg-info/*',
              '%exclude %{_prefix}/lib/python*/site-packages/dftimewolf/*.pyc',
              '%exclude %{_prefix}/lib/python*/site-packages/dftimewolf/*.pyo',
              ('%exclude %{_prefix}/lib/python*/site-packages/dftimewolf/'
               '__pycache__/*')]

          python_spec_file.extend(lines)
          break

        elif line.startswith('%prep'):
          in_description = False

          python_spec_file.append(
              '%package -n {0:s}-%{{name}}'.format(python_package))
          python_spec_file.append('{0:s}'.format(summary))
          python_spec_file.append('')
          python_spec_file.append(
              '%description -n {0:s}-%{{name}}'.format(python_package))
          python_spec_file.extend(description)

        elif in_description:
          # Ignore leading white lines in the description.
          if not description and not line:
            continue

          description.append(line)

        python_spec_file.append(line)

      return python_spec_file


dftimewolf_description = (
    'Digital forensic orchestration.')

dftimewolf_long_description = (
    'dfTimeWolf, a framework for orchestrating forensic collection, processing '
    'and data export.')

setup(
    name='dftimewolf',
    version=dftimewolf.__version__,
    description=dftimewolf_description,
    long_description=dftimewolf_long_description,
    url='https://github.com/log2timeline/dftimewolf',
    author='DFTimewolf development team',
    license='Apache License, Version 2.0',
    packages=find_packages(),
    cmdclass={
        'bdist_rpm': BdistRPMCommand},
    classifiers=[
        'Development Status :: 4 - Beta',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    entry_points={
        'console_scripts': ['dftimewolf=dftimewolf.cli.dftimewolf_recipes:main']
    },
    data_files=[('dftimewolf', ['dftimewolf/config.json'])],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'pytz',
        'bs4',
        'requests',
    ],
    test_suite='nose.collector',
    test_require=[
        'bs4',
        'nose'
    ]
)
