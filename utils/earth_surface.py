import sys, os
import time
import numpy as np
import pandas as pd
from PIL import Image
import multiprocessing as mp
import plotly.graph_objects as go
from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt


def degree2radians(degree):
    #convert degrees to radians
    return degree*np.pi/180

def mapping_map_to_sphere(lon, lat, radius=1):
    #this function maps the points of coords (lon, lat) to points onto the  sphere of radius radius
    
    lon=np.array(lon, dtype=np.float64)
    lat=np.array(lat, dtype=np.float64)
    lon=degree2radians(lon)
    lat=degree2radians(lat)
    xs=radius*np.cos(lon)*np.cos(lat)
    ys=radius*np.sin(lon)*np.cos(lat)
    zs=radius*np.sin(lat)
    return xs, ys, zs


# Make shortcut to Basemap object, 
# not specifying projection type for this example
m = Basemap() 


# Functions converting coastline/country polygons to lon/lat traces
def polygons_to_traces(poly_paths, N_poly):
    ''' 
    pos arg 1. (poly_paths): paths to polygons
    pos arg 2. (N_poly): number of polygon to convert
    '''
    # init. plotting list
    lons=[]
    lats=[]

    for i_poly in range(N_poly):
        poly_path = poly_paths[i_poly]
        
        # get the Basemap coordinates of each segment
        coords_cc = np.array(
            [(vertex[0],vertex[1]) 
             for (vertex,code) in poly_path.iter_segments(simplify=False)]
        )
        
        # convert coordinates to lon/lat by 'inverting' the Basemap projection
        lon_cc, lat_cc = m(coords_cc[:,0],coords_cc[:,1], inverse=True)
    
        
        lats.extend(lat_cc.tolist()+[None]) 
        lons.extend(lon_cc.tolist()+[None])
        
    return lons, lats

# Function generating coastline lon/lat 
def get_coastline_traces():
    poly_paths = m.drawcoastlines().get_paths() # coastline polygon paths
    N_poly = 91  # use only the 91st biggest coastlines (i.e. no rivers)
    cc_lons, cc_lats= polygons_to_traces(poly_paths, N_poly)
    return cc_lons, cc_lats

# Function generating country lon/lat 
def get_country_traces():
    poly_paths = m.drawcountries().get_paths() # country polygon paths
    N_poly = len(poly_paths)  # use all countries
    country_lons, country_lats = polygons_to_traces(poly_paths, N_poly)
    return country_lons, country_lats


# Get list of of coastline, country, and state lon/lat 

# cc_lons, cc_lats = get_coastline_traces()
# country_lons, country_lats = get_country_traces()

#concatenate the lon/lat for coastlines and country boundaries:
# lons = cc_lons # +[None]+country_lons
# lats = cc_lats # +[None]+country_lats

# xs, ys, zs = mapping_map_to_sphere(lons, lats, radius=1.01)

# boundaries={
#    'type':'scatter3d',
#    'x':xs,
#    'y':ys,
#    'z':zs,
#    'mode':'lines',
#    'line':
#    {
#       'color':'black', 
#       'width':1
#    }
# }

def generate_colors_array(colorscale_resolution):

   if not (255 / colorscale_resolution).is_integer():
      print("Colorscale resoution does not produce whole numbers.")
      sys.exit(1)

   n = 0
   num_colors = int(255 / colorscale_resolution + 1) ** 3
   norm_scale = np.linspace(0, 1, num_colors)
   colors_array = np.zeros((num_colors, 3), dtype=np.int16)
   for i in range(0, 256, colorscale_resolution):
      for j in range(0, 256, colorscale_resolution):
         for k in range(0, 256, colorscale_resolution):
            colors_array[n, :] = np.array([i, j, k])
            n += 1

   return norm_scale, colors_array


def generate_color_scale(norm_scale, colors_array):

   colorscale = []
   for scale, color in zip(norm_scale, colors_array):

      colorscale.append([
         scale,
         f'rgb({color[0]},{color[1]},{color[2]})'
      ])
   
   return colorscale


def encode_image(image, colors_array, norm_scale):

   encoded_img = np.zeros((image.shape[1], image.shape[2]))
   for i in range(image.shape[1]):
      for j in range(image.shape[2]):
         diff = colors_array - image[:,i,j]
         diff_magnitude = np.linalg.norm(diff, axis=1)
         min_idx = np.where(diff_magnitude == diff_magnitude.min())
         encoded_pixel = norm_scale[min_idx[0][0]]
         encoded_img[i,j] = encoded_pixel
      
      print(f'Row {i}')
   
   return encoded_img


def fitting_colors(image, first_color, second_color, increments):

   colors_array = np.zeros((increments, 3), dtype=np.int16)
   r1, g1, b1 = first_color
   r2, g2, b2 = second_color
   for i in range(increments):
      factor = i / increments
      r = int(r1 + (r2 - r1) * factor)
      g = int(g1 + (g2 - g1) * factor)
      b = int(b1 + (b2 - b1) * factor)
      colors_array[i,:] = np.array([r, g, b])

   fittest_colors = {"colors": [], "diffs": []}
   for i in range(image.shape[1]):
      for j in range(image.shape[2]):
         diff = colors_array - image[:,i,j]
         diff_magnitude = np.linalg.norm(diff, axis=1)
         min_diff = diff_magnitude.min()
         min_idx = np.where(diff_magnitude == min_diff)
         if min_diff <= 10:
            fittest_colors["colors"].append(min_idx[0][0])
            fittest_colors["diffs"].append(min_diff)
   
   df = pd.DataFrame(fittest_colors)
   df.hist(layout=(1, 2), figsize=(10, 5))
   plt.tight_layout()
   plt.show()

   pdb.set_trace()


# kernel_size = 10
colorscale_resolution = 17 

small = (270, 540)
medium = (540, 1080)
large = (1080, 2160)
blue_marble = np.asarray(Image.open('earth_data\\world.jpg').resize(small, Image.LANCZOS)).T

# blue_marble = np.asarray(Image.open('world.jpg')).T
# norm_scale, colors_array = generate_colors_array(colorscale_resolution)

colors_array = np.array(
   [
      [27, 69, 127],
      [40, 67, 121], # blue
      [35, 63, 119], 
      [30, 59, 117], 
      [27, 56, 111],
      [25, 54, 105],
      [23, 51, 100],
      [21, 49, 94], 
      [19, 46, 89], 
      [16, 44, 83], 
      [14, 41, 77], 
      [12, 39, 72], 
      [10, 36, 66], 
      [8, 34, 61], # navy blue
      [7, 30, 54],
      [6, 27, 48],
      [5, 23, 42],
      [2, 10, 18], # darkest blue
      [18, 27, 8], # darkest green
      [24, 41, 9],
      [23, 34, 10],
      [27, 40, 12],
      [32, 47, 14],
      [36, 54, 16],
      [39, 54, 19],
      [41, 61, 18],
      [46, 68, 21], # darker green
      [49, 70, 24],
      [51, 71, 25],
      [53, 72, 27],
      [55, 73, 28],
      [56, 74, 30],
      [58, 75, 31],
      [60, 76, 33],
      [62, 77, 34],
      [64, 79, 36],
      [66, 82, 34],
      [70, 83, 36],
      [74, 84, 38],
      [78, 85, 41],
      [82, 86, 43], # dark green
      [115, 93, 64],
      [118, 97, 66],
      [120, 99, 67],
      [130, 107, 72],
      [137, 112, 79],
      [143, 116, 87],
      [150, 123, 84],
      [151, 117, 82],
      [153, 129, 97],
      [158, 135, 105],
      [166, 149, 115],
      [166, 137, 105],
      [181, 138, 98],
      [190, 147, 101], # very light red
      [194, 152, 107],
      [196, 151, 104],
      [198, 154, 110],
      [189, 159, 117],
      [183, 158, 120],
      [187, 162, 125],
      [199, 165, 121],
      [208, 176, 131],
      [201, 174, 132],
      [203, 177, 132],
      [202, 175, 133],
      [202, 178, 138],
      [206, 179, 134],
      [212, 185, 141],
      [174, 175, 166],
      [252, 252, 252]
   ]
)

# fitting_colors(blue_marble, colors_array[58], colors_array[59], 10)
# 
# pdb.set_trace()

norm_scale = np.linspace(0, 1, colors_array.shape[0])

# encoded_img = np.load("earth_surface.npy")
start_time = time.time()
encoded_img = encode_image(blue_marble, colors_array, norm_scale)
end_time = time.time()
elapsed_time = end_time - start_time

# pdb.set_trace()

radius = 6.378 * 10**6
theta = np.linspace(0, 2 * np.pi, blue_marble.shape[1])
phi = np.linspace(0, np.pi, blue_marble.shape[2])

x = radius * np.outer(np.cos(theta), np.sin(phi))
y = radius * np.outer(np.sin(theta), np.sin(phi))
z = radius * np.outer(np.ones(np.size(theta)), np.cos(phi))

colorscale = generate_color_scale(norm_scale, colors_array)

surface={
   "type": "surface",
   "x": x,
   "y": y,
   "z": z,
   "surfacecolor": encoded_img,
   "colorscale": colorscale,
   "hoverinfo": "none",
   "showscale": False,
}


noaxis=dict(showbackground=False,
            showgrid=False,
            showline=False,
            showticklabels=False,
            ticks='',
            title='',
            zeroline=False)

layout3d=dict(title='Outgoing Longwave Radiation Anomalies<br>Dec 2017-Jan 2018',
              font=dict(family='Balto', size=14),
              width=800, 
              height=800,
              scene=dict(xaxis=noaxis, 
                         yaxis=noaxis, 
                         zaxis=noaxis,
                         aspectratio=dict(x=1,
                                          y=1,
                                          z=1),
                         # camera=dict(eye=dict(x=1.15, 
                         #             y=1.15, 
                         #             z=1.15)
                         #            )
            ),
            paper_bgcolor='rgba(235,235,235, 0.9)'  
           )
             
fig = go.Figure(data=[surface], layout=layout3d)
fig.show()

# if __name__ == "__main__":

   # start_time = time.time()
   # results = []
   # with mp.Pool(processes=os.cpu_count()) as pool:
   #    manager = mp.Manager().list()
   #    for i in range(reduced_img.shape[1]):
   #       for j in range(reduced_img.shape[2]):
   #          result = pool.apply_async(
   #             func=encode_pixel, 
   #             args=(reduced_img[:, i, j], colors_array, norm_scale)
   #          )
   #          results.append(result)
   #    
   # while not all(map(lambda x: x.ready(), results)):
   #    pass

   # for idx, result in enumerate(results):
   #    row, col = divmod(idx, reduced_img.shape[2])
   #    encoded_img[row, col] = result.get()

   # end_time = time.time()
   # elapsed_time1 = end_time - start_time
