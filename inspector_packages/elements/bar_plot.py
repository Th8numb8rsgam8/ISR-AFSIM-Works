from inspector_packages import *
from plotly.subplots import make_subplots

class BarPlot:

   @staticmethod
   def generate_barplots(frame, subplot_category, bar_graph_category, bar_stack_category):
            
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

      fig.update_layout(
         barmode='stack', 
         paper_bgcolor='rgba(0,0,0,0)', 
         plot_bgcolor='rgba(0,0,0,0)',
         showlegend=False)

      return fig