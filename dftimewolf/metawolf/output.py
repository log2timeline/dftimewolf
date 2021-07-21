#!/usr/bin/env python
# -*- coding: utf-8 -*-

PURPLE = '\033[95m'
GREEN = '\033[92m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RED = '\033[91m'
ENDC = '\033[0m'


class MetawolfOutput:
  """MetawolfOutput handles formatting of strings to display in Metawolf."""

  def Welcome(self) -> None:
    """Print Metawolf welcome message."""
    print(self.Color('''
     _____            __           __      __        .__    _____ 
    /     \    ____ _/  |_ _____  /  \    /  \ ____  |  | _/ ____\\
   /  \ /  \ _/ __ \\\\   __\\\\__  \ \   \/\/   //  _ \ |  | \   __\ 
  /    Y    \\\\  ___/ |  |   / __ \_\        /(  <_> )|  |__|  |   
  \____|__  / \___  >|__|  (____  / \__/\  /  \____/ |____/|__|   
          \/      \/            \/       \/                      
      ''', PURPLE))

  @staticmethod
  def Color(string: str, color: str) -> str:
    """Return a colored output for stdout.

    Args:
      string (str): The string to format.
      color (str): The color to format the string with.

    Returns:
      str: The formatted string.
    """
    return '{0:s}{1!s}{2:s}'.format(color, string, ENDC)
