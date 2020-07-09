"""Module providing custom logging formatters."""
import logging
import random

def _GenerateColorSequences():
  """Generates ANSI codes for 256 colors."""
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
BOLD = '\u001b[1m'  # Bold / bright modifier

LOG_FORMAT = ('[%(asctime)s] [{0:s}{color:s}%(name)-20s{1:s}] %(levelname)-8s'
              ' %(message)s')

LEVEL_COLOR_MAP = {
    'WARNING': YELLOW,
    'INFO': WHITE,
    'DEBUG': BLUE,
    'CRITICAL': BOLD + BG_RED + WHITE,
    'ERROR': RED
}


class ColorFormatter(logging.Formatter):
  """Helper class used to add color to log messages depending on their level."""
  def __init__(self, random_color=False, **kwargs):
    """Initializes the ColorFormatter object.

    Args:
      random_color (bool): If True, will colorize the module name with a random
          color picked from COLOR_SEQS.
    """
    color = ''
    if random_color:
      color = random.choice(COLOR_SEQS)
    kwargs['fmt'] = LOG_FORMAT.format(BOLD, RESET_SEQ, color=color)
    super(ColorFormatter, self).__init__(**kwargs)

  def format(self, record):
    """Hooks the native format method and colorizes messages.

    Args:
      record (logging.LogRecord): Native log record.

    Returns:
      str: The formatted message string.
    """
    message = record.getMessage()
    loglevel_color = LEVEL_COLOR_MAP.get(record.levelname)
    if loglevel_color:
      message = loglevel_color + message + RESET_SEQ
    record.msg = message
    return super(ColorFormatter, self).format(record)
