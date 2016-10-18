"""Timewolf CLI.

This is the Timewolf all-in-one CLI tool. It does the following:
1) Collect artifacts from local filesystem or from a GRR client.
2) Process the artifacts with Plaso log2timeline tool.
3) Create a new Timesketch sketch or append to an existing one.
4) Upload the plaso storage files to Timesketch.
5) Output a link to the sketch.

Example use:
$ timewolf_cli --hosts cpelton.greendale.edu --reason 12345
$ timewolf_cli --paths /path/to/artifacts/ --reason 12345

You can also combine --paths and --hosts to collect artifacts from both.

In the case of collecting artifacts from a host via GRR you may need approval
for the host in question.
"""

import getpass
import webbrowser
import netrc
import re
import sys
import gflags

from dftimewolf.lib import collectors
from dftimewolf.lib import processors
from dftimewolf.lib import timesketch_utils
from dftimewolf.lib import utils as timewolf_utils

FLAGS = gflags.FLAGS
gflags.DEFINE_list(u'hosts', [],
                   u'One or more hostnames to collect artifacts from with GRR')
gflags.DEFINE_list(u'paths', [],
                   u'One or more paths to files to process on the filesystem')
gflags.DEFINE_string(u'reason', None, u'Reason for requesting client access')
gflags.DEFINE_string(u'grr_server_url', u'http://localhost:8000',
 u'GRR server to use')
gflags.DEFINE_string(u'timesketch_server_url', u'http://localhost:5000',
                     u'Timesketch server to use')
gflags.DEFINE_string(u'artifacts', None,
                     u'Comma separated list of GRR artifacts to fetch')
gflags.DEFINE_string(u'timezone', None, u'Timezone to use for Plaso processing')
gflags.DEFINE_list(
    u'approvers', None,
    u'Comma seperated list of usernames to approve GRR client access')
gflags.DEFINE_boolean(u'open_in_browser', False,
                      u'Open the resulting sketch in a browser window')
gflags.DEFINE_integer(u'sketch_id', None, u'Timesketch sketch to append to')
gflags.DEFINE_boolean(u'verbose', False, u'Show extended output')
gflags.DEFINE_string(u'username', None, u'GRR/Timesketch username')


def main(argv):
  """Timewolf tool."""
  try:
    argv = FLAGS(argv)  # parse flags
  except gflags.FlagsError, e:
    sys.exit(e)
  # Console output helper
  console_out = timewolf_utils.TimewolfConsoleOutput(
      sender=u'TimewolfCli', verbose=FLAGS.verbose)

  if not (FLAGS.paths || FLAGS.hosts):
    console_out.StdErr(u'paths or hosts must be specified', die=True)


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

  grr_host = re.search(r"://(\S+):\d+", FLAGS.grr_server_url).group(1)
  netrc_entry = netrc_file.authenticators(grr_host)
  if netrc_entry:
    username = netrc_entry[0]
    password = netrc_entry[2]
  else:
    username = FLAGS.username
    password = getpass.getpass()

  # Collect artifacts
  try:
    collected_artifacts = collectors.CollectArtifactsHelper(
        FLAGS.hosts, FLAGS.paths, FLAGS.artifacts, FLAGS.reason,
        FLAGS.approvers, FLAGS.verbose, FLAGS.grr_server_url, username,
        password)
  except (ValueError, RuntimeError) as e:
    console_out.StdErr(e, die=True)

  # Process artifacts
  if FLAGS.timezone:
    if not timewolf_utils.IsValidTimezone(FLAGS.timezone):
      console_out.StdErr(
          u'Unknown timezone: {0:s}'.format(FLAGS.timezone), die=True)

  processed_artifacts = processors.ProcessArtifactsHelper(collected_artifacts,
                                                          FLAGS.timezone,
                                                          FLAGS.verbose)

  if processed_artifacts:
    # Check if sketch exists and that the user has access to it, or exit.
    if FLAGS.sketch_id:
      try:
        timesketch_api.GetSketch(FLAGS.sketch_id)
        sketch_id = FLAGS.sketch_id
      except ValueError as e:
        console_out.StdErr(e, die=True)
    else:
      sketch_id = timesketch_api.CreateSketch(FLAGS.reason, FLAGS.reason)

    # Export artifacts
    for path_name in processed_artifacts:
      path = path_name[0]
      name = path_name[1]
      new_timeline_id = timesketch_api.UploadTimeline(name, path)
      timesketch_api.AddTimelineToSketch(sketch_id, new_timeline_id)

    sketch_url = timesketch_api.GetSketchURL(sketch_id)

    # Final output to stdout
    console_out.StdOut(sketch_url)

    # Open new webbrowser window/tab opening the result analysis URL
    if FLAGS.open_in_browser:
      webbrowser.open_new(sketch_url)


if __name__ == '__main__':
  main(sys.argv)
