# ***** BEGIN GPL LICENSE BLOCK *****
#
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ***** END GPL LICENCE BLOCK *****


bl_info = {
    "name": "Lumiere",
    "author": "Cédric Brandin, Nathan Craddock",
    "version": (0, 0, 50),
    "blender": (2, 76, 3),
    "location": "",
    "description": "Interactive Lighting Add-on",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Render"}

import bpy, bgl, os, blf
from bpy_extras import view3d_utils
from mathutils import Vector, Matrix, Quaternion, Euler
from bpy.types import PropertyGroup, UIList, Panel, Operator
from bpy.props import IntProperty, FloatProperty, BoolProperty, FloatVectorProperty, EnumProperty, StringProperty, CollectionProperty, PointerProperty
from bpy_extras.object_utils import AddObjectHelper, object_data_add
import math
import bmesh
import time


#########################################################################################################

#########################################################################################################

def draw_callback_px(self, context):


    region = context.region
    rv3d = bpy.context.space_data.region_3d

   
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glColor4f(1.0, 0.4, 0, 0.5)
    lw = 4 // 2
    bgl.glLineWidth(lw*4)

#---Draw lines around the view3D
    bgl.glBegin(bgl.GL_LINE_STRIP)
    bgl.glVertex2i(lw, lw)
    bgl.glVertex2i(region.width - lw, lw)
    bgl.glVertex2i(region.width - lw, region.height - lw)
    bgl.glVertex2i(lw, region.height - lw)
    bgl.glVertex2i(lw, lw)
    bgl.glEnd()

#---Restore opengl defaults
    bgl.glLineWidth(1)
    bgl.glDisable(bgl.GL_BLEND)
    bgl.glColor4f(0.0, 0.0, 0.0, 1.0)
       
#########################################################################################################

#########################################################################################################
def get_enum_items(self, context):
    light_names = [obj for obj in bpy.context.scene.objects if obj.data.name.startswith("Lumi")]
    return [(ln, ln, "") for ln in light_names]

#########################################################################################################

#########################################################################################################
def get_mat_name(light):
    mat_name = "Mat_" + light
    mat = bpy.data.materials.get(mat_name)
    
    return(mat_name, mat)

#########################################################################################################

#########################################################################################################
def get_distance(context):
    v3d = context.space_data
    rv3d = v3d.region_3d
    
    return rv3d.view_distance

#########################################################################################################

#########################################################################################################           
def create_empty(self, context, name):
    #distance = get_distance(context)
    empty = bpy.data.objects.new(name = name + "_Empty", object_data = None)
    context.scene.objects.link(empty)
    context.active_object.data.name = name
    light = context.object
    empty.empty_draw_type = "SPHERE"
    empty.empty_draw_size = 0.00001
    empty.location = light['hit']
    light_constraint = light.constraints.new(type='TRACK_TO')
    light_constraint.target = context.scene.objects.get(empty.name)
    light_constraint.up_axis = "UP_Y"
    light_constraint.track_axis = "TRACK_NEGATIVE_Z"
    light_constraint.influence = 0

    obj = bpy.data.objects

#---Parent the empty to the target object
    target = obj[self.target_name]
    empty.parent = target
    empty.matrix_parent_inverse = target.matrix_world.inverted()
    
#---Parent the light to the target object

    light.parent = target
    light.matrix_parent_inverse = target.matrix_world.inverted()

    return empty             

#########################################################################################################

#########################################################################################################           
class RemoveLight(bpy.types.Operator):
    bl_idname = "object.remove"
    bl_label = "Remove light"
    bl_options = {"REGISTER"}

    name = bpy.props.StringProperty()
    
    
    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        light = context.active_object
        empty = bpy.context.scene.objects[light.data.name + "_Empty"]
        
    #---Remove light    
        context.scene.objects.active = light
        bpy.ops.object.delete() 
    #---Remove empty
        bpy.data.objects[empty.name].select = True
        bpy.ops.object.delete()
        return {"FINISHED"}


#########################################################################################################

#########################################################################################################
def raycast_light(self, distance, context, event, coord, ray_max=1000.0):
    scene = context.scene
    i = 0
    p = 0
    length_squared = 0
    light = context.active_object
    empty_name = light.data.name + "_Empty"
    if bpy.data.objects.get(empty_name) is not None:
        empty = context.scene.objects[empty_name]
        light.constraints['Track To'].influence = 0

#---Get the ray from the viewport and mouse
    view_vector = view3d_utils.region_2d_to_vector_3d(self.region, self.rv3d, (coord))
    ray_origin = view3d_utils.region_2d_to_origin_3d(self.region, self.rv3d, (coord))

    ray_target = ray_origin + view_vector

#---Select the object 
    def visible_objects_and_duplis():
        if light.objtarget != "":
            obj = bpy.data.objects[light.objtarget]
            yield (obj, obj.matrix_world.copy())
        else :
            for obj in context.visible_objects:
                if obj.type == 'MESH' and not obj.data.name.startswith("Lumi"):
                    yield (obj, obj.matrix_world.copy())

                if obj.dupli_type != 'NONE':
                    obj.dupli_list_create(scene)
                    for dob in obj.dupli_list:
                        obj_dupli = dob.object
                        if obj_dupli.type == 'MESH':
                            yield (obj_dupli, dob.matrix_world.copy())

                obj.dupli_list_clear()

#---Cast the ray
    def obj_ray_cast(obj, matrix):
    #---Get the ray relative to the object
        matrix_inv = matrix.inverted()
        ray_origin_obj = matrix_inv * ray_origin
        ray_target_obj = matrix_inv * ray_target
        ray_direction_obj = ray_target_obj - ray_origin_obj

    #---Cast the ray
        success, hit, normal, face_index = obj.ray_cast(ray_origin_obj, ray_direction_obj)

        return  success, hit, normal

#---Find the closest object
    best_length_squared = ray_max * ray_max
    best_obj = None

#---Position of the light from the object
    for obj, matrix in visible_objects_and_duplis():
        i = 1

        success, hit, normal = obj_ray_cast(obj, matrix)
        
        if success :

        #---Define direction based on the normal of the object or the view angle
            if light.normal and (i == 1): 
                direction = (normal * matrix.inverted())
            else:
                direction = (view_vector).reflect(normal * matrix.inverted())
            
        #---Define range
            hit_world = (matrix * hit) + (distance * direction) 

            length_squared = ((matrix * hit) - ray_origin).length_squared

            if length_squared < best_length_squared:
                best_length_squared = length_squared
                self.matrix = matrix
                self.hit = hit
                self.hit_world = hit_world
                self.direction = direction
                self.target_name = obj.name
                
#---Define location, rotation and scale
    if length_squared > 0 :
        rotaxis = (self.direction.to_track_quat('Z','Y'))      
        light['hit'] = (self.matrix * self.hit)
        light['dir'] = self.direction

        if bpy.data.objects.get(empty_name) is not None:
            empty.location = light['hit']

    #---Rotation    
        light.rotation_euler = rotaxis.to_euler()

    #---Location
        light.location = Vector((self.hit_world[0], self.hit_world[1], self.hit_world[2]))

    #---Update the position of the sun from the background texture
        if light.typlight =="Sky" :
            update_sky(self, context)    

#########################################################################################################

#########################################################################################################
def add_gradient(self, context):
    cobj = context.active_object
    cobj["typgradient"] = 1
    
    if cobj.data.name.startswith("Lumiere") and cobj.typlight in ("Panel", "Pencil"):

        mat_name, mat = get_mat_name(cobj.data.name)

        emit = mat.node_tree.nodes["Emission"]
             
    #---Color Ramp Node
        colramp = mat.node_tree.nodes.new(type="ShaderNodeValToRGB")
        colramp.color_ramp.elements[0].color = (1,1,1,1)
        colramp.location = (-700,-120) 

    #---Grandient Node 
        grad = mat.node_tree.nodes.new(type="ShaderNodeTexGradient")
        #Link to ColorRamp
        mat.node_tree.links.new(grad.outputs[0], colramp.inputs['Fac'])
        grad.location = (-900,-120) 
        
    #---Mapping Node
        textmap = mat.node_tree.nodes.new(type="ShaderNodeMapping")
        textmap.vector_type = "TEXTURE"
        #Link to Grandient
        #mat.node_tree.links.new(textmap.outputs[0], grad.inputs['Vector'])
        textmap.location = (-1300,-120) 

    #---Geometry Node
        geom = mat.node_tree.nodes.new(type="ShaderNodeNewGeometry")
        #Link to the mapping nodes
        #mat.node_tree.links.new(geom.outputs[5], textmap.inputs['Vector'])
        geom.location = (-1500,-240)         

#########################################################################################################

#########################################################################################################
def emit_plan_mat():
#---Create a new material for cycles Engine.
    bpy.context.scene.render.engine = 'CYCLES'
    
    mat_name, mat = get_mat_name(bpy.context.scene.objects.active.data.name)
     
    if mat is not None: 
        mat.node_tree.nodes.clear()
    else: 
        mat = bpy.data.materials.new(mat_name)
    mat.use_nodes= True
    mat.node_tree.nodes.clear() # Clear default nodes

#---Texture Coordinate
    coord = mat.node_tree.nodes.new(type = 'ShaderNodeTexCoord')
    coord.location = (-1500,00) 
    
#---Texture Shader Node
    texture = mat.node_tree.nodes.new(type = 'ShaderNodeTexImage')
    mat.node_tree.links.new(coord.outputs[0], texture.inputs[0])
    texture.location = (-600,150)
            
#---Geometry Node : Backface
    backface = mat.node_tree.nodes.new(type = 'ShaderNodeNewGeometry')
    backface.location = (000,250)

#---Invert Node
    invert = mat.node_tree.nodes.new(type="ShaderNodeInvert")
    invert.location = (-200,75) 

#---Transparent Node
    trans = mat.node_tree.nodes.new(type="ShaderNodeBsdfTransparent")
    trans.location = (-200,-25) 

#---Emission Node
    emit = mat.node_tree.nodes.new(type = 'ShaderNodeEmission')
    mat.node_tree.nodes["Emission"].inputs[0].default_value = bpy.context.active_object.lightcolor
    emit.location = (-200,-100)

#---Light Falloff
    falloff = mat.node_tree.nodes.new(type = 'ShaderNodeLightFalloff')
    #Link Coordinate
    mat.node_tree.links.new(falloff.outputs[1], emit.inputs[1])
    falloff.location = (-400,-200)
        
#---Mix Shader Node 1
    mix1 = mat.node_tree.nodes.new(type="ShaderNodeMixShader")
    #Link Invert 
    mat.node_tree.links.new(invert.outputs[0], mix1.inputs[0])
    #Link Transparent 
    mat.node_tree.links.new(trans.outputs[0], mix1.inputs[1])
    #Link Emission 
    mat.node_tree.links.new(emit.outputs[0], mix1.inputs[2])
     
#---Mix Shader Node 2
    mix2 = mat.node_tree.nodes.new(type="ShaderNodeMixShader")
    #Link Backface
    mat.node_tree.links.new(backface.outputs[6], mix2.inputs[0])
    #Link Transparent 
    mat.node_tree.links.new(trans.outputs[0], mix2.inputs[1])
    #Link Mix 1
    mat.node_tree.links.new(mix1.outputs[0], mix2.inputs[2])
    mix2.location = (200,0)   
    
#---Output Shader Node
    output = mat.node_tree.nodes.new(type = 'ShaderNodeOutputMaterial')
    output.location = (400,0)
    output.select
    mat.node_tree.nodes["Emission"].inputs[1].default_value = 1
    #Link them togheter
    mat.node_tree.links.new(mix2.outputs[0], output.inputs['Surface'])

#########################################################################################################

#########################################################################################################
def light_energy(cobj):

    if cobj.typlight in ("Panel", "Pencil"):

    #---If the object is a copy, need to copy the material and rename it        
        mat_name, mat = get_mat_name(cobj.data.name)
        obj_mat = cobj.material_slots[0].name
        if mat_name != obj_mat:
            new_material = bpy.data.materials[obj_mat].copy()
            new_material.name = mat_name
            bpy.data.objects[cobj.name].active_material = new_material
            
        node_falloff = mat.node_tree.nodes["Light Falloff"]
        node_falloff.inputs[0].default_value = cobj.energy
        node_emission = mat.node_tree.nodes["Emission"]
        node_emission.inputs[0].default_value = cobj.lightcolor
    elif cobj.typlight == "Sun":
        node_emission = cobj.data.node_tree.nodes["Emission"]
        node_emission.inputs[0].default_value = cobj.lightcolor    
        node_emission.inputs[1].default_value = cobj.energy
    elif cobj.typlight == "Sky":
    #---Sky Texture
        bpy.data.worlds['World'].node_tree.nodes["Background"].inputs[1].default_value = cobj.energy*4
        node_emission = cobj.data.node_tree.nodes["Emission"]     
        node_emission.inputs[1].default_value = cobj.energy
    #---Lamp value
        node_emission = cobj.data.node_tree.nodes["Emission"]
        node_emission.inputs[0].default_value = cobj.lightcolor    
        node_emission.inputs[1].default_value = cobj.energy
    else:
        node_falloff = cobj.data.node_tree.nodes["Light Falloff"]
        node_falloff.inputs[0].default_value = cobj.energy
        node_emission = cobj.data.node_tree.nodes["Emission"]
        node_emission.inputs[0].default_value = cobj.lightcolor    

#########################################################################################################

#########################################################################################################
def update_shape(self, context):
    cobj = self
    if cobj.typlight == "Panel":
        if cobj.shape == "Star":
            update_light_star(self, context)

        elif cobj.shape in ("Rectangular", "Circle"):
            create_light_grid(self, context)

#########################################################################################################

#########################################################################################################
def create_light_star(self, context, n_verts, xtrnrad, itrnrad):

    section_angle = 360.0 / n_verts 
    z = 0
    verts = []
    edges = []
    faces = []
    listvert = []
    
#---External radius, internal radius
    radius = [xtrnrad, itrnrad]
    
#---Create vertices
    for i in range(n_verts):
        x = math.sin(math.radians(section_angle*i)) * radius[i % 2]
        y = math.cos(math.radians(section_angle*i)) * radius[i % 2]
        verts.append((x, y, z))

#---Create faces 
    for f in range(n_verts - 1, -1, -1):
        listvert.extend([f])
    faces.extend([listvert])

#---Create object
    i = 0
    for ob in bpy.context.scene.objects:
        if ob.type != 'EMPTY' and ob.data.name.startswith("Lumi"):
            i += 1
            
    mesh = bpy.data.meshes.new(name="Lumiere." + str(i))
    mesh.from_pydata(verts, edges, faces)
    mesh.update(calc_edges=True)
    object_data_add(context, mesh)
    context.object.draw_type = 'WIRE'
    
#---Add the material
    emit_plan_mat()
    cobj = context.object
    mat_name, mat = get_mat_name(cobj.data.name)  
    add_gradient(self, context)

#---Add 1 simple subsurf
    cobj.modifiers.new("subd", type='SUBSURF')
    cobj.modifiers["subd"].subdivision_type="SIMPLE"
    bpy.ops.object.modifier_apply(modifier="subd")

    cobj.active_material = mat
    cobj.cycles_visibility.camera = False
    cobj.cycles_visibility.shadow = False
    cobj.shape = context.scene.shape
    cobj.typlight = context.scene.typlight
    self.nbside = n_verts
    self.scale_x = xtrnrad  
    cobj.scale_y = 0.5 
    cobj.energy = 10
    return(cobj)    

#########################################################################################################

#########################################################################################################
def update_light_star(self, context):

    cobj = self
    if cobj.nbside < 12: cobj.nbside = 12
    n_verts = cobj.nbside
    xtrnrad = cobj.xtrnrad
    itrnrad = cobj.itrnrad  

    section_angle = 360.0 / n_verts 
    z = 0
    verts = []
    edges = []
    faces = []
    listvert = []

    mat_name, mat = get_mat_name(cobj.data.name)
    
#---External radius, internal radius
    radius = [xtrnrad, itrnrad]
    
#---Create vertices
    for i in range(n_verts):
        x = math.sin(math.radians(section_angle*i)) * radius[i % 2]
        y = math.cos(math.radians(section_angle*i)) * radius[i % 2]
        verts.append((x, y, z))

#---Create faces 
    for f in range(n_verts - 1, -1, -1):
        listvert.extend([f])
    faces.extend([listvert])

#---Get the mesh
    old_mesh = cobj.data
    mesh = bpy.data.meshes.new(name=cobj.name)
    
#---Update the mesh
    mesh.from_pydata(verts, edges, faces)
    mesh.update(calc_edges=True)

#---Retrieve the name and delete the old mesh
    for i in bpy.data.objects:
        if i.data == old_mesh:
            i.data = mesh
    name = old_mesh.name
    old_mesh.user_clear()
    bpy.data.meshes.remove(old_mesh)
    mesh.name = name       

#---Add the material
    cobj.active_material = mat      
    
#---Add 1 simple subsurf
    cobj.modifiers.new("subd", type='SUBSURF')
    cobj.modifiers["subd"].subdivision_type="SIMPLE"
    bpy.ops.object.modifier_apply(modifier="subd") 

#########################################################################################################

#########################################################################################################
def create_light_circle(self, context, nb_verts):
    
    n_verts = nb_verts
    section_angle = 360.0 / n_verts 
    z = 0
    verts = []
    edges = []
    faces = []
    listvert = []

#---Create vertices
    for i in range(n_verts):
        x = math.sin(math.radians(section_angle*i)) 
        y = math.cos(math.radians(section_angle*i)) 
        verts.append((x, y, z))

#---Create faces 
    for f in range(n_verts - 1, -1, -1):
        listvert.extend([f])
    faces.extend([listvert])

#---Create object
    i = 0
    for ob in context.scene.objects:
        if ob.type != 'EMPTY' and ob.data.name.startswith("Lumi"):
            i += 1
    
#---Create the mesh
    mesh = bpy.data.meshes.new(name="Lumiere." + str(i))
    mesh.from_pydata(verts, edges, faces)
    mesh.update(calc_edges=True)
    object_data_add(context, mesh)

#---Add the material
    emit_plan_mat()
    plan = bpy.context.active_object
    mat_name, mat = get_mat_name(plan.data.name)
    plan.active_material = mat
    add_gradient(self, context)
       
#---Change the visibility 
    cobj = bpy.context.object
    cobj.draw_type = 'WIRE'
    cobj.cycles_visibility.camera = False
    cobj.cycles_visibility.shadow = False
    
#---Add 1 simple subsurf
    cobj.modifiers.new("subd", type='SUBSURF')
    cobj.modifiers["subd"].subdivision_type="SIMPLE"
    bpy.ops.object.modifier_apply(modifier="subd")
    cobj.typlight = context.scene.typlight
    cobj.shape = context.scene.shape
    cobj.energy = 10
    
    return(cobj)    

#########################################################################################################

#########################################################################################################
def grid_mesh(self, context, nb_verts, left, start):
    
    section_angle = 360.0 / nb_verts 
    z = 0
    verts = []

#---Create vertices
    for i in range(nb_verts):
        x = math.sin(math.radians(section_angle*i+45)) 
        y = math.cos(math.radians(section_angle*i+45))
        verts.append((x-left, y-start, z))

    return(verts)    

#########################################################################################################

#########################################################################################################
def create_light_grid(self, context):
    verts = []
    edges = []
    faces = []
    listvert = []
    listfaces = []
        
    obj_light = context.active_object
    if obj_light.nbcol < 1: obj_light.nbcol = 1
    if obj_light.nbrow < 1: obj_light.nbrow = 1
    
    gapx = obj_light.gapx
    gapy = obj_light.gapy
    widthx = 1 * obj_light.scale_x
    widthy = 1 * obj_light.scale_y
    left = -((widthx * (obj_light.nbcol-1)) + (gapx * (obj_light.nbcol-1)) ) / 2
    right = left + widthx
    start = -((widthy * (obj_light.nbrow-1)) + (gapy * (obj_light.nbrow-1))) / 2
    end = start + widthy
    i = 0

#---Get the material
    mat_name, mat = get_mat_name(obj_light.data.name)
    
    for x in range(obj_light.nbcol):
    #---Create Verts, Faces on X axis
        nbvert = len(verts)
        verts.extend(grid_mesh(self, context, obj_light.nbside, left, start))
        faces.append([f for f in range((obj_light.nbside + nbvert) - 1, nbvert-1, -1)])  
        start2 = end + gapy
        end2 = start2 + widthy

        for y in range(obj_light.nbrow-1):
        #---Create Verts, Faces on Z axis
            nbvert = len(verts)
            verts.extend(grid_mesh(self, context, obj_light.nbside, left, start2))
            faces.append([f for f in range((obj_light.nbside + nbvert) - 1, nbvert-1, -1)])  
            start2 = end2 + gapy
            end2 = start2 + widthy

        left = right + gapx
        right = left + widthx
        
#---Get the mesh
    old_mesh = obj_light.data
    mesh = bpy.data.meshes.new(name=obj_light.name)
  
    
#---Update the mesh
    mesh.from_pydata(verts, edges, faces)
    mesh.update(calc_edges=True)
    
#---Retrieve the name and delete the old mesh
    for i in bpy.data.objects:
        if i.data == old_mesh:
            i.data = mesh
    name = old_mesh.name
    old_mesh.user_clear()
    bpy.data.meshes.remove(old_mesh)
    mesh.name = name    
    
    context.object.draw_type = 'WIRE'
    
#---Add the material
    cobj = context.active_object
    mat_name, mat = get_mat_name(cobj.data.name)    
    cobj.active_material = mat
    context.object.cycles_visibility.camera = False
    context.object.cycles_visibility.shadow = False
    cobj.modifiers.new("subd", type='SUBSURF')
    cobj.modifiers["subd"].subdivision_type="SIMPLE"
    bpy.ops.object.modifier_apply(modifier="subd")

#########################################################################################################

#########################################################################################################
def create_light_point():
    i = 0
    bpy.ops.object.lamp_add(type='POINT', view_align=False, location=(0,0,0))

    for ob in bpy.context.scene.objects:
        if ob.type != 'EMPTY' and ob.data.name.startswith("Lumi"):
            i += 1
    bpy.context.active_object.data.name = "Lumiere." + str(i)
    cobj = bpy.context.object
    cobj.data.cycles.use_multiple_importance_sampling = True
    cobj.typlight = bpy.context.scene.typlight

#---Link Falloff
    emit = cobj.data.node_tree.nodes["Emission"]
    falloff = cobj.data.node_tree.nodes.new("ShaderNodeLightFalloff")
    falloff.inputs[0].default_value = cobj.energy
    cobj.data.node_tree.links.new(falloff.outputs[1], emit.inputs[1])
    falloff.location = (-200,300) 
    
    return(cobj)

#########################################################################################################

#########################################################################################################
def create_light_sun():
    i = 0
    bpy.ops.object.lamp_add(type='SUN', view_align=False, location=(0,0,0))
    
    for ob in bpy.context.scene.objects:
        if ob.type != 'EMPTY' and ob.data.name.startswith("Lumi"):
            i += 1
    bpy.context.active_object.data.name = "Lumiere." + str(i)
    cobj = bpy.context.object
    cobj.data.cycles.use_multiple_importance_sampling = True
    cobj.typlight = bpy.context.scene.typlight
    emit = cobj.data.node_tree.nodes["Emission"]
    emit.inputs[1].default_value = cobj.energy
    emit.location = (200,0)   
 
    return(cobj)

#########################################################################################################

#########################################################################################################
def create_light_spot():

    i = 0
    bpy.ops.object.lamp_add(type='SPOT', view_align=False, location=(0,0,0))
    for ob in bpy.context.scene.objects:
        if ob.type != 'EMPTY' and ob.data.name.startswith("Lumi"):
            i += 1
    bpy.context.active_object.data.name = "Lumiere." + str(i)
    cobj = bpy.context.object
    cobj.data.cycles.use_multiple_importance_sampling = True
    cobj.typlight = bpy.context.scene.typlight

#---Link Falloff
    emit = cobj.data.node_tree.nodes["Emission"]
    falloff = cobj.data.node_tree.nodes.new("ShaderNodeLightFalloff")
    falloff.inputs[0].default_value = cobj.energy
    cobj.data.node_tree.links.new(falloff.outputs[1], emit.inputs[1])
    falloff.location = (-200,300)   
        
    return(cobj)

#########################################################################################################

#########################################################################################################
def create_light_area():
    i = 0
    bpy.ops.object.lamp_add(type='AREA', view_align=False, location=(0,0,0))
    bpy.context.object.data.shape = 'RECTANGLE'
    for ob in bpy.context.scene.objects:
        if ob.type != 'EMPTY' and ob.data.name.startswith("Lumi"):
            i += 1
    bpy.context.active_object.data.name = "Lumiere." + str(i)
    cobj = bpy.context.object
    cobj.data.cycles.use_multiple_importance_sampling = True
    cobj.typlight = bpy.context.scene.typlight
    
#---Link Falloff
    emit = cobj.data.node_tree.nodes["Emission"]
    falloff = cobj.data.node_tree.nodes.new("ShaderNodeLightFalloff")
    falloff.inputs[0].default_value = cobj.energy
    cobj.data.node_tree.links.new(falloff.outputs[1], emit.inputs[1])
    falloff.location = (-200,100)   

#---Color Ramp Node
    colramp = cobj.data.node_tree.nodes.new(type="ShaderNodeValToRGB")
    colramp.color_ramp.elements[0].color = (1,1,1,1)
    cobj.data.node_tree.links.new(colramp.outputs[0], emit.inputs[0])
    colramp.location = (-300,334)  

#---Dot Product
    dotpro = cobj.data.node_tree.nodes.new("ShaderNodeVectorMath")
    dotpro.operation = 'DOT_PRODUCT'
    cobj.data.node_tree.links.new(dotpro.outputs[1], colramp.inputs[0])
    dotpro.location = (-500, 200)

#---Geometry Node
    geom = cobj.data.node_tree.nodes.new(type="ShaderNodeNewGeometry")
    cobj.data.node_tree.links.new(geom.outputs[1], dotpro.inputs[0])
    cobj.data.node_tree.links.new(geom.outputs[4], dotpro.inputs[1])
    geom.location = (-717,168)         
        
    return(cobj)


#########################################################################################################

#########################################################################################################
def create_light_sky():
    i = 0

    world = bpy.context.scene.world

#---Create a new world if not exist
    if not world:
        bpy.data.worlds.new("World")
        world = bpy.data.worlds['Lumiere_world']

    world.use_nodes= True
    world.node_tree.nodes.clear() 

#---Add a lamp for the sun and drive the sky texture
    cobj = create_light_sun()       
    #Add a blackbody for a "real" sun color
    blackbody = cobj.data.node_tree.nodes.new("ShaderNodeBlackbody")
    emit = cobj.data.node_tree.nodes["Emission"]
    #Horizon daylight kelvin temperature by default
    blackbody.inputs[0].default_value = 4000
    blackbody.location = (-200,0)   
    cobj.data.node_tree.links.new(blackbody.outputs[0], emit.inputs[0])

#---Use multiple importance sampling for the world
    bpy.context.scene.world.cycles.sample_as_light = True
    cobj.data.cycles.use_multiple_importance_sampling = True
    
#---Shaders
    sky = world.node_tree.nodes.new("ShaderNodeTexSky")
    background = world.node_tree.nodes.new('ShaderNodeBackground')
    output = world.node_tree.nodes.new("ShaderNodeOutputWorld")

#---Links
    world.node_tree.links.new(sky.outputs[0], background.inputs[0])
    world.node_tree.links.new(background.outputs[0], output.inputs[0])
    background.inputs[1].default_value = 2.0

#---UI
    sky.location = (-200,0)
    output.location = (200,0)

    cobj.typlight = bpy.context.scene.typlight

    return(cobj)



#########################################################################################################

#########################################################################################################
class AddLight(bpy.types.Operator):
    """Create a new light"""
    bl_idname = "object.add_light"
    bl_label = "Add Light"
    bl_options = {'REGISTER', 'UNDO', 'GRAB_CURSOR'}


    #-------------------------------------------------------------------
    count=0
    modif = False
    energy = 10
    rotz = 0
    create_light = False
    editmode = bpy.props.BoolProperty(default=False)
    act_light = bpy.props.StringProperty()
    #-------------------------------------------------------------------
    
    def transform_light(self, context, event, obj_light):

    #---Start the modifications
        if event.type == 'MOUSEMOVE' and self.doPick and not self.lmb:
            if event.value == 'PRESS':
                bpy.context.window.cursor_modal_set("SCROLL_X")
            #---range : 
                if self.dist_light:
                   
                    self.modif = True
                    delta = self.first_mouse_x - event.mouse_x
                    obj_light.range += delta * 0.2
                    # New raycast if no hit has been found
                    if not hasattr(self, "hit"):
                        hit_world = Vector(obj_light['hit']) + (obj_light.range * Vector(obj_light['dir']))
                    else:
                        hit_world = (self.matrix * self.hit) + (obj_light.range * Vector(obj_light['dir']))
                    obj_light.location = hit_world[0], hit_world[1], hit_world[2]
                    self.dist_light = False

            #---Scale on X and Y axis
                elif self.scale_light:
                    self.modif = True
                    delta = self.first_mouse_x - event.mouse_x
                    
                    if obj_light.typlight in ("Panel", "Pencil"):
                        obj_light.scale[0] += delta*.1
                        obj_light.scale[1] += delta*.1
                    elif obj_light.typlight in ("Point", "Sun", "Spot") :
                        lamp = obj_light.data
                        lamp.shadow_soft_size += delta * .05
                    elif obj_light.typlight =="Sky" :
                        lamp = obj_light.data
                        lamp.shadow_soft_size += delta * .002
                    #---Stick to the maximum of turbidity in the Sky texture
                        if lamp.shadow_soft_size > 0.1:
                            lamp.shadow_soft_size = 0.1
                        bpy.data.worlds['World'].node_tree.nodes["Sky Texture"].turbidity += delta * .05
                    elif obj_light.typlight == "Area":
                        lamp = obj_light.data
                        lamp.size += delta * .05
                        lamp.size_y += delta * .05                     
                            
                    self.scale_light = False

            #---Scale on X - Only for panel type
                elif self.scale_light_x:
                    self.modif = True
                    delta = self.first_mouse_x - event.mouse_x
                    if obj_light.typlight == "Panel":
                        if obj_light.shape == "Star": 


                            obj_light.xtrnrad += delta*.1
                        else:
                            obj_light.scale[0] += delta*.1
                    elif obj_light.typlight == "Area":
                        lamp = obj_light.data
                        lamp.size += delta * .05
                    elif obj_light.typlight == "Spot" :
                        lamp = obj_light.data
                        lamp.spot_size += delta * .05                        
                        
                    self.scale_light_x = False
                    
            #---Scale on Y - Only for panel type
                elif self.scale_light_y:
                    self.modif = True
                    delta = self.first_mouse_x - event.mouse_x
                    if obj_light.typlight == "Panel":
                        if obj_light.shape == "Star": 
                            obj_light.itrnrad += delta*.1
                        else:
                           obj_light.scale[1] += delta*.1
                    elif obj_light.typlight == "Area":
                        lamp = obj_light.data
                        lamp.size_y += delta * .05
                    elif obj_light.typlight == "Spot" :
                        lamp = obj_light.data
                        lamp.spot_blend += delta * .05                          
                        
                    self.scale_light_y = False

            #---Scale Gap Y - Only for the Grid shape
                elif self.scale_gapy:
                    self.modif = True
                    delta = self.first_mouse_x - event.mouse_x
                    obj_light.gapy += delta*.1

            #---Scale Gap X - Only for the Grid shape
                elif self.scale_gapx:
                    self.modif = True
                    delta = self.first_mouse_x - event.mouse_x                    
                    obj_light.gapx += delta*.1

            #---Rotate 'Z' axis
                elif self.rotate_light_z:
                    self.modif = True
                    delta = self.first_mouse_x - event.mouse_x 
                    lightMatrix = obj_light.matrix_world
                    rotaxis = (lightMatrix[0][2], lightMatrix[1][2], lightMatrix[2][2])
                    rot_mat = Matrix.Rotation(math.radians(delta), 4, rotaxis)
                    loc, rot, scale = obj_light.matrix_world.decompose()
                    smat = Matrix()
                    for i in range(3):
                        smat[i][i] = scale[i]
                    mat = Matrix.Translation(loc) * rot_mat * rot.to_matrix().to_4x4() * smat
                    obj_light.matrix_world = mat
                    self.rotz = delta

            #---Energy
                elif self.strength_light:
                    self.modif = True
                    delta = self.first_mouse_x - event.mouse_x
                    if obj_light.typlight in ("Panel", "Sun"):
                        obj_light.energy += delta * 0.1
                    elif obj_light.typlight =="Sky" :
                        obj_light.energy += delta * 0.02
                    else:
                        obj_light.energy += delta * 2
                    light_energy(obj_light)
                    self.strength_light = False             

                else:
                    return {'PASS_THROUGH'}
        #---Release ; Restore the default cursor
            else:
                bpy.context.window.cursor_modal_set("DEFAULT")

                    
        #---End of the modifications
            if event.value == 'RELEASE':
                bpy.context.window.cursor_modal_set("DEFAULT")
                self.modif = False
        
    #---Begin Interactive
        if event.value == 'PRESS' and self.doPick :
        #---Distance of the light from the object
            if (event.alt) and self.doPick :
                self.first_mouse_x = event.mouse_x
                self.dist_light = True

        #---Strength of the light / Gap of the Grid
            elif (event.shift):
                if event.type == 'Z':
                    if obj_light.shape == "Rectangular":
                        self.first_mouse_x = event.mouse_x
                        self.scale_gapy = True
                elif event.type == 'X':
                    if obj_light.shape == "Rectangular":
                        self.first_mouse_x = event.mouse_x
                        self.scale_gapx = True
                else:
                #---Strength of the light
                    self.first_mouse_x = event.mouse_x
                    self.strength_light = True

        #---Scale the light
            elif event.type == 'S' :
                self.first_mouse_x = event.mouse_x
                self.scale_light = True

        #---Scale the light on X axis
            elif event.type == 'X' :
                self.first_mouse_x = event.mouse_x
                self.scale_light_x = True

        #---Scale the light on Y axis
            elif event.type == 'Z' :
                self.first_mouse_x = event.mouse_x
                self.scale_light_y = True

        #---Change the view based on the normal of the object
            elif event.type == 'N':             
                obj_light.normal = not obj_light.normal

        #---Rotate the light on the local 'Z' axis.
            elif event.type == 'R':             
                self.first_mouse_x = event.mouse_x
                self.rotate_light_z = True
            
        #---Type of Fallof
            elif event.type == 'F':
                fallidx = int(obj_light.typfalloff)+1
                if fallidx > 2:
                    fallidx = 0
                obj_light.typfalloff = str(fallidx)

        #---Add a side.
            elif event.type == 'PAGE_UP' and obj_light.typlight == "Panel":
                    if obj_light.shape == "Star":
                        obj_light.nbside += 2
                    else:
                        obj_light.nbside += 1 

        #---Remove a side.
            elif event.type == 'PAGE_DOWN' and obj_light.typlight == "Panel":
                    if obj_light.shape == "Star":
                        obj_light.nbside -= 2
                        if obj_light.nbside < 12: obj_light.nbside = 12
                    else:
                        obj_light.nbside -= 1 
                        if obj_light.nbside < 3: obj_light.nbside = 3

        #---Add a row.
            elif event.type == 'UP_ARROW' and obj_light.typlight == "Panel" and obj_light.shape != "Star":
                obj_light.nbrow += 1 

        #---Remove a row.
            elif event.type == 'DOWN_ARROW' and obj_light.typlight == "Panel" and obj_light.shape != "Star":
                 obj_light.nbrow -= 1 
                 if obj_light.nbrow < 1: obj_light.nbrow = 1
                
        #---Add a column.
            elif event.type == 'RIGHT_ARROW' and obj_light.typlight == "Panel" and obj_light.shape != "Star":
                obj_light.nbcol += 1 
 
        #---Remove a column.
            elif event.type == 'LEFT_ARROW' and obj_light.typlight == "Panel" and obj_light.shape != "Star":
                obj_light.nbcol -= 1 
                if obj_light.nbcol < 1: obj_light.nbcol = 1               
        
    #---End Interactive
        if event.value == 'RELEASE' :
            self.dist_light = False
            self.strength_light = False
            self.scale_light = False
            self.scale_light_x = False
            self.scale_light_y = False
            self.scale_gapy = False
            self.scale_gapx = False
            self.rotate_light_z = False

            
    def check_region(self,context,event):
        if context.area != None:
            if context.area.type == "VIEW_3D":
                t_panel = context.area.regions[1]
                n_panel = context.area.regions[3]
                
                view_3d_region_x = Vector((context.area.x + t_panel.width, context.area.x + context.area.width - n_panel.width))
                view_3d_region_y = Vector((context.region.y, context.region.y+context.region.height))
                
                if event.mouse_x > view_3d_region_x[0] and event.mouse_x < view_3d_region_x[1] and event.mouse_y > view_3d_region_y[0] and event.mouse_y < view_3d_region_y[1]:
                    self.in_view_3d = True
                else:
                    self.in_view_3d = False
            else:
                self.in_view_3d = False         


    def modal(self, context, event):
        #-------------------------------------------------------------------
        coord = (event.mouse_region_x, event.mouse_region_y)
        context.area.tag_redraw()
        obj_light = context.active_object
        self.count +=1
        #v3d = context.space_data
        #rv3d = v3d.region_3d
        setcam = False
        #-------------------------------------------------------------------

    #---Find the limit of the view3d region
        self.check_region(context,event)
        try:
            if self.in_view_3d:


            #---Allow navigation
                if event.type in {'MIDDLEMOUSE'} or event.type.startswith("NUMPAD"): 
                    return {'PASS_THROUGH'}

            #---Orbit mode
                if event.type in ("G"):
                    obj_light.constraints['Track To'].influence = 1
                    return {'PASS_THROUGH'}
                
            #---Zoom Keys
                if (event.type in  {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'} and not 
                   (event.ctrl or event.shift or event.alt)):
                    return{'PASS_THROUGH'}

                if event.type == 'LEFTMOUSE':
                    self.lmb = event.value == 'PRESS'
                    self.click_start = time.time()

            #---RayCast the light
                if self.doPick is True and self.modif is False : 
                    if self.lmb :
                        raycast_light(self, obj_light.range, context, event, coord)
                        bpy.context.window.cursor_modal_set("SCROLL_XY")
                    self.create_light = True
                    
            #---Create Lights     
                if (event.ctrl) and event.type == 'LEFTMOUSE' and not self.editmode:
                    if event.value == 'PRESS':
                        self.doPick = True
                        self.dist_light = False
                        self.scale_gapy = False
                        self.scale_gapx = False
                        self.scale_light = False
                        self.scale_light_x = False
                        self.scale_light_y = False
                        self.strength_light = False
                        self.rotate_light_z = False

                    #---Define the different shape for the panel light
                        if context.scene.typlight == "Panel":
                            if context.scene.shape == "Star":
                                obj_light = create_light_star(self, context, 12, 1, 0.5)
                            elif context.scene.shape == "Rectangular" :
                                obj_light = create_light_circle(self, context, 4)
                                obj_light.nbside = 4
                                obj_light.nbrow = 1
                                obj_light.nbcol = 1
                            elif context.scene.shape == "Circle" :
                                obj_light = create_light_circle(self, context, 28)
                                obj_light.nbside = 28

                    #---Default lamp light
                        elif context.scene.typlight == "Point":
                            obj_light = create_light_point()
                        elif context.scene.typlight == "Sun":
                            obj_light = create_light_sun()                    
                        elif context.scene.typlight == "Spot":
                            obj_light = create_light_spot()    
                        elif context.scene.typlight == "Area":
                            obj_light = create_light_area()
                        elif context.scene.typlight == "Sky":
                            obj_light = create_light_sky() 
                            obj_light.energy = 2                   
                        light_energy(obj_light)
                        raycast_light(self, obj_light.range, context, event, coord)
                        empty = create_empty(self, context, obj_light.data.name)
            else:
                return {'PASS_THROUGH'}
            
        #---Transform the light
            if self.create_light :
                editmode = False
                obj_light = context.active_object

                if obj_light.constraints['Track To'].influence != 0:
                    bpy.ops.object.visual_transform_apply()
                    obj_light.constraints['Track To'].influence = 0
                #---Get the new direction.
                    lightMatrix = obj_light.matrix_world
                    theAxis = (lightMatrix[0][2], lightMatrix[1][2], lightMatrix[2][2])
                    obj_light['dir'] = theAxis
                
                str1 ="Range: ALT || Energy: LSHIFT || Normal: N || Fallof: F || "
                str2 =" "
                if context.scene.typlight in ("Panel"):
                    str2 = "Scale: S+Mouse Move || Scale X: X || Scale Y: Z || Arrows: Grid || Page UP/DOWN: Shape"
                elif context.scene.typlight in ("Area"):
                    str2 = "Scale: S+Mouse Move || Scale X: X || Scale Y: Z"
                else:
                    str2 = "Softness: S"
                text_header = str1 + str2 + " || Confirm: RMB"
                context.area.header_text_set(text_header)
                self.transform_light(context, event, obj_light)
            
                if event.type in {'RIGHTMOUSE', 'ESC'}:
                    obj_light.constraints['Track To'].influence = 0
                    bpy.context.area.header_text_set()
                    bpy.context.window.cursor_modal_set("DEFAULT")
                    bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
                    editmode = False
                    return {'FINISHED'}
                else:
                    return {'RUNNING_MODAL'}

        #---Undo before creating the light
            if event.type in {'RIGHTMOUSE', 'ESC'}:
                bpy.context.area.header_text_set()
                bpy.context.window.cursor_modal_set("DEFAULT")
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
                return{'FINISHED'}

            return {'PASS_THROUGH'}
        except:
            bpy.context.window.cursor_modal_set("DEFAULT")
            bpy.context.area.header_text_set()
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            return {'FINISHED'}

    def execute (self, context):
        for ob in bpy.context.scene.objects:
            if ob.type != 'EMPTY' and ob.data.name.startswith("Lumi"):
                ob.select = False
        return {'FINISHED'}


    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode == 'OBJECT'


    def invoke(self, context, event):
        for area in context.window.screen.areas:
            if area.type == 'VIEW_3D' :
                for space in area.spaces:
                    if space.type == 'VIEW_3D':                       
                        self.rv3d = context.region_data
                        self.region = context.region
                        self._initial_location = self.rv3d.view_location.copy()
                        self._initial_rotation = self.rv3d.view_rotation.copy()                        
                        if self.editmode:
                            context.scene.objects.active = bpy.data.objects[self.act_light] 
                        obj_light = bpy.context.active_object
                        self.doPick = False
                        self.lmb = False
                        if obj_light is not None and obj_light.type != 'EMPTY' and obj_light.data.name.startswith("Lumiere") and self.editmode:
                            for ob in bpy.context.scene.objects:

                                if ob.type != 'EMPTY' : 
                                    ob.select = False
                            obj_light.select = True
                            self.direction = obj_light.rotation_euler
                            self.hit_world = obj_light.location
                            self.doPick = True                            
                        context.area.header_text_set("Add light: CTRL+LMB || Confirm: ESC or RMB")
                        args = (self, context)
                        self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_callback_px, args, 'WINDOW', 'POST_PIXEL')                                                    
                        context.window_manager.modal_handler_add(self)
                        return {'RUNNING_MODAL'}
                    else:
                        self.report({'WARNING'}, "No active View3d detected !")
                        return {'CANCELLED'}
                             
#########################################################################################################

#########################################################################################################
def update_sky(self, context):
    cobj = context.active_object

#---Credits : https://www.youtube.com/watch?v=YXso7kNzxIU
    xAng = bpy.data.objects[cobj.name].rotation_euler[0]
    yAng = bpy.data.objects[cobj.name].rotation_euler[1]
    zAng = bpy.data.objects[cobj.name].rotation_euler[2]
    
    vec = Vector((0.0,0.0,1.0))
    xMat = Matrix(((1.1,0.0,0.0), (0.0, math.cos(xAng), -math.sin(xAng)), (0.0, math.sin(xAng), math.cos(xAng))))
    yMat = Matrix(((math.cos(yAng), 0.0, math.sin(yAng)), (0.0, 1.0, 0.0), (-math.sin(yAng), 0.0, math.cos(yAng))))
    zMat = Matrix(((math.cos(zAng), -math.sin(zAng), 0.0), (math.sin(zAng), math.cos(zAng), 0.0), (0.0, 0.0, 1.0)))
    
    vec = xMat * vec
    vec = yMat * vec
    vec = zMat * vec

    bpy.data.worlds['World'].node_tree.nodes['Sky Texture'].sun_direction = vec 
    blackbody = cobj.data.node_tree.nodes['Blackbody']
    #4000 -> HORIZON // 5780 -> Daylight
    blackbody.inputs[0].default_value = 4000 + (1780 * vec.z)     
    bpy.data.worlds["World"].use_nodes = cobj.skynode
                
#########################################################################################################

#########################################################################################################

def update_mat(self, context):
    cobj = self

    if cobj.type != 'EMPTY' and cobj.data.name.startswith("Lumiere"):

        if cobj.type == "MESH":
            mat_name, mat = get_mat_name(cobj.data.name)
            emit = mat.node_tree.nodes["Emission"]
            emit.inputs[0].default_value = cobj.lightcolor
            imtext = mat.node_tree.nodes['Image Texture']
            invert = mat.node_tree.nodes['Invert']
            invert.inputs[0].default_value = 1
            falloff = mat.node_tree.nodes["Light Falloff"]
            mat.node_tree.nodes["Light Falloff"].inputs[0].default_value = cobj.energy
            mat.node_tree.nodes["Light Falloff"].inputs[1].default_value = cobj.smooth
            mat.node_tree.links.new(falloff.outputs[int(cobj.typfalloff)], emit.inputs[1])            
            
            if cobj.filepath != "" and not cobj.gradient:
                if cobj.unlink == True:
                    cobj.filepath = ""
                    cobj.unlink = False
                else:

                    try:
                        img = bpy.data.images.load(cobj.filepath, check_existing=True)
                    except:
                        raise NameError("Cannot load image %s" % path)
                    imtext.image = img
                    mat.node_tree.links.new(imtext.outputs[0], emit.inputs[0])
                    mat.node_tree.links.new(imtext.outputs[0], invert.inputs[1])
                    invert.inputs[0].default_value = 0
            else:
                if imtext.outputs['Color'].links:
                    mat.node_tree.links.remove(imtext.outputs['Color'].links[0])


            if cobj.gradient:
                colramp = mat.node_tree.nodes['ColorRamp']
                grad = mat.node_tree.nodes['Gradient Texture']
                textmap = mat.node_tree.nodes['Mapping']
                geom = mat.node_tree.nodes['Geometry.001']
                coord = mat.node_tree.nodes['Texture Coordinate']
                
                colramp.color_ramp.interpolation = cobj.gradinterpo
                mat.node_tree.links.new(colramp.outputs[1], invert.inputs['Fac'])
                mat.node_tree.links.new(colramp.outputs[0], emit.inputs['Color'])
                mat.node_tree.nodes['Gradient Texture'].gradient_type = cobj.typgradient
                
                if cobj["typgradient"] in (1,4) : #LINEAR - DIAGONAL
                    mat.node_tree.links.new(textmap.outputs[0], grad.inputs['Vector'])
                    mat.node_tree.links.new(coord.outputs[0], textmap.inputs['Vector'])
                elif cobj["typgradient"] in (2,3) : #QUAD - EASING
                    mat.node_tree.links.new(textmap.outputs[0], grad.inputs['Vector'])
                    mat.node_tree.links.new(geom.outputs[5], textmap.inputs['Vector'])
                elif cobj["typgradient"] in (5, 6, 7) : #SPHERICAL - QUADRATIC_SPHERE - RADIAL
                    mat.node_tree.links.new(textmap.outputs[0], grad.inputs['Vector'])
                    mat.node_tree.links.new(coord.outputs[3], textmap.inputs['Vector'])            
            else:
                if mat.node_tree.nodes['ColorRamp'].outputs['Color'].links:
                    mat.node_tree.links.remove(mat.node_tree.nodes['ColorRamp'].outputs['Color'].links[0])
                    mat.node_tree.links.remove(mat.node_tree.nodes['ColorRamp'].outputs['Alpha'].links[0])

        else:
            mat = cobj.data

            if cobj.typlight in ("Sun", "Sky"):
                emit = mat.node_tree.nodes["Emission"]
                emit.inputs[0].default_value = cobj.lightcolor
                emit.inputs[1].default_value = cobj.energy   
            else:     
                falloff = mat.node_tree.nodes["Light Falloff"]
                emit = mat.node_tree.nodes["Emission"]
                emit.inputs[0].default_value = cobj.lightcolor
                mat.node_tree.nodes["Light Falloff"].inputs[0].default_value = cobj.energy
                mat.node_tree.nodes["Light Falloff"].inputs[1].default_value = cobj.smooth
                mat.node_tree.links.new(falloff.outputs[int(cobj.typfalloff)], emit.inputs[1])
                if cobj.gradient:
                    colramp = mat.node_tree.nodes['ColorRamp']
                    colramp.color_ramp.interpolation = cobj.gradinterpo
                    mat.node_tree.links.new(colramp.outputs[0], emit.inputs['Color'])
                else:
                    if mat.node_tree.nodes['ColorRamp'].outputs['Color'].links:
                        mat.node_tree.links.remove(mat.node_tree.nodes['ColorRamp'].outputs['Color'].links[0])
            
#########################################################################################################

#########################################################################################################
def show_hide_light(self, context):
    cobj = self
    if not cobj.hide:
        cobj.hide = True
        cobj.hide_render = True
    else:
        cobj.hide = False
        cobj.hide_render = False

#########################################################################################################

#########################################################################################################
def select_only(self, context):
    cobj = self
    for ob in bpy.context.scene.objects:
            if ob.type != 'EMPTY' and ob.data.name.startswith("Lumiere") and (ob.name != cobj.name) and cobj.show:
                if cobj.select_only:
                    if ob.show: ob.show = False
                else:
                    if not ob.show: ob.show = True

#########################################################################################################

#########################################################################################################
def update_gradient_pos(self, context):
    index = eval(str(repr(self) + ".nbr"))
    mat_name, mat = get_mat_name(context.scene.objects.active.data.name)
    
    if context.active_object.typlight not in ("Panel", "Pencil"):
        mat = context.active_object.data
        
    cobj = context.active_object
    colramp = mat.node_tree.nodes['ColorRamp'].color_ramp
    colramp.elements[index].position = cobj.prop_group.coll[index].pos

def update_gradient_col(self, context):
    index = eval(str(repr(self) + ".nbr"))
    mat_name, mat = get_mat_name(context.scene.objects.active.data.name)
    
    if context.active_object.typlight not in ("Panel", "Pencil"):
        mat = context.active_object.data
    cobj = context.active_object
    colramp = mat.node_tree.nodes['ColorRamp'].color_ramp
    colramp.elements[index].color = cobj.prop_group.coll[index].col

class Entry(PropertyGroup):
    pos = FloatProperty(name="", min=0, max=1, precision=2, default=0.5, update=update_gradient_pos)
    col = FloatVectorProperty(name="", min= 0, max= 1, subtype = "COLOR",  size = 4, update=update_gradient_col)
    nbr = IntProperty()

class Group(PropertyGroup):
    coll = CollectionProperty(type=Entry)
    index = IntProperty()

class SCENE_OT_add_gradient(Operator):
    bl_idname = "object.add_gradient"
    bl_label = "Gradient"
    
    act_light = bpy.props.StringProperty()
    
    def execute(self, context):
        
        if self.act_light != "": 
            context.scene.objects.active = bpy.data.objects[self.act_light] 
        else:
            self.act_light = context.active_object.name
        
        cobj = context.active_object
        
        if bpy.data.objects[self.act_light].show == True:
        #---Initialise the gradient
            context.active_object.gradient = True
        else:
            self.report({'INFO'}, 'The light must be in Show Mode')
        return {'FINISHED'}

#########################################################################################################

#########################################################################################################

# range from the object
bpy.types.Object.range = FloatProperty(
                            name="Range ",
                            description="Range from the object",
                            min=-100, max=100.0,
                            default=0.5,
                            precision=2,
                            subtype='DISTANCE',
                            unit='LENGTH',
                            )
                           
# Strength of the light
bpy.types.Object.energy = FloatProperty(
                          name="Strength",
                          description="Strength of the light",
                          min=0.01, max=100000.0,
                          default=10,
                          precision=2,
                          subtype='NONE',
                          unit='NONE',
                          update=update_mat)    
                           
# Smooth the light falloff
bpy.types.Object.smooth = FloatProperty(
                          name="",
                          description="Smooth the light falloff",
                          min=0.01, max=1000.0,
                          default=0,
                          precision=2,
                          subtype='NONE',
                          unit='NONE',
                          update=update_mat)    
                                                     
# Color of the light
bpy.types.Object.lightcolor = FloatVectorProperty(  
                              name = "",
                              subtype = "COLOR",
                              size = 4,
                              min = 0.0,
                              max = 1.0,
                              default = (0.8,0.8,0.8,1.0),
                              update=update_mat)    

bpy.types.Object.objtarget = StringProperty(
                           name="Target",
                           description="Select an object",)

bpy.types.Object.typlight = EnumProperty(name="Type ", 
                           items=(
                           ("Panel", "Panel light", "", 1),
                           ("Point", "Point light", "", 2),
                           ("Sun", "Sun light", "", 3),
                           ("Spot", "Spot light", "", 4),
                           ("Area", "Area light", "", 5),
                           ("Sky", "Sky Background", "", 6),
                           ), 
                           default='Panel')

bpy.types.Scene.typlight = EnumProperty(name="", 
                           items=(
                           ("Panel", "Panel light", "", 1),
                           ("Point", "Point light", "", 2),
                           ("Sun", "Sun light", "", 3),
                           ("Spot", "Spot light", "", 4),
                           ("Area", "Area light", "", 5),
                           ("Sky", "Sky Background", "", 6),
                           ), 
                           default='Panel')

bpy.types.Object.typfalloff = EnumProperty(name="", 
                           items=(
                           ("0", "Quadratic falloff", "", 1),
                           ("1", "Linear falloff", "", 2),
                           ("2", "Constant falloff", "", 3),
                           ), 
                           default='0',
                           update=update_mat)    

bpy.types.Scene.shape = EnumProperty(name="Shape", 
                           items=(
                           ("Rectangular", "Rectangular shape", "", 1),
                           ("Circle", "Circle shape", "", 2),
                           ("Star", "Star shape", "", 3),                          
                           ), 
                           default="Rectangular")  
                           
bpy.types.Object.shape = EnumProperty(name="", 
                           items=(
                           ("Rectangular", "Rectangular shape", "", 1),
                           ("Circle", "Circle shape", "", 2),
                           ("Star", "Star shape", "", 3),
                           ), 
                           default="Rectangular")  

bpy.types.Object.gradient = BoolProperty(
                            name="Gradient mode",
                            description="Enable/Disable color or gradient mode ",
                            default=False,
                            update=update_mat)    

bpy.types.Object.typgradient = EnumProperty(name="Gradient ", 
                           description="Gradient type",
                           items=(
                           ("LINEAR", "Linear", "", 1),
                           ("QUADRATIC", "Quad", "", 2),
                           ("EASING", "Easing", "", 3),
                           ("DIAGONAL", "Diagonal", "", 4),
                           ("SPHERICAL", "Spherical", "", 5),
                           ("QUADRATIC_SPHERE", "Quad Sphere", "", 6),
                           ("RADIAL", "Radial", "", 7),
                           ), 
                           default='LINEAR',
                           update=update_mat)  

bpy.types.Object.gradinterpo = EnumProperty(name="", 
                           description="Interpolation type",
                           items=(
                           ("EASE", "Ease", "", 1),
                           ("CARDINAL", "Cardinal", "", 2),
                           ("LINEAR", "Linear", "", 3),
                           ("B_SPLINE", "B-Spline", "", 4),
                           ("CONSTANT", "Constant", "", 5),
                            ),
                           default='LINEAR',
                           update=update_mat) 

bpy.types.Object.skynode = BoolProperty(
                            name="Sky node",
                            description="Enable/Disable nodes for world environment ",
                            default=True,
                            update=update_sky)

bpy.types.Object.filepath = StringProperty(
                           name = "Texture", 
                           subtype = "FILE_PATH",
                           update=update_mat) 

bpy.types.Object.unlink = BoolProperty(
                           name="",
                           description="Unlink image texture ",
                           default=False,
                           update=update_mat)  
                           
bpy.types.Object.nbside = IntProperty(
                           name="Nbr Side",
                           description="Number side of the panel light",
                           min=3, max=99,
                           default=4,
                           update=update_shape)                                                                

bpy.types.Object.nbrow = IntProperty(
                           name="Nbr Row",
                           description="Number of row for the grid panel",
                           min=1, max=99,
                           default=1,
                           update=update_shape) 

bpy.types.Object.nbcol = IntProperty(
                           name="Nbr Column",
                           description="Number of column for the grid panel",
                           min=1, max=99,
                           default=1,
                           update=update_shape) 

bpy.types.Object.scale_x = FloatProperty(
                           name="Scale X",
                           description="Scale the grid panel on X axis",
                           default=1,
                           min=1, max=999,
                           precision=3,
                           subtype='DISTANCE',
                           unit='LENGTH',
                           step=0.1,                                
                           update=update_shape) 

bpy.types.Object.scale_y = FloatProperty(
                           name="Scale Y",
                           description="Scale the grid panel on Y axis",
                           default=1,
                           min=1, max=999,
                           precision=3,
                           subtype='DISTANCE',
                           unit='LENGTH',
                           step=0.1,                           
                           update=update_shape) 

bpy.types.Object.xtrnrad = FloatProperty(
                           name="Scale Ext",
                           description="Scale the external radius",
                           default=1,
                           min=1, max=999,
                           precision=3,
                           subtype='DISTANCE',
                           unit='LENGTH',
                           step=0.1,                                
                           update=update_shape) 

bpy.types.Object.itrnrad = FloatProperty(
                           name="Scale Int",
                           description="Scale the internal radius",
                           default=.5,
                           min=.1, max=999,
                           precision=3,
                           subtype='DISTANCE',
                           unit='LENGTH',
                           step=0.1,                           
                           update=update_shape) 
                           
bpy.types.Object.gapx = FloatProperty(
                           name="Gap Row",
                           description="Gap between row for the grid panel",
                           min=0, max=999,
                           default=1,
                           precision=3,
                           subtype='DISTANCE',
                           unit='LENGTH',
                           step=0.1,                           
                           update=create_light_grid) 

bpy.types.Object.gapy = FloatProperty(
                           name="Gap Column",
                           description="Gap between column for the grid panel",
                           min=0, max=999,
                           default=1,
                           precision=3,
                           subtype='DISTANCE',
                           unit='LENGTH',
                           step=0.1,                           
                           update=create_light_grid)                                                                               
                           
bpy.types.Object.interp = FloatProperty(
                           name="Interpolation",
                           description="Interpolation of the angle / position of the light",
                           min=0, max=.9,
                           default=0,
                           precision=3,
                           subtype='NONE',
                           unit='NONE',
                           step=0.5)     

bpy.types.Object.normal = bpy.props.BoolProperty(default=False)
bpy.types.Object.expanded = bpy.props.BoolProperty(default=False)
bpy.types.Object.show = bpy.props.BoolProperty(default=True, update=show_hide_light)    
bpy.types.Object.select_only = bpy.props.BoolProperty(default=False, update=select_only)    
#########################################################################################################

#########################################################################################################

class PreSelAddonPreferences(bpy.types.Panel):
    bl_idname = "mesh.lumiere"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Lumieres"
    bl_label = "Lumieres"

    def draw_header(self, context):
        layout = self.layout
        cobj = context.object
        #layout.prop(cobj, "select", text="")
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        cobj = context.active_object
        col = layout.column()
        row = col.row(align=True)

        if context.mode != 'OBJECT' :
            row.label(text="Must be in OBJECT mode",icon='BLANK1')
        else:
#----------------------------------
# ADD MODE
#----------------------------------                    
        #---Type Light / Shape          
            col = layout.column(align=True)
            row = col.row(align=True)
            row.operator("object.add_light", text="Add Light", icon='BLANK1').editmode = False  

        #---Remove the light and the empty target
            if cobj is not None and cobj.type != 'EMPTY' and hasattr(cobj, "data") and cobj.data.name.startswith("Lumiere"):
                op = row.operator("object.remove", text="Remove light", icon='BLANK1')
                op.name = cobj.data.name   

            row = col.row(align=True)
            row.prop(scene, "typlight")
            if scene.typlight == "Panel": 
                row.prop(scene, "shape", text="")

#----------------------------------
# EDIT MODE
#----------------------------------         
            l = -1      
        #---For each layer
            for layer in bpy.data.scenes[scene.name].layers:
                l += 1
                objects_on_layer = [obj for obj in context.scene.objects if obj.type != 'EMPTY' and obj.layers[l] and layer == True and obj.data.name.startswith("Lumiere")]
                if layer == True and objects_on_layer != []: 
                
                #---Look for light in each layer
                    for object in objects_on_layer:
                        col = layout.column(align = True)
                        box = col.box()
                        row = col.row(align=True)

                        if object.type != 'EMPTY' and object.data.name.startswith("Lumiere") :
                        
                            cobj = bpy.context.scene.objects[object.name]

                            col = layout.column(align = True)


                            row = box.row(align=True)

                            row.prop(cobj, "expanded",icon="DOWNARROW_HLT" if cobj.expanded else "RIGHTARROW",icon_only=True, emboss=False)
                            row.prop(cobj, "select_only", icon='%s' % 'GHOST_DISABLED' if cobj.show else 'GHOST_ENABLED', text='', emboss=False)

                            op = row.operator("object.add_light", icon='ACTION_TWEAK', text='', emboss=False)
                            op.editmode = True
                            op.act_light = cobj.name   
                            
                            if cobj.expanded and cobj.show == False:
                                row.alert = True
                            
                            if cobj.show :
                                if cobj.type == 'LAMP':
                                    row.prop(cobj, "show", text='', icon='%s' % ('LAMP_' + cobj.data.type) ,  icon_only=True, emboss=False)
                                else:
                                    if cobj.typlight == "Pencil":
                                        row.prop(cobj, "show", text='', icon='%s' % 'GREASEPENCIL',  icon_only=True, emboss=False)
                                    else: 
                                        row.prop(cobj, "show", text='', icon='%s' % 'OUTLINER_OB_LATTICE',  icon_only=True, emboss=False)
                                
                            else:
                                row.prop(cobj, "show", icon='%s' % 'OUTLINER_OB_LAMP' if cobj.show else 'LAMP', text='', emboss=False, translate=False)
                            row.alert = False
                            
                            if not cobj.gradient: 
                                split = row.split(0.8, align=True)
                            else :
                                split = row
                                
                            if bpy.context.active_object== cobj: split.alert = True
                            split.prop(cobj, "name", text='')
                            split.alert = False

                            if not cobj.gradient: 
                                split.prop(cobj, "lightcolor")
                            else: 
                                split.label(text="",icon='COLOR')

                            if cobj.expanded:
                                row = box.row(align=True)

                            #---Search list for the target object
                                row.prop_search(cobj, "objtarget", scene, "objects")
                                col = box.column(align=True)
                                row = col.row(align=True)
                                if cobj.typlight != "Sky" : 
                                    if cobj.typlight == "Panel":
                                        row.prop(cobj.data.materials['Mat_'+cobj.data.name].cycles, "sample_as_light", text='MIS', toggle=True)
                                    else:
                                        row.prop(cobj.data.cycles, "use_multiple_importance_sampling", text='MIS', toggle=True)
                                        row.prop(cobj.data.cycles, "cast_shadow", text='Shadows', toggle=True)
                                    row.prop(cobj.cycles_visibility, "diffuse", text='Diff', toggle=True)
                                    row.prop(cobj.cycles_visibility, "glossy", text='Spec', toggle=True)
                                
                            #---Energy / Smooth
                                col = box.column(align=True)
                                row = col.row(align=True)
                                row.prop(cobj, "energy")
                                if cobj.typlight != "Sky":

                                    if cobj.typlight != "Sun":
                                    #---Falloff
                                        row = col.row(align=True)
                                        split = row.split(0.6, align=True)
                                        split.prop(cobj, "typfalloff") 
                                        
                                    #---Smooth
                                        split.prop(cobj, "smooth")

                                else:
                                    row = col.row(align=True)
                                    row.prop(cobj, "skynode", text="World node", icon="BLANK1")

                            #---Gradient UILIST for panel
                                if cobj.typlight in ("Panel", "Pencil", "Area"):
                                 
                                    if not cobj.gradient:
                                        col = box.column(align=True)
                                        row = col.row(align=True)
                                        if cobj.expanded and cobj.show == False:
                                            row.alert = True
                                        row.operator("object.add_gradient", icon='BLANK1').act_light = cobj.name
                                        row.alert = False
                                    else:
                                        col = box.column(align=True)
                                        row = col.row(align=True)
                                        row.prop(cobj, "gradient", text='Gradient type :', icon='BLANK1')
                                        row = box.row(align=True)
                                        
                                        if cobj.typlight in ("Panel", "Pencil"): row.prop(cobj, "typgradient", text="")

                                        #---Template Color Ramp
                                        #---Accesses the color ramp from the material
                                        colramp = cobj.data.materials['Mat_' + cobj.data.name].node_tree.nodes['ColorRamp']
                                        box.template_color_ramp(colramp, "color_ramp", expand=True)
                                       
                                col = box.column(align=True)
                                row = col.row(align=True)
                                if not cobj.gradient and cobj.typlight != "Sky":
                                    if cobj.typlight in ("Panel", "Pencil"):
                                        row = col.row(align=True)
                                        if cobj.filepath == "" and cobj.unlink == False:
                                            row.prop(cobj, "filepath")
                                        else:
                                            row.prop(cobj, "unlink", icon='ZOOMOUT')
                                            row.prop(cobj, "filepath")



#########################################################################################################

#########################################################################################################

def register():
    bpy.utils.register_module(__name__)
    bpy.types.Object.prop_group = PointerProperty(type=Group)
    
def unregister():
    bpy.utils.unregister_module(__name__)   
    del bpy.types.Object.prop_group
    
if __name__ == "__main__":
    register()
