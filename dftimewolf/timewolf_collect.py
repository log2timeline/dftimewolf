#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

import re
import sys
import gflags

from dftimewolf.lib import collectors
from dftimewolf.lib import utils as timewolf_utils

FLAGS = gflags.FLAGS
gflags.DEFINE_list(u'hosts', [],
                   u'One or more hostnames to collect artifacts from with GRR')
gflags.DEFINE_boolean(u'new_hunt', False, u'Start a new GRR hunt')
gflags.DEFINE_string(u'hunt_id', None,
                     u'Existing hunt to download current result set from')
gflags.DEFINE_list(u'paths', [],
                   u'One or more paths to artifacts on the filesystem')
gflags.DEFINE_string(u'reason', None, u'Reason for requesting _client access')
gflags.DEFINE_string(u'grr_server_url', u'http://localhost:8000',
                     u'GRR server to use')
gflags.DEFINE_string(u'artifacts', None,
                     u'Comma separated list of GRR artifacts to fetch')
gflags.DEFINE_boolean(u'use_tsk', False, u'Use TSK for artifact collection')
gflags.DEFINE_list(
    u'approvers', None,
    u'Comma separated list of usernames to approve GRR _client access')
gflags.DEFINE_boolean(u'verbose', False, u'Show extended output')
gflags.DEFINE_string(u'username', None, u'GRR username')


def main(argv):
  """Timewolf collect tool."""
  try:
    _ = FLAGS(argv)  # parse flags
  except gflags.FlagsError, e:
    sys.exit(e)
  # Console output helper.
  console_out = timewolf_utils.TimewolfConsoleOutput(
      sender=u'TimewolfCollectCli', verbose=FLAGS.verbose)

  if not (FLAGS.paths or FLAGS.hosts or FLAGS.hunt_id):
    console_out.StdErr(u'paths or hosts must be specified', die=True)
  elif (FLAGS.new_hunt and FLAGS.hosts):
    console_out.StdErr(u'new_hunt and hosts are mutually exclusive', die=True)
  elif (FLAGS.new_hunt and FLAGS.hunt_id):
    console_out.StdErr(u'new_hunt and hunt_id are mutually exclusive', die=True)

  grr_host = re.search(r'://(\S+):\d+', FLAGS.grr_server_url).group(1)
  username, password = timewolf_utils.GetCredentials(FLAGS.username, grr_host)

  # Collect artifacts
  try:
    collected_artifacts = collectors.CollectArtifactsHelper(
        FLAGS.hosts, FLAGS.new_hunt, FLAGS.hunt_id, FLAGS.paths,
        FLAGS.artifacts, FLAGS.use_tsk, FLAGS.reason, FLAGS.approvers,
        FLAGS.verbose, FLAGS.grr_server_url, username, password)
  except (ValueError, RuntimeError) as e:
    console_out.StdErr(e, die=True)

  # Send the result to stdout as space delimited paths.
  for path, name in collected_artifacts:
    console_out.StdOut(u'{0:s} {1:s}'.format(path, name))


if __name__ == '__main__':
  main(sys.argv)
