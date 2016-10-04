"""API Client for Timesketch."""
from bs4 import BeautifulSoup
import requests


class TimesketchApiClient(object):
  """API Client for Timesketch."""

  def __init__(self, host, username, password):
    self.host_url = host
    self.username = username
    self.password = password
    self.session = self._CreateSession()

  def _CreateSession(self):
    """Create HTTP session."""
    session = requests.Session()
    session.verify = False  # Depending on SSL cert is verifiable
    response = session.get(self.host_url)
    # Get the CSRF token from the response
    soup = BeautifulSoup(response.text, 'html.parser')
    csrf_token = soup.find('input', dict(name='csrf_token'))['value']
    login_data = dict(username=self.username, password=self.password)
    session.headers.update({
        'x-csrftoken': csrf_token,
        'referer': self.host_url
    })
    response = session.post(
        u'{0:s}/login/'.format(self.host_url), data=login_data)
    return session

  def CreateSketch(self, name, description):
    """Create a new sketch with the specified name and description."""
    resource_url = u'{0:s}/api/v1/sketches/'.format(self.host_url)
    form_data = {u'name': name, u'description': description}
    response = self.session.post(resource_url, json=form_data)
    response_dict = response.json()
    sketch_id = response_dict[u'objects'][0]['id']
    return sketch_id

  def UploadTimeline(self, timeline_name, plaso_storage_path):
    """Create a timeline with the specified name from the given plaso file."""
    resource_url = u'{0:s}/api/v1/upload/'.format(self.host_url)
    files = {'file': open(plaso_storage_path, 'rb')}
    data = {u'name': timeline_name}
    response = self.session.post(resource_url, files=files, data=data)
    response_dict = response.json()
    index_id = response_dict[u'objects'][0]['id']
    return index_id

  def AddTimelineToSketch(self, sketch_id, index_id):
    """Associate the specified timeline and sketch."""
    resource_url = u'{0:s}/api/v1/sketches/{1:d}/'.format(self.host_url,
                                                          sketch_id)
    form_data = {u'timelines': [index_id]}
    self.session.post(resource_url, json=form_data)

  def GetSketch(self, sketch_id):
    """Get information on the specified sketch."""
    resource_url = u'{0:s}/api/v1/sketches/{1:d}/'.format(self.host_url,
                                                          sketch_id)
    response = self.session.get(resource_url)
    response_dict = response.json()
    try:
      response_dict[u'objects']
    except KeyError:
      raise ValueError(u'Sketch does not exist or you have no access')
    return response_dict

  def GetSketchURL(self, sketch_id):
    """Get the full URL of the specified sketch."""
    resource_url = u'{0:s}/api/v1/sketches/{1:d}/'.format(self.host_url,
                                                          sketch_id)
    return resource_url


if __name__ == '__main__':
  timesketch = TimesketchApiClient(
      host=u'127.0.0.1', username=u'foo', password=u'bar')
  # Create new sketch with name 'foo' and description 'bar'
  ts_sketch_id = timesketch.CreateSketch(u'foo', u'bar')
  # Upload and index a new timeline from foo.plaso with name 'foobar timeline'
  ts_index_id = timesketch.UploadTimeline(
      u'foobar timeline', u'/tmp/foo.plaso')
  # Add the newly created timeline to the sketch
  timesketch.AddTimelineToSketch(ts_sketch_id, ts_index_id)
