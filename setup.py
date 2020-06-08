#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Installation and deployment script."""

import glob
import os
import sys

def parse_requirements(filename):
  with open(filename) as requirements:
    # Skipping -i https://pypi.org/simple
    return requirements.readlines()[1:]

try:
  from setuptools import find_packages, setup
except ImportError:
  from distutils.core import find_packages, setup

try:
  from distutils.command.bdist_msi import bdist_msi
except ImportError:
  bdist_msi = None

try:
  from distutils.command.bdist_rpm import bdist_rpm
except ImportError:
  bdist_rpm = None

version_tuple = (sys.version_info[0], sys.version_info[1])
if version_tuple[0] != 3 or version_tuple < (3, 6):
  print(('Unsupported Python version: {0:s}, version 3.6 or higher '
         'required.').format(sys.version))
  sys.exit(1)

# Change PYTHONPATH to include dftimewolf so that we can get the version.
sys.path.insert(0, '.')

import dftimewolf  # pylint: disable=wrong-import-position

if not bdist_msi:
  BdistMSICommand = None
else:
  class BdistMSICommand(bdist_msi):
    """Custom handler for the bdist_msi command."""

    # pylint: disable=invalid-name
    def run(self):
      """Builds an MSI."""
      # Command bdist_msi does not support the library version, neither a date
      # as a version but if we suffix it with .1 everything is fine.
      self.distribution.metadata.version += '.1'

      bdist_msi.run(self)


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
              '%files -n {0:s}-%{{name}}'.format(python_package),
              '%defattr(644,root,root,755)',
              '%doc ACKNOWLEDGEMENTS AUTHORS LICENSE',
              '%{_prefix}/lib/python*/site-packages/**/*.py',
              '%{_prefix}/lib/python*/site-packages/dftimewolf*.egg-info/*',
              '',
              '%exclude %{_prefix}/share/doc/*',
              '%exclude %{_prefix}/lib/python*/site-packages/**/*.pyc',
              '%exclude %{_prefix}/lib/python*/site-packages/**/*.pyo',
              '%exclude %{_prefix}/lib/python*/site-packages/**/__pycache__/*']

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
    'dfTimeWolf, a framework for orchestrating forensic collection, processing'
    ' and data export.')

setup(
    name='dftimewolf',
    version=dftimewolf.__version__,
    description=dftimewolf_description,
    long_description=dftimewolf_long_description,
    license='Apache License, Version 2.0',
    url='https://github.com/log2timeline/dftimewolf',
    maintainer='Log2Timeline maintainers',
    maintainer_email='log2timeline-maintainers@googlegroups.com',
    packages=find_packages(),
    cmdclass={
        'bdist_msi': BdistMSICommand,
        'bdist_rpm': BdistRPMCommand},
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    entry_points={
        'console_scripts': ['dftimewolf=dftimewolf.cli.dftimewolf_recipes:Main']
    },
    data_files=[
        ('share/dftimewolf', glob.glob(
            os.path.join('data', '*.json'))),
        ('share/dftimewolf/recipes', glob.glob(
            os.path.join('data', 'recipes', '*.json'))),
        ('share/doc/dftimewolf', [
            'ACKNOWLEDGEMENTS', 'AUTHORS', 'LICENSE']),
    ],
    include_package_data=True,
    zip_safe=False,
    install_requires=parse_requirements('requirements.txt'),
    test_suite='nose.collector',
    test_require=parse_requirements('requirements-dev.txt')
)
