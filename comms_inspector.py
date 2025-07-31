import subprocess
import json
import shutil, os, sys
import webbrowser
from datetime import datetime
from dateutil import parser
from utils.cli_args import CLIParser
from elements.network_plot import NetworkPlot
from elements.globe_plot import GlobePlot
from elements.globe_comms import GlobeComms
from dash_app.dash_layout import DashLayout
import numpy as np
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash_bootstrap_components as dbc
from dash import no_update, ctx, Input, Output, State
import pdb


class AFSIMCommsInspector:

   def __init__(self, 
      communications_data=None, 
      land_color=None, 
      ocean_color=None, 
      resolution=None,
      classification=None):

      self._handle_input_file(communications_data) 

      self._network_plot = NetworkPlot()
      self._globe_plot = GlobePlot(self._df, land_color, ocean_color, resolution)
      self._globe_comms = GlobeComms()
      self._dashboard = DashLayout(
         self._df, 
         self._timestamps, 
         classification, 
         self._network_plot.figure_name)
      self._app = self._dashboard.get_app()

      self._host = "127.0.0.1"
      self._port = 8050

      self._internal_messages = ["MESSAGE_INTERNAL", "MESSAGE_INCOMING", "MESSAGE_OUTGOING"]
      self._external_messages = ["MESSAGE_DELIVERY_ATTEMPT", "MESSAGE_RECEIVED"]

      self._plots_options = {
         "Bar Plot": {"Graph": self._dashboard.initialize_barplot(), "Options": self._dashboard.initialize_barplot_options()},
         "Network Plot": {"Graph": self._dashboard.initialize_network_plot(), "Options": self._dashboard.initialize_network_options()}
      }

      self._empty_plot = {
         "paper_bgcolor":'rgba(0,0,0,0)',
         "plot_bgcolor":'rgba(0,0,0,0)',
         "xaxis": 
         {
            "showgrid": False,
            "showticklabels": False,
            "ticks":'',
            "zeroline":False
         },
         "yaxis": 
         {
            "showgrid": False,
            "showticklabels": False,
            "ticks":'',
            "zeroline":False
         }
      }

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

      self._file_dir = Path(__file__)

      self._define_barplot_callback()
      self._define_network_plot_callback()
      self._define_plot_select_callback()
      self._define_filter_callback()
      self._define_filter_storage_callback()
      self._define_dropdown_options_callback()
      self._define_time_button_callback()
      self._define_time_label_callback()


   def _handle_input_file(self, communications_data):

      self._input_file = Path(communications_data)
      if not self._input_file.is_file():
         print(f'{self._input_file.absolute()} is not a file.')
         sys.exit(1)

      if not self._input_file.exists():
         print(f'{self._input_file.absolute()} file does not exist.')
         sys.exit(1)

      if os.path.basename(self._input_file.absolute()).endswith(".json"):
         self._execute_mission()
         self._configure_data(ran_mission=True)
      elif os.path.basename(self._input_file.absolute()).endswith(".csv"):
         self._configure_data(ran_mission=False)
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

      with open(self._file_dir.parent.joinpath("utils", "comm_detail_collector.txt"), "r") as collector:
         collector_string = collector.read()
         
      comms_file = self._file_dir.parent.joinpath("comms_analysis.afsim")
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
         self._file_dir.parent.joinpath("comms_analysis.csv"))


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
         self._csv_file_path = self._file_dir.parent.joinpath("comms_analysis.csv")
      else:
         self._csv_file_path = self._input_file

      self._df = pd.read_csv(self._csv_file_path).fillna(value=substitutions)
      self._df["Timestamp"] = self._df["ISODate"].apply(lambda x: parser.isoparse(x).timestamp())
      self._timestamps = self._df["Timestamp"].unique()

      self._current_frame = self._df

      self._filter_options = {
         "Event_Type": self._df["Event_Type"].unique(),
         "Message_SerialNumber": self._df["Message_SerialNumber"].unique(),
         "Message_Originator": self._df["Message_Originator"].unique(),
         "Message_Type": self._df["Message_Type"].unique(),
         "Sender_Name": self._df["Sender_Name"].unique(),
         "Sender_Type": self._df["Sender_Type"].unique(),
         "Sender_BaseType": self._df["Sender_BaseType"].unique(),
         "SenderPart_Name": self._df["SenderPart_Name"].unique(),
         "SenderPart_Type": self._df["SenderPart_Type"].unique(),
         "SenderPart_BaseType": self._df["SenderPart_BaseType"].unique(),
         "Receiver_Name": self._df["Receiver_Name"].unique(),
         "Receiver_Type": self._df["Receiver_Type"].unique(),
         "Receiver_BaseType": self._df["Receiver_BaseType"].unique(),
         "ReceiverPart_Name": self._df["ReceiverPart_Name"].unique(),
         "ReceiverPart_Type": self._df["ReceiverPart_Type"].unique(),
         "ReceiverPart_BaseType": self._df["ReceiverPart_BaseType"].unique()
      }


   def _filter_dataframe(self):

      df = self._df
      for key, val in self._filter_options.items():
         if val is not None and len(val) != 0:
            df = df[df[key].isin(val)]

      return df


   def _generate_barplots(self, frame, subplot_category, bar_graph_category, bar_stack_category):
         
      num_cols = 2
      quotient, remainder = divmod(len(frame[subplot_category].unique()), num_cols)
      num_rows = quotient + remainder

      fig = make_subplots(
         rows=num_rows if num_rows >= 3 else 3,
         cols=num_cols,
         subplot_titles=frame[subplot_category].unique().astype(str),
      )

      subplot_grp = 1
      for idx, category in enumerate(frame[subplot_category].unique()):
         row, col = divmod(idx, num_cols)
         bar_data = frame[frame[subplot_category] == category]
         for _, stack_category in enumerate(bar_data[bar_stack_category].unique()):
            stack = bar_data[bar_data[bar_stack_category] == stack_category]
            series = stack[bar_graph_category].value_counts()
            fig.append_trace(
               go.Bar(
                  x=series.index,
                  y=series.values,
                  customdata=series.to_list(),
                  hovertemplate=f'{stack_category}' + ' - %{customdata}<extra></extra>',
                  offsetgroup=subplot_grp
               ),
               row+1, col+1
            )
         subplot_grp += 1

      fig.update_layout(barmode='stack', showlegend=False)

      return fig


   def _define_time_label_callback(self):

      @self._app.callback(
         Output("time-label", "children"),
         Input("time-slider", "value"),
         Input('radios', 'value')
      )
      def _write_time_label(value, radio_val):

         current_time = datetime.utcfromtimestamp(value).strftime("%H:%M:%S.%f")[:-3]

         if radio_val:
            return f"Current Time: {current_time}"
         else:
            return "Bar Plots not tied to time!"


   def _define_barplot_callback(self):

      @self._app.callback(
         Output("bar-graph", "figure"),
         Input("time-slider", "value"),
         Input("subplot-category", "value"),
         Input("bar-graph-category", "value"),
         Input("bar-stack-category", "value"),
         Input("display-memory", "data"),
         Input('radios', 'value')
      )
      def update_barplots(
         time_value, subplot_category, 
         bar_graph_category, bar_stack_category,
         filter_data, radio_val):

         frame = self._current_frame

         if radio_val:
            frame = frame[frame["Timestamp"] == time_value]

         if not frame.empty:
            return self._generate_barplots(frame, subplot_category, bar_graph_category, bar_stack_category)
         else:
            return go.Figure({"data": None, "layout": self._empty_plot})


   def _define_network_plot_callback(self):

         @self._app.callback(
            Output(self._network_plot.figure_name, "figure"),
            Input("time-slider", "value"),
            Input("network-layout", "value"),
            Input("display-memory", "data"),
            Input('radios', 'value')
         )
         def update_network_plot(time_value, network_layout, filter_data, radio_val):

            frame = self._current_frame

            if radio_val:
               frame = frame[frame["Timestamp"] == time_value]

            frame = frame[frame["Event_Type"].isin(self._external_messages)]
            if not frame.empty:
               return self._network_plot.generate_network_figure(frame, network_layout, self._empty_plot)
            else:
               return go.Figure({"data": None, "layout": self._empty_plot})


   def _define_plot_select_callback(self):

      @self._app.callback(
         Output("plots-area", "children"),
         Output("plot-filters", "children"),
         Input("plot-options", "value")
      )
      def select_plot(plot_option):

         option = self._plots_options[plot_option]

         return option["Graph"], option["Options"]


   def _define_time_button_callback(self):

      @self._app.callback(
         Output('time-slider', 'value', allow_duplicate=True),
         Input('previous-time', 'n_clicks'),
         Input('next-time', 'n_clicks'),
         State('time-slider', 'value'),
         prevent_initial_call=True
      )
      def shift_time(previous_time, next_time, current_time):

         if current_time is None:
            return self._timestamps[0]

         current_idx = np.where(self._timestamps == current_time)[0][0]

         if ctx.triggered_id == "previous-time":
            if current_idx != 0:
               return self._timestamps[current_idx-1]
            else:
               return self._timestamps[0]

         if ctx.triggered_id == "next-time":
            if current_idx != self._timestamps.shape[0] - 1:
               return self._timestamps[current_idx+1]
            else:
               return self._timestamps[-1]


   def _define_filter_callback(self):

      @self._app.callback(
         [Output('my-graph', 'figure'),
         # Output('empty-dataframe-message', 'style'), Output('empty-dataframe-message', 'children'),
         Output('time-slider', 'min'), Output('time-slider', 'max'),
         Output('time-slider', 'value'), Output('time-slider', 'marks')],
         Input('time-slider', 'value'),
         Input("display-memory", "data"),
         # State('empty-dataframe-message', 'style')
      )
      def filter_frame(value, filter_data):

         frame = self._current_frame

         if ctx.triggered_id != "time-slider":
            self._timestamps = frame["Timestamp"].unique()

         if ctx.triggered_id != "time-slider":
            frame = frame[frame["Timestamp"] == self._timestamps[0]]
            current_time = datetime.utcfromtimestamp(self._timestamps[0]).strftime("%H:%M:%S.%f")[:-3]
         else:
            frame = frame[frame["Timestamp"] == value]
            current_time = datetime.utcfromtimestamp(value).strftime("%H:%M:%S.%f")[:-3]

         update = []

         internal = frame[frame["Event_Type"].isin(self._internal_messages)]
         external = frame[frame["Event_Type"].isin(self._external_messages)]
         if not external.empty:
            transmission_plots, transmission_directions = self._globe_comms.update_external_events(external, current_time)
            update.extend(transmission_directions)
            update.extend(transmission_plots)

         if not internal.empty:
            new_plot = self._globe_comms.update_internal_events(internal, current_time)
            update.append(new_plot)

         self._globe_plot.set_camera_view(internal, external)
         fig = self._globe_plot.build_earth_figure(update)

         if ctx.triggered_id != "time-slider" and len(self._timestamps) != 0:
            slider_marks = {}
            for val in self._timestamps:
               slider_marks[val] = '' 
            return fig, self._timestamps[0], self._timestamps[-1], self._timestamps[0], slider_marks
         else:
            return fig, no_update, no_update, no_update, no_update


   def _define_filter_storage_callback(self):

      @self._app.callback(
         Output("filter-memory", "data", allow_duplicate=True),
         Input("event-type", "value"),
         Input("msg-serial-number", "value"),
         Input("msg-originator", "value"),
         Input("msg-type", "value"),
         Input("sender-name", "value"),
         Input("sender-type", "value"),
         Input("sender-basetype", "value"),
         Input("sender-part", "value"),
         Input("sender-part-type", "value"),
         Input("sender-part-basetype", "value"),
         Input("receiver-name", "value"),
         Input("receiver-type", "value"),
         Input("receiver-basetype", "value"),
         Input("receiver-part", "value"),
         Input("receiver-part-type", "value"),
         Input("receiver-part-basetype", "value"),
         prevent_initial_call=True
      )
      def store_filter_info(
         evt_type, 
         msg_serial_number, msg_originator, msg_type,
         sender_name, sender_type, sender_basetype,
         sender_part, sender_part_type, sender_part_basetype,
         rcvr_name, rcvr_type, rcvr_basetype, 
         rcvr_part, rcvr_part_type, rcvr_part_basetype):

         self._filter_options["Event_Type"] = evt_type
         self._filter_options["Message_SerialNumber"] = msg_serial_number
         self._filter_options["Message_Originator"] = msg_originator
         self._filter_options["Message_Type"] = msg_type
         self._filter_options["Sender_Name"] = sender_name
         self._filter_options["Sender_Type"] = sender_type
         self._filter_options["Sender_BaseType"] = sender_basetype
         self._filter_options["SenderPart_Name"] = sender_part
         self._filter_options["SenderPart_Type"] = sender_part_type
         self._filter_options["SenderPart_BaseType"] = sender_part_basetype
         self._filter_options["Receiver_Name"] = rcvr_name
         self._filter_options["Receiver_Type"] = rcvr_type
         self._filter_options["Receiver_BaseType"] = rcvr_basetype
         self._filter_options["ReceiverPart_Name"] = rcvr_part
         self._filter_options["ReceiverPart_Type"] = rcvr_part_type
         self._filter_options["ReceiverPart_BaseType"] = rcvr_part_basetype

         self._current_frame = self._filter_dataframe()

         data = {"frame_filtered": True}

         return data

   
   def _define_dropdown_options_callback(self):

      @self._app.callback(
         [Output("event-type", "options"),
         Output("msg-serial-number", "options"),
         Output("msg-originator", "options"),
         Output("msg-type", "options"),
         Output("sender-name", "options"),
         Output("sender-type", "options"),
         Output("sender-basetype", "options"),
         Output("sender-part", "options"),
         Output("sender-part-type", "options"),
         Output("sender-part-basetype", "options"),
         Output("receiver-name", "options"),
         Output("receiver-type", "options"),
         Output("receiver-basetype", "options"),
         Output("receiver-part", "options"),
         Output("receiver-part-type", "options"),
         Output("receiver-part-basetype", "options")],
         Output("display-memory", "data"),
         Input("filter-memory", "data"),
         prevent_initial_call=True
      )
      def update_dropdown_options(filter_data):

         options = [] 
         for column in self._filter_options:
            options.append(self._current_frame[column].unique())

         options.append(True)
         
         return options
         

   def run(self):
      webbrowser.open(f"http://{self._host}:{self._port}/")
      self._app.run_server(debug=False, host=self._host, port=self._port)


if __name__ == "__main__":

   cli_parser = CLIParser()

   visualizer = AFSIMCommsInspector(**cli_parser.arguments)
   visualizer.run()