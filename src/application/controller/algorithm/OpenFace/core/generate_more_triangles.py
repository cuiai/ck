
import  numpy as np
from scipy.spatial import Delaunay

def generate_more_triangles(points_delaunay):
    """
    generate more triangles.
    """
    tri = Delaunay(np.asarray(points_delaunay))
    simplices = tri.simplices

    new_points = []
    for lines in simplices:
        pt_x = int((points_delaunay[int(lines[0])][0] + points_delaunay[int(lines[1])][0] + points_delaunay[int(lines[2])][0])/3)
        pt_y = int((points_delaunay[int(lines[0])][1] + points_delaunay[int(lines[1])][1] + points_delaunay[int(lines[2])][1])/3)
        new_points.append([pt_x, pt_y])

    points_delaunay.extend(new_points)
    return points_delaunay

def generate_point_in_triangle(x1, x2, x3, y1, y2, y3):
    """
    get a point in a triangle.
    """
    return (int((x1 + x2 + x3)/3), int((y1 + y2 + y3)/3))
