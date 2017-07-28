"""DFTimewolf recipe for collecting data from the filesystem.

- Collectors collect from a path in the FS
- Processes them with a local install of plaso
- Exports them to a new Timesketch sketch
"""

__author__ = u'tomchop@google.com (Thomas Chopitea)'

class LocalPlasoRecipe(object):
  """Definitions for the LocalPlaso recipe.

  Attributes:
    name: str, Recipe name.
    contents: Dict describing the recipe behavior.
    args: (flag, description) tuples of arguments that are loaded at runtime.
  """
  name = 'local_plaso'

  contents = {
      'name': 'local_plaso',
      'params': {},
      'collectors': [
          {
              'name': 'FilesystemCollector',
              'args': {
                  'paths': ['@paths'],
                  'verbose': True,
                  },
              }
          ],
      'processors': [
          {
              'name': 'LocalPlasoProcessor',
              'args': {
                  'timezone': None,
                  'verbose': True,
                  },
              }
          ],
      'exporters': [
          {
              'name': 'TimesketchExporter',
              'args': {
                  'ts_endpoint': None,
                  'ts_username': None,
                  'ts_password': None,
                  'incident_id': '@incident_id',
                  'sketch_id': None,
                  'verbose': True,
                  }
              }
          ],
      }

  args = [
      ('paths', 'Paths to process'),
      ('--incident_id', 'Incident ID (used for Timesketch descrption)'),
  ]

  @classmethod
  def load(cls, user_config):
    """Populates timesketch-related fields with the user's configuration.
    Args:
      user_config: dict contatining data to correctly use the Timesketch
          export module

    Raises:
      ValueError if one of the keys is missing.
    """
    if user_config is None:
      raise ValueError("Timesketch configuration needed for local_plaso")
    if ('ts_endpoint' not in user_config or
        'ts_username' not in user_config or
        'ts_password' not in user_config):
      raise ValueError(
          "ts_endpoint, ts_username or ts_password not found in configuration")

    ts_endpoint = user_config['ts_endpoint']
    ts_username = user_config['ts_username']
    ts_password = user_config['ts_password']
    cls.contents['exporters'][0]['args']['ts_endpoint'] = ts_endpoint
    cls.contents['exporters'][0]['args']['ts_username'] = ts_username
    cls.contents['exporters'][0]['args']['ts_password'] = ts_password
