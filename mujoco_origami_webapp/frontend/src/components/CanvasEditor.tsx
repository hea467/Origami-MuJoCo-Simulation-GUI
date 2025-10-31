import React, { useState, useRef } from "react";
import { Stage, Layer, Circle, Line } from "react-konva"; // Added Polygon
import axios from "axios"; // add to top of file


// Type definitions
type Point = { x: number; y: number };
// In Python: graph maps (x,y) to list of [(neighbor_pos, type_int)]
// We use vertex indices for simplicity in TS arrays.
// foldType: 0 = boundary, 1 = mountain, 2 = valley (from Python)
type Edge = { from: number; to: number; foldType: number };

const CANVAS_WIDTH = 800;
const CANVAS_HEIGHT = 600;
const VERTEX_RADIUS = 10; // Python uses 20, but 10 is fine for Konva
const LINE_WIDTH = 3;
const SNAP_DIST = 30; // For aligning vertex

const JOINT_TYPES = ["x", "y", "z_all", "z_up", "z_down"];
const ACTUATOR_AXES = ["x", "y", "z"];
const Z_SUFFIXES = ["_all", "_up", "_down"];



// const LINE_COLOR_CHOICES = ["blue", "red", "yellow"]; // 0: boundary, 1: mountain, 2: valley

export default function CanvasEditor() {
    const [vertices, setVertices] = useState<Point[]>([]); // Array of {x, y}
    const [edges, setEdges] = useState<Edge[]>([]); // Array of {from: index, to: index, foldType: int}
    const [selectedVertex, setSelectedVertex] = useState<number | null>(null);
    const [facesToDraw, setFacesToDraw] = useState<Point[][]>([]); // Store actual points for polygons
    const [joints, setJoints] = useState<Record<number, boolean[]>>({});
    // Each is: [isActive, suffix]
    const [actuators, setActuators] = useState<Record<number, [boolean, string][]>>({});


    const stageRef = useRef<any>(null);

    // --- Vertex and Edge Manipulation ---
    const addVertex = (pos: Point) => {
        const alignedPos = alignVertex(pos);
        // Prevent adding vertex too close to another
        if (vertices.some(v => Math.hypot(v.x - alignedPos.x, v.y - alignedPos.y) < VERTEX_RADIUS / 2)) {
            return -1; // Indicate vertex not added
        }
        setVertices(prev => [...prev, alignedPos]);
        return vertices.length; // Return new vertex index
    };

    const addEdge = (fromIdx: number, toIdx: number) => {
        if (fromIdx === toIdx) return;
        // Avoid duplicate edges
        if (!edges.some(e => (e.from === fromIdx && e.to === toIdx) || (e.from === toIdx && e.to === fromIdx))) {
            setEdges(prev => [...prev, { from: fromIdx, to: toIdx, foldType: 0 }]);
        }
    };

    const alignVertex = (pos: Point): Point => {
        if (vertices.length === 0) return pos;
        let xPos = pos.x;
        let yPos = pos.y;

        const closestXVertex = vertices.reduce((prev, curr) =>
            Math.abs(curr.x - pos.x) < Math.abs(prev.x - pos.x) ? curr : prev
        );
        if (Math.abs(closestXVertex.x - pos.x) < SNAP_DIST) {
            xPos = closestXVertex.x;
        }

        const closestYVertex = vertices.reduce((prev, curr) =>
            Math.abs(curr.y - pos.y) < Math.abs(prev.y - pos.y) ? curr : prev
        );
        if (Math.abs(closestYVertex.y - pos.y) < SNAP_DIST) {
            yPos = closestYVertex.y;
        }
        return { x: xPos, y: yPos };
    };

    const findVertexAtPos = (pos: Point): number => {
        return vertices.findIndex(v => Math.hypot(v.x - pos.x, v.y - pos.y) <= VERTEX_RADIUS);
    };

    // Add this constant near your other constants
    const CLICK_NEAR_EDGE_THRESHOLD = 10; // pixels, similar to Python's threshold

    // ... inside your CanvasEditor component
    const distanceToLine = (p: Point, a: Point, b: Point): number => {
        const A = p.x - a.x;
        const B = p.y - a.y;
        const C = b.x - a.x;
        const D = b.y - a.y;
        const dot = A * C + B * D;
        const lenSq = C * C + D * D;
        let param = -1;
        if (lenSq !== 0) param = dot / lenSq;

        let xx, yy;
        if (param < 0) {
            xx = a.x;
            yy = a.y;
        } else if (param > 1) {
            xx = b.x;
            yy = b.y;
        } else {
            xx = a.x + param * C;
            yy = a.y + param * D;
        }

        const dx = p.x - xx;
        const dy = p.y - yy;
        return Math.sqrt(dx * dx + dy * dy);
    };

    const handleStageClick = (e: any) => {
        if (e.target?.getClassName() === 'Line') {
            return; // Don't do anything if the click originated from a line
        }

        const stage = stageRef.current;
        if (!stage) return;
        const pointerPos = stage.getPointerPosition();
        if (!pointerPos) return;

        // 1. Check for click on an existing vertex (highest priority)
        const clickedVertexIdx = findVertexAtPos(pointerPos);
        if (clickedVertexIdx !== -1) {
            if (selectedVertex === null) {
                setSelectedVertex(clickedVertexIdx);
            } else {
                if (selectedVertex !== clickedVertexIdx) {
                    addEdge(selectedVertex, clickedVertexIdx);
                }
                setSelectedVertex(null); // Deselect or finish edge
            }
            return; // Click handled
        }

        // 2. Check if click is near an existing edge (but not on its endpoint vertices)
        for (let i = 0; i < edges.length; i++) {
            const edge = edges[i];
            // Ensure vertices for the edge exist (important if vertices can be deleted)
            if (edge.from >= vertices.length || edge.to >= vertices.length) continue;

            const vFrom = vertices[edge.from];
            const vTo = vertices[edge.to];

            // Calculate distance from click to the line segment
            if (distanceToLine(pointerPos, vFrom, vTo) < CLICK_NEAR_EDGE_THRESHOLD) {
                // Python's safeguard: ensure click is not within radius of either endpoint vertex
                // This gives vertex clicks (handled above) priority even if the vertex is on the line.
                // This check here ensures that if the vertex click was *just* missed but is still close to the line,
                // we correctly identify it as a line click rather than an accidental vertex add.
                const distToVFrom = Math.hypot(pointerPos.x - vFrom.x, pointerPos.y - vFrom.y);
                const distToVTo = Math.hypot(pointerPos.x - vTo.x, pointerPos.y - vTo.y);

                if (distToVFrom > VERTEX_RADIUS && distToVTo > VERTEX_RADIUS) {
                    // If click is near line and NOT on its endpoint vertices, treat as line click
                    handleLineClick(i, { evt: { preventDefault: () => { } } }); // Pass a mock event
                    setSelectedVertex(null); // Deselect any currently selected vertex
                    return; // Click handled as line interaction
                }
            }
        }

        // 3. Try to select a face if clicking inside one
        const allDetectedFaceVertexIndices = detectAllFaces();
        const allDetectedFacePoints = allDetectedFaceVertexIndices.map(faceIndices =>
            faceIndices.map(idx => vertices[idx]).filter(v => v !== undefined) // Ensure all points are valid
        );

        // Ensure findPolygon can handle potentially empty polygons from the filter
        const clickedFacePoints = findPolygon(
            pointerPos,
            allDetectedFacePoints.filter(poly => poly.length >= 3)
        );


        if (clickedFacePoints && clickedFacePoints.length > 0) {
            const faceKey = clickedFacePoints.map(p => `${p.x}-${p.y}`).sort().join(',');
            const isAlreadyDrawn = facesToDraw.some(drawnFace => {
                const drawnFaceKey = drawnFace.map(p => `${p.x}-${p.y}`).sort().join(',');
                return faceKey === drawnFaceKey;
            });
            if (!isAlreadyDrawn) {
                setFacesToDraw(prev => [...prev, clickedFacePoints]);
            }
            setSelectedVertex(null); // Deselect any vertex
            return; // Click handled
        }

        // 4. If not clicking a vertex, near an edge, or on a face, add a new vertex
        addVertex(pointerPos); // addVertex already handles alignment and proximity checks
        setSelectedVertex(null); // Clear selection after potentially adding a vertex
    };

    const handleLineClick = (edgeIndex: number, event: any) => {
        event.evt.preventDefault();
        event.cancelBubble = true;

        setEdges((prevEdges) =>
            prevEdges.map((edge, i) =>
                i === edgeIndex
                    ? { ...edge, foldType: edge.foldType === 1 ? 0 : 1 }
                    : edge
            )
        );
    };


    // --- Face Detection (Closer to Python Logic) ---

    // Builds an adjacency list for the graph: Map<vertexIndex, neighborIndex[]>
    const buildAdjacencyList = (includeFoldTypes: number[] | null = null): Map<number, number[]> => {
        const adj = new Map<number, number[]>();
        vertices.forEach((_, i) => adj.set(i, []));
        edges.forEach(edge => {
            if (includeFoldTypes === null || includeFoldTypes.includes(edge.foldType)) {
                adj.get(edge.from)?.push(edge.to);
                adj.get(edge.to)?.push(edge.from);
            }
        });
        return adj;
    };

    // Finds all paths between start and end using DFS, avoiding cycles in the current path.
    // graphAdj: Adjacency list (Map<number, number[]>)
    const findAllPathsDFS = (
        graphAdj: Map<number, number[]>,
        startNode: number,
        endNode: number,
        currentPath: number[] = [startNode]
    ): number[][] => {
        if (startNode === endNode) {
            return [currentPath];
        }

        const paths: number[][] = [];
        const neighbors = graphAdj.get(startNode) || [];

        for (const neighbor of neighbors) {
            if (!currentPath.includes(neighbor)) { // Avoid immediate cycles in this path
                const newPaths = findAllPathsDFS(graphAdj, neighbor, endNode, [...currentPath, neighbor]);
                paths.push(...newPaths);
            }
        }
        return paths;
    };


    const detectAllFaces = (): number[][] => { // Returns array of faces (each face is an array of vertex indices)
        const faces: number[][] = [];
        const uniqueFaceKeys = new Set<string>(); // To store sorted vertex indices string for uniqueness
        const graphAdj = buildAdjacencyList(); // Build graph with all edges

        const foldEdges = edges.filter(e => e.foldType === 1 || e.foldType === 2);

        for (const foldEdge of foldEdges) {
            const start = foldEdge.from;
            const end = foldEdge.to;

            // Temporarily remove the current foldEdge from consideration for path finding between its own nodes
            // Or ensure findAllPaths doesn't use it. A simpler approach for now:
            // findAllPaths will find paths using other edges.
            const paths = findAllPathsDFS(graphAdj, start, end);

            for (const path of paths) {
                // A path from start to end, when combined with the foldEdge (start,end), forms a cycle.
                // The path itself must not be the direct foldEdge.
                if (path.length > 1 && (path.length > 2 || (path[0] !== start || path[1] !== end))) {
                    // Python: if len(path) >= 3:
                    // Here, path = [start, n1, ..., end]. The fold (start,end) completes it.
                    // So the actual face vertices are just `path`.
                    if (path.length >= 3) {
                        const faceVerticesIndices = [...path]; // The path itself forms the boundary
                        const key = faceVerticesIndices.slice().sort((a, b) => a - b).join('-');
                        if (!uniqueFaceKeys.has(key)) {
                            faces.push(faceVerticesIndices);
                            uniqueFaceKeys.add(key);
                        }
                    }
                }
            }
        }
        return faces;
    };

    // --- Point in Polygon and Find Polygon (from Python, adapted) ---
    const isPointInPolygon = (point: Point, polygon: Point[]): boolean => {
        if (polygon.length < 3) return false;
        let inside = false;
        const x = point.x, y = point.y;
        for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
            const xi = polygon[i].x, yi = polygon[i].y;
            const xj = polygon[j].x, yj = polygon[j].y;
            const intersect = ((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi);
            if (intersect) inside = !inside;
        }
        return inside;
    };

    const findPolygon = (clickPos: Point, polygons: Point[][]): Point[] | null => {
        // Sort polygons by area (smallest first) for accurate picking if overlapping
        // This is an approximation; true area calculation can be complex.
        // Python sorts by len(points), which is simpler.
        const sortedPolygons = polygons.sort((a, b) => polygonArea(a) - polygonArea(b));
        for (const poly of sortedPolygons) {
            if (isPointInPolygon(clickPos, poly)) {
                return poly;
            }
        }
        return null;
    };

    const polygonArea = (polygon: Point[]): number => { // Shoelace formula
        let area = 0;
        for (let i = 0; i < polygon.length; i++) {
            const j = (i + 1) % polygon.length;
            area += polygon[i].x * polygon[j].y;
            area -= polygon[j].x * polygon[i].y;
        }
        return Math.abs(area / 2);
    };

    // --- Rendering ---
    const getLineColor = (foldType: number) => {
        return foldType === 1 ? "red" : "blue";
    };


    // Helper to sort points for consistent polygon drawing (optional, but good for complex shapes)
    const sortPointsCounterClockwise = (points: Point[]): Point[] => {
        if (points.length < 3) return points;
        const center = points.reduce((acc, p) => ({ x: acc.x + p.x / points.length, y: acc.y + p.y / points.length }), { x: 0, y: 0 });
        return points.slice().sort((a, b) => Math.atan2(a.y - center.y, a.x - center.x) - Math.atan2(b.y - center.y, b.x - center.x));
    };

    const generateDesignJson = () => {
        const json: any = {
            canvas: {},
            folds: { mountain: {}, valley: {} },
            grounded_vertices: [],
            joints: {},
            actuators: {},
            bodies: {}
        };

        // === Vertices ===
        vertices.forEach((v, i) => {
            const key = `v${i + 1}`;
            json.canvas[key] = [v.x / 100, v.y / 100]; // same scaling as Pygame
        });

        // === Folds ===
        let mountainCount = 1;
        edges.forEach((edge) => {
            if (edge.foldType === 1) {
                const v1 = `v${edge.from + 1}`;
                const v2 = `v${edge.to + 1}`;
                const key = `mountain${mountainCount++}`;
                json.folds.mountain[key] = {
                    [v1]: json.canvas[v1],
                    [v2]: json.canvas[v2],
                };
            }
        });

        // === Faces → Bodies ===
        facesToDraw.forEach((face, i) => {
            const vertexIndices = face.map((pt) => {
                // Match point to vertex index
                const idx = vertices.findIndex(v => v.x === pt.x && v.y === pt.y);
                return `v${idx + 1}`;
            });
            json.bodies[`body${i + 1}`] = vertexIndices;
        });
        // === Joints ===
        Object.entries(joints).forEach(([vertexIdxStr, jointFlags]) => {
            const vKey = `v${parseInt(vertexIdxStr) + 1}`;
            json.joints[vKey] = jointFlags;  // [x, y, z_all, z_up, z_down]
        });

        // === Actuators ===
        Object.entries(actuators).forEach(([vertexIdxStr, actuatorList]) => {
            const vKey = `v${parseInt(vertexIdxStr) + 1}`;
            const zActuator = actuatorList[2]; // Z-axis actuator [bool, "_type"]
            if (zActuator[0]) {
                json.actuators[vKey] = actuatorList;  // send all axes, only z has a suffix
            }
        });


        return json;
    };


    return (
        <div>
            <h3>Origami Canvas</h3>
            <Stage
                width={CANVAS_WIDTH}
                height={CANVAS_HEIGHT}
                onMouseDown={handleStageClick}
                ref={stageRef}
                style={{ border: "1px solid grey" }}
            >
                <Layer>
                    {/* Draw Faces */}
                    {facesToDraw.map((facePoints, i) => {
                        const sortedFacePoints = sortPointsCounterClockwise(facePoints);
                        const flatPoints = sortedFacePoints.flatMap(p => [p.x, p.y]);
                        // Simple color cycling for faces
                        const faceColor = `rgba(${173 + i * 7 % 255}, ${216 + i * 10 % 255}, ${50 + i * 50 % 255}, 0.5)`;
                        return (
                            <Line
                                key={`face-${i}`}
                                points={flatPoints}
                                fill={faceColor}
                                stroke="darkgreen"
                                strokeWidth={1}
                                closed={true}
                            />
                        );
                    })}

                    {/* Draw Edges */}
                    {edges.map((edge, i) => {
                        if (edge.from >= vertices.length || edge.to >= vertices.length) return null; // Safety check
                        const fromV = vertices[edge.from];
                        const toV = vertices[edge.to];
                        return (
                            <Line
                                key={`edge-${i}`}
                                points={[fromV.x, fromV.y, toV.x, toV.y]}
                                stroke={getLineColor(edge.foldType)}
                                strokeWidth={LINE_WIDTH}
                                hitStrokeWidth={10} // Makes it easier to click lines
                                onClick={(e) => handleLineClick(i, e)} // Pass event to stop propagation
                                onTap={(e) => handleLineClick(i, e)} // For touch devices
                            />
                        );
                    })}

                    {/* Draw Vertices */}
                    {vertices.map((v, i) => (
                        <Circle
                            key={`vertex-${i}`}
                            x={v.x}
                            y={v.y}
                            radius={VERTEX_RADIUS}
                            fill={selectedVertex === i ? "orange" : "blue"} // Python's VERTEX_COLOR
                            stroke={selectedVertex === i ? "darkred" : "darkblue"}
                            strokeWidth={1}
                        />
                    ))}
                </Layer>
            </Stage>
            {selectedVertex !== null && (
                <div style={{ marginTop: "10px", padding: "10px", border: "1px solid #ccc", maxWidth: "400px" }}>
                    <h4>Configure v{selectedVertex + 1}</h4>

                    <div>
                        <strong>Joints:</strong><br />
                        {["x", "y"].map((axis, i) => (
                            <label key={`joint-${axis}`} style={{ marginRight: "10px" }}>
                                <input
                                    type="checkbox"
                                    checked={joints[selectedVertex]?.[i] || false}
                                    onChange={(e) => {
                                        const current = joints[selectedVertex] || [false, false, false, false, false];
                                        const updated = [...current];
                                        updated[i] = e.target.checked;
                                        setJoints((prev) => ({ ...prev, [selectedVertex]: updated }));
                                    }}
                                />
                                {axis}
                            </label>
                        ))}
                        <div style={{ marginTop: "6px" }}>
                            Z Joint Mode:
                            {["z_all", "z_up", "z_down"].map((label, zIndex) => (
                                <label key={label} style={{ marginLeft: "10px" }}>
                                    <input
                                        type="radio"
                                        name={`z_mode_${selectedVertex}`}
                                        checked={joints[selectedVertex]?.[2 + zIndex] || false}
                                        onChange={() => {
                                            const updated = [false, false, false, false, false];
                                            const current = joints[selectedVertex] || updated;
                                            updated[0] = current[0];
                                            updated[1] = current[1];
                                            updated[2 + zIndex] = true;
                                            setJoints((prev) => ({ ...prev, [selectedVertex]: updated }));
                                        }}
                                    />
                                    {label.replace("z_", "")}
                                </label>
                            ))}
                        </div>
                    </div>

                    <div style={{ marginTop: "10px" }}>
                        <strong>Actuators:</strong><br />
                        {ACTUATOR_AXES.map((axis, i) => (
                            <label key={`actuator-${axis}`} style={{ marginRight: "10px" }}>
                                <input
                                    type="checkbox"
                                    checked={actuators[selectedVertex]?.[i]?.[0] || false}
                                    onChange={(e) => {
                                        const jointConfig = joints[selectedVertex] || [false, false, false, false, false];
                                        const current = actuators[selectedVertex] || [
                                            [false, ""],
                                            [false, ""],
                                            [false, ""],
                                        ];
                                        const updated = [...current];

                                        if (i < 2) {
                                            // x or y
                                            updated[i] = [e.target.checked, ""];
                                        } else {
                                            // z
                                            const zTypeIndex = jointConfig.slice(2).findIndex((v) => v);
                                            const suffix = Z_SUFFIXES[zTypeIndex] || "_all";
                                            updated[2] = [e.target.checked, e.target.checked ? suffix : ""];
                                        }

                                        setActuators((prev) => ({ ...prev, [selectedVertex]: updated }));
                                    }}
                                />
                                {axis}
                            </label>
                        ))}
                    </div>
                </div>
            )}


            <button onClick={async () => {
                const designJson = generateDesignJson(); // your existing function
                try {
                    const response = await axios.post("http://127.0.0.1:5000/generate-xml", designJson, {
                        responseType: "blob", // tell browser it's a file (XML)
                        headers: { "Content-Type": "application/json" },
                    });

                    const blob = new Blob([response.data], { type: "application/xml" });
                    const url = window.URL.createObjectURL(blob);
                    const link = document.createElement("a");
                    link.href = url;
                    link.download = "simulation.xml";
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                } catch (err) {
                    console.error("Error submitting design:", err);
                    alert("Failed to generate XML. Is your backend running?");
                }
            }}>Generate & Download XML</button>

            {/* Future: Add buttons for save, joint editing mode, etc. */}
        </div>
    );
}