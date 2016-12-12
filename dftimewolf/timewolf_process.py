#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Timewolf CLI tool to process artifacts.

This Timewolf tool processes artifacts with Plaso log2timeline tool.

Example use:
$ timewolf_process --path /path/to/artifacts/

You can also run it by sending path and name on stdin:
echo "/path/to/artifacts/ timeline_name" | timewolf_process

This is designed to work with another Timewolf tools named timewolf_collect:
$ timewolf_collect --path path/to/artifacts/ --reason 123 | timewolf_process

The output is space delimited string with path and timeline name. E.g:
/path/to/timeline.plaso timeline_name

This can then be piped into other tools, e.g. timewolf_export:
$ timewolf_process --path /path/to/artifacts/ | timewolf_export --reason 123
"""

import sys
import gflags

from dftimewolf.lib import collectors
from dftimewolf.lib import processors
from dftimewolf.lib import utils

FLAGS = gflags.FLAGS
gflags.DEFINE_boolean(u'local_plaso', False, u'Use the local plaso installation')
gflags.DEFINE_string(u'path', None, u'Path to artifacts to process')
gflags.DEFINE_string(u'name', None, u'Name the timeline')
gflags.DEFINE_string(u'timezone', None, u'Timezone to use for Plaso processing')
gflags.DEFINE_boolean(u'verbose', False, u'Show extended output')


def main(argv):
  """Timewolf process tool."""
  try:
    _ = FLAGS(argv)  # parse flags
  except gflags.FlagsError, e:
    sys.exit(e)
  # Console output helper
  console_out = utils.TimewolfConsoleOutput(
      sender=u'TimewolfProcessCli', verbose=FLAGS.verbose)

  if FLAGS.path:
    # Collect the artifacts with the filesystem collector
    collector = collectors.FilesystemCollector(FLAGS.path, FLAGS.name,
                                               FLAGS.verbose)
    collected_artifacts = [(collector.Collect(), collector.collection_name)]
  else:
    # Read from stdin, expects space delimited lines with path and name
    collected_artifacts = ((path, name) for path, name in utils.ReadFromStdin())

  # Process the artifacts
  if FLAGS.timezone:
    if not utils.IsValidTimezone(FLAGS.timezone):
      console_out.StdErr(u'Unknown timezone', die=True)

  processed_artifacts = processors.ProcessArtifactsHelper(collected_artifacts,
                                                          FLAGS.timezone,
							  FLAGS.local_plaso,
                                                          FLAGS.verbose)

  # Send the result to stdout
  for plaso_storage_file_path, timeline_name in processed_artifacts:
    console_out.StdOut(u'{0:s} {1:s}'.format(plaso_storage_file_path,
                                             timeline_name))


if __name__ == '__main__':
  main(sys.argv)
