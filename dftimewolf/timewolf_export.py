"""Timewolf CLI tool to export processed artifacts.

This Timewolf tool exports Plaso storage files to Timesketch.

Example use:
Using flags:
$ timewolf_export --path /path/to/storage/file.plaso --name timeline_name /
--reason 123

You can also run it by sending path and name on stdin:
echo "/path/to/storage/file.plaso timeline_name" | timewolf_export --reason 123

This is designed to work with another set of Timewolf tools named
timewolf_collect and timewolf_process:
$ timewolf_collect --host cpelton.greendale.edu --reason 123 |
timewolf_process | timewolf_export --reason 123

The output is the URL to the sketch in Timesketch. E.g:
https://timesketch.greendale.edu/sketch/4711/
"""

import getpass
import os
import netrc
import re
import sys
import gflags

from dftimewolf.lib import timesketch_utils
from dftimewolf.lib import utils as timewolf_utils

FLAGS = gflags.FLAGS
gflags.DEFINE_string(u'reason', None, u'Reason for requesting client access')
gflags.DEFINE_string(u'path', None, u'Path to Plaso storage file')
gflags.DEFINE_string(u'name', None, u'Name the timeline')
gflags.DEFINE_string(u'timesketch_server_url', u'http://localhost:5000',
                     u'Timesketch server to use')
gflags.DEFINE_integer(u'sketch_id', None, u'Timesketch sketch to append to')
gflags.DEFINE_boolean(u'verbose', False, u'Show extended output')
gflags.DEFINE_string(u'username', None, u'Timesketch username')


def main(argv):
  """Timewolf export tool."""
  try:
    argv = FLAGS(argv)  # parse flags
  except gflags.FlagsError, e:
    sys.exit(e)
  # Console output helper
  console_out = timewolf_utils.TimewolfConsoleOutput(
      sender=u'TimewolfExportCli', verbose=FLAGS.verbose)

  netrc_file = netrc.netrc()
  ts_host = re.search(r"://(\S+):\d+", FLAGS.timesketch_server_url).group(1)
  netrc_entry = netrc_file.authenticators(ts_host)
  if netrc_entry:
    username = netrc_entry[0]
    password = netrc_entry[2]
  else:
    username = FLAGS.username
    password = getpass.getpass()

  timesketch_api = timesketch_utils.TimesketchApiClient(
      FLAGS.timesketch_server_url, username, password)

  # Export artifacts
  if FLAGS.path:
    if not FLAGS.name:
      FLAGS.name = os.path.basename(FLAGS.path.rstrip(u'/'))
    processed_artifacts = [(FLAGS.path, FLAGS.name)]
  else:
    processed_artifacts = ((path, name)
                           for path, name in timewolf_utils.ReadFromStdin())

  if processed_artifacts:
    # Check if sketch exists and that the user have access to it, or exit.
    if FLAGS.sketch_id:
      try:
        timesketch_api.GetSketch(FLAGS.sketch_id)
        sketch_id = FLAGS.sketch_id
      except ValueError as e:
        console_out.StdErr(e, die=True)
    else:
      sketch_id = timesketch_api.CreateSketch(FLAGS.reason, FLAGS.reason)

    for path_name in processed_artifacts:
      path = path_name[0]
      name = path_name[1]
      new_timeline_id = timesketch_api.UploadTimeline(name, path)
      timesketch_api.AddTimelineToSketch(sketch_id, new_timeline_id)

    sketch_url = timesketch_api.GetSketchURL(sketch_id)

    # Final output
    console_out.StdOut(sketch_url)
  else:
    console_out.StfErr(u'No processed artifacts found', die=True)


if __name__ == '__main__':
  main(sys.argv)
