"""Module providing custom logging formatters and colorization for ANSI
compatible terminals."""
import datetime
import logging
import tempfile
from logging import LogRecord
from typing import Any


def GenerateTempLogFile() -> str:
  """Generates a temporary log file name."""
  now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
  logfile = tempfile.NamedTemporaryFile(
    mode='a',
    prefix=f'dftimewolf-run-{now}_',
    suffix='.log',
    delete=False)
  log_filename = logfile.name
  logfile.close()
  return log_filename


SUCCESS = 25  # 25 is right between INFO and WARNING


LEVEL_COLOR_MAP = {
    'WARNING': '\u001b[0;93m',
    'SUCCESS': '\u001b[1;30;42m',
    'INFO': '\u001b[0;97m',
    'DEBUG': '\u001b[0;94m',
    'CRITICAL': '\u001b[1;31;107m',
    'ERROR': '\u001b[0;91m'
}
RESET_SEQ = '\u001b[0m'


_DEBUG_FORMATTER = logging.Formatter('[%(asctime)s] [%(name)-20s] %(levelname)-8s [%(threadName)-22s] %(message)s')
_DEFAULT_FORMATTER = logging.Formatter('[%(asctime)s] [%(name)-20s] %(levelname)-8s %(message)s')


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
      handler_level: int,
      colorize: bool = True,
      **kwargs: Any) -> None:
    """Initializes the WolfFormatter object.

    Args:
      colorize (bool): If True, output will be colorized.
    """
    self._formatter = _DEBUG_FORMATTER if handler_level == logging.DEBUG else _DEFAULT_FORMATTER
    self._colorize = colorize

    super().__init__(**kwargs)

  def format(self, record: LogRecord) -> str:
    """Hooks the native format method and colorizes messages if needed.

    Args:
      record (logging.LogRecord): Native log record.

    Returns:
      str: The formatted message string.
    """
    message = record.msg

    if self._colorize:
      loglevel_color = LEVEL_COLOR_MAP.get(record.levelname)
      if loglevel_color:
        message = loglevel_color + message + RESET_SEQ

    record.msg = message

    return self._formatter.format(record)
