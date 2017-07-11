"""Small module to search for and load configuration files."""

import importlib
import json
import os
import pkgutil

LOCATIONS = [
    os.curdir,
    os.path.expanduser('~'),
    os.environ.get('DFTIMEWOLF_CONFIG'),
]

FILENAMES = [
    'dftimewolf.json',
    '.dftimewolfrc',
]

_CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))

DEFAULT_RECIPE_DIRECTORIES = [
    os.path.join(_CURRENT_DIR, 'cli', 'recipes')
]

DEFAULT_MODULE_DIRECTORIES = [
    os.path.join(_CURRENT_DIR, 'lib'),
]

DEFAULT_PACKAGE_NAME = 'dftimewolf'

_CONFIG = None


# TODO(tomchop): The import process is convoluted.
# Find a way of make it simpler.
def import_modules():
  """Imports DFTimewolf's modules from specified directories.

  Recursively load all modules containing a MODCLASS attribute and add them
  to the module_dict dictionary. Will try loading modules using the python
  packages specified in the loaded configuration file, fall back to default
  otherwise.

  Returns:
    A dictionary describing collectors, processors, and exporters with their
    respective names and classes.

  """
  module_directories = get_config()['module_dirs']
  module_dict = {'collectors': {}, 'processors': {}, 'exporters': {}}
  for directory in module_directories:
    for subdir in module_dict:
      package = get_config().get('python_package', DEFAULT_PACKAGE_NAME)
      package = package + '.modules.' + subdir
      d = os.path.join(directory, subdir)
      for _, name, _ in pkgutil.walk_packages([d], prefix='.'):

        try:
          module = importlib.import_module(name, package=package)
        except ImportError:
          # Fall back to original package
          package = DEFAULT_PACKAGE_NAME + '.lib.' + subdir
          module = importlib.import_module(name, package=package)

        if hasattr(module, 'MODCLASS'):
          for module_name, module_class in module.MODCLASS:
            module_dict[subdir][module_name] = module_class

  return module_dict


def import_recipes():
  """Imports DFTimewolf recipes from specified directories.

  Load all modules from a given recipe directory. If two recipes with identical
  names are loaded, the last one will prevail.

  Returns:
    A dictionary of recipe names and recipe modules.

  """
  recipe_directories = get_config()['recipe_dirs']
  recipe_dict = {}
  for _, name, _ in pkgutil.walk_packages(recipe_directories, prefix='.'):
    package = get_config().get('python_package', DEFAULT_PACKAGE_NAME)
    try:
      module = importlib.import_module(name, package=package + '.recipes')
    except ImportError:
      package = DEFAULT_PACKAGE_NAME + '.cli'
      module = importlib.import_module(name, package=package + '.recipes')

    recipe_name = name[1:]
    recipe_dict[recipe_name] = module
  return recipe_dict


def get_config():
  """Searches several locations for a dftimewolf_config.json file.

  Searches for a dftimewolf_config.json file in the current directory, user's
  home directory, or an DFTIMEWOLF_CONFIG environment variable. If found file is
  decoded as a JSON object.

  Returns:
    JSON object or None
  """
  # pylint: disable=W0603
  global _CONFIG
  if _CONFIG:
    return _CONFIG

  for location in LOCATIONS:
    for filename in FILENAMES:
      if not location or not filename:
        continue
      try:
        full_path = os.path.abspath(os.path.join(location, filename))
        with open(full_path) as config:
          _CONFIG = json.loads(config.read())
          _CONFIG['recipe_dirs'].extend(DEFAULT_RECIPE_DIRECTORIES)
          _CONFIG['module_dirs'].extend(DEFAULT_MODULE_DIRECTORIES)
          print 'Using config file: {0:s}'.format(full_path)
          return _CONFIG
      except IOError:
        pass
      except KeyError as e:
        print('ERROR: configuration file {0:s} '
              'is missing a {1:s} key:'.format(filename, e))

  print 'ERROR: No valid .dftimewolfrc file found. See README for details.'
  exit(-1)
