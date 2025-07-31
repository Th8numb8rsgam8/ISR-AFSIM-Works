import dash_bootstrap_components as dbc
from dash import dcc, html, Dash


class DashLayout:

   def __init__(self, df, timestamps, classification, network_plot_name):

      self._df = df
      self._timestamps = timestamps
      self._classification = classification
      self._network_plot_name = network_plot_name

      self._app = Dash(
         title="AFSIM Communications Inspector",
         external_stylesheets=[
            '/static/styles.css',
            '/static/bootstrap.min.css'
         ]
      )

      self._set_dash_layout()


   def get_app(self):

      return self._app


   def initialize_barplot(self):

      barplot = dcc.Graph(
         id='bar-graph', 
         config={"scrollZoom": False}, 
         style={'height': '200vh'}
      )

      return barplot


   def initialize_barplot_options(self):

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

      barplot_dropdowns = dbc.AccordionItem([
         self._create_dropdown("Subplot Category", "subplot-category", subplot_options, False, None, "Event_Type", False),
         self._create_dropdown("Bar Graph Category", "bar-graph-category", subplot_options, False, None, "Sender_Name", False),
         self._create_dropdown("Bar Stack Category", 'bar-stack-category', subplot_options, False, None, "Receiver_Name", False)
      ], title="Bar Charts Options")

      return barplot_dropdowns


   def initialize_network_plot(self):

      network_plot = dcc.Graph(
         id=self._network_plot_name, 
         config={"scrollZoom": True}, 
         style={"height": "80vh"})

      return network_plot


   def initialize_network_options(self):

      network_options = ["Spring", "Circular", "Shell", "Spectral", "Random", "Kamada Kawai", "Multipartite"]

      network_dropdowns = dbc.AccordionItem([
         self._create_dropdown("Network Layout", "network-layout", network_options, False, None, "Spring", False),
      ], title="Network Options")

      return network_dropdowns


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
               self._create_dropdown("Plots", "plot-options", ["Bar Plot", "Network Plot"], False, False, "Bar Plot", False),
               self._create_plots_area(),
               self._create_time_label(),
               self._create_button_group()
            ], width=6)
      ])

      return displayed_data


   def _create_options_row(self):

      options_row = dbc.Row(
         id="options-row",
         style={
            'position': 'relative',
            'textAlign': 'center',
            'zIndex': '5'
         },
         children=[
            dbc.Col(self._create_filter_options(), width=6),
            dbc.Col(self._create_plot_filters(), width=6),
         ]
      )

      return options_row


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


   def _create_globe_visual(self):

      graph = dcc.Graph(
         id='my-graph', 
         config={"scrollZoom": True}, 
         style={'height': '80vh'})

      return graph


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


   def _create_plots_area(self):

      bar_plots = dcc.Loading(
         children=[html.Div(
            id='plots-area',
            style={
               'overflowY': 'scroll',
               'height': '80vh'
            },
         )],
         target_components={
            "bar-graph": "figure",
            self._network_plot_name: "figure"},
         type="graph"
      )
         
      return bar_plots


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


   def _create_plot_filters(self):

      subplot_filters = dbc.Accordion(id="plot-filters", start_collapsed=True)

      return subplot_filters 

   
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