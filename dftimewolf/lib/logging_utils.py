"""Module providing custom logging formatters and colorization for ANSI
compatible terminals."""
import inspect
import logging
import os
import random
import threading
from logging import LogRecord
from typing import Any, List

SUCCESS = 25  # 25 is right between INFO and WARNING


def _GenerateColorSequences() -> List[str]:
  """Generates ANSI codes for 256 colors.

  Works on Linux and macOS, Windows (WSL) to be confirmed.
  """
  sequences = []
  for i in range(0, 16):
    for j in range(0, 16):
      code = str(i * 16 + j)
      seq = '\u001b[38;5;' + code + 'm'
      sequences.append(seq)
  return sequences


COLOR_SEQS = _GenerateColorSequences()
RESET_SEQ = '\u001b[0m'

# Cherrypick a few interesting values. We still want the whole list of colors
# so that modules have a good amount colors to chose from.
# pylint: disable=unbalanced-tuple-unpacking
BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = COLOR_SEQS[8:16]
BG_RED = '\u001b[41m'  # Red background
BG_GREEN = '\u001b[42m'  # Green background
BOLD = '\u001b[1m'  # Bold / bright modifier

# We'll get something like this:
# [2020-07-09 18:06:05,187] [TimesketchExporter  ] INFO     Sketch 23 created
LOG_FORMAT = (
    '[%(asctime)s] [{0:s}{color:s}%(name)-20s{1:s}] %(levelname)-8s'
    ' %(message)s')

LEVEL_COLOR_MAP = {
    'WARNING': YELLOW,
    'SUCCESS': BOLD + BG_GREEN + BLACK,
    'INFO': WHITE,
    'DEBUG': BLUE,
    'CRITICAL': BOLD + BG_RED + WHITE,
    'ERROR': RED
}


class WolfLogger(logging.getLoggerClass()):  # type: ignore
  """Custom logging Class with a `success` logging function."""

  def success(self, *args: Any, **kwargs: Any) -> None:  # pylint: disable=invalid-name
    """Logs a success message."""
    super(WolfLogger, self).log(SUCCESS, *args, **kwargs)

logging.setLoggerClass(WolfLogger)


class WolfFormatter(logging.Formatter):
  """Helper class used to add color to log messages depending on their level."""

  def __init__(
      self,
      colorize: bool = True,
      random_color: bool = False,
      threaded: bool = False,
      **kwargs: Any) -> None:
    """Initializes the WolfFormatter object.

    Args:
      colorize (bool): If True, output will be colorized.
      random_color (bool): If True, will colorize the module name with a random
          color picked from COLOR_SEQS.
    """
    self.threaded = threaded
    self.colorize = colorize
    kwargs['fmt'] = LOG_FORMAT.format('', '', color='')
    if self.colorize:
      color = ''
      if random_color:
        color = random.choice(COLOR_SEQS)
      kwargs['fmt'] = LOG_FORMAT.format(BOLD, RESET_SEQ, color=color)
    super(WolfFormatter, self).__init__(**kwargs)

  def format(self, record: LogRecord) -> str:
    """Hooks the native format method and colorizes messages if needed.

    Args:
      record (logging.LogRecord): Native log record.

    Returns:
      str: The formatted message string.
    """
    if self.colorize:
      message = record.getMessage()
      loglevel_color = LEVEL_COLOR_MAP.get(record.levelname)
      if loglevel_color:
        message = loglevel_color + message + RESET_SEQ
      record.msg = message

    if self.threaded:
      stack = [i.function for i in inspect.stack()]
      if 'Process' in stack:
        thread_name = threading.current_thread().getName()
        message = record.getMessage()
        record.msg = "[{0:s}] {1:s}".format(thread_name, message)
    return super(WolfFormatter, self).format(record)
