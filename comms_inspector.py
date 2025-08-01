import webbrowser
from utils.cli_args import CLIParser
from inspector_packages.dash_app.dash_callbacks import DashCallbacks
from inspector_packages.mission_execution.executor import Executor
from pathlib import Path
import pdb


class AFSIMCommsInspector:

   def __init__(self, 
      communications_data=None, 
      land_color=None, 
      ocean_color=None, 
      resolution=None,
      classification=None):

      self._mission_executor = Executor(Path(__file__), Path(communications_data))
      df = self._mission_executor.handle_input_file()

      self._callbacks = DashCallbacks(df, land_color, ocean_color, resolution, classification)

      self._host = "127.0.0.1"
      self._port = 8050


   def run(self):
      webbrowser.open(f"http://{self._host}:{self._port}/")
      self._callbacks.app.run_server(debug=False, host=self._host, port=self._port)


if __name__ == "__main__":

   cli_parser = CLIParser()

   visualizer = AFSIMCommsInspector(**cli_parser.arguments)
   visualizer.run()