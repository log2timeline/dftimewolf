import logging
import random

COLOR_SEQS = []
RESET_SEQ = '\u001b[0m'

for i in range(0, 16):
  for j in range(0, 16):
    code = str(i * 16 + j)
    seq = '\u001b[38;5;' + code + 'm'
    COLOR_SEQS.append(seq)

# Cherrypick a few interesting values. We still want the whole list of colors
# so that modules have a good amount colors to chose from.
BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = COLOR_SEQS[8:16]
BG_RED = '\u001b[41m'  # Red background
BOLD = '\u001b[1m'  # Bold / bright modifier

LOG_FORMAT = '[%(asctime)s] [{0:s}{color:s}%(name)-20s{1:s}] %(levelname)-8s %(message)s'

COLORS = {
    'WARNING': YELLOW,
    'INFO': WHITE,
    'DEBUG': BLUE,
    'CRITICAL': BOLD + BG_RED + WHITE,
    'ERROR': RED
}

class ColorFormatter(logging.Formatter):

  def __init__(self, random_color=False, **kwargs):
    color = ''
    if random_color:
      color = random.choice(COLOR_SEQS)
    kwargs['fmt'] = LOG_FORMAT.format(BOLD, RESET_SEQ, color=color)
    super(ColorFormatter, self).__init__(**kwargs)

  def format(self, record):
    message = record.getMessage()
    loglevel_color = COLORS.get(record.levelname)
    if loglevel_color:
      message = loglevel_color + message + RESET_SEQ
    record.msg = message
    return super(ColorFormatter, self).format(record)
