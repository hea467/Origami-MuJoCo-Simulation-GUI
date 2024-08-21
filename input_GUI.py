import pygame
import sys
import math
import json

# Initialize Pygame
pygame.init()

# Constants for the display
WIDTH, HEIGHT = 800, 600
BACKGROUND_COLOR = (255, 255, 255)
VERTEX_COLOR = (0, 0, 255)
LINE_COLOR_CHOICES = [(0, 0, 255), (255, 0, 0), (255, 255, 0)]
VERTEX_RADIUS = 20
LINE_WIDTH = 3

JOINT_TYPES = ['X Linear', 'Y Linear', 'Z Linear', 'X Rotational', 'Y Rotational', 'Z Rotational', 'X-pos Actuator', 'Y-pos Actuator', 'Z-pos Actuator', 'Grounded']
BAR_WIDTH = 200
BAR_HEIGHT = 30 * len(JOINT_TYPES)
BAR_POSITION = (WIDTH - BAR_WIDTH - 10, 10)  # 10 pixels from the top right corner

# Set up the display
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Vertex Connector")

graph = {}
mountain_folds = []
valley_folds = []

faces = []
faces_to_draw = []
joints = {}
actuators = {}
grounds = {}

def draw_vertices():
    ''' Draws all the vertices on the GUI with the assigned color and radius. 
    Also draws indicators for acitive joints. '''
    for vertex in graph.keys():
        pygame.draw.circle(screen, VERTEX_COLOR, vertex, VERTEX_RADIUS)
        if vertex in joints:
            for i, is_active in enumerate(joints[vertex]):
                if is_active:
                    indicator_pos = (vertex[0] + 15 * math.cos(i * math.pi / 3),
                                     vertex[1] + 15 * math.sin(i * math.pi / 3))
                    pygame.draw.circle(screen, (255, 0, 0), indicator_pos, 3)
        if vertex in actuators:
            for i, is_active in enumerate(actuators[vertex]):
                if is_active:
                    indicator_pos = (vertex[0] + 20 * math.cos((i + 6) * math.pi / 3),
                                     vertex[1] + 20 * math.sin((i + 6) * math.pi / 3))
                    pygame.draw.circle(screen, (0, 255, 0), indicator_pos, 3)

def draw_lines():
    ''' Draws the edges between vertices. Some edges represents a boundary edge, if it is blue. 
    Mountain folds are red and valley folds are yellow. '''
    for vertex in graph.keys():
        for neighbour in graph[vertex]:   
            pygame.draw.line(screen, LINE_COLOR_CHOICES[neighbour[1]], neighbour[0], vertex, LINE_WIDTH)

def draw_faces():
    ''' Draws all the selected faces on the GUI canvas. '''
    color = [173, 216, 50]
    for face in faces_to_draw:
        sorted_face =  sort_points_counterclockwise(face)
        pygame.draw.polygon(screen, (color[0], color[1], color[2]) , sorted_face)  # Draw face outlines in light gray
        color[2] += 20
        color[2] = color[2] % 255

def draw_joint_properties(vertex, properties):
    ''' Draws whether certain joints have been selected. '''
    x, y = vertex
    for i, prop in enumerate(properties):
        if prop:
            # Draw an indicator for this property
            # This is a simple example; you might want to create more sophisticated graphics
            color = (255, 0, 0) if i < 3 else (0, 255, 0)  # Red for linear, Green for rotational
            pygame.draw.circle(screen, color, (x + (i-3)*10, y + (i//3)*10), 3)
            
def draw_joint_selection_bar():
    ''' If the key J is clicked, this shows a display bar that allows user to input joint information'''
    pygame.draw.rect(screen, (200, 200, 200), (*BAR_POSITION, BAR_WIDTH, BAR_HEIGHT))
    for i, joint_type in enumerate(JOINT_TYPES):
        button_rect = (BAR_POSITION[0], BAR_POSITION[1] + i * 30, BAR_WIDTH, 25)
        pygame.draw.rect(screen, (150, 150, 150), button_rect)
        font = pygame.font.Font(None, 24)
        text = font.render(joint_type, True, (0, 0, 0))
        screen.blit(text, (button_rect[0] + 5, button_rect[1] + 5))

def find_vertex(pos):
    ''' From the position of a click, determine whether the user is trying to click on a vertex. '''
    for vertex in graph.keys():
        if math.sqrt((vertex[0] - pos[0]) ** 2 + (vertex[1] - pos[1]) ** 2) <= VERTEX_RADIUS:
            return vertex
    return None

def find_is_there_nearby_vertex(pos):
    ''' Match the position of a click to see if it is position is close to any of the exitsting vertices. '''
    for vertex in graph.keys():
        if math.sqrt((vertex[0] - pos[0]) ** 2 + (vertex[1] - pos[1]) ** 2) <= 30:
            return True
    return False

def point_line_distance(px, py, x1, y1, x2, y2):
    ''' Calculates the distance from between a pint and the center of the line. '''
    line_mag = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    if line_mag < 0.000001:
        return math.sqrt((px - x1) ** 2 + (py - y1) ** 2)

    u = ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / (line_mag ** 2)
    closest_x = x1 + u * (x2 - x1)
    closest_y = y1 + u * (y2 - y1)

    if u < 0:
        closest_x = x1
        closest_y = y1
    elif u > 1:
        closest_x = x2
        closest_y = y2

    return math.sqrt((px - closest_x) ** 2 + (py - closest_y) ** 2)

def find_line(pos, graph, threshold=10):
    ''' Finds a line. '''
    px, py = pos
    for vertex in graph.keys():
        x1, y1 = vertex
        for neighbour in graph[vertex]:
            x2, y2 = neighbour[0][0], neighbour[0][1]
            if point_line_distance(px, py, x1, y1, x2, y2) <= threshold:
                if not (math.sqrt((x1 - px) ** 2 + (y1 - py) ** 2) <= VERTEX_RADIUS or
                        math.sqrt((x2 - px) ** 2 + (y2 - py) ** 2) <= VERTEX_RADIUS):
                    neighbour[1] = (neighbour[1] + 1) % len(LINE_COLOR_CHOICES)
                    for n in graph[neighbour[0]]:
                        if n[0] == vertex:
                            n[1]= neighbour[1]
                    find_folds(graph)
                    return neighbour[0], vertex
    return False

def delete_vertex(vertex):
    ''' Deletes a vertex. '''
    global graph
    for neighbor in graph[vertex]:
        for next_neigh in graph[neighbor[0]]: 
            if next_neigh[0] == vertex:
                graph[neighbor[0]].remove(next_neigh)
    if vertex in graph.keys():
        del graph[vertex]
        
def delete_line(line):
    ''' Deletes a line. Somehow doesn't work very well yet.
      My guess is that there is an issue abt where it is called. '''
    global graph 
    v1, v2 = line
    for lines1 in graph[v1]:
        if lines1 == v2 :
            graph[v1].remove(lines1)
    for lines2 in graph[v2]:
        if lines2 == v1:
            graph[v2].remove(lines2)

def align_vertex(pos):
    ''' Aligns a new vertex with existing vertices. '''
    vertices = graph.keys()
    if not graph.keys():
        return pos
    closest_x = min(vertices, key=lambda v: abs(v[0] - pos[0]))[0]
    closest_y = min(vertices, key=lambda v: abs(v[1] - pos[1]))[1]
    xpos = pos[0] 
    ypos = pos[1]
    if abs(closest_x - pos[0]) < 30: 
        xpos = closest_x
    if abs(closest_y - pos[1]) < 30:
        ypos = closest_y
    return (xpos, ypos)

def find_folds(graph):
    ''' Changes the status of an edge, rotating between a mountain, valley and boundary edge. '''
    global mountain_folds, valley_folds, faces, faces_to_draw
    mountain_folds = []
    valley_folds = []
    faces = []
    faces_to_draw = []
    for v in graph.keys():
        for neighbor in graph[v]:
            if neighbor[1] == 1:
                if (neighbor[0], v) not in mountain_folds:
                    mountain_folds.append((v, neighbor[0]))
            if neighbor[1] == 2: 
                if (neighbor[0], v) not in valley_folds:
                    valley_folds.append((v, neighbor[0]))
    detect_faces(graph, mountain_folds, valley_folds)

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


def find_all_paths(graph, start, end, path=[]):
    ''' Finds all paths from start to end on a graph. Used in face detection. '''
    path = path + [start]
    if start == end:
        return [path]
    if start not in graph:
        return []
    paths = []
    for neighbor in graph[start]:
        if neighbor[0] not in path:  # Only consider normal edges: and neighbor[1] == 0
            new_paths = find_all_paths(graph, neighbor[0], end, path)
            for new_path in new_paths:
                # for path in paths: 
                #     if len(new_path) < len(path) and len(new_path) > 2: 
                #         paths.remove(path)
                # if len(new_path) > 2: 
                    paths.append(new_path)
    # filtered_paths = filter_shortest_lists(paths)
    return paths

def detect_faces(graph, mountain_folds, valley_folds):
    ''' When the user clicks on a fold from vertex X and vertex Y, 
    we detect faces by finding all possible paths on the graph from X to Y. We count every path >= 3 as a face. '''
    global faces
    faces = []
    repition_track = []
    folds = mountain_folds + valley_folds
    for fold in folds:
        start, end = fold
        paths = find_all_paths(graph, start, end)
        # print("paths", paths)
        for path in paths:
            if len(path) >= 3:  # A face should have at least 3 vertices
                f = list(sorted(path))  # Sort to avoid duplicates due to different starting points
                if f not in repition_track:
                    faces.append(path)
                    repition_track.append(f)
        # print("faces", faces)


def is_point_in_polygon(x, y, polygon):
    ''' Detect whether a location (x, y) is inside a given polygon. '''
    num = len(polygon)
    j = num - 1
    odd_nodes = False
    for i in range(num):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if yi < y and yj >= y or yj < y and yi >= y:
            if xi + (y - yi) / (yj - yi) * (xj - xi) < x:
                odd_nodes = not odd_nodes
        j = i
    return odd_nodes

def find_polygon(click_pos, faces):
    ''' Sorts the faces by size. Check whether we clicked inside any of the 
    faces by starting with the smallest face. '''
    px, py = click_pos
    sorted_list = sorted(faces, key=len)
    for polygon in sorted_list:
        if is_point_in_polygon(px, py, polygon):
            return polygon
    return None

def toggle_joint_property(vertex, property_index):
    ''' Keeps track of which joint property is active for the vertex the function is called on. '''
    if vertex not in joints:
        joints[vertex] = [False] * 6
    if vertex not in actuators:
        actuators[vertex] = [False] * 3
    if vertex not in grounds: 
        grounds[vertex] = False
    if property_index < 6:
        joints[vertex][property_index] = not joints[vertex][property_index]
    elif property_index >= 6 and property_index < 9:
        actuator_index = property_index - 6
        actuators[vertex][actuator_index] = not actuators[vertex][actuator_index]
    else: 
        grounds[vertex] = not grounds[vertex]

def save_to_json(graph, mountain_folds, valley_folds, faces_to_draw, grounds):
    ''' When the user hits the ENTER key, this function collects all the information 
    into a Json file in a format create.py is able to parse and output to an XML file. '''
    data = {"canvas": {}, 
            "folds": {"mountain": {}, "valley": {}}, 
            "closed_loop": False, 
            "grounded_vertices": [], 
            "joints": {}, 
            "actuators": [], 
            "bodies":{} }
    
    for vertex, joint_properties in joints.items():
        v_key = f"v{list(graph.keys()).index(vertex) + 1}"
        data["joints"][v_key] = joint_properties
    
    # Collect vertices
    for idx, vertex in enumerate(graph.keys(), start=1):
        v_key = f"v{idx}"
        scaled_vertex = [coord / 100.0 for coord in vertex]
        data["canvas"][v_key] = scaled_vertex
    
    # Collect actuators
    for vertex, actuator_properties in actuators.items():
        v_key = f"v{list(graph.keys()).index(vertex) + 1}"
        if actuator_properties[0]:
            data["actuators"].append([v_key, 0])
        if actuator_properties[1]:
            data["actuators"].append([v_key, 1])
        if actuator_properties[2]:
            data["actuators"].append([v_key, 2])

    # Collect folds
    for idx, fold in enumerate(mountain_folds, start=1):
        f_key = f"mountain{idx}"
        v1_key = f"v{list(graph.keys()).index(fold[0]) + 1}"
        v2_key = f"v{list(graph.keys()).index(fold[1]) + 1}"
        scaled_fold = [[coord / 100.0 for coord in fold[0]], [coord / 1000.0 for coord in fold[1]]]
        data["folds"]["mountain"][f_key] = {
            v1_key: scaled_fold[0],
            v2_key: scaled_fold[1]
        }

    for idx, fold in enumerate(valley_folds, start=1):
        f_key = f"valley{idx}"
        v1_key = f"v{list(graph.keys()).index(fold[0]) + 1}"
        v2_key = f"v{list(graph.keys()).index(fold[1]) + 1}"
        scaled_fold = [[coord / 100.0 for coord in fold[0]], [coord / 1000.0 for coord in fold[1]]]
        data["folds"]["valley"][f_key] = {
            v1_key: scaled_fold[0],
            v2_key: scaled_fold[1]
        }
        
    # Collect bodies 
    if not faces_to_draw: 
        face_str=[]
        for idx, vertex in enumerate(list(graph.keys()), start = 1):
            v_key = f"v{idx}"
            face_str.append(v_key)
        data["bodies"]["body1"] = face_str
    else:
        for idx, face in enumerate(faces_to_draw, start= 1):
            face_str = []
            for vertex in face:
                v_key = f"v{list(graph.keys()).index(vertex) + 1}"
                face_str.append(v_key)
            data["bodies"][f"body{idx}"] = face_str
            
    # Collect Grounds 
    for vertex, ground in grounds.items():
        if ground: 
            data["grounded_vertices"].append(f"v{list(graph.keys()).index(vertex) + 1}")

    with open("./designs/design.json", "w") as json_file:
        json.dump(data, json_file, indent=4)
        print(f"Design saved to design.json at {json_file}")

def get_clicked_joint_type(click_pos):
    if BAR_POSITION[0] <= click_pos[0] <= BAR_POSITION[0] + BAR_WIDTH:
        for i in range(len(JOINT_TYPES)):
            if BAR_POSITION[1] + i * 30 <= click_pos[1] <= BAR_POSITION[1] + (i + 1) * 30:
                return i
    return None

# Main loop
running = True
selected_vertex = None

joint_edit_mode = False

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_j:
                joint_edit_mode = not joint_edit_mode
                print("Edit mode turned on")
            if event.key == pygame.K_RETURN:
                save_to_json(graph, mountain_folds, valley_folds, faces_to_draw, grounds)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            click_pos = event.pos
            if joint_edit_mode:
                if selected_vertex:
                    property_index = get_clicked_joint_type(click_pos)
                    if property_index is not None:
                        toggle_joint_property(selected_vertex, property_index)
                        # print("JOINTS: ", joints)
                        # print("ACTUATORS: ", actuators)
                        # print("GROUNDS", grounds)
            else:

                clicked_vertex = find_vertex(event.pos)
                clicked_line = find_line(event.pos, graph)
                
                if not clicked_line:
                    if clicked_vertex:
                        if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                            delete_vertex(clicked_vertex)
                        elif selected_vertex:
                            graph[selected_vertex].append([clicked_vertex, 0])
                            graph[clicked_vertex].append([selected_vertex, 0])
                            selected_vertex = None
                        else:
                            selected_vertex = clicked_vertex
                    else:
                        polygon = find_polygon(click_pos, faces)
                        if polygon:
                            # print("graph", graph)
                            # print("faces: ", faces)
                            # print("clicked in polygon: ", polygon)
                            faces_to_draw.append(polygon)
                            continue
                            # sorted_face =  sort_points_counterclockwise(polygon)
                            # pygame.draw.polygon(screen, (173, 216, 200) , sorted_face)
                        aligned_pos = align_vertex(event.pos)
                        if not find_is_there_nearby_vertex(aligned_pos):
                            graph[aligned_pos] = []
                        joints[aligned_pos] = [False] * 6
                else:
                    if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                            delete_line(clicked_line)
                    if clicked_vertex:
                        if selected_vertex:
                            graph[selected_vertex].append([clicked_vertex, 0])
                            graph[clicked_vertex].append([selected_vertex, 0])
                            selected_vertex = None
                        else:
                            selected_vertex = clicked_vertex
    
    screen.fill(BACKGROUND_COLOR)
    draw_vertices()
    draw_lines()
    draw_faces()
    if joint_edit_mode:
        draw_joint_selection_bar()
        if selected_vertex:
            # Highlight the selected vertex
            pygame.draw.circle(screen, (255, 255, 100), selected_vertex, VERTEX_RADIUS + 2, 2)
    pygame.display.flip()

pygame.quit()
sys.exit()