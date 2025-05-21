import math
import subprocess
import json, pickle
import shutil, os, sys
import webbrowser, warnings
from datetime import datetime
from dateutil import parser
from utils.cli_args import CLIParser
import numpy as np
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash_bootstrap_components as dbc
from dash import no_update, ctx, dcc, html, callback, Dash, Input, Output, State
import pdb


class AFSIMCommsInspector:

   def __init__(self, 
      communications_data=None, 
      land_color=None, 
      ocean_color=None, 
      resolution=None,
      classification=None):

      self._host = "127.0.0.1"
      self._port = 8050

      self._internal_messages = ["MESSAGE_INTERNAL", "MESSAGE_INCOMING", "MESSAGE_OUTGOING"]
      self._external_messages = ["MESSAGE_DELIVERY_ATTEMPT", "MESSAGE_RECEIVED"]

      self._transmission_interval = 50000
      self._transmission_result = {
         "Success": {"color_name": "mediumturquoise", "rgb": [72, 209, 204]},
         "Fail": {"color_name": "darkred", "rgb": [139, 0, 0]}
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
      self._classification = classification


      self._handle_input_file(communications_data) 

      self._app = Dash(
         title="AFSIM Communications Inspector",
         external_stylesheets=[
            '/static/styles.css',
            '/static/bootstrap.min.css'
         ]
      )

      self._equator_radius = 6.378 * 10**6
      self._polar_radius = 6.357 * 10**6

      self._load_earth_data(land_color, ocean_color, resolution)

      self._set_earth_points()
      self._set_earth_surface()

      self._set_axes_range()
      self._set_axes_attributes()

      self._initialize_figure()
      self._set_dash_layout()

      self._define_barplot_callback()
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


   def _load_earth_data(self, land_color=None, ocean_color=None, resolution=None):

      earth_data = Path("earth_data")
      self._earth_image = np.load(earth_data.joinpath(f"earth_image_{resolution}.npy"))
      if land_color is not None and ocean_color is not None:
         cutoff = 0.24285714285714285
         land_ocean = self._earth_image > cutoff
         self._earth_image = np.where(land_ocean == True, 1, 0)
         self._earth_colorscale = [[0, ocean_color], [1, land_color]]
      else:
         with open(earth_data.joinpath("earth_colorscale"), "rb") as f:
            self._earth_colorscale = pickle.load(f)


   def _get_curve_points_on_sphere(self, point1, point2, num_points=50):
      """
      Calculates points along the great-circle curve between two points on a sphere.

      Args:
          point1: Tuple (x, y, z) coordinates of the first point.
          point2: Tuple (x, y, z) coordinates of the second point.
          num_points: Number of points to generate along the curve.

      Returns:
          A list of tuples, where each tuple is (x, y, z) coordinates of a point on the curve.
      """

      # Calculate the angle between the two points
      vector_dot = np.dot(point1, point2)
      vector_magnitudes_mult = np.linalg.norm(point1) * np.linalg.norm(point2)
      angle = np.arccos(vector_dot / vector_magnitudes_mult)

      # Generate points along the great-circle curve
      x, y, z = [], [], []
      for i in range(num_points+1):
          t = i / num_points
          new_angle = angle * t
          sin_angle = np.sin(new_angle)
          sin_remaining_angle = np.sin(angle - new_angle)
          
          new_point = (sin_remaining_angle * point1 + sin_angle * point2) / np.sin(angle)
          x.append(new_point[0])
          y.append(new_point[1])
          z.append(new_point[2])

      return x, y, z

   def _get_points_on_line_segment(self, point1, point2, num_points=50):

      x, y, z = [], [], []
      for i in range(num_points+1):
         t = i / num_points
         new_point = (1 - t) * point1 + t * point2
         x.append(new_point[0])
         y.append(new_point[1])
         z.append(new_point[2])

      return x, y, z


   def _los_hits_horizon(self, sender_location, receiver_location):

      diff = receiver_location - sender_location
      t = -(sender_location * diff).sum() / (diff ** 2).sum()

      if 0 < t < 1:
         closest_point = sender_location + t * diff
         return np.linalg.norm(closest_point) <= self._equator_radius
      else:
         return False


   def _set_earth_points(self):

      theta = np.linspace(0, 2 * np.pi, self._earth_image.shape[0]) + np.pi
      phi = np.linspace(0, np.pi, self._earth_image.shape[1])

      self._earth_x = self._equator_radius * np.outer(np.cos(theta), np.sin(phi))
      self._earth_y = self._equator_radius * np.outer(np.sin(theta), np.sin(phi))
      self._earth_z = self._polar_radius * np.outer(np.ones(np.size(theta)), np.cos(phi))


   def _set_earth_surface(self):

      self._earth_surface = {
         "type": "surface",
         "name": "Earth Surface",
         "x": self._earth_x,
         "y": self._earth_y,
         "z": self._earth_z,
         "surfacecolor": self._earth_image,
         "colorscale": self._earth_colorscale,
         "hoverinfo": "none",
         "showscale": False,
      }


   def _set_axes_range(self):

      x_limit = self._df[["SenderLocation_X", "ReceiverLocation_X"]].abs().max().max()
      y_limit = self._df[["SenderLocation_Y", "ReceiverLocation_Y"]].abs().max().max()
      z_limit = self._df[["SenderLocation_Z", "ReceiverLocation_Z"]].abs().max().max()

      self._axes_range = [
         -max(x_limit, y_limit, z_limit, self._equator_radius),
         max(x_limit, y_limit, z_limit, self._equator_radius)
         ]


   def _set_axes_attributes(self):

      self._axes_attributes = {
         "range": self._axes_range,
         "nticks": 5,
         "showbackground": False,
         "showgrid": False,
         "showline": False,
         "showticklabels": False,
         "ticks":'',
         "title":'',
         "zeroline":False
      }

   def _globe_layout(self, camera_view={"x": 3, "y": 0, "z": 0}):

      globe_layout = {
         "scene":
         {
            "xaxis": self._axes_attributes,
            "yaxis": self._axes_attributes,
            "zaxis": self._axes_attributes,
            "aspectmode": "cube",
            "camera": {
               "eye": camera_view
            }
         }
      }

      return globe_layout


   def _initialize_figure(self):

      self._fig = go.Figure(
         {
            "data": [self._earth_surface],
            "layout": self._globe_layout()
         }
      )

   def _create_dropdown(self, col_name, dropdown_id, options, multi, placeholder=None, value=None, clearable=True):

      dropdown = html.Div(
         className='labeled-div',
         children=[
            html.Label(col_name),
            dcc.Dropdown(
               id=dropdown_id, 
               options=options,
               placeholder=placeholder,
               value=value,
               multi=multi,
               clearable=clearable)
         ]
      )

      return dropdown

   def _create_slider(self):

      slider_marks = {}
      for val in self._timestamps:
         slider_marks[val] = '' 

      slider = dcc.Slider(
         id="time-slider",
         min=self._timestamps[0], 
         max=self._timestamps[-1],
         step=None,
         marks=eval(str(slider_marks)),
         value=self._timestamps[0],
         dots=False,
         updatemode="mouseup",
         tooltip={
            "placement": "top", 
            "always_visible": True,
            "transform": "convertToHMS"
         })

      return slider


   def _create_globe_visual(self):

      graph = dcc.Graph(
         id='my-graph', 
         config={"scrollZoom": True}, 
         style={'height': '80vh'})

      return graph
   

   def _build_earth_figure(self, traces, camera_view):

      fig = go.Figure(
         {
            "data": traces,
            "layout": self._globe_layout(camera_view)
         }
      )

      return fig
   

   def _set_camera_view(self, internal_df, external_df):

         camera_zoom = 3
         internal_pts = internal_df[["SenderLocation_X", "SenderLocation_Y", "SenderLocation_Z"]]
         sender_pts = external_df[["SenderLocation_X", "SenderLocation_Y", "SenderLocation_Z"]]
         rcvr_pts = external_df[["ReceiverLocation_X", "ReceiverLocation_Y", "ReceiverLocation_Z"]]
         rcvr_pts = rcvr_pts.rename(columns=
            {"ReceiverLocation_X": "SenderLocation_X",
             "ReceiverLocation_Y": "SenderLocation_Y",
             "ReceiverLocation_Z": "SenderLocation_Z"})

         points_df = pd.concat([internal_pts, sender_pts, rcvr_pts], ignore_index=True)

         with warnings.catch_warnings():
            warnings.filterwarnings('error', category=RuntimeWarning)
            try:
               camera_location = points_df.dropna(axis=0).drop_duplicates().values.mean(axis=0)
               camera_vector = camera_location / np.linalg.norm(camera_location)
               camera_zoom = 2 * points_df.apply(lambda x: np.linalg.norm(x), axis=1).max() / self._axes_range[1]
               camera_center = camera_zoom * camera_vector
               return {"x": camera_center[0], "y": camera_center[1], "z": camera_center[2]}
            except RuntimeWarning as e:
               return {"x": camera_zoom, "y": 0, "z": 0}


   def _create_filter_options(self):

      filter_options = dbc.Accordion(
         children=[dbc.AccordionItem([
            self._create_dropdown("Event Type", "event-type", self._df["Event_Type"].unique(), True, "All Events"),
            self._create_dropdown("Message Serial Number", "msg-serial-number", self._df["Message_SerialNumber"].unique(), True, "All Serial Numbers"),
            self._create_dropdown("Message Originator", "msg-originator", self._df["Message_Originator"].unique(), True, "All Originators"),
            self._create_dropdown("Message Type", "msg-type", self._df["Message_Type"].unique(), True, "All Message Types"),
            self._create_dropdown("Sender", "sender-name", self._df["Sender_Name"].unique(), True, "All Senders"),
            self._create_dropdown("Sender Type", "sender-type", self._df["Sender_Type"].unique(), True, "All Sender Types"),
            self._create_dropdown("Sender BaseType", "sender-basetype", self._df["Sender_BaseType"].unique(), True, "All Sender BaseTypes"),
            self._create_dropdown("Sender Part", "sender-part", self._df["SenderPart_Name"].unique(), True, "All Sender Parts"),
            self._create_dropdown("Sender Part Type", "sender-part-type", self._df["SenderPart_Type"].unique(), True, "All Sender Part Types"),
            self._create_dropdown("Sender Part BaseType", "sender-part-basetype", self._df["SenderPart_BaseType"].unique(), True, "All Sender Part BaseTypes"),
            self._create_dropdown("Receiver", "receiver-name", self._df["Receiver_Name"].unique(), True, "All Receivers"),
            self._create_dropdown("Receiver Type", "receiver-type", self._df["Receiver_Type"].unique(), True, "All Receiver Types"),
            self._create_dropdown("Receiver BaseType", "receiver-basetype", self._df["Receiver_BaseType"].unique(), True, "All Receiver BaseTypes"),
            self._create_dropdown("Receiver Part", "receiver-part", self._df["ReceiverPart_Name"].unique(), True, "All Receiver Parts"),
            self._create_dropdown("Receiver Part Type", "receiver-part-type", self._df["ReceiverPart_Type"].unique(), True, "All Receiver Part Types"),
            self._create_dropdown("Receiver Part BaseType", "receiver-part-basetype", self._df["ReceiverPart_BaseType"].unique(), True, "All Receiver Part BaseTypes"),
            ], title="Filter Options")],
            start_collapsed=True
         )

      return filter_options


   def _create_time_label(self):

      time_label = html.Div(
         id='time-label',
         style={
            'textAlign': 'center',
            'fontWeight': 'bold',
            'paddingTop': '20px'
         }
      )

      return time_label


   def _create_bar_subplots(self):

      bar_plots = html.Div(
         style={
            'overflowY': 'scroll',
            'height': '80vh'
         },
         children=[dcc.Graph(
            id='bar-graph', 
            config={"scrollZoom": False}, 
            style={'height': '200vh'}
         )]
      )

      return bar_plots


   def _create_subplot_filters(self):

      subplot_options = [
         "ISODate", "Event_Type", "Message_SerialNumber", "Message_Originator",
         "Message_Type", "Message_Size", "Message_Priority", "Message_DataTag",
         "OldMessage_SerialNumber", "OldMessage_Originator", "OldMessage_Type",
         "OldMessage_Size", "OldMessage_Priority", "OldMessage_DataTag",
         "Sender_Name", "Sender_Type", "Sender_BaseType",
         "SenderPart_Name", "SenderPart_Type", "SenderPart_BaseType",
         "Receiver_Name", "Receiver_Type", "Receiver_BaseType",
         "ReceiverPart_Name", "ReceiverPart_Type", "ReceiverPart_BaseType",
         "CommInteraction_Succeeded", "CommInteraction_Failed",
         "CommInteraction_FailedStatus", "Queue_Size"]

      subplot_filters = dbc.Accordion(
         children=[dbc.AccordionItem([
            self._create_dropdown("Subplot Category", "subplot-category", subplot_options, False, None, "Event_Type", False),
            self._create_dropdown("Bar Graph Category", "bar-graph-category", subplot_options, False, None, "Sender_Name", False),
            self._create_dropdown("Bar Stack Category", 'bar-stack-category', subplot_options, False, None, "Receiver_Name", False)
         ], title="Bar Charts Options")],
         start_collapsed=True 
      )

      return subplot_filters


   def _create_time_buttons(self):

      buttons = html.Div(
         style={
            'textAlign': 'center',
            'paddingBottom': '20px'
         },
         children=[
            dbc.Button("Previous Time", id="previous-time", color="primary"),
            dbc.Button("Next Time", id="next-time", color="primary")
         ]
      )

      return buttons

   
   def _create_button_group(self):

      button_group = html.Div(
         style={
            'textAlign': 'center',
            'paddingTop': '20px'
         },
         children=[
            dbc.Row(html.Label("Connect to Time Slider")),
            dbc.Row(
               style={
                  'textAlign': 'center'
               },
               children=[
                  html.Div(
                     dbc.RadioItems(
                     id="radios",
                     className="btn-group",
                     inputClassName="btn-check",
                     labelClassName="btn btn-outline-primary",
                     labelCheckedClassName="active",
                     options=[
                        {"label": "YES", "value": 1},
                        {"label": "NO", "value": 0}
                     ],
                     value=1
                  )
               )]
            )
         ],
         className="radio-group"
      )

      return button_group

   def _create_dataframe_message(self):

      df_message = html.Div(
         "AFSIM Communications Inspector",
         id="empty-dataframe-message",
         style={
            'position': 'fixed',
            'left': '0',
            'height': '100%',
            'width': '100%',
            'textAlign': 'center',
            'paddingTop': '40vh',
            'fontSize': 'xxx-large',
            'fontWeight': 'bold',
            'opacity': '0.5',
            'backgroundColor': 'unset',
            'zIndex': '-1'
         }
      )

      return df_message

   def _create_displayed_data_row(self):

      displayed_data = dbc.Row(
         id="displayed-data",
         style={
            'display': 'flex',
            'zIndex': '1'
         },
         children=[
            dbc.Col([
               self._create_globe_visual(),
               self._create_slider(),
               self._create_time_buttons()
            ], width=6),
            dbc.Col([
               self._create_bar_subplots(),
               self._create_time_label(),
               self._create_button_group()
            ], width=6)
      ])

      return displayed_data

   def _create_options_row(self):

      options_row = dbc.Row(
         id="options_row",
         style={
            'position': 'relative',
            'textAlign': 'center',
            'zIndex': '5'
         },
         children=[
            dbc.Col(self._create_filter_options(), width=6),
            dbc.Col(self._create_subplot_filters(), width=6),
         ]
      )

      return options_row

   def _create_classification_markings(self, pos):

      markings = dbc.Row(
         id=f"{pos}-classification",
         style={
            'position': 'relative',
            'textAlign': 'center',
            'color': 'crimson',
            'fontSize': 'x-large',
            'fontWeight': 'bold',
            'zIndex': '5'
         },
         children=[
            dbc.Col(html.Label(self._classification), width=12)
         ]
      )

      return markings


   def _set_dash_layout(self):
      
      self._app.layout = dcc.Loading(
         children=[
            html.Div(
               id="main-display",
               children=[
                  self._create_classification_markings("top"),
                  self._create_dataframe_message(),
                  self._create_displayed_data_row(),
                  self._create_options_row(),
                  self._create_classification_markings("bottom"),
               ]
            ),
            dcc.Store(id="filter-memory"),
            dcc.Store(id="display-memory")
         ],
         target_components={"main-display": "children"},
      )


   def _update_internal_events(self, internal_df, current_time):

      x, y, z = [], [], []
      internal_events = []
      internal_colors = []
      for sender, group in internal_df.groupby("Sender_Name"):
         x.append(group["SenderLocation_X"].values[0])
         y.append(group["SenderLocation_Y"].values[0])
         z.append(group["SenderLocation_Z"].values[0])

         event_info = '' 
         event_info = f'Time (H:M:S): {current_time}<br>'
         event_info += f'Platform: {sender}<br>'
         event_num = 0
         for idx, row in group.iterrows():
            event_num += 1
            event_info += f'\
{event_num}. Event Type: {row["Event_Type"]}<br> \
   Platform Parts: {row["SenderPart_Name"]} >> {row["ReceiverPart_Name"]}<br> \
   Message Type: {row["Message_Type"]}<br> \
   Message Number: {row["Message_SerialNumber"]}<br> \
   Message Originator: {row["Message_Originator"]}<br>'
         event_info += '<extra></extra>' 
         internal_events.append(event_info)

         if not group[group["Event_Type"] == "MESSAGE_OUTGOING"].empty and \
            not group[group["Event_Type"] == "MESSAGE_INCOMING"].empty:
            internal_colors.append('goldenrod')
         elif not group[group["Event_Type"] == "MESSAGE_OUTGOING"].empty:
            internal_colors.append('cornflowerblue')
         elif not group[group["Event_Type"] == "MESSAGE_INCOMING"].empty:
            internal_colors.append('mediumspringgreen')
         else:
            internal_colors.append('salmon')

      updated_plot = {
         "type": "scatter3d",
         "name": "internal",
         "x": x,
         "y": y,
         "z": z,
         "mode": "markers",
         "customdata": internal_events,
         "hovertemplate":'%{customdata}',
         "marker": 
         {
            "size": 5,
            "color": internal_colors 
         },
         "opacity": 1,
         "showlegend": False
      }

      return updated_plot

   def _transmission_info_text(self, current_time, transmission, group):

         sender, sender_part, receiver, receiver_part = transmission

         transmission_info = ''
         transmission_info = f'Time (H:M:S): {current_time}<br>'
         transmission_info += f'Sender: {sender} >> Receiver: {receiver}<br>'
         transmission_num = 0
         transmission_result = "Success"
         for idx, row in group.iterrows():
            transmission_num += 1
            transmission_info += f'\
<b>{transmission_num}. Event Type: {row["Event_Type"]}</b><br> \
   Platform Parts: {sender_part} >> {receiver_part}<br> \
   Message Type: {row["Message_Type"]}<br> \
   Message Number: {row["Message_SerialNumber"]}<br> \
   Message Originator: {row["Message_Originator"]}<br>'
            if row["CommInteraction_FailedStatus"] != "Does Not Exist":
               transmission_result = "Fail"
               transmission_info += f'    Failure Reason: {row["CommInteraction_FailedStatus"]}<br>'
         transmission_info += '<extra></extra>' 

         return transmission_info, transmission_result

   def _create_transmission_line(self, group):

      line_data = {}
      sender_location = np.array([
         group["SenderLocation_X"].values[0], 
         group["SenderLocation_Y"].values[0], 
         group["SenderLocation_Z"].values[0]])

      receiver_location = np.array([
         group["ReceiverLocation_X"].values[0], 
         group["ReceiverLocation_Y"].values[0], 
         group["ReceiverLocation_Z"].values[0]])
         
      platform_range = group["SenderToRcvr_Range"].values[0]
      num_arrows, remainder = divmod(platform_range, self._transmission_interval)
      delta = (0.5 * remainder / platform_range) * (receiver_location - sender_location)
      first_arrow = sender_location + delta
      last_arrow = receiver_location - delta

      if self._los_hits_horizon(sender_location, receiver_location):
         x, y, z = self._get_curve_points_on_sphere(first_arrow, last_arrow, int(num_arrows) if num_arrows != 0 else 10)
      else:
         x, y, z = self._get_points_on_line_segment(first_arrow, last_arrow, int(num_arrows) if num_arrows != 0 else 10)

      line_data.update({
         "x": [sender_location[0]] + x + [receiver_location[0]],
         "y": [sender_location[1]] + y + [receiver_location[1]],
         "z": [sender_location[2]] + z + [receiver_location[2]],
      })

      if num_arrows != 0:
         u, v, w = [], [], []
         arrow_x, arrow_y, arrow_z = [], [], []
         for i in range(int(num_arrows)):
            pt1 = np.array([x[i], y[i], z[i]])
            pt2 = np.array([x[i+1], y[i+1], z[i+1]])
            vector = pt2 - pt1
            arrow_center = pt1 + 0.5 * vector
            arrow_x.append(arrow_center[0])
            arrow_y.append(arrow_center[1])
            arrow_z.append(arrow_center[2])
            u.append(vector[0])
            v.append(vector[1])
            w.append(vector[2])
            arrows = {
               "arrow_x": arrow_x,
               "arrow_y": arrow_y,
               "arrow_z": arrow_z,
               "u": u, "v": v, "w": w
            }
            line_data["arrows"] = arrows


      return line_data

   def _marker_color(self, num_markers, success):

      rgb = self._transmission_result[success]["rgb"]
      marker_color = f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}"
      marker_visibility = [f"{marker_color}, 1)"] + [f"{marker_color}, 0)"] * num_markers + [f"{marker_color}, 1)"]

      return marker_visibility

   def _update_external_events(self, external_df, current_time):

      transmissions, transmission_directions = [], []
      for transmission, group in external_df.groupby(["Sender_Name", "SenderPart_Name", "Receiver_Name", "ReceiverPart_Name"]):

         transmission_info, success = self._transmission_info_text(current_time, transmission, group)
         line_data = self._create_transmission_line(group)
         marker_colors = self._marker_color(len(line_data["x"])-2, success)

         transmissions.append(
            {
               "type": "scatter3d",
               "name": "external",
               "x": line_data["x"],
               "y": line_data["y"],
               "z": line_data["z"],
               "mode": "lines+markers",
               "customdata": [transmission_info] * len(line_data["x"]),
               "hovertemplate":'%{customdata}',
               "marker":
               {
                  "size": 5,
                  "color": marker_colors
               },
               "line": 
               {
                  "width": 1,
                  "color": self._transmission_result[success]["color_name"]
               },
               "opacity": 1,
               "showlegend": False
            }
         )

         if line_data.get("arrows") is not None:
            transmission_directions.append(
               {
                  "type": "cone",
                  "name": "transmission_direction",
                  "x": line_data["arrows"]["arrow_x"],
                  "y": line_data["arrows"]["arrow_y"],
                  "z": line_data["arrows"]["arrow_z"],
                  "u": line_data["arrows"]["u"],
                  "v": line_data["arrows"]["v"],
                  "w": line_data["arrows"]["w"],
                  "sizemode": "scaled",
                  "sizeref": 0.3,
                  "colorscale": [
                     [0, self._transmission_result[success]["color_name"]],
                     [1, self._transmission_result[success]["color_name"]],
                  ],
                  "showscale": False,
                  "customdata": [transmission_info] * len(line_data["arrows"]["arrow_x"]),
                  "hovertemplate":'%{customdata}',
               }
            )

      return transmissions, transmission_directions


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
         # Input("filter-memory", "data"),
         Input('radios', 'value')
      )
      def update_barplots(
         time_value, subplot_category, 
         bar_graph_category, bar_stack_category,
         filter_data, radio_val):

         print("BARPLOT")
         frame = self._current_frame

         if radio_val:
            frame = frame[frame["Timestamp"] == time_value]

         if not frame.empty:
            return self._generate_barplots(frame, subplot_category, bar_graph_category, bar_stack_category)
         else:
            return no_update


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

         print("FILTERING")
         frame = self._current_frame

         if ctx.triggered_id != "time-slider":
            self._timestamps = frame["Timestamp"].unique()

         # if len(self._timestamps) != 0:

         # empty_dataframe['zIndex'] = '-1'
         # empty_dataframe['backgroundColor'] = 'unset'

         if ctx.triggered_id != "time-slider":
            frame = frame[frame["Timestamp"] == self._timestamps[0]]
            current_time = datetime.utcfromtimestamp(self._timestamps[0]).strftime("%H:%M:%S.%f")[:-3]
         else:
            frame = frame[frame["Timestamp"] == value]
            current_time = datetime.utcfromtimestamp(value).strftime("%H:%M:%S.%f")[:-3]

         update = []
         update.append(self._earth_surface)

         internal = frame[frame["Event_Type"].isin(self._internal_messages)]
         external = frame[frame["Event_Type"].isin(self._external_messages)]
         if not external.empty:
            transmission_plots, transmission_directions = self._update_external_events(external, current_time)
            update.extend(transmission_directions)
            update.extend(transmission_plots)

         if not internal.empty:
            new_plot = self._update_internal_events(internal, current_time)
            update.append(new_plot)

         camera_view = self._set_camera_view(internal, external)
         fig = self._build_earth_figure(update, camera_view)

         if ctx.triggered_id != "time-slider" and len(self._timestamps) != 0:
            slider_marks = {}
            for val in self._timestamps:
               slider_marks[val] = '' 
            return fig, self._timestamps[0], self._timestamps[-1], self._timestamps[0], slider_marks
         else:
            return fig, no_update, no_update, no_update, no_update
      # else:
      #    empty_dataframe['zIndex'] = '2'
      #    empty_dataframe['backgroundColor'] = 'pink'
      #    return no_update, empty_dataframe, "Filters Produced Empty Dataframe.", no_update, no_update, no_update, no_update

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

         print("STORING")

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

         print("FILTER UPDATE")

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