import sys, os, shutil
import subprocess, json
from pathlib import Path
from dateutil import parser
import pandas as pd

class Executor:


   def __init__(self, program_file, communications_data):

      self._program_file = program_file
      self._input_file = communications_data

      self._required_events = [
         "enable SIMULATION_STARTING SetupParameters",
         "enable SIMULATION_COMPLETE FinishVisualization"]

      self._message_events = {
         "MESSAGE_OUTGOING": "enable MESSAGE_OUTGOING MessageOutgoing",
         "MESSAGE_INCOMING": "enable MESSAGE_INCOMING MessageIncoming",
         "MESSAGE_INTERNAL": "enable MESSAGE_INTERNAL MessageInternal",
         "MESSAGE_DELIVERY_ATTEMPT": "enable MESSAGE_DELIVERY_ATTEMPT MessageDeliveryAttempt",
         "MESSAGE_DISCARDED": "enable MESSAGE_DISCARDED MessageDiscarded",
         "MESSAGE_FAILED_ROUTING": "enable MESSAGE_FAILED_ROUTING MessageFailedRouting",
         "MESSAGE_HOP": "enable MESSAGE_HOP MessageHop",
         "MESSAGE_UPDATED": "enable MESSAGE_UPDATED MessageUpdated",
         "MESSAGE_QUEUED": "enable MESSAGE_QUEUED MessageQueued",
         "MESSAGE_RECEIVED": "enable MESSAGE_RECEIVED MessageReceived",
         "MESSAGE_TRANSMITTED": "enable MESSAGE_TRANSMITTED MessageTransmitted",
         "MESSAGE_TRANSMITTED_HEARTBEAT": "enable MESSAGE_TRANSMITTED_HEARTBEAT MessageTransmittedHeartbeat",
         "MESSAGE_TRANSMIT_ENDED": "enable MESSAGE_TRANSMIT_ENDED MessageTransmitEnded"
      }


   def handle_input_file(self):

      if not self._input_file.is_file():
         print(f'{self._input_file.absolute()} is not a file.')
         sys.exit(1)

      if not self._input_file.exists():
         print(f'{self._input_file.absolute()} file does not exist.')
         sys.exit(1)

      if os.path.basename(self._input_file.absolute()).endswith(".json"):
         self._execute_mission()
         return self._configure_data(ran_mission=True)
      elif os.path.basename(self._input_file.absolute()).endswith(".csv"):
         return self._configure_data(ran_mission=False)
      else:
         print(f'{self._input_file.absolute()} is not JSON or CSV.')
         sys.exit(1)


   def _execute_mission(self):

      with open(self._input_file, "r") as f:
         input_config = json.load(f)
         observer_string = "\n   ".join(["observer", *self._required_events])
         for key, enabled in input_config["message_events"].items():
            if enabled:
               observer_string = "\n   ".join([observer_string, self._message_events[key]])
            else:
               observer_string = "\n   ".join([observer_string, "# " + self._message_events[key]])
         observer_string += "\nend_observer"

      with open(self._program_file.parent.joinpath("utils", "comm_detail_collector.txt"), "r") as collector:
         collector_string = collector.read()
         
      comms_file = self._program_file.parent.joinpath("comms_analysis.afsim")
      startup_file = Path(input_config["scenario_startup"])
      include_doc = "include_once " + str(startup_file.absolute().as_posix()) 
      with open(comms_file, "w") as f:
         f.write("\n".join([include_doc, collector_string, observer_string]))

      print(f"\033[32mRunning mission for {startup_file}...\033[0;0m")
      mission_result = subprocess.run(
         [input_config["mission_exe_path"], str(comms_file.absolute())], 
         cwd=str(startup_file.parent))

      if mission_result.returncode != 0:
         print("\033[31mMission execution error... exiting!\033[0;0m")
         sys.exit(1)

      print(f"\033[32mMission execution of {startup_file} successfully completed.\033[0;0m")
      os.remove(comms_file)
      shutil.move(
         startup_file.parent.joinpath("comms_analysis.csv"),
         self._program_file.parent.joinpath("comms_analysis.csv"))


   def _configure_data(self, ran_mission=True):

      substitutions = {
         'Message_SerialNumber': -1,
         'Message_Originator': 'unknown',
         'Message_Size': -1,
         'Message_Priority': -1,
         'Message_DataTag': -1,
         'OldMessage_SerialNumber': -1,
         'OldMessage_Originator': 'unknown',
         'OldMessage_Type': 'Does Not Exist',
         'OldMessage_Size': -1,
         'OldMessage_Priority': -1,
         'OldMessage_DataTag': -1,
         'Sender_Type': 'unknown',
         'Sender_BaseType': 'unknown',
         'SenderPart_Type': 'unknown',
         'SenderPart_BaseType': 'unknown',
         'Receiver_Name': 'Does Not Exist',
         'Receiver_Type': 'unknown',
         'Receiver_BaseType': 'unknown',
         'ReceiverPart_Name': 'Does Not Exist',
         'ReceiverPart_Type': 'unknown',
         'ReceiverPart_BaseType': 'unknown',
         'CommInteraction_Succeeded': -1,
         'CommInteraction_Failed': -1,
         'CommInteraction_FailedStatus': 'Does Not Exist',
         'Queue_Size': -1
         }

      if ran_mission:
         csv_file_path = self._program_file.parent.joinpath("comms_analysis.csv")
      else:
         csv_file_path = self._input_file

      df = pd.read_csv(csv_file_path).fillna(value=substitutions)
      df["Timestamp"] = df["ISODate"].apply(lambda x: parser.isoparse(x).timestamp())

      return df