# this code is an adaptation of code from 
# https://www.artstation.com/artwork/w6r9Wg
# Note: there is no python script on this website, 
# I wrote the code by hand from instructions


# BLENDER VERSION IN WHICH I WORKED IN: 3.2.2


import os, sys, bpy, re
from pathlib import Path
from math import radians, sin, cos, sqrt


# Delete the default cube from scene
bpy.ops.object.select_all(action = 'DESELECT')
bpy.data.objects['Cube'].select_set(True)

# set use_global = True to delete globally and remove object from all scenes
bpy.ops.object.delete(use_global = False) 


# Delete the default light from scene
bpy.ops.object.select_all(action = 'DESELECT')
bpy.data.objects['Light'].select_set(True)
bpy.ops.object.delete(use_global = False)



# --------------- STEP 0: Get the name of fabric -------------------

# Regex cheat sheet:
# https://pythex.org/

# Assume a file with '.png', '.jpg', '.jpeg' extension contains a map (e.g. Normal, BaseColor,Roughness etc...)
# And asume that file has name: Fabric01_2K_BaseColor.png or similar

# Create Regex to pick out the name of Fabric (Here it is Fabric01)
fabric_name_regex = re.compile(r'^[0-9a-zA-Z]+')

# import_array contains all files in current working directory
import_array = os.listdir()

# search the current working directory for Fabric name
for filename in import_array:
    # print(filename)
    
    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        
        # mo variable name is just a generic name to use for Match objects.
        mo = fabric_name_regex.search(filename)
        if mo != None:
            fabric_name = mo.group() # get Matched object as string
            break


# --------------- STEP 1: Create object and material ---------------


# TODO: Find a better 'low-level' way to create a plane instead of using bpy.ops.mesh.primitive_plane_add()
# Generally we like to avoid using bpy.ops because that indirectly uses the 'blender UI', instead of any lower level commands

# create plane object
bpy.ops.mesh.primitive_plane_add()
main_object = bpy.context.active_object

# set scale
main_object.scale[0] = 1.0 # x scale
main_object.scale[1] = 1.0 # y scale
main_object.scale[2] = 1.0 # z scale

# Note: I did not find a way of changing the dimensions of object, but we can change scale

# rename object to name of fabric
bpy.context.active_object.name = fabric_name
name_object = bpy.context.active_object.name


# create material
name_material = name_object + "_Material"
main_material = bpy.data.materials.new(name_material)
main_material.use_nodes = True


# Rename main_material.node_tree.nodes to nodes for convenience
nodes = main_material.node_tree.nodes

# Rename main_material.node_tree.links to links for convenience
links = main_material.node_tree.links


# get principled bsdf node from created material
bsdf = nodes["Principled BSDF"]

# get material output node from created material
material_output = nodes["Material Output"]


# create Normal map node and connect it to bsdf
# we input into this normal_map either NormalDX.jpg or NormalGL.jpg later in the code
normal_map = nodes.new('ShaderNodeNormalMap')
links.new(bsdf.inputs[22], normal_map.outputs[0])



#----------------------NOTE---------------------------



# Following code is used only if we are using a Normal map
# from DirectX. Then we need to convert it to OpenGL equivalent.

# create CombineRGB node
combine_rgb = nodes.new('ShaderNodeCombineRGB')
links.new(normal_map.inputs[1], combine_rgb.outputs[0])

# create NodeInvert node
invert = nodes.new('ShaderNodeInvert')
links.new(combine_rgb.inputs[1], invert.outputs[0])

# create SeparateRGB node
separate_rgb = nodes.new('ShaderNodeSeparateRGB')
links.new(invert.inputs[1], separate_rgb.outputs[1])
links.new(combine_rgb.inputs[0], separate_rgb.outputs[0])
links.new(combine_rgb.inputs[2], separate_rgb.outputs[2])

#-------------------END OF NOTE-----------------------



# create ColorRamp node
# used only if we have an Ambient Occlusion (AO) map to combine it with Base Color map
color_ramp = nodes.new('ShaderNodeValToRGB')
color_ramp.location = -500, 650
color_ramp.color_ramp.elements[0].position = 0.779



# create Mix RGB node
# used later to combine Base Colour and AO map 
mix_rgb = nodes.new('ShaderNodeMixRGB')
mix_rgb.location = -200, 750
mix_rgb.blend_type = 'OVERLAY'
mix_rgb.inputs[0].default_value = 0.466

# add links
links.new(mix_rgb.inputs[2], color_ramp.outputs[0])
links.new(bsdf.inputs[0], mix_rgb.outputs[0])


# create Displacement node
displacement = nodes.new('ShaderNodeDisplacement')
displacement.location = -400, 100
links.new(material_output.inputs[2], displacement.outputs[0])


# add vector mapping node
mapping = nodes.new('ShaderNodeMapping')
mapping.location = -2200, -200

# add texture coordinates node and link to mapping node
texture_coordinate = nodes.new('ShaderNodeTexCoord')
texture_coordinate.location = -2400, -200
links.new(mapping.inputs[0], texture_coordinate.outputs[2])

# add value node to make manipulating the scale of mapping easier
value_node = nodes.new('ShaderNodeValue')
value_node.location = -2400, -450
links.new(mapping.inputs[3], value_node.outputs[0])
value_node.outputs[0].default_value = 1.0



# following code is for prettier look of nodes in Shader Editor
map_array = [normal_map, combine_rgb, invert, separate_rgb]

iteration_x = 0
iteration_y = 0

for i in map_array:
    i.location = -200 - iteration_x, -300 - iteration_y
    iteration_x += 200
    iteration_y += 50




# Assign material to object
if main_object.data.materials:
    main_object.data.materials[0] = main_material
    main_object.data.materials[0].name = name_material

else:
    main_object.data.materials.append(main_material)



# ---------- STEP 2: Read images of textures by their name and position them in shader editor----------

# flag which checks if we have inserted normal map
# this is later useful when the fabric has both NormalDX.png and NormalGL.png 
# types of normal maps and we need to insert only one
is_normal_map_inserted = False

# We assume that all relevant files are inside the current working directory
cwd = Path.cwd()

for filename in import_array: # loop over files
    dot_jpg_array = filename.split(".")

    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        
        # Regex to find the end of stringname with map type (e.g. Normal, Roughness etc...)
        map_type_regex = re.compile(r'[0-9a-zA-Z]+$')
        
        mo1 = fabric_name_regex.search(dot_jpg_array[0])
        mo2 = map_type_regex.search(dot_jpg_array[0])
        if mo1 != None and mo2 != None:
            fabric_name = mo1.group() # get Matched object as string
            map_name = mo2.group() 
            
        else:
            raise Exception('Something is wrong with file name or map name or Regex search')
        

        if fabric_name == name_object: # check if fabric name matches name of object
            
            # TODO: Rename everywhere type_material variable to map_name
            type_material = map_name

            tex_image = nodes.new('ShaderNodeTexImage')
            tex_image.location = -750 - iteration_x, 520 - iteration_y

            # load image, asume imgae has format eg. Fabric019_2K_Color.jpg
            for image in os.listdir(cwd):
                if image.endswith(type_material + "." + dot_jpg_array[1]) and image.startswith(name_object):
                    path_to_image_to_load = cwd / image
            
            
            #tex_image_to_load_name = name_object + "_" + type_material + "." + dot_jpg_array[1]
            #path_to_image_to_load = cwd / tex_image_to_load_name
            tex_image.image = bpy.data.images.load(path_to_image_to_load.__str__())

            if type_material in ["AO", "Metallic", "Roughness", "Normal", "NormalDX", "NormalGL", "Displacement", "Opacity"]:
                
                # do not apply gamma encoding to Non-Color maps
                tex_image.image.colorspace_settings.name = 'Non-Color'
            
            # ---------------------- NOTE -----------------------
            # CHECK WHICH TYPE OF NORMAL IS USED IN THE FILE, DirectX or OpenGL
            # If we are using DirectX, we just need to invert the green channel
            # to get OpenGL convention. Blender uses OpenGL convention
            
            # assume DirectX convention
            if (type_material == "Normal" or type_material == "NormalDX") and not is_normal_map_inserted:
                links.new(separate_rgb.inputs[0], tex_image.outputs[0])
                links.new(tex_image.inputs[0], mapping.outputs[0])
                is_normal_map_inserted = True
            
            elif type_material == "NormalGL" and not is_normal_map_inserted:
                links.new(normal_map.inputs[1], tex_image.outputs[0])
                is_normal_map_inserted = True

            elif type_material == "Base Color" or type_material == "Color":
                links.new(mix_rgb.inputs[1], tex_image.outputs[0])
                links.new(tex_image.inputs[0], mapping.outputs[0])

            elif type_material == "AO":
                links.new(color_ramp.inputs[0], tex_image.outputs[0])
                links.new(tex_image.inputs[0], mapping.outputs[0])
                
            elif type_material == "Displacement":
                links.new(displacement.inputs[0], tex_image.outputs[0])
                links.new(tex_image.inputs[0], mapping.outputs[0])
            
            # Quick into about using opacity map in blender:
            # https://www.youtube.com/watch?v=udRLe6F6Z-0
            elif type_material == "Opacity":
                links.new(bsdf.inputs[21], tex_image.outputs[0])
                links.new(tex_image.inputs[0], mapping.outputs[0])
                main_material.blend_method = 'CLIP'           
            
            elif type_material == "Roughness":
                links.new(bsdf.inputs[9], tex_image.outputs[0])
                links.new(tex_image.inputs[0], mapping.outputs[0])

            iteration_x += 100
            iteration_y += 270

        else:
            raise Exception("Fabric name does not match the name of the object in scene")




# ------------------STEP 3: Set camera and lights--------------

# The following camera and light setup is arbitrary, you can change
# it so that it suits your need

camera = bpy.data.objects["Camera"]

camera.rotation_euler[0] = 0
camera.rotation_euler[1] = 0
camera.rotation_euler[2] = 0

camera.location[0] = 0 # x coordinate
camera.location[1] = 0 # y
camera.location[2] = 5 # z


# Create light datablock
point_light_data = bpy.data.lights.new(name = "myPointLightData", type = 'POINT')
point_light_data.energy = 1000

# Create new object, pass the light data 
point_light = bpy.data.objects.new(name = "myPointLight", object_data = point_light_data)

# Link object to collection in context
bpy.context.collection.objects.link(point_light)

point_light.rotation_euler[0] = 0
point_light.rotation_euler[1] = 0
point_light.rotation_euler[2] = 0

point_light.location[0] = 1 # x
point_light.location[1] = 1 # y
point_light.location[2] = 2 # z


# Create light datablock
area_light_data = bpy.data.lights.new(name = "myAreaLightData", type = 'AREA')
area_light_data.energy = 150

# Resizing area light
area_light_data.size = 1
area_light_data.size_y = 1

# Create new object, pass the light data 
area_light = bpy.data.objects.new(name = "myAreaLight", object_data = area_light_data)

# Link object to collection in context
bpy.context.collection.objects.link(area_light)

# Change light position and rotation
area_light.location = (0, 1.5, 0.25)
area_light.rotation_euler[0] = radians(-35)
area_light.rotation_euler[1] = 0
area_light.rotation_euler[2] = 0



# ------------------STEP 4: Render Image -----------------------

# render the image and save it as a .jpg file
# I have added the option to render multiple images of same material in a for loop
# by rotating the light in various positions
# Maybe you would want to rotate the area light, plane or camera instead of the point light?
# depends how you want to  generate your data


# you can add an object(i.e. the plane) to rotate_and_render variables if you want by: subject = bpy.context.object
def rotate_and_render(output_dir, output_file_pattern_string = name_object + '_Render%d.jpg', rotation_steps = 32, rotation_angle = 360.0,  light = point_light): 
    
    x = light.location[0] # x coordinate
    y = light.location[1] # y
    r = sqrt(x**2 + y**2)
    
    for step in range(0, rotation_steps):
        
        angle = radians(step * (rotation_angle / rotation_steps))
        
        
        light.location[0] = r * cos(angle) # set x coordinate
        light.location[1] = r * sin(angle) # set y coordinate
        
        # TODO: Figure out how to note down position of light once rotated, read the TODO at bottom of this page
        
        bpy.context.scene.render.filepath = os.path.join(output_dir, (output_file_pattern_string % step))
        bpy.ops.render.render(write_still = True)
    
    light.location[0] = x
    light.location[1] = y

# add subject = main_object if you redefined the function
rotate_and_render(output_dir = cwd.__str__(), rotation_steps = 6,  light = point_light)


# TODO: Figure out how to note down the scene properties
#       like lighting, camera position etc...
#       it doesn't have to be like format in blender, can be some other format

# TODO: Export light map as a .png file as in Single image portrait relighting paper

# TODO: Figure out how to have single script to generate
#       multiple .blend files for data generation 