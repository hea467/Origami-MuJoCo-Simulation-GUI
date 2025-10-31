import numpy as np
from typing import List, Tuple

def offset_colinear(polygon: List[Tuple[float, float]] ):
    if len(polygon) < 3:
        return polygon
    cleaned = [polygon[0]]
    shifted_vertices = []
    for i in range(1, len(polygon)):
        p, q, r = polygon[i - 1], polygon[i], polygon[((i + 1)%len(polygon))]
        # Calculate cross product to determine collinearity
        if (q[0] - p[0]) * (r[1] - q[1]) != (q[1] - p[1]) * (r[0] - q[0]):
            cleaned.append(q)
        else:
            cleaned.append((q[0]*0.9, (q[1]*0.9)))
            shifted_vertices.append(i)

    # cleaned.append(polygon[-1])  
    return cleaned, shifted_vertices
def is_fixed_edge(edge, fixed_edges):
    """Check if an edge is in the list of fixed edges."""
    return edge in fixed_edges or tuple(reversed(edge)) in fixed_edges
def point_in_triangle(p: Tuple[float, float], a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]) -> bool:
    """Check if point p is inside triangle abc."""
    ax, ay = a
    bx, by = b
    cx, cy = c
    px, py = p
    v0 = (cx - ax, cy - ay)
    v1 = (bx - ax, by - ay)
    v2 = (px - ax, py - ay)
    dot00 = v0[0] * v0[0] + v0[1] * v0[1]
    dot01 = v0[0] * v1[0] + v0[1] * v1[1]
    dot02 = v0[0] * v2[0] + v0[1] * v2[1]
    dot11 = v1[0] * v1[0] + v1[1] * v1[1]
    dot12 = v1[0] * v2[0] + v1[1] * v2[1]
    invDenom = 1 / (dot00 * dot11 - dot01 * dot01)
    u = (dot11 * dot02 - dot01 * dot12) * invDenom
    v = (dot00 * dot12 - dot01 * dot02) * invDenom
    return u >= 0 and v >= 0 and u + v < 1

def is_convex(polygon, a, b, c):
    # Check if the triangle abc is oriented counterclockwise
    return (polygon[b][0] - polygon[a][0]) * (polygon[c][1] - polygon[a][1]) - (polygon[b][1] - polygon[a][1]) * (polygon[c][0] - polygon[a][0]) > 0

def is_ear(polygon, a, b, c, fixed_edges):
    """Determine if the vertex b is an ear in the polygon."""
    if not is_convex(polygon, a, b, c):
        return False
    if is_fixed_edge((a, c), fixed_edges):
        return False  # Cannot clip this ear because it would break a fixed edge
    triangle = (polygon[a], polygon[b], polygon[c])
    for i, p in enumerate(polygon):
        if i not in (a, b, c) and point_in_triangle(p, *triangle):
            return False
    return True

def triangulate_polygon_with_fixed_edges(polygon, fixed_edges):
    """Triangulate the polygon while preserving fixed edges."""
    if len(polygon) < 3:
        return []
    triangles = []
    indices = list(range(len(polygon)))
    while len(indices) > 3:
        ear_found = False
        for i in range(len(indices)):
            prev, current, next = indices[i-1], indices[i], indices[(i + 1) % len(indices)]
            if is_ear(polygon, prev, current, next, fixed_edges):
                triangles.append((prev, current, next))
                indices.pop(i)
                ear_found = True
                break
        if not ear_found:
            raise ValueError("No ear found. The fixed edges may prevent further triangulation.")
    triangles.append(tuple(indices))
    return triangles

# Using the new vertices
# vertices = [(0, 0), (2, 0), (2, 1), (2, 2), (0, 2), (0, 1)]
# vertices = [(2, 0), (2, 1), (2, 2), (0, 1), (0, 2), (0, 0)]

# cleaned, changed = offset_colinear(vertices)
# fixed_edges = [(cleaned[2], cleaned[5])]
# print(cleaned)
# triangles = triangulate_polygon_with_fixed_edges(cleaned, fixed_edges)
# print("Triangles:", triangles)
