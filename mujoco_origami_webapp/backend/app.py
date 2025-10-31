from flask import Flask, request, jsonify
from flask import Flask, request
from flask_cors import CORS


from create2 import get_mjcf_flex
import parse_input_with_bodies
import json


app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/generate-xml', methods=['POST'])
def generate_xml():
    data = request.get_json()
    vertices, fixed_edges = parse_input_with_bodies.find_and_order_vertices(data)
    edges = parse_input_with_bodies.create_bodies(vertices, data["bodies"])
    vertices_list = [[x, y, 0.05] for (x, y) in vertices.values()]
    grounds = [i for i, v in enumerate(vertices.values()) if v in data["grounded_vertices"]]
    joints = data["joints"]
    actuators = data["actuators"]
    xml_str = get_mjcf_flex("demo", vertices_list, edges, grounds, joints, actuators)
    return xml_str, 200, {'Content-Type': 'application/xml'}

if __name__ == '__main__':
    app.run(debug=True)
