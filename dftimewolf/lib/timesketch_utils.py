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

  def __init__(self, host, username, password):
    """Initialize the Timesketch API client object.

    Args:
      host (str): Hostname and port of Timesketch instance
      username (str): Timesketch username
      password (str): Timesketch password
    """
    self.host_url = host
    self.api_base_url = '{0:s}/api/v1'.format(self.host_url)
    self.username = username
    self.session = self._create_session(username, password)

  def _create_session(self, username, password):
    """Create HTTP session.

    Args:
      username (str): Timesketch username
      password (str): Timesketch password

    Returns:
      requests.Session: Session object.
    """
    session = requests.Session()
    session.verify = False  # Depending on SSL cert is verifiable
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

  def create_sketch(self, name, description):
    """Create a new sketch with the specified name and description.

    Args:
      name (str): Title of sketch
      description (str): Description of sketch

    Returns:
      int: ID of created sketch
    """
    resource_url = '{0:s}/sketches/'.format(self.api_base_url)
    form_data = {'name': name, 'description': description}
    response = self.session.post(resource_url, json=form_data)
    response_dict = response.json()
    sketch_id = response_dict['objects'][0]['id']
    return sketch_id

  def upload_timeline(self, timeline_name, plaso_storage_path):
    """Create a timeline with the specified name from the given plaso file.

    Args:
      timeline_name (str): Name of timeline
      plaso_storage_path (str): Local path of plaso file to be uploaded

    Returns:
      int: ID of uploaded timeline
    """
    resource_url = '{0:s}/upload/'.format(self.api_base_url)
    files = {'file': open(plaso_storage_path, 'rb')}
    data = {'name': timeline_name}
    response = self.session.post(resource_url, files=files, data=data)
    response_dict = response.json()
    index_id = response_dict['objects'][0]['id']
    return index_id

  def export_artifacts(self, processed_artifacts, sketch_id):
    """Upload provided artifacts to specified, or new if non-existent, sketch.

    Args:
      processed_artifacts:  List of (timeline_name, artifact_path) tuples
      sketch_id: ID of sketch to append the timeline to

    Returns:
      int: ID of sketch
    """

    # Export processed timeline(s)
    for timeline_name, artifact_path in processed_artifacts:
      new_timeline_id = self.upload_timeline(timeline_name, artifact_path)
      self.add_timeline_to_sketch(sketch_id, new_timeline_id)

    return sketch_id

  def add_timeline_to_sketch(self, sketch_id, index_id):
    """Associate the specified timeline and sketch.

    Args:
      sketch_id (int): ID of sketch
      index_id (int): ID of timeline to add to sketch
    """
    resource_url = '{0:s}/sketches/{1:d}/'.format(self.api_base_url, sketch_id)
    form_data = {'timelines': [index_id]}
    self.session.post(resource_url, json=form_data)

  def get_sketch(self, sketch_id):
    """Get information on the specified sketch.

    Args:
      sketch_id (int): ID of sketch

    Returns:
      dict: Dictionary of sketch information


    Raises:
      ValueError: Sketch is inaccessible
    """
    resource_url = '{0:s}/sketches/{1:d}/'.format(self.api_base_url, sketch_id)
    response = self.session.get(resource_url)
    response_dict = response.json()
    try:
      response_dict['objects']
    except KeyError:
      raise ValueError('Sketch does not exist or you have no access')
    return response_dict

  def get_sketch_url(self, sketch_id):
    """Get the full URL of the specified sketch.

    Args:
      sketch_id: ID of sketch
    Returns:
      str: URL of sketch
    """
    resource_url = '{0:s}/sketch/{1:d}/'.format(self.host_url, sketch_id)
    return resource_url
