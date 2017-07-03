"""This is the setup file for the project. The standard setup rules apply:
   python setup.py build
   sudo python setup.py install
"""

from setuptools import find_packages
from setuptools import setup


def readme():
  """Reads README and returns its contents."""
  with open('README') as f:
    return f.read()

setup(
    name='dftimewolf',
    version='2017.06',
    description='Digital forensic orchestration',
    long_description=readme(),
    url='https://github.com/log2timeline/dftimewolf',
    author='DFTimewolf development team',
    license='Apache License, Version 2.0',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    entry_points={
        'console_scripts': ['dftimewolf=dftimewolf.cli.dftimewolf_recipes:main']
    },
    data_files=[('dftimewolf', ['dftimewolf/dftimewolf.json'])],
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
