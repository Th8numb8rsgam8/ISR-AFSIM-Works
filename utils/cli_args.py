import argparse
import matplotlib.colors as colors

import pdb

class CLIParser:

   def __init__(self):

      self._available_colors = list(colors.CSS4_COLORS.keys())
      self._parse_arguments()

   @property
   def arguments(self):
      return self._arguments

   @arguments.setter
   def arguments(self, value):
      raise AttributeError("Arguments are read-only")

   def _parse_arguments(self):

      cli_parser = argparse.ArgumentParser(
         prog="AFSIM Communications Inspector",
         formatter_class=argparse.RawDescriptionHelpFormatter,
         description=
         '''
         This application helps to visualize and perform exploratory
         analysis of AFSIM communications with the following features:
         1. Globe visualization of platforms
         2. Ability to filter communications data for a focused analysis.
         ''')

      cli_parser.add_argument(
         "communications_data",
         metavar="C:/path/to/file",
         type=str,
         help="JSON Config file or CSV file path to AFSIM communications data."
      )

      cli_parser.add_argument(
         "-L", "--land-color",
         metavar="coral",
         dest="land_color",
         type=str,
         default=None,
         choices=self._available_colors,
         help="Land color on globe."
      )

      cli_parser.add_argument(
         "-O", "--ocean-color",
         metavar="aqua",
         dest="ocean_color",
         type=str,
         default=None,
         choices=self._available_colors,
         help="Ocean color on globe."
      )

      cli_parser.add_argument(
         "-R", "--resolution",
         metavar="low",
         dest="resolution",
         type=str,
         default="low",
         choices=["low", "medium", "high"],
         help="Globe surface resolution."
      )

      cli_parser.add_argument(
         "-C", "--classification",
         metavar="CUI",
         dest="classification",
         type=str,
         default="CUI",
         help="Classification of data used"
      )

      cli_parser.add_argument("--version", action="version", version='%(prog)s 0.0.1')
      self._arguments = vars(cli_parser.parse_args())