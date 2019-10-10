# -*- coding: utf-8 -*-
"""API Client for Timesketch."""
from __future__ import unicode_literals

from bs4 import BeautifulSoup
import requests


class TimesketchApiClient(object):
  """API Client for Timesketch.

  Attributes:
    host_url (str): Hostname and port of Timesketch instance
    api_base_url (str): Base URL of API
    username (str): Timesketch username
    session (requests.Session): HTTP session for calls to Timesketch
  """

  def __init__(self, host_url, username, password, verify_tls=True):
    """Initialize the Timesketch API client object.

    Args:
      host_url (str): URL of Timesketch instance
      username (str): Timesketch username
      password (str): Timesketch password
      verify_tls (Optional[bool]): Whether to verify x509 certificates during TLS
          connections.
    """
    self.host_url = host_url
    self.api_base_url = '{0:s}/api/v1'.format(self.host_url)
    self.username = username
    self.session = self._CreateSession(username, password)
    self._verify_tls = verify_tls

  def _CreateSession(self, username, password):
    """Create a session with a Timesketch server.

    Args:
      username (str): Timesketch username
      password (str): Timesketch password

    Returns:
      requests.Session: Session object.
    """
    session = requests.Session()
    session.verify = self._verify_tls
    try:
      response = session.get(self.host_url)
    except requests.exceptions.ConnectionError:
      return False
    # Get the CSRF token from the response
    soup = BeautifulSoup(response.text, 'html.parser')
    csrf_token = soup.find('input', dict(name='csrf_token'))['value']
    login_data = dict(username=username, password=password)
    session.headers.update({
        'x-csrftoken': csrf_token,
        'referer': self.host_url
    })
    _ = session.post('{0:s}/login/'.format(self.host_url), data=login_data)
    return session

  def CreateSketch(self, name, description):
    """Creates a new sketch on a Timesketch server.

    Args:
      name (str): title of the sketch.
      description (str): description of the sketch.

    Returns:
      int: identifier of the sketch on the Timesketch server.
    """
    resource_url = '{0:s}/sketches/'.format(self.api_base_url)
    form_data = {'name': name, 'description': description}
    response = self.session.post(resource_url, json=form_data)
    response_dict = response.json()
    sketch_id = response_dict['objects'][0]['id']
    return sketch_id

  def _UploadTimeline(self, timeline_name, plaso_storage_path):
    """Uploades a plaso storage file to a timeline on a Timesketch server.

    The Timesketch server will create the timeline if it does not exist.

    Args:
      timeline_name (str): name of the timeline.
      plaso_storage_path (str): local path of the plaso storage file to
          be uploaded.

    Returns:
      int: identifier of the timeline on the Timesketch server.

    Raises:
      RuntimeError: If the JSON response from Timesketch cannot be decoded.
    """
    resource_url = '{0:s}/upload/'.format(self.api_base_url)
    files = {'file': open(plaso_storage_path, 'rb')}
    data = {'name': timeline_name}
    response = self.session.post(resource_url, files=files, data=data)
    try:
      response_dict = response.json()
    except ValueError:
      raise RuntimeError(
          'Could not decode JSON response from Timesketch'
          ' (Status {0:d}):\n{1:s}'.format(
              response.status_code, response.content))

    return response_dict['objects'][0]['id']

  def ExportArtifacts(self, processed_artifacts, sketch_id):
    """Upload provided artifacts to specified, or new if non-existent, sketch.

    Args:
      processed_artifacts (list[tuple[str, str]): pairs of timeline names and
          artifact paths to upload to a Timesketch server.
      sketch_id (int): identifier of sketch to append the timeline to.

    Returns:
      int: identifier of the sketch on the Timesketch server.
    """
    # Export processed timeline(s)
    for timeline_name, artifact_path in processed_artifacts:
      print('Uploading {0:s} to timeline {1:s}'.format(
          artifact_path, timeline_name))
      new_timeline_id = self._UploadTimeline(timeline_name, artifact_path)
      self._AddTimelineToSketch(sketch_id, new_timeline_id)

    return sketch_id

  def _AddTimelineToSketch(self, sketch_id, index_id):
    """Associates a timeline with a sketch.

    Args:
      sketch_id (int): identifier of the sketch on the Timesketch server.
      index_id (int): identifier of timeline on the Timesketch server to
          add to sketch.
    """
    resource_url = '{0:s}/sketches/{1:d}/timelines/'.format(
        self.api_base_url, sketch_id)
    form_data = {'timeline': [index_id]}
    self.session.post(resource_url, json=form_data)

  def GetSketchUrl(self, sketch_id):
    """Retrieves the full URL of a sketch.

    Args:
      sketch_id (int): identifier of the sketch on the Timesketch server.

    Returns:
      str: URL of sketch.
    """
    return '{0:s}/sketch/{1:d}/'.format(self.host_url, sketch_id)
