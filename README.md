# Origami-MuJoCo-Simulation-GUI

A fold is simulated in MuJoCo using the flex library by specifying two separate bodies, each to one side of the fold. This will create flexibility where the fold would be. Then, we must specify mobility on vertices that has mobility when folding. This will allow the bodies to move relative to the fold. Below is a video illustrating how a mountain fold is created: 


https://github.com/user-attachments/assets/6a5c2bb2-a780-4ec5-8956-4dcad9937e87


Here are the written instructions. To run the Graphical User Interface, run input_GUI.py. Provide inputs using the following guide lines: 
1. Create all the vertices by clicking the positions that you want to create the vertex.
2. Connect the vertices by clicking one vertex then the vertex you want to connect it to.
3. Create a fold by clicking on the edge where the fold would be, the edge should change from blue to red / yellow (either works).
4. Add joint properties by double clicking on a joint and pressing the key J. Then toggle the properties you want for the joint.
5. Specify bodies by clicking in the center of the polygon you wish the body to be. The body dected will be colored green.
6. Press enter to save the design to a json file.

Now that deisgn is saved in the design folder in a json format, you could view it. Then, run create.py, and it will create a deisgn using the json file in the format of an XML file. 
Render the XML file in MuJoCo and make appropiate edits: 



https://github.com/user-attachments/assets/7288b6b1-930f-469c-a3b1-ffbf043ac83e


