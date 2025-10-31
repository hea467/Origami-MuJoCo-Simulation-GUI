import numpy as np
import matplotlib.pyplot as plt
import xml.etree.ElementTree as ET
import json 
import triangle_mesh
import parse_input_with_bodies
import random

def plot(vertices):
    plt.scatter(vertices[:, 0], vertices[:, 1])
    plt.gca().set_aspect('equal', adjustable='box')
    plt.show()
def axis_to_string(ax):
    if ax == 'x': 
        return "1 0 0"
    elif ax == 'y':
        return "0 1 0"
    else:
        return "0 0 1"
    
def get_joint_range(joint_type):
    """Returns the correct range for different joint types."""
    if joint_type == 'x' or joint_type == 'y': 
        return "-1 1"
    elif joint_type == 'z_all':
        return "-1 1"
    elif joint_type == 'z_up':
        return "0 1"
    elif joint_type == 'z_down':
        return "-1 0"
    else:
        return "-1 1"

def get_mjcf_flex(name, vertices, edges, grounds, joints, actuators_data, rgba="0 0 1 0.9"):
    mj = ET.Element("mujoco", model=name)
    slide_axes = ['x', 'y', 'z']
    # extension = ET.SubElement(mj, "extension")
    # ET.SubElement(extension, "plugin", plugin="mujoco.elasticity.solid")
    ET.SubElement(mj, "include", file = "scene.xml")
    worldbody = ET.SubElement(mj, "worldbody")
    # ET.SubElement(worldbody, 'geom', type = "plane", size = "10 10 0.1", rgba="1 1 1 1")
    for i, (x, y, z) in enumerate(vertices):
        body = ET.SubElement(worldbody, 'body', name=f"v{i+1}", pos=f"{x} {y} {z + 0.5}")
        ET.SubElement(body, 'inertial', pos="0 0 0", mass="0.01", diaginertia="1.66667e-05 1.66667e-05 1.66667e-05")
        if f"v{i+1}" in joints:
            joint_data = joints[f"v{i+1}"]

            for j, joint_active in enumerate(joint_data):
                if joint_active:
                    joint_type = ['x', 'y', 'z_all', 'z_up', 'z_down'][j]
                    range_str = get_joint_range(joint_type)
                    ET.SubElement(body, 'joint', 
                                  name=f"v{i+1}_j{joint_type}", 
                                  pos="0 0 0", 
                                  axis=axis_to_string(joint_type[0]), 
                                  type="slide", 
                                  limited="true", 
                                  range=range_str)
    # Add deformable Tsection
    deformable = ET.SubElement(mj, 'deformable')
    # Add flex objects based on edges
    for body_name, flex_objects in edges.items():
        for flex_name, triangles in flex_objects.items():
            if isinstance(triangles[0], list):
                elements = " ".join(" ".join(map(str, triangle)) for triangle in triangles)
            else:
                elements = " ".join(map(str, triangles))
            flex_vertices = " ".join("0 0 0" for _ in range(flex_name.count("v")))
            green = random.uniform(0.5, 1.0)
            blue = random.uniform(0.5, 1.0)
            rgba_string = f"0 {green} {blue} 1"
            flex = ET.SubElement(deformable, 'flex', name=body_name, dim="2", body=flex_name,
                                vertex=flex_vertices, element=elements, rgba=rgba_string)
    # Add equality section
    equality = ET.SubElement(mj, 'equality')
    for body_name in edges.keys():
        ET.SubElement(equality, 'flex', flex=body_name)
    actuators = ET.SubElement(mj, 'actuator')
    for vertex, actuator_types in actuators_data.items():
        print(actuator_types)
        v_index = int(vertex[1:])  # Extract numerical index from "v10"
        for i, (actuator_active, suffix) in enumerate(actuator_types):
            if actuator_active:
                axis_type = ['x', 'y', 'z'][i]
                joint_name = f"v{v_index}_j{axis_type}{suffix}"
                ET.SubElement(actuators, "position",
                              name=f"{axis_type}-pos{v_index}",
                              joint=joint_name,
                              dampratio="1")                
    # Convert the XML tree to a string and print it
    tree = ET.ElementTree(mj)
    ET.indent(tree, space="\t", level=0)
    xml_str = ET.tostring(mj, encoding='unicode')
    return xml_str

if __name__ == '__main__':
    # 1) get the input from the json file 
    # Opening JSON file
    f = open('design.json')
    data = json.load(f)
    # 2) Process input so that we can run the triangulate algorithm, with fixed edges being the folds 
    vertices, fixed_edges = parse_input_with_bodies.find_and_order_vertices(data)
    edges = parse_input_with_bodies.create_bodies(vertices, data["bodies"])
    vertices_list = []
    for vertex_name in vertices.keys():
        vertices_list.append(vertices[vertex_name])
    # print("The list of vertices", vertices_list)
    #adding in the z axis and getting things in final form
    vertices = [[x, y, 0.05] for (x, y) in vertices_list]
    #get grounded vertices
    grounds= []
    for v in data["grounded_vertices"]:
        coor = data["canvas"][v]
        indx = vertices.index([coor[0], coor[1], 1])
        grounds.append(indx)
    actuators = data["actuators"]

    # print("Triangle arrangement: ", output_connections)
    # print("sorted vertices: ", vertices)
    # print("grounded vertices: ", grounds)
    # print("bodies created: ", edges)
    # Closing file
    f.close()
    joints = data["joints"]
    name = "demo"
    xml_str = get_mjcf_flex(name, vertices, edges, grounds, joints, actuators)
    with open(f"{name}.xml", "w") as f:
        f.write(xml_str)
    