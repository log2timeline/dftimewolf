"""Timewolf CLI tool to collect artifacts.

This Timewolf tool collects files from either local filesystem or via GRR.

Example use:
$ timewolf_collect --hosts cpelton.greendale.edu --reason 12345
$ timewolf_collect --paths /path/to/artifacts/ --reason 12345

The output is space delimited string with path and collection name. E.g:
/tmp/03498209842093840284/C.12349439849383/ C.12349439849383

This can then be piped into other tools, e.g. timewolf_process
$ timewolf_collect --path /path/to/artifacts/ --reason 12345 | timewolf_process
"""

import getpass
import netrc
import re
import sys
import gflags

from dftimewolf.lib import collectors
from dftimewolf.lib import utils as timewolf_utils

FLAGS = gflags.FLAGS
gflags.DEFINE_list(u'hosts', [],
                   u'One or more hostnames to collect artifacts from with GRR')
gflags.DEFINE_list(u'paths', [],
                   u'One or more paths to artifacts on the filesystem')
gflags.DEFINE_string(u'reason', None, u'Reason for requesting client access')
gflags.DEFINE_string(u'grr_server_url', u'http://localhost:8000',
 u'GRR server to use')
gflags.DEFINE_string(u'artifacts', None,
                     u'Comma seperated list of GRR artifacts to fetch')
gflags.DEFINE_list(
    u'approvers', None,
    u'Comma seperated list of usernames to approve GRR client access')
gflags.DEFINE_boolean(u'verbose', False, u'Show extended output')
gflags.DEFINE_string(u'username', None, u'GRR username')


def main(argv):
  """Timewolf collect tool."""
  try:
    argv = FLAGS(argv)  # parse flags
  except gflags.FlagsError, e:
    sys.exit(e)
  # Console output helper.
  console_out = timewolf_utils.TimewolfConsoleOutput(
      sender=u'TimewolfCollectCli', verbose=FLAGS.verbose)

  if not (FLAGS.paths || FLAGS.hosts):
    console_out.StdErr(u'paths or hosts must be specified', die=True)


  netrc_file = netrc.netrc()
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

  # Send the result to stdout as space delimited paths.
  for path, name in collected_artifacts:
    console_out.StdOut(u'{0:s} {1:s}'.format(path, name))


if __name__ == '__main__':
  main(sys.argv)
