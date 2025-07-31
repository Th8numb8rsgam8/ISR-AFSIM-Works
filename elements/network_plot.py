import sys
import networkx as nx
import plotly.graph_objects as go

class NetworkPlot:

   def __init__(self):

      self._figure_name = "network-graph"

      self._edge_width = [
         {"range": [1, 10], "width": 0.5},
         {"range": [10, 20], "width": 1},
         {"range": [20, 30], "width": 1.5},
         {"range": [30, 40], "width": 2},
         {"range": [40, 50], "width": 2.5},
         {"range": [50, 60], "width": 3},
         {"range": [60, 70], "width": 3.5},
         {"range": [70, 80], "width": 4},
         {"range": [80, 90], "width": 4.5},
         {"range": [90, sys.maxsize], "width": 5},
      ]


   @property
   def figure_name(self):

      return self._figure_name


   def generate_network_figure(self, frame, network_layout, empty_plot):

      node_positions = self._get_network_layout(frame, network_layout)

      node_x, node_y, node_text, nodes_visited = {}, {}, {}, []
      edge_width = []
      nodes_traces, edge_traces, directions = [], [], []
      for transmission, group in frame.groupby(["Sender_Name", "Receiver_Name"]):

         sender, receiver = transmission[0], transmission[1]
         sender_type = group["Sender_Type"].iloc[0]
         receiver_type = group["Receiver_Type"].iloc[0]

         self._set_node_info(node_x, node_y, node_text, node_positions, nodes_visited, sender, sender_type)
         self._set_node_info(node_x, node_y, node_text, node_positions, nodes_visited, receiver, receiver_type)

         edge_width = self._get_edge_width(group.shape[0])

         edge_traces.append(self._add_edge(node_positions[sender], node_positions[receiver], edge_width))

         arrow_text = [f"{group.shape[0]}" + "<extra></extra>", f"{group.shape[0]}" + "<extra></extra>"]
         directions.append(self._add_direction(node_positions[sender], node_positions[receiver], arrow_text))

      for platform_type in node_x:
         nodes_traces.append(self._add_node(
            node_x[platform_type], 
            node_y[platform_type], 
            platform_type, 
            node_text[platform_type]))

      fig =  go.Figure({"data": nodes_traces + edge_traces + directions, "layout": empty_plot})

      return fig
         

   def _get_network_layout(self, frame, network_layout):

      transmissions = frame[["Sender_Name", "Receiver_Name"]].drop_duplicates()
      edges = [(row[0], row[1]) for _, row in transmissions.iterrows()]
      G = nx.Graph()
      G.add_edges_from(edges)

      if network_layout == "Spring":
         node_positions = nx.spring_layout(G)
      elif network_layout == "Circular":
         node_positions = nx.circular_layout(G)
      elif network_layout == "Shell":
         node_positions = nx.shell_layout(G)
      elif network_layout == "Spectral":
         node_positions = nx.spectral_layout(G)
      elif network_layout == "Random":
         node_positions = nx.random_layout(G)

      return node_positions


   def _get_edge_width(self, num):

      edge_width = 1
      for rng_step in self._edge_width:
         min_rng, max_rng = rng_step["range"]
         if min_rng < num <= max_rng:
            edge_width = rng_step["width"]
            break

      return edge_width


   def _add_edge(self, start, end, edge_width):

      edge = {
         "type": "scatter",
         "name": "edge",
         "x": [start[0], end[0]],
         "y": [start[1], end[1]],
         "mode": "lines",
         "hoverinfo": "none",
         "zorder": 1,
         "line": 
         {
            "width": edge_width,
            "color": "black"
         },
         "showlegend": False
      }

      return edge

   
   def _add_direction(self, start, end, text):

      arrow_start = start + 0.25 * (end - start)
      arrow_end = start + 0.75 * (end - start)

      direction = {
         "type": "scatter",
         "name": "network",
         "x": [arrow_start[0], arrow_end[0]], 
         "y": [arrow_start[1], arrow_end[1]],
         "mode": "markers",
         "zorder": 1,
         "customdata": text,
         "hovertemplate":'%{customdata}',
         "marker":
         {
            "size": 15,
            "color": "black",
            "symbol": "arrow-up",
            "angleref": "previous"
         },
         "showlegend": False
      }

      return direction


   def _add_node(self, x, y, node_type, text):

      node = {
         "type": "scatter",
         "name": node_type,
         "x": x,
         "y": y,
         "mode": "markers",
         "zorder": 2,
         "customdata": text,
         "hovertemplate":'%{customdata}',
         "marker":
         {
            "size": 20,
         },
      }

      return node

   
   def _set_node_info(self, node_x, node_y, node_text, node_positions, nodes_visited, node_name, node_type):

      if node_name not in nodes_visited:
         if node_type not in node_x:
            node_x[node_type] = []
            node_y[node_type] = []
            node_text[node_type] = []
         pos = node_positions[node_name]
         node_x[node_type].append(pos[0])
         node_y[node_type].append(pos[1])
         node_text[node_type].append(f"{node_name}" + "<extra></extra>")
         nodes_visited.append(node_name)