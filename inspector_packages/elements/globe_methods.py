import numpy as np

class GlobeMethods:

   EQUATOR_RADIUS = 6.378 * 10**6
   POLAR_RADIUS = 6.357 * 10**6

   @staticmethod
   def get_curve_points_on_sphere(point1, point2, num_points=50):
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


   @staticmethod
   def get_points_on_line_segment(point1, point2, num_points=50):

      x, y, z = [], [], []
      for i in range(num_points+1):
         t = i / num_points
         new_point = (1 - t) * point1 + t * point2
         x.append(new_point[0])
         y.append(new_point[1])
         z.append(new_point[2])

      return x, y, z


   @staticmethod
   def los_hits_horizon(sender_location, receiver_location):

      diff = receiver_location - sender_location
      t = -(sender_location * diff).sum() / (diff ** 2).sum()

      if 0 < t < 1:
         closest_point = sender_location + t * diff
         return np.linalg.norm(closest_point) <= GlobeMethods.EQUATOR_RADIUS
      else:
         return False