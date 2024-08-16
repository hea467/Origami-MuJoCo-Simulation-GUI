import json
import math
import triangle_mesh
from typing import Tuple

def calculate_centroid(points):
    """ Calculate the centroid from a list of (x,y) coordinates. """
    x_sum = sum(point[0] for point in points)
    y_sum = sum(point[1] for point in points)
    n = len(points)
    return (x_sum / n, y_sum / n)

def sort_points_counterclockwise(points):
    """ Sort a list of (x,y) points counterclockwise with respect to their centroid. """
    centroid = calculate_centroid(points)
    cx, cy = centroid

    def polar_angle(point):
        """ Return polar angle (in radians) from centroid for sorting. """
        x, y = point
        return math.atan2(y - cy, x - cx)

    sorted_points = sorted(points, key=polar_angle)
    return sorted_points


# 2) Process input so that we can run the triangulate algorithm, with fixed edges being the folds 

# we need the list of vertexes, the canvas, and the other ones
def find_and_order_vertices(data):
    vertices = {}
    fixed_edges =[]

    for v in (data["canvas"]).keys():
        vertices[v] = (data["canvas"][v][0], data["canvas"][v][1])
    for valley in (data["folds"]["valley"]).keys():
        fold = []
        for edge in (data["folds"]["valley"][valley]).keys():
            pos = (data["folds"]["valley"][valley][edge][0], data["folds"]["valley"][valley][edge][1])
            if edge not in vertices.keys():
                vertices[edge] = pos
            fold.append(pos)
        fixed_edges.append((fold[0], fold[1]))

    for mountain in (data["folds"]["mountain"]).keys():
        fold = []
        for edge in (data["folds"]["mountain"][mountain]).keys():
            pos = (data["folds"]["mountain"][mountain][edge][0], data["folds"]["mountain"][mountain][edge][1])
            if edge not in vertices.keys():
                vertices[edge] = pos
            fold.append(pos)
        fixed_edges.append((fold[0], fold[1]))
    return vertices, fixed_edges


def add_v_prefix(nums):
    # Convert each integer to string with 'v' prefixed and join with ' '
    result = " ".join(f"v{num}" for num in nums)
    return result

def vertex_to_index(polygon_vertices: list, triangle): 
    new = []
    for v_inx in triangle:
        p_indx = polygon_vertices.index(v_inx)
        new.append(p_indx)
    return new

def create_bodies(vertices_to_pos_dict, bodies_dict):
    '''For each body, we can divide it into a triangular mesh, store it in the body dictionary format
    After iterating through all the bodies, we should have divided up all the '''
    bodies = {}
    body_count = 1
    for body in bodies_dict.keys():
        vertices_in_body = bodies_dict[body] #["v1, v2, v3, v4, v5, v6"]
        vertices_positions = [] #[(0, 0), (0, 1), ....]
        for vertex in vertices_in_body:
            vertices_positions.append(vertices_to_pos_dict[vertex])
        sorted_vertices = sort_points_counterclockwise(vertices_positions) #[(2, 0), (0, 1), ....]
        cleaned, changed = triangle_mesh.offset_colinear(sorted_vertices) 
        output_connections = triangle_mesh.triangulate_polygon_with_fixed_edges(cleaned,fixed_edges=[]) #[(0,1 2), (2, 3 4), ...]
        output_connections_with_unsorted_vertices = []
        for triangle in output_connections:
            (v1_indx, v2_indx, v3_indx) = triangle 
            v1_coor = sorted_vertices[v1_indx]
            v2_coor = sorted_vertices[v2_indx]
            v3_coor = sorted_vertices[v3_indx]
            ori_unsorted_v1_inx = vertices_positions.index(v1_coor)
            ori_unsorted_v2_inx = vertices_positions.index(v2_coor)
            ori_unsorted_v3_inx = vertices_positions.index(v3_coor)
            output_connections_with_unsorted_vertices.append([ori_unsorted_v1_inx , ori_unsorted_v2_inx, ori_unsorted_v3_inx])
        string_of_body_vertices = " ".join(vertices_in_body)
        bodies[f"body{body_count}"] = {string_of_body_vertices: output_connections_with_unsorted_vertices}
        body_count += 1
    return bodies 
        


if __name__ == '__main__':
    # 1) get the input from the json file 
    # Opening JSON file
    f = open('design.json')
    data = json.load(f)
    # 2) Process input so that we can run the triangulate algorithm, with fixed edges being the folds 
    vertices, fixed_edges = find_and_order_vertices(data)
    bodies = create_bodies(vertices, data["bodies"])
    print(bodies)
    f.close()
    