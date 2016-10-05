"""API Client for Timesketch."""
from bs4 import BeautifulSoup
import requests


class TimesketchApiClient(object):
  """API Client for Timesketch.

  Attributes:
    host_url: Hostname and port of Timesketch instance
    username: Timesketch username
    session: HTTP session for calls to Timesketch
  """

  def __init__(self, host, username, password):
    """Initialize the Timesketch API client object.

    Args:
      host: Hostname and port of Timesketch instance
      api_base_url: Base URL of API
      username: Timesketch username
      password: Timesketch password
    """
    self.host_url = host
    self.api_base_url = u'{0:s}/api/v1'.format(self.host_url)
    self.username = username
    self.session = self._CreateSession(username, password)

  def _CreateSession(self, username, password):
    """Create HTTP session.

    Args:
      username: Timesketch username
      password: Timesketch password

    Returns:
      Session object
    """
    session = requests.Session()
    session.verify = False  # Depending on SSL cert is verifiable
    response = session.get(self.host_url)
    # Get the CSRF token from the response
    soup = BeautifulSoup(response.text, 'html.parser')
    csrf_token = soup.find('input', dict(name='csrf_token'))['value']
    login_data = dict(username=username, password=password)
    session.headers.update({
        'x-csrftoken': csrf_token,
        'referer': self.host_url
    })
    response = session.post(
        u'{0:s}/login/'.format(self.host_url), data=login_data)
    return session

  def CreateSketch(self, name, description):
    """Create a new sketch with the specified name and description.

    Args:
      name: Title of sketch
      description: Description of sketch
    Returns:
      Integer corresponding to ID of created sketch
    """
    resource_url = u'{0:s}/sketches/'.format(self.api_base_url)
    form_data = {u'name': name, u'description': description}
    response = self.session.post(resource_url, json=form_data)
    response_dict = response.json()
    sketch_id = response_dict[u'objects'][0]['id']
    return sketch_id

  def UploadTimeline(self, timeline_name, plaso_storage_path):
    """Create a timeline with the specified name from the given plaso file.

    Args:
      timeline_name: Name of timeline
      plaso_storage_file: Local path of plaso file to be uploaded
    Returns:
      Integer corresponding to ID of uploaded timeline
    """
    resource_url = u'{0:s}/upload/'.format(self.api_base_url)
    files = {'file': open(plaso_storage_path, 'rb')}
    data = {u'name': timeline_name}
    response = self.session.post(resource_url, files=files, data=data)
    response_dict = response.json()
    index_id = response_dict[u'objects'][0]['id']
    return index_id

  def AddTimelineToSketch(self, sketch_id, index_id):
    """Associate the specified timeline and sketch.

    Args:
      sketch_id: ID of sketch
      index_id: ID of timeline to add to sketch
    """
    resource_url = u'{0:s}/sketches/{1:d}/'.format(self.api_base_url, sketch_id)
    form_data = {u'timelines': [index_id]}
    self.session.post(resource_url, json=form_data)

  def GetSketch(self, sketch_id):
    """Get information on the specified sketch.

    Args:
      sketch_id: ID of sketch
    Returns:
      Dictionary of sketch information
    Raises:
      ValueError: Sketch is inaccessible
    """
    resource_url = u'{0:s}/sketches/{1:d}/'.format(self.api_base_url, sketch_id)
    response = self.session.get(resource_url)
    response_dict = response.json()
    try:
      response_dict[u'objects']
    except KeyError:
      raise ValueError(u'Sketch does not exist or you have no access')
    return response_dict

  def GetSketchURL(self, sketch_id):
    """Get the full URL of the specified sketch.

    Args:
      sketch_id: ID of sketch
    Returns:
      URL of sketch
    """
    resource_url = u'{0:s}/sketches/{1:d}/'.format(self.host_url, sketch_id)
    return resource_url
