import numpy as np
import matplotlib.pyplot as plt
import xml.etree.ElementTree as ET
import json 
import parse_input_with_bodies

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

def get_mjcf_flex(name, vertices, edges, grounds, joints,actuators, rgba="0 0 1 0.9"):
    mj = ET.Element("mujoco", model=name)
    slide_axes = ['x', 'y', 'z']
    extension = ET.SubElement(mj, "extension")
    ET.SubElement(extension, "plugin", plugin="mujoco.elasticity.solid")
    ET.SubElement(mj, "include", file = "scene.xml")
    worldbody = ET.SubElement(mj, "worldbody")
    for i, (x, y, z) in enumerate(vertices):
        body = ET.SubElement(worldbody, 'body', name=f"v{i+1}", pos=f"{(x/10)} {(y/10)} {(z/10 + 0.005)}")
        ET.SubElement(body, 'inertial', pos="0 0 0", mass="0.01", diaginertia="1.66667e-05 1.66667e-05 1.66667e-05")
        if i not in grounds:
            if (f"v{i+1}") in joints.keys():
                for j in range(3):  # Handles x, y, z for slide joints
                    if joints[f"v{i+1}"][j]:
                        ET.SubElement(body, 'joint', name=f"v{i+1}_j{j+1}", pos="0 0 0", axis= axis_to_string(slide_axes[j]), type="slide")
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
            flex = ET.SubElement(deformable, 'flex', name=body_name, dim="2", body=flex_name,
                                vertex=flex_vertices, element=elements, rgba=rgba)
    # Add equality section
    equality = ET.SubElement(mj, 'equality')
    for body_name in edges.keys():
        ET.SubElement(equality, 'flex', flex=body_name)

    # Actuator section 
    actuator_section = ET.SubElement(mj, 'actuator')
    for actuator in actuators: 
        v, axis = actuator
        if axis == 0:
            ax = 'x'
        if axis == 1:
            ax = 'y'
        if axis == 2:
            ax = 'z'
        if not joints[v][axis]: 
            #if the joints required is not there
            ET.SubElement(body, 'joint', name=f"{v}_j{axis+1}", pos="0 0 0", axis= axis_to_string(ax), type="slide")
        ET.SubElement(actuator_section, "position", name = f"{v}_act{ax}", joint = f"{v}_j{axis + 1}", kp = "20", dampratio = "1", ctrlrange = "-0.05 0.45")

    # Convert the XML tree to a string and print it
    tree = ET.ElementTree(mj)
    ET.indent(tree, space="\t", level=0)
    xml_str = ET.tostring(mj, encoding='unicode')
    return xml_str

if __name__ == '__main__':
    # 1) get the input from the json file 
    # Opening JSON file
    f = open('./designs/design.json')
    data = json.load(f)
    # 2) Process input so that we can run the triangulate algorithm, with fixed edges being the folds 
    vertices, fixed_edges = parse_input_with_bodies.find_and_order_vertices(data)
    edges = parse_input_with_bodies.create_bodies(vertices, data["bodies"])
    vertices_list = []
    for vertex_name in vertices.keys():
        vertices_list.append(vertices[vertex_name])
    #print("The list of vertices", vertices_list)
    #adding in the z axis and getting things in final form
    vertices = [[x, y, 1] for (x, y) in vertices_list]
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
    with open(f"./XML_files/{name}.xml", "w") as f:
        f.write(xml_str)
        print(f"Wrote to XML file {name} successfully")
    