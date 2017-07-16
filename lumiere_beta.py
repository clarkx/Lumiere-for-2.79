# -*- coding:utf-8 -*-

# ***** BEGIN GPL LICENSE BLOCK *****
#
#   Lumiere : Blender addon for Blender 3D
#   Copyright (C) 2017 Cédric Brandin
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
# 
# ***** END GPL LICENCE BLOCK *****


bl_info = {
    "name": "Lumiere",
    "author": "Cédric Brandin (Clarkx)",
    "version": (0, 0, 8),
    "blender": (2, 76, 3),
    "location": "View3D",
    "description": "Interactive Lighting Add-on",
    "warning": "Beta version",
    "wiki_url": "https://github.com/clarkx/Lumiere/wiki",
    "tracker_url": "https://github.com/clarkx/Lumiere/issues",
    "category": "Render"}

import bpy, bgl, os, blf
from bpy_extras import view3d_utils
from mathutils import Vector, Matrix, Quaternion, Euler
from bpy.types import PropertyGroup, UIList, Panel, Operator
from bpy.props import IntProperty, FloatProperty, BoolProperty, FloatVectorProperty, EnumProperty, StringProperty, CollectionProperty, PointerProperty
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from collections import defaultdict, Counter
from bpy_extras.view3d_utils import location_3d_to_region_2d
import textwrap
import math
import bmesh
import time
import json

#########################################################################################################

#########################################################################################################
def update_panel(self, context):
    """Update the UI panel of the addon from the preferences"""
    try:
        bpy.utils.unregister_class(LumierePreferences)
    except:
        pass
    LumierePreferences.bl_category = context.user_preferences.addons[__name__].preferences.category
    bpy.utils.register_class(LumierePreferences)
    
#########################################################################################################

#########################################################################################################
class LumierePrefs(bpy.types.AddonPreferences):
    """Preferences of the keymap for the interactive mode"""
    bl_idname = __name__

    #Align the light based on the view reflection or the normal of the target object
    bpy.types.Scene.Key_Normal = StringProperty(
                               name="View",
                               description="Align the light with the Reflection or the Normal",
                               maxlen=1,
                               default="N")

    #Rotate the light on the Z axis
    bpy.types.Scene.Key_Rotate = StringProperty(
                               name="Rotate",
                               description="Rotate the light on the Z axis",
                               maxlen=1,
                               default="R")

    #Change the type of the falloff
    bpy.types.Scene.Key_Falloff = StringProperty(
                               name="Falloff",
                               description="Change the Falloff type of the light",
                               maxlen=1,
                               default="F")

    #Scale the light on X and Y axis
    bpy.types.Scene.Key_Scale = StringProperty(
                               name="Scale",
                               description="Scale the light on the Y axis",
                               maxlen=1,
                               default="S")     

    #Scale the light on Y axis                             
    bpy.types.Scene.Key_Scale_Y = StringProperty(
                               name="Scale Y",
                               description="Scale the light on the Y axis",
                               maxlen=1,
                               default="Z")

    #Scale the light on X axis                             
    bpy.types.Scene.Key_Scale_X = StringProperty(
                               name="Scale X",
                               description="Scale the light on the X axis",
                               maxlen=1,
                               default="X")

    #Orbit mode                        
    bpy.types.Scene.Key_Orbit = StringProperty(
                               name="Orbit",
                               description="Orbit mode",
                               maxlen=1,
                               default="G")
                                                           
    #Distance of the light
    bpy.types.Scene.Key_Distance = EnumProperty(name="Distance", 
                               description="Distance from the target object to the light",
                               items=(
                               ("shift", "shift", "shift", 1),                         
                               ("alt", "alt", "alt", 2),
                               ("ctrl", "ctrl", "ctrl", 3),
                                ),
                               default="alt")                                
                               
    #Energy of the light
    bpy.types.Scene.Key_Strength = StringProperty(
                                name="Energy", 
                                description="Energy of the light",
                                maxlen=1,
                                default="E")
                                                           
    #Invert the direction of the light
    bpy.types.Scene.Key_Invert = StringProperty(
                               name="Invert", 
                               description="Invert the direction of the light",
                               maxlen=1,
                               default="I")

    #Grid Gap 
    bpy.types.Scene.Key_Gap = EnumProperty(name="Grid Gap", 
                               description="Grid Gap",
                               items=(
                               ("shift", "shift", "shift", 1),                         
                               ("alt", "alt", "alt", 2),
                               ("ctrl", "ctrl", "ctrl", 3),
                                ),
                               default="shift") 
                               
    #HUD Color
    bpy.types.Scene.HUD_color = FloatVectorProperty(    
                                  name = "",
                                  subtype = "COLOR",
                                  size = 4,
                                  min = 0.0,
                                  max = 1.0,
                                  default = (1.0, 0.09, 0.3, 0.8))                                 

    category = bpy.props.StringProperty(
            name="Category",
            description="Choose a name for the category of the panel",
            default="Lumiere",
            update=update_panel,
            )
                               
    def draw(self, context):
        scene = context.scene
        layout = self.layout
        row = layout.row()
        row.prop(scene, "Key_Normal")
        row.prop(scene, "Key_Rotate")
        row.prop(scene, "Key_Falloff")
        row = layout.row()
        row.prop(scene, "Key_Scale")
        row.prop(scene, "Key_Scale_Y")
        row.prop(scene, "Key_Scale_X")
        row = layout.row()
        row.prop(scene, "Key_Orbit")
        row.prop(scene, "Key_Distance")
        row.prop(scene, "Key_Strength")
        row = layout.row()
        row.prop(scene, "Key_Invert")
        row.prop(scene, "Key_Gap")
        row.prop(self, "category")
        row = layout.row()
        row.prop(scene, "HUD_color", text="HUD Color")
        # split = row.split(0.5, align=False)
        # split.prop(self, "category")
        # split.prop(scene, "HUD_color", text="HUD Color")
        
#########################################################################################################

#########################################################################################################
def draw_text(color, font_id, left, height, text):
    """Display the differents informations in the interactive mode"""
    bgl.glColor4f(*color)
    blf.enable(font_id,blf.SHADOW)
    blf.shadow(font_id, 5, color[0]-.5, color[1]-.5, color[2]-.5, color[3]-.5) # blur_size being 0 means colored Font, 3 or 5 means a colored rim around the font.# Note that you can only use (0, 3, 5).
    blf.shadow_offset(font_id,0,0)
    blf.position(font_id, left, height, 0)
    blf.draw(font_id, text)
    blf.disable(font_id,blf.SHADOW)

def draw_line(x, y, color, width, text_width):
    """Draw a simple line to separate the informations"""
    bgl.glLineWidth(width)
    bgl.glColor4f(*color)
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glBegin(bgl.GL_LINES)
    bgl.glVertex2f(x, y)
    bgl.glVertex2f(x+text_width, y)
    bgl.glEnd()
    bgl.glLineWidth(1)

def draw_circle_2d(color, cx, cy, r):
    """Draw a circle in bgl for HUD"""
    #http://slabode.exofire.net/circle_draw.shtml
    num_segments = 4 
    if num_segments < 1:
        num_segments = 1
    theta = 2 * 3.1415926 / num_segments
    c = math.cos(theta) 
    s = math.sin(theta)
    x = r 
    y = 0
    bgl.glColor4f(*color)
    bgl.glEnable(bgl.GL_LINE_SMOOTH)
    bgl.glBegin(bgl.GL_LINE_LOOP)
    for i in range (num_segments):
        bgl.glVertex2f(x + cx, y + cy)
        t = x
        x = c * x - s * y
        y = s * t + c * y
    bgl.glEnd() 

def draw_bounding_box(context, softbox, matrix, c):
    """Draw the bounding bow of object in bgl"""
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glColor4f(c[0], c[1], c[2], 0.4)
    bgl.glLineWidth(5)
    bbox_mat = [matrix * Vector(b) for b in softbox.bound_box]
    bbox = [location_3d_to_region_2d(context.region, context.space_data.region_3d, b) for b in bbox_mat]
    # bgl.glDisable(bgl.GL_DEPTH_TEST)
    bgl.glBegin(bgl.GL_LINE_STRIP)
    bgl.glVertex2f(*bbox[0])
    bgl.glVertex2f(*bbox[1])
    bgl.glVertex2f(*bbox[2])
    bgl.glVertex2f(*bbox[3])
    bgl.glVertex2f(*bbox[0])
    bgl.glVertex2f(*bbox[4])
    bgl.glVertex2f(*bbox[5])
    bgl.glVertex2f(*bbox[6])
    bgl.glVertex2f(*bbox[7])
    bgl.glVertex2f(*bbox[4])
    bgl.glEnd()
    
    bgl.glBegin(bgl.GL_LINES)
    bgl.glVertex2f(*bbox[1])
    bgl.glVertex2f(*bbox[5])
    bgl.glVertex2f(*bbox[2])
    bgl.glVertex2f(*bbox[6])
    bgl.glVertex2f(*bbox[3])
    bgl.glVertex2f(*bbox[7])
    bgl.glEnd()
    
def draw_callback_px(self, context, event):
    """Display and draw bgl informations"""
    obj_light = context.active_object
    txt_add_light = "Add light: CTRL+LMB"
    region = context.region
    lw = 4 // 2
    hudcol = context.scene.HUD_color[0], context.scene.HUD_color[1], context.scene.HUD_color[2], context.scene.HUD_color[3]
    bgl.glColor4f(*hudcol)
    left = 20

#---Region overlap on
    overlap = bpy.context.user_preferences.system.use_region_overlap
    t_panel_width = 0
    if context.area == self.lumiere_area :
        if overlap:
            for region in bpy.context.area.regions:
                if region.type == 'TOOLS':
                    left += region.width
                    
    #---Draw frame around the view3D
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glLineWidth(4)
        bgl.glBegin(bgl.GL_LINE_STRIP)
        bgl.glVertex2i(lw, lw)
        bgl.glVertex2i(region.width - lw, lw)
        bgl.glVertex2i(region.width - lw, region.height - lw)
        bgl.glVertex2i(lw, region.height - lw)
        bgl.glVertex2i(lw, lw)
        bgl.glEnd() 
        
    #---Text attribute 
        font_id = 0  
        blf.size(font_id, 20, 72)

    #---Create light mode
        if not self.editmode:
            draw_text(hudcol, font_id, left, region.height-55, txt_add_light)   

    #---Interactive mode
        if self.editmode:

        #---Interactive mode    
            if obj_light is not None and obj_light.type != 'EMPTY' and obj_light.data.name.startswith("Lumiere"):
                softbox = get_lamp(context, obj_light.Lumiere.lightname)
                #---Draw bounding box
                # if obj_light.Lumiere.typlight == "Panel":
                    # matrix = softbox.matrix_world
                    # color = obj_light.Lumiere.lightcolor
                    # draw_bounding_box(context, softbox, matrix, color)

                # elif obj_light.Lumiere.typlight in ("Area", "Spot", "Point", "Sun"):
                #---Draw circle
                    # bgl.glLineWidth(5)
                    # color = obj_light.Lumiere.lightcolor
                    # location = location_3d_to_region_2d(context.region, context.space_data.region_3d, obj_light.matrix_world.translation)
                    # draw_circle_2d((color[0], color[1], color[2], 0.4), location[0], location[1], 20) 
            
            #---Light Name
                txt_light_name = "| Light: " + obj_light.name
                txt_to_draw = self.reflect_angle + txt_light_name
                draw_text(hudcol, font_id, left, region.height-55, txt_to_draw)

            #---Draw a line
                text_width, text_height = blf.dimensions(font_id, txt_to_draw)
                draw_line(left, region.height-62, hudcol, 2, text_width)
                
            #---Keys 
                key_height = region.height-82
                
                lamp_name = "LAMP_" + obj_light.data.name
                if obj_light.Lumiere.typlight == "Env":
                    txt_rotation = "Rotation: " + str(round(float(obj_light.Lumiere.hdri_rotation),2))
                    draw_text(hudcol, font_id, left, key_height, txt_rotation)
                else:
                    
                    if self.strength_light:
                        txt_strength = "Energy: " + str(round(obj_light.Lumiere.energy,3))
                        draw_text(hudcol, font_id, left, key_height, txt_strength)

                    elif self.orbit:
                        txt_orbit = "Orbit mode"
                        draw_text(hudcol, font_id, left, key_height, txt_orbit)

                    elif self.dist_light:
                        txt_range = "Range: " + str(round(obj_light.Lumiere.range,3))
                        draw_text(hudcol, font_id, left, key_height, txt_range)
                        
                    elif self.rotate_light_x:
                        txt_rotation = "Rotation X: " + str(round(math.degrees(obj_light.rotation_euler.x),3))
                        draw_text(hudcol, font_id, left, key_height, txt_rotation)
                                            
                    elif self.rotate_light_y:
                        txt_rotation = "Rotation Y: " + str(round(math.degrees(obj_light.rotation_euler.y),3))
                        draw_text(hudcol, font_id, left, key_height, txt_rotation)
                                            
                    elif self.rotate_light_z:
                        txt_rotation = "Rotation Z: " + str(round(math.degrees(obj_light.rotation_euler.z),3))
                        draw_text(hudcol, font_id, left, key_height, txt_rotation)
                    
                    elif self.falloff_mode :
                        if (time.time() < (self.key_start + 0.5)):
                            if obj_light.Lumiere.typfalloff == "0":
                                draw_text(hudcol, font_id, left, key_height, "Quadratic Falloff")
                            elif obj_light.Lumiere.typfalloff == "1":
                                draw_text(hudcol, font_id, left, key_height, "Linear Falloff")
                            elif obj_light.Lumiere.typfalloff == "2":
                                draw_text(hudcol, font_id, left, key_height, "Constant Falloff")
                        else:
                            self.falloff_mode = False
                    
                    elif self.scale_light:
                        if obj_light.Lumiere.typlight == "Spot" :
                            txt_scale = "Size: " + str(round(math.degrees(bpy.data.lamps[lamp_name].spot_size),3))
                        elif obj_light.Lumiere.typlight == "Area" :
                            txt_scale = "Size: " + str(round( (obj_light.scale[0] + obj_light.scale[1]) / 2, 3))
                        elif obj_light.Lumiere.typlight == "Point":
                            txt_scale = "Soft shadow size: " + str(round(bpy.data.lamps[lamp_name].shadow_soft_size,3))
                        elif obj_light.Lumiere.typlight in ("Sun", "Sky"):
                            txt_scale = "Soft shadow size: " + str(round(bpy.data.lamps[lamp_name].shadow_soft_size,3))
                        else:
                            txt_scale = "Scale: " + str(round( (softbox.scale[0] + softbox.scale[1]) / 2, 3))
                        draw_text(hudcol, font_id, left, key_height, txt_scale)
                    
                    elif self.scale_light_x:
                        if obj_light.Lumiere.typlight == "Spot" :
                            txt_scale = "Shadow size: " + str(round(bpy.data.lamps[lamp_name].shadow_soft_size,3))
                        elif obj_light.Lumiere.typlight == "Area" :
                            txt_scale = "Size X: " + str(round(obj_light.scale[0], 3))                  
                        elif obj_light.Lumiere.typlight == "Panel":
                            txt_scale = "Scale X: " + str(round(softbox.scale[0], 3))
                        draw_text(hudcol, font_id, left, key_height, txt_scale)

                    elif self.scale_light_y:
                        if obj_light.Lumiere.typlight == "Spot" :
                            txt_scale = "Blend: " + str(round(bpy.data.lamps[lamp_name].spot_blend,3))
                        elif obj_light.Lumiere.typlight == "Area" :
                            txt_scale = "Size Y: " + str(round(obj_light.scale[1], 3))
                        elif obj_light.Lumiere.typlight == "Panel":
                            txt_scale = "Scale Y: " + str(round(softbox.scale[1], 3))
                        draw_text(hudcol, font_id, left, key_height, txt_scale)

                    elif self.scale_gapx:
                        txt_scale = "Gap X: " + str(round(obj_light.Lumiere.gapx, 3))
                        draw_text(hudcol, font_id, left, key_height, txt_scale)     

                    elif self.scale_gapy:
                        txt_scale = "Gap Y: " + str(round(obj_light.Lumiere.gapy, 3))
                        draw_text(hudcol, font_id, left, key_height, txt_scale)     
                                                
    #---Restore opengl defaults
        bgl.glLineWidth(1)
        bgl.glDisable(bgl.GL_BLEND)
        bgl.glColor4f(0.0, 0.0, 0.0, 1.0)

#########################################################################################################

#########################################################################################################   
def draw_target_ob(self, context, event):
    """Get the targeted object with object_picker() and draw the name in BGL """

    color=(.033, .033, .033, 0.3)
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glColor4f(*color)
    x, y = self.mouse_path
    font_id = 0 
    blf.size(font_id, 15, 72)
    w, h, t = (25, 2, 5)
    line_height = (blf.dimensions(font_id, "M")[1] * 1.45)
#---Get the name of the object  
    self.picker = object_picker(self, context, self.mouse_path)
    
    if self.picker is not None:
        if bpy.data.objects[self.picker].data.name.startswith("Lumiere"):
            color=(.231, .13, .13, .8)
            bgl.glColor4f(*color)
            text_width, text_height = blf.dimensions(font_id, "No light as target")
        else:
            text_width, text_height = blf.dimensions(font_id, self.picker)
        
        #Draw rectangle
        bgl.glBegin(bgl.GL_QUADS)
        bgl.glVertex2f(x+w+t+text_width+t, y+t+line_height)
        bgl.glVertex2f(x+w, y+t+line_height) 
        bgl.glVertex2f(x+w, y) 
        bgl.glVertex2f(x+w+t+text_width+t, y)       
        bgl.glEnd() 

        color=(1, 1, 1, 1.0)
        bgl.glColor4f(*color)   
        blf.position(font_id, x+w+t, y+t, 0)
        if bpy.data.objects[self.picker].data.name.startswith("Lumiere"):
            blf.draw(font_id, "No light as target") 
        else:
            blf.draw(font_id, self.picker)  
                
#---Restore opengl defaults
    bgl.glLineWidth(1)
    bgl.glDisable(bgl.GL_BLEND)
    bgl.glColor4f(0.0, 0.0, 0.0, 1.0)   
#########################################################################################################

#########################################################################################################   
def draw_target_px(self, context, event):
    """Get the brightest pixel """
    
    if context.area == self.lumiere_area :  
        uv_x, uv_y = self.mouse_path
        x, y = (event.mouse_x - self.view_3d_region_x[0], event.mouse_y)

    #---Draw stippled lines
        bgl.glLineStipple(4, 0x5555)
        bgl.glEnable(bgl.GL_LINE_STIPPLE)
        bgl.glEnable(bgl.GL_BLEND)
        hudcol = context.scene.HUD_color
        bgl.glColor4f(hudcol[0], hudcol[1], hudcol[2], hudcol[3])
        bgl.glLineWidth(4)
        bgl.glBegin(bgl.GL_LINE_STRIP)
        bgl.glVertex2f(x,0)
        bgl.glVertex2f(x,self.img_size_y)
        bgl.glEnd()

    #---Restore opengl defaults
        bgl.glLineWidth(1)
        bgl.glDisable(bgl.GL_BLEND)
        bgl.glColor4f(0.0, 0.0, 0.0, 1.0)   

#########################################################################################################

#########################################################################################################
def object_picker(self, context, coord):
    """Return the name of the object under the eyedropper by ray_cast"""
    scene = context.scene
    region = context.region
    rv3d = context.region_data
    ray_max = 10000
    view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
    ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
    ray_target = (view_vector * ray_max) - ray_origin
    success, location, normal, index, object, matrix = scene.ray_cast(ray_origin, ray_target)

    if success:
        return(object.name)
    else:
        return(None)
#########################################################################################################

#########################################################################################################
def get_mat_name(light):
    """Return the name of the material of the light"""
    mat_name = "Mat_" + light
    mat = bpy.data.materials.get(mat_name)
    
    return(mat_name, mat)
    
#########################################################################################################

#########################################################################################################           
def target_constraint(self, context, name):
    """Add an empty on the target point to constraint the orbit mode"""
    obj_light = context.object
    empty = bpy.data.objects.new(name = name + "_Empty", object_data = None)
    context.scene.objects.link(empty)
    context.active_object.data.name = name
    empty.empty_draw_type = "SPHERE"
    empty.empty_draw_size = 0.00001
    empty.location = obj_light['hit']
    obj_light.constraints['Track To'].target = context.scene.objects.get(empty.name)
    obj_light.constraints['Track To'].up_axis = "UP_Y"
    obj_light.constraints['Track To'].track_axis = "TRACK_NEGATIVE_Z"   
    obj_light.constraints['Track To'].influence = 1
    if bpy.data.objects.get("PROJECTOR_" + obj_light.data.name) is not None:
        projector = bpy.data.objects["PROJECTOR_" + obj_light.data.name]
        projector.constraints['Track To'].target = context.scene.objects.get(empty.name)
        projector.constraints['Track To'].up_axis = "UP_Y"
        projector.constraints['Track To'].track_axis = "TRACK_NEGATIVE_Z"   
        projector.constraints['Track To'].influence = 1     
        
#########################################################################################################

#########################################################################################################           
def remove_constraint(self, context, name):
    """Remove the empty and the constraint of the object for the orbit mode"""
    obj_light = context.object
    bpy.data.objects[obj_light.name].select = True
    bpy.ops.object.visual_transform_apply()
    empty = context.scene.objects.get(name + "_Empty") 
    obj_light.constraints['Track To'].influence = 0
    obj_light['dir'] = (obj_light.location - Vector(obj_light['hit'])).normalized() 
        
    context.scene.objects.unlink(empty)
    bpy.data.objects.remove(empty)
#########################################################################################################

#########################################################################################################           
def update_constraint(self, context, event, name):
    """Update the object properties for the orbit mode"""
    obj_light = context.object
    empty = context.scene.objects.get(name + "_Empty") 
    v3d = context.space_data
    rv3d = v3d.region_3d
    v_m = context.area.spaces[0].region_3d.view_matrix
    self.offset = -(self.initial_mouse - Vector((event.mouse_x, event.mouse_y, 0.0))) * 0.02
    obj_light.location = self.initial_location + Vector(self.offset)*v_m
#---Source: http://blender.stackexchange.com/questions/21259/is-possible-to-calculate-the-shortest-distance-between-two-geometry-objects-via    
    lst = [] 
    lst.append(obj_light.location)
    lst.append(empty.location)
    distance = math.sqrt((lst[0][0] - lst[1][0])**2 + (lst[0][1] - lst[1][1])**2 + (lst[0][2] - lst[1][2])**2)
    obj_light.Lumiere.range = distance
    
#########################################################################################################

#########################################################################################################
def raycast_light(self, range, context, coord, ray_max=1000.0):
    """Compute the location and rotation of the light from the angle or normal of the targeted face off the object"""
    scene = context.scene
    i = 0
    p = 0
    length_squared = 0
    light = context.active_object
    light['pixel_select'] = False
    self.reflect_angle = "View" if light.Lumiere.reflect_angle == "0" else "Normal"

#---Get the ray from the viewport and mouse
    view_vector = view3d_utils.region_2d_to_vector_3d(self.region, self.rv3d, (coord))
    ray_origin = view3d_utils.region_2d_to_origin_3d(self.region, self.rv3d, (coord))
    ray_target = ray_origin + view_vector

#---Select the object 
    def visible_objects_and_duplis():
        if light.Lumiere.objtarget != "":
            obj = bpy.data.objects[light.Lumiere.objtarget]
            yield (obj, obj.matrix_world.copy())
        else :
            for obj in context.visible_objects:
                if obj.type == 'MESH' and "Lumiere" not in obj.data.name:
                    yield (obj, obj.matrix_world.copy())

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
            if self.reflect_angle == "Normal" and (i == 1): 
                direction = (normal * matrix.inverted())
            else:
                direction = (view_vector).reflect(normal * matrix.inverted())
            
            if light.Lumiere.invert_ray:
                direction *= -1
            
        #---Define range
            hit_world = (matrix * hit) + (range * direction)

            length_squared = ((matrix * hit) - ray_origin).length_squared

            if length_squared < best_length_squared:
                best_length_squared = length_squared
                self.matrix = matrix
                self.hit = hit
                self.hit_world = hit_world
                self.direction = direction
                self.target_name = obj.name

            #---Parent the light to the target object
                light.parent = obj
                light.matrix_parent_inverse = obj.matrix_world.inverted()
                
#---Define location, rotation and scale
    if length_squared > 0 :
        rotaxis = (self.direction.to_track_quat('Z','Y')).to_euler()
        light['hit'] = (self.matrix * self.hit)
        light['dir'] = self.direction

    #---Rotation    
        light.rotation_euler = rotaxis
        
    #---Lock the rotation on Horizontal or Vertical axis
        if light.Lumiere.lock_light == "Vertical":
            light.rotation_euler[0] = math.radians(90)
        elif light.Lumiere.lock_light == "Horizontal":
            light.rotation_euler[0] = math.radians(0)

        if range < 0:
            print("RANGE NEGATIF")
            
        if light.Lumiere.typlight == "Env":
            if light.Lumiere.rotation_lock_img:
                light.Lumiere.img_rotation = light.Lumiere.img_pix_rot + math.degrees(light.rotation_euler.z)
            else:
                light.Lumiere.hdri_rotation = light.Lumiere.hdri_pix_rot + math.degrees(light.rotation_euler.z)

    #---Location
        light.location = Vector((self.hit_world[0], self.hit_world[1], self.hit_world[2]))

    #---Update the position of the sun from the background texture
        if light.Lumiere.typlight in ("Sky") :
            update_sky(self, context)    

#########################################################################################################

#########################################################################################################
def repeat_group_mat(mat, name_group):
    """Group node to repeat pattern"""
#---Group Node
    pattern_group = bpy.data.node_groups.get(name_group)
    if pattern_group is None: 
        pattern_group = bpy.data.node_groups.new(type="ShaderNodeTree", name=name_group)

    #---Group inputs and outputs
        pattern_group.inputs.new("NodeSocketColor","Image")
        pattern_group.inputs.new("NodeSocketFloat", "Repeat X")
        pattern_group.inputs.new("NodeSocketFloat", "Repeat Y")
        pattern_group.outputs.new("NodeSocketColor","Image")
        
        pattern_group.inputs[1].min_value = 0
        pattern_group.inputs[2].min_value = 0
        
        input_node = pattern_group.nodes.new("NodeGroupInput")
        input_node.location = (-500, 0)
        
        output_node = pattern_group.nodes.new("NodeGroupOutput")
        output_node.location = (500, 0)
        
    #---Add nodes to group
        group_separate = pattern_group.nodes.new('ShaderNodeSeparateRGB')
        group_separate.location = (-300.0, 80.0)
        pattern_group.links.new(input_node.outputs['Image'], group_separate.inputs[0])
        
        group_multiply1 = pattern_group.nodes.new('ShaderNodeMath')
        group_multiply1.operation = "MULTIPLY"
        group_multiply1.location = (-100.0, 80.0)
        group_multiply1.inputs[1].default_value = 1
        pattern_group.links.new(group_separate.outputs[0], group_multiply1.inputs[0])
        pattern_group.links.new(input_node.outputs["Repeat X"], group_multiply1.inputs[1])
        
        group_modulo1 = pattern_group.nodes.new('ShaderNodeMath')
        group_modulo1.location = (100.0, 80.0)
        group_modulo1.operation = "MODULO"
        group_modulo1.inputs[1].default_value = 1
        pattern_group.links.new(group_multiply1.outputs[0], group_modulo1.inputs[0])
        
        group_multiply2 = pattern_group.nodes.new('ShaderNodeMath')
        group_multiply2.operation = "MULTIPLY"
        group_multiply2.location = (-100.0, -80.0)
        group_multiply2.inputs[1].default_value = 1
        pattern_group.links.new(group_separate.outputs[1], group_multiply2.inputs[0])
        pattern_group.links.new(input_node.outputs["Repeat Y"], group_multiply2.inputs[1])
        
        group_modulo2 = pattern_group.nodes.new('ShaderNodeMath')
        group_modulo2.operation = "MODULO"
        group_modulo2.location = (100.0, -80.0)
        group_modulo2.inputs[1].default_value = 1
        pattern_group.links.new(group_multiply2.outputs[0], group_modulo2.inputs[0])
        
        group_combine = pattern_group.nodes.new('ShaderNodeCombineRGB')
        group_combine.location = (300.0, 20.0)
        pattern_group.links.new(group_modulo1.outputs[0], group_combine.inputs[0])
        pattern_group.links.new(group_modulo2.outputs[0], group_combine.inputs[1])

        pattern_group.links.new(group_combine.outputs[0], output_node.inputs[0])

    group_node = mat.node_tree.nodes.new("ShaderNodeGroup")
    group_node.name = name_group
    group_node.node_tree = pattern_group
    
    return(group_node)
#########################################################################################################

#########################################################################################################
def projector_mat():
    """Cycles material nodes for the front projector"""
    
    bpy.context.scene.render.engine = 'CYCLES'

#------------------------------
#BLACK MATERIAL 1 : BASE PROJECTOR
#------------------------------

#---Create black material if not exist.
    mat = bpy.data.materials.get("BASE_PROJECTOR_mat")
    
    if mat is not None: 
        mat.node_tree.nodes.clear()
    else: 
        mat = bpy.data.materials.new("BASE_PROJECTOR_mat")
        mat.use_nodes= True
        mat.node_tree.nodes.clear()

#---Geometry
    geometry = mat.node_tree.nodes.new(type = 'ShaderNodeNewGeometry')
    geometry.location = (-60.0, 520.0)

#---Diffuse Node 1
    diffuse1 = mat.node_tree.nodes.new(type = 'ShaderNodeBsdfDiffuse')
    diffuse1.inputs[0].default_value = [0,0,0,1]
    diffuse1.location = (-60.0, 300.0)
    
#---Diffuse Node 2
    diffuse2 = mat.node_tree.nodes.new(type = 'ShaderNodeBsdfDiffuse')
    diffuse2.inputs[0].default_value = [1,1,1,1]
    diffuse2.location = (-60.0, 180.0)
    
#---Transparent Node
    trans = mat.node_tree.nodes.new(type="ShaderNodeBsdfTransparent")
    trans.inputs[0].default_value = [1,1,1,1]
    trans.location = (-60.0, 60.0)

#---Mix Shader Node 1
    mix = mat.node_tree.nodes.new(type="ShaderNodeMixShader")
    mix.location = (120.0, 300.0)
    #Link Geometry Backfacing
    mat.node_tree.links.new(geometry.outputs[6], mix.inputs[0])
    #Link Diffuse 1
    mat.node_tree.links.new(diffuse1.outputs[0], mix.inputs[1])
    #Link Diffuse 2
    mat.node_tree.links.new(diffuse2.outputs[0], mix.inputs[2])
     
#---Output Shader Node
    output = mat.node_tree.nodes.new(type = 'ShaderNodeOutputMaterial')
    output.location = (280.0, 300.0)
    mat.node_tree.links.new(diffuse1.outputs[0], output.inputs['Surface'])

#----------------------------------
#TRANSPARENT MATERIAL 2 : PROJECTOR
#----------------------------------

#---Create a new material for cycles Engine.
    cobj = bpy.context.scene.objects.active
    mat_name, mat = get_mat_name(cobj.data.name)

    if mat is not None: 
        mat.node_tree.nodes.clear()
    else: 
        mat = bpy.data.materials.new(mat_name)
        
    mat.use_nodes= True
    # Clear default nodes
    mat.node_tree.nodes.clear() 
    mat.alpha = 0.5

#----------------
#TEXTURE MATERIAL
#----------------

#---Repeat image group node 
    image_group_node = repeat_group_mat(mat, "Repeat_Texture")
    image_group_node.inputs[1].default_value = 1
    image_group_node.inputs[2].default_value = 1

#---Texture Coordinate
    coord = mat.node_tree.nodes.new(type = 'ShaderNodeTexCoord')
    coord.location = (-1040.0, -80.0)

#---Geometry
    geometry = mat.node_tree.nodes.new(type = 'ShaderNodeNewGeometry')
    geometry.location = (-1040.0, -340.0)

#---Repeat group for texture image
    image_group_node.location = (-560.0, -20.0)
    mat.node_tree.links.new(coord.outputs[0], image_group_node.inputs[0])

#---Image Texture Shader Node
    texture = mat.node_tree.nodes.new(type = 'ShaderNodeTexImage')
    mat.node_tree.links.new(image_group_node.outputs[0], texture.inputs[0])
    texture.projection = 'BOX'
    texture.location = (-380.0, 80.0)

#---Saturation
    saturation = mat.node_tree.nodes.new(type = 'ShaderNodeMixRGB')
    saturation.inputs['Fac'].default_value = 0
    saturation.inputs['Color1'].default_value = [1,1,1,1]
    saturation.inputs['Color2'].default_value = [1,1,1,1]
    mat.node_tree.links.new(texture.outputs[0], saturation.inputs[1])
    saturation.blend_type = 'SATURATION'
    saturation.location = (-200.0, 40.0)

#---Gamma
    gamma = mat.node_tree.nodes.new(type = 'ShaderNodeGamma')
    mat.node_tree.links.new(saturation.outputs[0], gamma.inputs[0])
    gamma.location = (-20.0, 0.0)

#---Bright / Contrast
    bright = mat.node_tree.nodes.new(type = 'ShaderNodeBrightContrast')
    mat.node_tree.links.new(gamma.outputs[0], bright.inputs[0])
    bright.location = (160.0, 20.0)

#---Invert Node
    invert = mat.node_tree.nodes.new(type="ShaderNodeInvert")
    invert.inputs['Fac'].default_value = 0
    mat.node_tree.links.new(bright.outputs[0], invert.inputs[1])
    invert.location = (340.0, 0.0)

#-----------------
#GRADIENT MATERIAL
#-----------------
    
#---Mapping Node
    textmap = mat.node_tree.nodes.new(type="ShaderNodeMapping")
    mat.node_tree.links.new(coord.outputs[0], textmap.inputs[0])
    textmap.vector_type = "TEXTURE"
    textmap.location = (-820.0, -220.0)
    
#---Grandient Node 1
    grad1 = mat.node_tree.nodes.new(type="ShaderNodeTexGradient")
    mat.node_tree.links.new(textmap.outputs[0], grad1.inputs[0])
    grad1.location = (-460.0, -220.0)
    
#---Repeat gradient group node 
    gradient_group_node = repeat_group_mat(mat, "Repeat_Gradient")
    gradient_group_node.location = (-280.0, -220.0)
    mat.node_tree.links.new(grad1.outputs[0], gradient_group_node.inputs[0])
    gradient_group_node.inputs[1].default_value = 1
    gradient_group_node.inputs[2].default_value = 1
    
#---Grandient Node 2
    grad2 = mat.node_tree.nodes.new(type="ShaderNodeTexGradient")
    mat.node_tree.links.new(gradient_group_node.outputs[0], grad2.inputs[0])
    grad2.location = (-100.0, -220.0)
    
#---Color ramp
    colramp = mat.node_tree.nodes.new(type="ShaderNodeValToRGB")
    mat.node_tree.links.new(grad2.outputs[0], colramp.inputs[0])
    colramp.location = (80.0, -120.0)


#-------
#OUTPUT
#-------

#---Geometry Node 2
    geometry2 = mat.node_tree.nodes.new(type="ShaderNodeNewGeometry")
    geometry2.location = (520.0, 200.0)
    
#---Transparent Node
    trans = mat.node_tree.nodes.new(type="ShaderNodeBsdfTransparent")
    trans.location = (520.0, -20.0)

#---Transparent Node 2
    trans2 = mat.node_tree.nodes.new(type="ShaderNodeBsdfTransparent")
    #mat.node_tree.links.new(invert.outputs[0], trans2.inputs[0])
    trans2.location = (520.0, -100.0)
    
#---Mix Shader Node
    mix = mat.node_tree.nodes.new(type="ShaderNodeMixShader")
    mix.location = (700.0, 20.0)
    #Link BackFacing
    mat.node_tree.links.new(geometry2.outputs[6], mix.inputs[0])
    #Link Transparent 
    mat.node_tree.links.new(trans.outputs[0], mix.inputs[1])
    #Link Transparent 2 
    mat.node_tree.links.new(trans2.outputs[0], mix.inputs[2])

#---Light Path
    light_path = mat.node_tree.nodes.new(type="ShaderNodeLightPath")
    light_path.location = (700.0, 300.0)

#---ADD Math
    add = mat.node_tree.nodes.new(type = 'ShaderNodeMath')
    mat.node_tree.links.new(light_path.outputs[0], add.inputs[0])
    mat.node_tree.links.new(light_path.outputs[3], add.inputs[1])
    add.operation = 'ADD'
    add.location = (880.0, 300.0) 


#--------------
#EDGE THICKNESS
#--------------

#---Geometry
    geometry = mat.node_tree.nodes.new(type = 'ShaderNodeNewGeometry')
    geometry.location = (340.0, -200.0)
    
#---Grandient Node 
    grad3 = mat.node_tree.nodes.new(type="ShaderNodeTexGradient")
    mat.node_tree.links.new(geometry.outputs[5], grad3.inputs[0])
    grad3.gradient_type = 'QUADRATIC'
    grad3.location = (520.0, -200.0)
    
#---Color ramp
    edge_colramp = mat.node_tree.nodes.new(type="ShaderNodeValToRGB")
    edge_colramp.color_ramp.elements[1].position = 0.025
    mat.node_tree.links.new(grad3.outputs[0], edge_colramp.inputs[0])
    edge_colramp.location = (700.0, -120.0)
    
#---Translucent Node
    trans = mat.node_tree.nodes.new(type="ShaderNodeBsdfTranslucent")
    mat.node_tree.links.new(edge_colramp.outputs[0], trans.inputs[0])
    trans.location = (1000.0, -120.0)
    
#---Edge Mix Shader Node
    edge_mix = mat.node_tree.nodes.new(type="ShaderNodeMixShader")
    edge_mix.location = (1200.0, 20.0)
    #Light path
    edge_mix.inputs[0].default_value = 1
    mat.node_tree.links.new(add.outputs[0], edge_mix.inputs[0])
    #Link Transparent 
    mat.node_tree.links.new(mix.outputs[0], edge_mix.inputs[1])
    #Link Translucent
    mat.node_tree.links.new(trans.outputs[0], edge_mix.inputs[2])

#-------
#OUTPUT
#-------
        
#---Output Shader Node
    output = mat.node_tree.nodes.new(type = 'ShaderNodeOutputMaterial')
    output.location = (1420.0, 20.0)
    mat.node_tree.links.new(edge_mix.outputs[0], output.inputs['Surface'])
    
#########################################################################################################

#########################################################################################################
def softbox_mat(cobj):
    """Cycles material nodes for the panel light"""
    
#---Create a new material for cycles Engine.
    bpy.context.scene.render.engine = 'CYCLES'
    # cobj = bpy.context.scene.objects.active
    mat_name, mat = get_mat_name(cobj.data.name)
    cobj["typgradient"] = 1
    
    if mat is not None: 
        mat.node_tree.nodes.clear()
    else: 
        mat = bpy.data.materials.new(mat_name)
    mat.use_nodes= True
    mat.node_tree.nodes.clear() # Clear default nodes
    mat.alpha = 0.5

#---Texture Coordinate
    coord = mat.node_tree.nodes.new(type = 'ShaderNodeTexCoord')
    coord.location = (-2880.0, 60.0)
    
#---Geometry Node 
    geom = mat.node_tree.nodes.new(type="ShaderNodeNewGeometry")
    geom.location = (-2880.0, -180.0)
    
#---Mapping Node
    textmap = mat.node_tree.nodes.new(type="ShaderNodeMapping")
    mat.node_tree.links.new(coord.outputs[0], textmap.inputs[0])
    textmap.vector_type = "TEXTURE"
    textmap.location = (-2680.0000, -100.0000)

#---Gradient Node 
    grad = mat.node_tree.nodes.new(type="ShaderNodeTexGradient")
    mat.node_tree.links.new(textmap.outputs[0], grad.inputs[0])
    grad.location = (-2300.0000, -200.0000)
    
#---Separate RGB
    sepRGB = mat.node_tree.nodes.new(type = 'ShaderNodeSeparateRGB')
    mat.node_tree.links.new(grad.outputs[0], sepRGB.inputs[0])
    sepRGB.location = (-2080.0, -200.0) 
    
#---Multiply 01 = R
    multiplyR = mat.node_tree.nodes.new(type = 'ShaderNodeMath')
    mat.node_tree.links.new(sepRGB.outputs[0], multiplyR.inputs[0])
    multiplyR.operation = 'MULTIPLY'
    multiplyR.inputs[1].default_value = 1
    multiplyR.location = (-1880.0, -120.0)

#---Modulo 01 = R
    moduloR = mat.node_tree.nodes.new(type = 'ShaderNodeMath')
    mat.node_tree.links.new(multiplyR.outputs[0], moduloR.inputs[0])
    moduloR.operation = 'MODULO'
    moduloR.inputs[1].default_value = 1
    moduloR.location = (-1700.0, -120.0) 
    
#---Multiply 02 = G
    multiplyG = mat.node_tree.nodes.new(type = 'ShaderNodeMath')
    mat.node_tree.links.new(sepRGB.outputs[1], multiplyG.inputs[0])
    multiplyG.operation = 'MULTIPLY'
    multiplyG.inputs[1].default_value = 1
    multiplyG.location = (-1880.0, -300.0) 
    
#---Modulo 02 = G
    moduloG = mat.node_tree.nodes.new(type = 'ShaderNodeMath')
    mat.node_tree.links.new(multiplyG.outputs[0], moduloG.inputs[0])
    moduloG.operation = 'MODULO'
    moduloG.inputs[1].default_value = 1
    moduloG.location = (-1700.0000, -300.0000) 
    
#---Combine RGB
    combRGB = mat.node_tree.nodes.new(type = 'ShaderNodeCombineRGB')
    mat.node_tree.links.new(moduloR.outputs[0], combRGB.inputs[0])
    mat.node_tree.links.new(moduloG.outputs[0], combRGB.inputs[1])
    combRGB.location = (-1520.0000, -200.0000) 

#---Grandient Node Linear
    linear_grad = mat.node_tree.nodes.new(type="ShaderNodeTexGradient")
    mat.node_tree.links.new(combRGB.outputs[0], linear_grad.inputs[0])
    linear_grad.location = (-1340.0000, -200.0000)   

#---Object info
    object_info = mat.node_tree.nodes.new(type="ShaderNodeObjectInfo")
    object_info.name = "Object_Info"
    object_info.location = (-1520.0000, -360.0000)
    
#---Multiply Object Info for random color
    random_color = mat.node_tree.nodes.new(type = 'ShaderNodeMath')
    random_color.name = "Random_Color"
    mat.node_tree.links.new(object_info.outputs[3], random_color.inputs[0])
    random_color.operation = 'MULTIPLY'
    random_color.inputs[1].default_value = 0
    random_color.location = (-1340.0000, -360.0000)

#---Mix Random Color
    mix_random_color = mat.node_tree.nodes.new(type = 'ShaderNodeMixRGB')
    mix_random_color.name = "Mix_Random_Color"
    mix_random_color.inputs[0].default_value = 1
    mix_random_color.blend_type = 'ADD'
    mat.node_tree.links.new(linear_grad.outputs[0], mix_random_color.inputs[1])
    mat.node_tree.links.new(random_color.outputs[0], mix_random_color.inputs[2])
    mix_random_color.location = (-1120.0000, -160.0000) 

#---Color Ramp Node
    colramp = mat.node_tree.nodes.new(type="ShaderNodeValToRGB")
    mat.node_tree.links.new(linear_grad.outputs[0], colramp.inputs['Fac'])
    colramp.color_ramp.elements[0].color = (1,1,1,1)
    colramp.location = (-920.0000, -120.0000)   

#---Image Texture 
    texture = mat.node_tree.nodes.new(type = 'ShaderNodeTexImage')
    mat.node_tree.links.new(coord.outputs[0], texture.inputs[0])
    texture.projection = 'BOX'
    texture.location = (-1340.0, 160.0)

#---Bright / Contrast
    bright = mat.node_tree.nodes.new(type = 'ShaderNodeBrightContrast')
    mat.node_tree.links.new(texture.outputs[0], bright.inputs[0])
    bright.location = (-1120.0, 80.0)

#---Gamma
    gamma = mat.node_tree.nodes.new(type = 'ShaderNodeGamma')
    mat.node_tree.links.new(bright.outputs[0], gamma.inputs[0])
    gamma.location = (-940.0, 60.0)

#---Hue / Saturation / Value
    hue = mat.node_tree.nodes.new(type = 'ShaderNodeHueSaturation')
    mat.node_tree.links.new(gamma.outputs[0], hue.inputs[4])
    hue.location = (-760.0, 80.0)
    
#---Random Energy
    random_energy = mat.node_tree.nodes.new(type = 'ShaderNodeMath')
    random_energy.name = "Random_Energy"
    random_energy.operation = 'ADD'
    random_energy.inputs[1].default_value = 0
    random_energy.location = (-600.0, -180.0)

#---Mix Color Texture
    mix_color_texture = mat.node_tree.nodes.new(type = 'ShaderNodeMixRGB')
    mix_color_texture.name = "Mix_Color_Texture"
    mix_color_texture.inputs[0].default_value = 1
    mix_color_texture.location = (-400.0, 0.0)
    
#---Light Falloff
    falloff = mat.node_tree.nodes.new(type = 'ShaderNodeLightFalloff')
    falloff.inputs[0].default_value = 10
    falloff.location = (-400.0, -180.0)

#---Invert Node
    invert = mat.node_tree.nodes.new(type="ShaderNodeInvert")
    invert.location = (-200,75) 

#---Transparent Node
    trans = mat.node_tree.nodes.new(type="ShaderNodeBsdfTransparent")
    trans.inputs[0].default_value = (1,1,1,1)
    trans.location = (-200,-25) 

#---Emission Node
    emit = mat.node_tree.nodes.new(type = 'ShaderNodeEmission')
    emit.inputs[0].default_value = bpy.context.active_object.Lumiere.lightcolor
    mat.node_tree.links.new(falloff.outputs[0],  emit.inputs[1])
    emit.location = (-200,-100)

#---Diffuse Node
    diffuse = mat.node_tree.nodes.new(type = 'ShaderNodeBsdfDiffuse')
    diffuse.inputs[0].default_value = bpy.context.active_object.Lumiere.lightcolor
    diffuse.location = (-200,-200)

#---Geometry Node : Backface
    backface = mat.node_tree.nodes.new(type = 'ShaderNodeNewGeometry')
    backface.location = (000,250)

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
    #Link them together
    mat.node_tree.links.new(mix2.outputs[0], output.inputs['Surface']) 
#########################################################################################################

#########################################################################################################
def create_light_env(self, context, dupli_name = "Lumiere"):
    """Cycles material nodes for the environment light"""
    
#---Create a new world if not exist
    world = ""
    for w in bpy.data.worlds:
        if w.name == "Lumiere_world":
            world = bpy.data.worlds['Lumiere_world']
            
    if world == "":
        bpy.context.scene.world = bpy.data.worlds.new("Lumiere_world")
        world = bpy.context.scene.world

    world.use_nodes= True
    world.node_tree.nodes.clear() 
    cobj = bpy.context.object   

#---Use multiple importance sampling for the world
    context.scene.world.cycles.sample_as_light = True

#---Texture Coordinate
    coord = world.node_tree.nodes.new(type = 'ShaderNodeTexCoord')
    coord.location = (-1660.0, 220.0)
        
#---Mapping Node HDRI
    textmap = world.node_tree.nodes.new(type="ShaderNodeMapping")
    textmap.vector_type = "POINT"
    world.node_tree.links.new(coord.outputs[0], textmap.inputs[0])
    textmap.location = (-1480.0, 440.0)

#---Mapping Node Reflection
    textmap2 = world.node_tree.nodes.new(type="ShaderNodeMapping")
    textmap2.vector_type = "POINT"
    world.node_tree.links.new(coord.outputs[0], textmap2.inputs[0])
    textmap2.location = (-1480.0, 100.0)

#-> Blur from  Bartek Skorupa : Source https://www.youtube.com/watch?v=kAUmLcXhUj0&feature=youtu.be&t=23m58s
#---Noise Texture
    noisetext = world.node_tree.nodes.new(type="ShaderNodeTexNoise")
    noisetext.inputs[1].default_value = 1000
    noisetext.inputs[2].default_value = 16
    noisetext.inputs[3].default_value = 200
    noisetext.location = (-1120.0, -60.0)

#---Substract
    substract = world.node_tree.nodes.new(type="ShaderNodeMixRGB")
    substract.blend_type = 'SUBTRACT'
    substract.inputs[0].default_value = 1
    world.node_tree.links.new(noisetext.outputs[0], substract.inputs['Color1'])
    substract.location = (-940.0, -60.0)

#---Add
    add = world.node_tree.nodes.new(type="ShaderNodeMixRGB")
    add.blend_type = 'ADD'
    add.inputs[0].default_value = 0
    world.node_tree.links.new(textmap2.outputs[0], add.inputs['Color1'])
    world.node_tree.links.new(substract.outputs[0], add.inputs['Color2'])
    add.location = (-760.0, 100.0)

#-> End Blur

#---Environment Texture 
    envtext = world.node_tree.nodes.new(type = 'ShaderNodeTexEnvironment')
    world.node_tree.links.new(textmap.outputs[0], envtext.inputs[0])
    envtext.location = (-580,380)

#---Bright / Contrast
    bright = world.node_tree.nodes.new(type = 'ShaderNodeBrightContrast')
    world.node_tree.links.new(envtext.outputs[0], bright.inputs[0])
    bright.location = (-400,340)

#---Gamma
    gamma = world.node_tree.nodes.new(type = 'ShaderNodeGamma')
    world.node_tree.links.new(bright.outputs[0], gamma.inputs[0])
    gamma.location = (-220,320)

#---Hue / Saturation / Value
    hue = world.node_tree.nodes.new(type = 'ShaderNodeHueSaturation')
    world.node_tree.links.new(gamma.outputs[0], hue.inputs[4])
    hue.location = (-40,340)
    
#---Reflection Texture 
    imagtext = world.node_tree.nodes.new(type = 'ShaderNodeTexEnvironment')
    world.node_tree.links.new(add.outputs[0], imagtext.inputs[0])
    imagtext.location = (-580,100)

#---Bright / Contrast
    bright2 = world.node_tree.nodes.new(type = 'ShaderNodeBrightContrast')
    world.node_tree.links.new(imagtext.outputs[0], bright2.inputs[0])
    bright2.location = (-400,40)

#---Gamma
    gamma2 = world.node_tree.nodes.new(type = 'ShaderNodeGamma')
    world.node_tree.links.new(bright2.outputs[0], gamma2.inputs[0])
    gamma2.location = (-220,40)

#---Hue / Saturation / Value
    hue2 = world.node_tree.nodes.new(type = 'ShaderNodeHueSaturation')
    world.node_tree.links.new(gamma2.outputs[0], hue2.inputs[4])
    hue2.location = (-40,40)
    
#---Light path 
    lightpath = world.node_tree.nodes.new(type = 'ShaderNodeLightPath')
    lightpath.location = (-40,620)
    
#---Math 
    math = world.node_tree.nodes.new(type = 'ShaderNodeMath')
    math.use_clamp = True
    math.operation = 'SUBTRACT'
    world.node_tree.links.new(lightpath.outputs[0], math.inputs[0])
    world.node_tree.links.new(lightpath.outputs[3], math.inputs[1])
    math.location = (160,560)
                
#---Background 01
    background1 = world.node_tree.nodes.new(type = 'ShaderNodeBackground')
    background1.inputs[0].default_value = (0.8,0.8,0.8,1.0)
    background1.location = (160,280)
        
#---Background 02
    background2 = world.node_tree.nodes.new(type = 'ShaderNodeBackground')
    background2.location = (160,180)
    
#---Mix Shader Node
    mix = world.node_tree.nodes.new(type="ShaderNodeMixShader")
    world.node_tree.links.new(math.outputs[0], mix.inputs[0])
    world.node_tree.links.new(background1.outputs[0], mix.inputs[1])
    world.node_tree.links.new(background2.outputs[0], mix.inputs[2])
    mix.location = (340,320)

#---Output
    output = world.node_tree.nodes.new("ShaderNodeOutputWorld") 
    output.location = (520,300)
    
#---Links
    world.node_tree.links.new(mix.outputs[0], output.inputs[0])

#---Create the light mesh object for the duplication of the lamp
    dupli = create_dupli(self, context) 

    create_light_env_widget(self, context, dupli)

#---Make the dupliverts object active
    bpy.context.scene.objects.active = bpy.data.objects[dupli.name]

    return(dupli)
#########################################################################################################

#########################################################################################################
def create_softbox(self, context, newlight = False, dupli_name = "Lumiere"):
    """Create the panel light with modifiers"""
    edges = []
    faces = []
    listvert = []
    
    verts = [Vector((-1, 1, 0)),
             Vector((1, 1, 0)),
             Vector((1, -1, 0)),
             Vector((-1, -1, 0)),
            ]
    
#---Create the DupliVerts
    if newlight:
        dupli = get_object(context, self.lightname)
    else:
        dupli = create_dupli(self, context, dupli_name)

#---Create faces 
    for f in range(len(verts) - 1, -1, -1):
        listvert.extend([f])
    faces.extend([listvert])

#---Create object
    i = 0
    for ob in context.scene.objects:
        if ob.type != 'EMPTY' and ob.data.name.startswith("Lumiere"):
            i += 1
    
#---Create the mesh
    softbox_name = "SOFTBOX_" + dupli.data.name
    
    if softbox_name in bpy.data.meshes:
        mesh = bpy.data.meshes[softbox_name]
        bpy.data.meshes.remove(mesh)

    mesh = bpy.data.meshes.new(name=softbox_name)
    cobj = bpy.data.objects.new(softbox_name, mesh)
    cobj.select = True
    context.scene.objects.link(cobj)
    mesh.from_pydata(verts, edges, faces)
    mesh.update()
    context.scene.objects.active = bpy.data.objects[softbox_name]

#---Add the material
    cobj = context.object
    softbox_mat(cobj)
    mat_name, mat = get_mat_name(cobj.data.name)
    cobj.active_material = mat
       
#---Change the visibility 
    cobj.Lumiere.lightname = cobj.data.name
    cobj.draw_type = 'TEXTURED'
    cobj.show_transparent = True
    cobj.show_wire = True
    cobj.cycles_visibility.camera = False
    cobj.cycles_visibility.shadow = False
    
#---Add Bevel
    cobj.modifiers.new("Bevel", type='BEVEL')
    cobj.modifiers["Bevel"].use_only_vertices = True
    cobj.modifiers["Bevel"].use_clamp_overlap = True
    cobj.modifiers["Bevel"].loop_slide = True
    cobj.modifiers["Bevel"].width = .25
    cobj.modifiers["Bevel"].segments = 5
    cobj.modifiers["Bevel"].profile = .5
    cobj.modifiers["Bevel"].show_expanded = False

#---Add 1 simple subsurf
    cobj.modifiers.new("subd", type='SUBSURF')
    cobj.modifiers["subd"].subdivision_type="SIMPLE"
    cobj.modifiers["subd"].show_expanded = False
    cobj.modifiers["subd"].render_levels = 1
    
#---Add constraints COPY LOCATION + ROTATION
    cobj.constraints.new(type='COPY_LOCATION')
    cobj.constraints["Copy Location"].target = bpy.data.objects[dupli.name]
    cobj.constraints["Copy Location"].show_expanded = False
    cobj.constraints.new(type='COPY_ROTATION')
    cobj.constraints["Copy Rotation"].show_expanded = False
    cobj.constraints["Copy Rotation"].target = bpy.data.objects[dupli.name]
    
    cobj.Lumiere.typlight = "Panel"
    cobj.Lumiere.energy = 10

#---Parent the blender lamp to the light mesh
    cobj.parent = dupli
    cobj.matrix_parent_inverse = dupli.matrix_world.inverted()

#---Make the dupliverts object active
    bpy.context.scene.objects.active = bpy.data.objects[dupli.name]
    
    return(dupli)   
#########################################################################################################

#########################################################################################################
def create_projector(self, context, light_name):
    """Create the projector with modifiers"""
    
#---Get the object used for DupliVerts  
    dupli = get_object(context, light_name)
        
#---Create the mesh
    projector_name = "PROJECTOR_" + light_name
    if projector_name in bpy.data.meshes:
        mesh = bpy.data.meshes[projector_name]
        bpy.data.meshes.remove(mesh)

    bpy.ops.mesh.primitive_plane_add(location=(0, 0, 0))
    projector = bpy.context.object
    projector.draw_type = 'WIRE'
    projector.data.name = projector_name
    projector.name = projector_name
    projector.Lumiere.lightname = projector_name
    
#---Add the material
    projector_mat()
    mat_name, mat = get_mat_name(projector_name)
    projector.active_material = mat

#---Parent the projector to the light for DupliVerts
    projector.parent = dupli
    projector.matrix_parent_inverse = dupli.matrix_world.inverted()
    projector.parent_type = 'OBJECT'

#---Change the visibility 
    projector.draw_type = 'WIRE'
    projector.show_transparent = True
    projector.show_wire = False
    projector.cycles_visibility.camera = False
    projector.cycles_visibility.diffuse = False
    projector.cycles_visibility.glossy = True
    projector.cycles_visibility.transmisison = False
    projector.cycles_visibility.scatter = False
    projector.cycles_visibility.shadow = True
    
#---Add Bevel
    projector.modifiers.new("Bevel", type='BEVEL')
    projector.modifiers["Bevel"].show_expanded = False
    projector.modifiers["Bevel"].use_only_vertices = True
    projector.modifiers["Bevel"].use_clamp_overlap = True
    projector.modifiers["Bevel"].loop_slide = True
    projector.modifiers["Bevel"].width = 0
    projector.modifiers["Bevel"].segments = 6
    projector.modifiers["Bevel"].profile = .5
    projector.modifiers["Bevel"].limit_method = 'ANGLE'
    projector.modifiers["Bevel"].angle_limit = math.radians(80)

#---Add 1 simple subsurf
    projector.modifiers.new("subd", type='SUBSURF')
    projector.modifiers["subd"].subdivision_type="SIMPLE"
    projector.modifiers["subd"].render_levels = 1
    projector.modifiers["subd"].show_expanded = False

#---Add Solidify
    projector.modifiers.new("Solidify", type='SOLIDIFY')
    projector.modifiers["Solidify"].thickness = 0.0001
    projector.modifiers["Solidify"].use_rim = True
    projector.modifiers["Solidify"].use_rim_only = False
    projector.modifiers["Solidify"].offset = -1.0
    projector.modifiers["Solidify"].show_expanded = False
    
#---Add constraints COPY ROTATION   
    # projector.constraints.new(type='TRACK_TO')
    # projector.constraints["Track To"].show_expanded = False
    projector.constraints.new(type='COPY_ROTATION')
    projector.constraints["Copy Rotation"].show_expanded = False    
    projector.constraints["Copy Rotation"].target = bpy.data.objects[dupli.name]
    
    update_projector_scale_min_x(self, context)
    update_projector_scale_min_y(self, context)
    projector.select = False
    dupli.select = True
    
    return(projector)   

#########################################################################################################

#########################################################################################################
def create_base_projector(self, context, light_name):
    """Create the back of the projector with modifiers"""
    
#---Get the object used for DupliVerts  
    dupli = get_object(context, light_name)
    projector = get_object(context, "PROJECTOR_" + light_name)
    
#---Create the mesh
    base_projector_name = "BASE_PROJECTOR_" + light_name
    if base_projector_name in bpy.data.meshes:
        mesh = bpy.data.meshes[base_projector_name]
        bpy.data.meshes.remove(mesh)

    bpy.ops.mesh.primitive_plane_add(location=(0, 0, 0))
    base_projector = bpy.context.object
    base_projector.dimensions[0] = projector.dimensions[0]
    base_projector.dimensions[1] = projector.dimensions[1]
    base_projector.draw_type = 'WIRE'
    base_projector.data.name = base_projector.name = base_projector_name
    base_projector.Lumiere.lightname = base_projector_name
    
#---Add the material
    projector_mat()
    mat = bpy.data.materials.get("BASE_PROJECTOR_mat")
    base_projector.data.materials.append(mat)

#---Parent the projector to the light for DupliVerts
    base_projector.parent = dupli
    base_projector.parent_type = 'VERTEX'
    bpy.data.objects[base_projector.name].select = False
    
#---Change the visibility 
    base_projector.draw_type = 'WIRE'
    base_projector.show_transparent = True
    base_projector.show_wire = False
    base_projector.cycles_visibility.camera = False
    base_projector.cycles_visibility.diffuse = True
    base_projector.cycles_visibility.glossy = True
    base_projector.cycles_visibility.transmisison = False
    base_projector.cycles_visibility.scatter = False
    base_projector.cycles_visibility.shadow = True
    
#---Add Bevel
    base_projector.modifiers.new("Bevel", type='BEVEL')
    base_projector.modifiers["Bevel"].show_expanded = False
    base_projector.modifiers["Bevel"].use_only_vertices = True
    base_projector.modifiers["Bevel"].use_clamp_overlap = True
    base_projector.modifiers["Bevel"].loop_slide = True
    base_projector.modifiers["Bevel"].width = 0
    base_projector.modifiers["Bevel"].segments = 6
    base_projector.modifiers["Bevel"].profile = .5
    base_projector.modifiers["Bevel"].limit_method = 'ANGLE'
    base_projector.modifiers["Bevel"].angle_limit = math.radians(80)

#---Add Solidify
    base_projector.modifiers.new("Solidify", type='SOLIDIFY')
    base_projector.modifiers["Solidify"].thickness = 1.5
    base_projector.modifiers["Solidify"].use_rim = True
    base_projector.modifiers["Solidify"].use_rim_only = True
    base_projector.modifiers["Solidify"].offset = -0.5
    base_projector.modifiers["Solidify"].show_expanded = False

#---Add 1 simple subsurf
    base_projector.modifiers.new("subd", type='SUBSURF')
    base_projector.modifiers["subd"].subdivision_type="SIMPLE"
    base_projector.modifiers["subd"].levels = 2
    base_projector.modifiers["subd"].render_levels = 2
    base_projector.modifiers["subd"].show_expanded = False
    base_projector.modifiers["subd"].show_only_control_edges = True

#---Add taper
    base_projector.modifiers.new("Taper", type='SIMPLE_DEFORM')
    base_projector.modifiers["Taper"].show_expanded = False
    base_projector.modifiers["Taper"].deform_method = 'TAPER'
    base_projector.modifiers["Taper"].factor = 0
    base_projector.modifiers["Taper"].limits[1] = 0.75
    
#---Add constraints TRACK TO + COPY LOCATION    
    # base_projector.constraints.new(type='TRACK_TO')
    # base_projector.constraints["Track To"].show_expanded = False
    base_projector.constraints.new(type='COPY_LOCATION')
    base_projector.constraints["Copy Location"].target = bpy.data.objects[dupli.name]
    base_projector.constraints["Copy Location"].show_expanded = False
    base_projector.constraints.new(type='COPY_ROTATION')
    base_projector.constraints["Copy Rotation"].show_expanded = False
    base_projector.constraints["Copy Rotation"].target = bpy.data.objects[dupli.name]

    update_projector(self, context)

#---Add drivers
    add_driver(base_projector.cycles_visibility, projector, 'glossy', 'cycles_visibility.glossy')
    add_driver(base_projector.modifiers["Bevel"], dupli, 'width', 'Lumiere.projector_smooth')
    add_driver(base_projector.modifiers["Bevel"], projector, 'segments', 'modifiers["Bevel"].segments')
    add_driver(base_projector.modifiers["Solidify"], dupli, 'thickness', 'Lumiere.projector_range', func = '(thickness / 3) + ')
    add_driver(base_projector.modifiers["Taper"], dupli, 'factor', 'Lumiere.projector_taper', func = '1 - ')

    return(base_projector)  

#########################################################################################################

#########################################################################################################
def create_light_custom(self, context, cobj):
    """Create custom light"""
    
    i = 0

    for ob in context.scene.objects:
        if ob.type != 'EMPTY' and ob.data.name.startswith("Lumi"):
            i += 1
    
#---Create the DupliVerts
    dupli = create_dupli(self, context) 
    
#---Add the material
    cobj.data.name = "SOFTBOX_" + dupli.data.name
    softbox_mat(cobj)
    mat_name, mat = get_mat_name(cobj.data.name)
    cobj.active_material = mat
       
#---Change the visibility 
    cobj.Lumiere.lightname = cobj.data.name
    cobj.draw_type = 'TEXTURED'
    cobj.show_transparent = True
    cobj.show_wire = True
    cobj.cycles_visibility.camera = False
    cobj.cycles_visibility.shadow = False
    
#---Add Bevel
    cobj.modifiers.new("Bevel", type='BEVEL')
    cobj.modifiers["Bevel"].use_only_vertices = True
    cobj.modifiers["Bevel"].use_clamp_overlap = True
    cobj.modifiers["Bevel"].loop_slide = True
    cobj.modifiers["Bevel"].width = .25
    cobj.modifiers["Bevel"].segments = 5
    cobj.modifiers["Bevel"].profile = .5
    cobj.modifiers["Bevel"].show_expanded = False

#---Add 1 simple subsurf
    cobj.modifiers.new("subd", type='SUBSURF')
    cobj.modifiers["subd"].subdivision_type="SIMPLE"
    cobj.modifiers["subd"].show_expanded = False
    cobj.modifiers["subd"].render_levels = 1
    
#---Add constraints COPY LOCATION + ROTATION
    cobj.constraints.new(type='COPY_LOCATION')
    cobj.constraints["Copy Location"].target = bpy.data.objects[dupli.name]
    cobj.constraints["Copy Location"].show_expanded = False
    cobj.constraints.new(type='COPY_ROTATION')
    cobj.constraints["Copy Rotation"].show_expanded = False
    cobj.constraints["Copy Rotation"].target = bpy.data.objects[dupli.name]
    
    cobj.Lumiere.typlight = "Panel"
    cobj.Lumiere.energy = 10

#---Parent the blender lamp to the light mesh
    cobj.parent = dupli
    cobj.matrix_parent_inverse = dupli.matrix_world.inverted()

#---Make the dupliverts object active
    bpy.context.scene.objects.active = bpy.data.objects[dupli.name]
    
    return(dupli)   
    
#########################################################################################################

#########################################################################################################
def create_light_point(self, context, newlight = False, dupli_name = "Lumiere"):
    """Create a blender light point"""
    
#---Create the light mesh object for the duplication of the lamp
    if newlight:
        dupli = get_object(context, self.lightname)

    else:
        dupli = create_dupli(self, context, dupli_name)
        
#---Create the point lamp
    bpy.ops.object.lamp_add(type='POINT', view_align=False, location=(0,0,0))
    bpy.context.active_object.data.name = "LAMP_" + dupli.data.name 
    lamp = bpy.context.object
    lamp.name = "LAMP_" + dupli.data.name 

#---Initialize MIS / Type / Name    
    lamp.data.cycles.use_multiple_importance_sampling = True
    lamp.Lumiere.typlight = bpy.context.scene.Lumiere.typlight
    lamp.Lumiere.lightname = bpy.context.active_object.data.name

#---Constraints 
    bpy.ops.object.constraint_add(type='COPY_TRANSFORMS')
    lamp.constraints["Copy Transforms"].target = bpy.data.objects[dupli.name]
    context.scene.objects.active = bpy.data.objects[dupli.name]

#---Parent the blender lamp to the dupli mesh
    lamp.parent = dupli

#---Create nodes
    if not newlight:    
        create_lamp_nodes(self, context, lamp)
    
    return(dupli)

#########################################################################################################

#########################################################################################################
def create_light_sun(self, context, newlight = False, dupli_name = "Lumiere"):
    """Create a blender light sun"""
    
#---Create the light mesh object for the duplication of the lamp
    if newlight:
        dupli = get_object(context, self.lightname)
    else:
        dupli = create_dupli(self, context, dupli_name)
    
#---Create the sun lamp
    bpy.ops.object.lamp_add(type='SUN', view_align=False, location=(0,0,0))
    
    if dupli.Lumiere.typlight == "Env":
        context.active_object.data.name = "WORLD_" + dupli.data.name 
    else:
        context.active_object.data.name = "LAMP_" + dupli.data.name 
    lamp = context.object
    lamp.name = "LAMP_" + dupli.data.name 

#---Initialize MIS / Type / Name
    lamp.data.cycles.use_multiple_importance_sampling = True
    lamp.Lumiere.typlight = "Sun"
    lamp.Lumiere.lightname = context.active_object.data.name

#---Constraints 
    bpy.ops.object.constraint_add(type='COPY_TRANSFORMS')
    lamp.constraints["Copy Transforms"].target = bpy.data.objects[dupli.name]
    context.scene.objects.active = bpy.data.objects[dupli.name]

#---Parent the blender lamp to the dupli mesh
    lamp.parent = dupli 

    #---Create nodes
    if not newlight:    
        create_lamp_nodes(self, context, lamp)
    
    return(dupli)
#########################################################################################################

#########################################################################################################
def create_light_spot(self, context, newlight = False, dupli_name = "Lumiere"):
    """Create a blender light spot"""
    
#---Create the light mesh object for the duplication of the lamp
    if newlight:
        dupli = get_object(context, self.lightname)

    else:
        dupli = create_dupli(self, context, dupli_name)

#---Create the spot lamp
    bpy.ops.object.lamp_add(type='SPOT', view_align=False, location=(0,0,0))
    context.active_object.data.name = "LAMP_" + dupli.data.name 
    lamp = context.object
    lamp.name = "LAMP_" + dupli.data.name 
    lamp.data.cycles.use_multiple_importance_sampling = True
    lamp.Lumiere.typlight = "Spot"
    lamp.Lumiere.lightname = context.active_object.data.name

#---Constraints
    bpy.ops.object.constraint_add(type='COPY_TRANSFORMS')
    lamp.constraints["Copy Transforms"].target = bpy.data.objects[dupli.name]

#---Parent the blender lamp to the dupli mesh
    context.scene.objects.active = bpy.data.objects[dupli.name]
    lamp.parent = dupli
    
#---Create nodes
    if not newlight:    
        create_lamp_nodes(self, context, lamp)

    return(dupli)

#########################################################################################################

#########################################################################################################
def create_light_sky(self, context, dupli_name = "Lumiere"):
    """Create light sky"""
    
#---Create a new world if not exist
    world = ""
    for w in bpy.data.worlds:
        if w.name == "Lumiere_world":
            world = bpy.data.worlds['Lumiere_world']
            
    if world == "":
        context.scene.world = bpy.data.worlds.new("Lumiere_world")
        world = context.scene.world

    world.use_nodes= True
    world.node_tree.nodes.clear() 

#---Add a lamp for the sun and drive the sky texture
    cobj = create_light_sun(self, context, dupli_name = dupli_name)     

#---Use multiple importance sampling for the world
    context.scene.world.cycles.sample_as_light = True
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

    cobj.Lumiere.typlight = "Sky"

    return(cobj)
#########################################################################################################

#########################################################################################################
def create_light_area(self, context, newlight = False, dupli_name = "Lumiere"):
    """Create a blender light area"""
    
#---Create the light mesh object for the duplication of the lamp
    if newlight:
        dupli = get_object(context, self.lightname)
    else:
        dupli = create_dupli(self, context, dupli_name)
        
#---Create the area lamp
    bpy.ops.object.lamp_add(type='AREA', view_align=False, location=(0,0,0))
    lamp = bpy.context.object
    lamp.name = "LAMP_" + dupli.data.name
    lamp.data.shape = 'RECTANGLE'
    lamp.data.name = "LAMP_" + dupli.data.name 
    lamp.data.cycles.use_multiple_importance_sampling = True
    lamp.Lumiere.typlight = "Area"
    lamp.Lumiere.lightname = context.active_object.data.name

#---Add constraints COPY LOCATION + ROTATION
    lamp.constraints.new(type='COPY_LOCATION')
    lamp.constraints["Copy Location"].target = bpy.data.objects[dupli.name]
    lamp.constraints["Copy Location"].show_expanded = False
    lamp.constraints.new(type='COPY_ROTATION')
    lamp.constraints["Copy Rotation"].show_expanded = False
    lamp.constraints["Copy Rotation"].target = bpy.data.objects[dupli.name]

#---Parent the blender lamp to the dupli mesh
    context.scene.objects.active = bpy.data.objects[dupli.name]
    lamp.parent = dupli
    
#---Create nodes
    if not newlight:    
        create_lamp_nodes(self, context, lamp)
    
    return(dupli)
    
#########################################################################################################

#########################################################################################################
def create_dupli(self, context, dupli_name = "Lumiere"):
    """Single point mesh for duplication of the blender lamp and projector"""
    
    verts = [(0, 0, 0)]

#---Create object
    i = 0
    split_name = dupli_name.split(".")
    if split_name[0] in context.scene.objects:
        while dupli_name in context.scene.objects:
            i += 1
            dupli_name = split_name[0] + "." + str(i).zfill(3)

    me = bpy.data.meshes.new(name= "Lumiere")
    dupli = bpy.data.objects.new(dupli_name, me)
    dupli.select = True
    context.scene.objects.link(dupli)
    me.from_pydata(verts, [], [])
    me.update()

    context.scene.objects.active = bpy.data.objects[dupli_name]

    dupli = context.object
    dupli.Lumiere.typlight = context.scene.Lumiere.typlight
    dupli.Lumiere.lightname = dupli.data.name 
    dupli.constraints.new(type='TRACK_TO')

#---Change the visibility 
    dupli.draw_type = 'TEXTURED'
    dupli.show_transparent = True
    dupli.show_wire = True
    dupli.cycles_visibility.camera = False
    dupli.cycles_visibility.diffuse = True
    dupli.cycles_visibility.glossy = True
    dupli.cycles_visibility.transmisison = False
    dupli.cycles_visibility.scatter = False
    dupli.cycles_visibility.shadow = True
    dupli.dupli_type = 'VERTS'
    
    return (dupli)

#########################################################################################################

#########################################################################################################
def create_lamp_nodes(self, context, lamp):
    """Cysles material nodes for blender lights"""
    
#---Emission
    emit = lamp.data.node_tree.nodes["Emission"]
    emit.inputs[1].default_value = lamp.Lumiere.energy
    emit.location = (120.0, 320.0)  
    
#---Blackbody : Horizon daylight kelvin temperature for sun
    blackbody = lamp.data.node_tree.nodes.new("ShaderNodeBlackbody")
    blackbody.inputs[0].default_value = 4000
    blackbody.location = (-100.0, 480.0)    
    
#---Color Ramp Node for area
    colramp = lamp.data.node_tree.nodes.new(type="ShaderNodeValToRGB")
    colramp.color_ramp.elements[0].color = (1,1,1,1)
    # lamp.data.node_tree.links.new(colramp.outputs[0], emit.inputs[0])
    colramp.location = (-180.0, 380.0)  
    
#---Light Falloff
    falloff = lamp.data.node_tree.nodes.new("ShaderNodeLightFalloff")
    falloff.inputs[0].default_value = lamp.Lumiere.energy
    if lamp.data.type != "SUN":
        lamp.data.node_tree.links.new(falloff.outputs[1], emit.inputs[1])
    falloff.location = (-100.0, 140.0)  

#---Dot Product
    dotpro = lamp.data.node_tree.nodes.new("ShaderNodeVectorMath")
    dotpro.operation = 'DOT_PRODUCT'
    lamp.data.node_tree.links.new(dotpro.outputs[1], colramp.inputs[0])
    dotpro.location = (-360.0, 320.0)

#---Geometry Node
    geom = lamp.data.node_tree.nodes.new(type="ShaderNodeNewGeometry")
    lamp.data.node_tree.links.new(geom.outputs[1], dotpro.inputs[0])
    lamp.data.node_tree.links.new(geom.outputs[4], dotpro.inputs[1])
    geom.location = (-540.0, 360.0)        

#########################################################################################################

#########################################################################################################
def create_lamp_grid(self, context):
    """Create a grid of lights and projector with the repetition of duplicators"""
    
    verts = []
    edges = []
    faces = []
    listvert = []
    listfaces = []
        
    # obj_light = context.active_object
    obj_light = get_object(context, self.lightname)
    if obj_light.Lumiere.nbcol < 1: obj_light.Lumiere.nbcol = 1
    if obj_light.Lumiere.nbrow < 1: obj_light.Lumiere.nbrow = 1

    gapx = obj_light.Lumiere.gapx
    gapy = obj_light.Lumiere.gapy
    widthx = .01 #* obj_light.Lumiere.scale_x
    widthy = .01 #* obj_light.Lumiere.scale_y
    left = -((widthx * (obj_light.Lumiere.nbcol-1)) + (gapx * (obj_light.Lumiere.nbcol-1)) ) / 2
    right = left + widthx
    start = -((widthy * (obj_light.Lumiere.nbrow-1)) + (gapy * (obj_light.Lumiere.nbrow-1))) / 2
    end = start + widthy
    i = 0

#---Get the material
    mat_name, mat = get_mat_name(obj_light.data.name)
    
    for x in range(obj_light.Lumiere.nbcol):
    #---Create Verts, Faces on X axis
        nbvert = len(verts)
        verts.extend([(left,start,0)])
        start2 = end + gapy
        end2 = start2 + widthy

        for y in range(obj_light.Lumiere.nbrow-1):
        #---Create Verts, Faces on Z axis
            nbvert = len(verts)
            verts.extend([(left,start2,0)])
            start2 = end2 + gapy
            end2 = start2 + widthy

        left = right + gapx
        right = left + widthx

#---Get the mesh
    old_mesh = obj_light.data
    mesh = bpy.data.meshes.new(name=obj_light.name)
 
#---Update the mesh
    mesh.from_pydata(verts, [], [])
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
    context.object.show_transparent = True
    context.object.show_wire = True

    cobj = context.active_object
    cobj.Lumiere.lightname = cobj.data.name
    context.object.cycles_visibility.camera = False

#########################################################################################################

#########################################################################################################
def create_light_env_widget(self, context, dupli):
    """Create a simple widget to indicate the interactive target for the environment light"""
    
#---Create widget
    size = .8
    verts = [(0.0*size, 0.29663604497909546*size, 0.0*size), (-0.05787081643939018*size, 0.2909362316131592*size, 0.0*size), (-0.11351769417524338*size, 0.27405592799186707*size, 0.0*size), (-0.16480213403701782*size, 0.24664384126663208*size, 0.0*size), (-0.2097533494234085*size, 0.2097533494234085*size, 0.0*size), (-0.24664384126663208*size, 0.16480213403701782*size, 0.0*size), (-0.27405592799186707*size, 0.11351767927408218*size, 0.0*size), (-0.2909362316131592*size, 0.05787082761526108*size, 0.0*size), (-0.29663604497909546*size, 2.2395397536456585e-08*size, 0.0*size), (-0.2909362316131592*size, -0.0578707791864872*size, 0.0*size), (-0.27405598759651184*size, -0.1135176420211792*size, 0.0*size), (-0.24664384126663208*size, -0.16480213403701782*size, 0.0*size), (-0.2097533494234085*size, -0.2097533494234085*size, 0.0*size), (-0.16480213403701782*size, -0.24664384126663208*size, 0.0*size), (-0.1135176420211792*size, -0.27405592799186707*size, 0.0*size), (-0.05787074938416481*size, -0.2909362316131592*size, 0.0*size), (9.665627942467836e-08*size, -0.29663604497909546*size, 0.0*size), (0.05787093564867973*size, -0.2909362018108368*size, 0.0*size), (0.11351781338453293*size, -0.2740558981895447*size, 0.0*size), (0.16480228304862976*size, -0.24664373695850372*size, 0.0*size), (0.20975348353385925*size, -0.20975323021411896*size, 0.0*size), (0.24664399027824402*size, -0.1648019701242447*size, 0.0*size), (0.2740560472011566*size, -0.11351746320724487*size, 0.0*size), (0.29093629121780396*size, -0.05787056311964989*size, 0.0*size), (0.29663604497909546*size, 2.864314581074723e-07*size, 0.0*size), (0.2909362018108368*size, 0.057871121913194656*size, 0.0*size), (0.2740557789802551*size, 0.11351799219846725*size, 0.0*size), (0.24664364755153656*size, 0.1648024320602417*size, 0.0*size), (0.20975308120250702*size, 0.2097536027431488*size, 0.0*size), (0.16480180621147156*size, 0.24664407968521118*size, 0.0*size), (0.11351729184389114*size, 0.2740561366081238*size, 0.0*size), (0.05787036940455437*size, 0.29093629121780396*size, 0.0*size), (0.0*size, 0.5299842357635498*size, 0.0*size), (-0.20281623303890228*size, 0.48964163661003113*size, 0.0*size), (-0.3747554123401642*size, 0.3747554123401642*size, 0.0*size), (-0.48964163661003113*size, 0.2028162032365799*size, 0.0*size), (-0.5299842357635498*size, 4.001270070830287e-08*size, 0.0*size), (-0.48964163661003113*size, -0.20281609892845154*size, 0.0*size), (-0.3747554123401642*size, -0.3747554123401642*size, 0.0*size), (-0.20281609892845154*size, -0.4896417260169983*size, 0.0*size), (1.726908180899045e-07*size, -0.5299842357635498*size, 0.0*size), (0.202816441655159*size, -0.48964157700538635*size, 0.0*size), (0.37475571036338806*size, -0.37475523352622986*size, 0.0*size), (0.48964181542396545*size, -0.20281578600406647*size, 0.0*size), (0.5299842357635498*size, 5.117523755870934e-07*size, 0.0*size), (0.4896414279937744*size, 0.20281675457954407*size, 0.0*size), (0.37475499510765076*size, 0.3747558891773224*size, 0.0*size), (0.20281550288200378*size, 0.4896419644355774*size, 0.0*size), ]
    edges = [(1, 0), (2, 1), (3, 2), (4, 3), (5, 4), (6, 5), (7, 6), (8, 7), (9, 8), (10, 9), (11, 10), (12, 11), (13, 12), (14, 13), (15, 14), (16, 15), (17, 16), (18, 17), (19, 18), (20, 19), (21, 20), (22, 21), (23, 22), (24, 23), (25, 24), (26, 25), (27, 26), (28, 27), (29, 28), (30, 29), (31, 30), (0, 31), (0, 32), (2, 33), (4, 34), (6, 35), (8, 36), (10, 37), (12, 38), (14, 39), (16, 40), (18, 41), (20, 42), (22, 43), (24, 44), (26, 45), (28, 46), (30, 47), ]

#---Get the mesh if already exist
    world_name = "WORLD_" + dupli.data.name
    if world_name in bpy.data.meshes:
        mesh = bpy.data.meshes[world_name]
        bpy.data.meshes.remove(mesh)
    
#---Create the mesh
    mesh = bpy.data.meshes.new(world_name)
    mesh.from_pydata(verts, edges, [])
    mesh.update(calc_edges=True)
    object_data_add(context, mesh)
    cobj = context.object
    cobj.Lumiere.lightname = cobj.data.name
    cobj.draw_type = 'WIRE'
    
#---Add constraints COPY LOCATION + ROTATION
    cobj.constraints.new(type='COPY_LOCATION')
    cobj.constraints["Copy Location"].target = bpy.data.objects[dupli.name]
    cobj.constraints["Copy Location"].show_expanded = False
    cobj.constraints.new(type='COPY_ROTATION')
    cobj.constraints["Copy Rotation"].show_expanded = False
    cobj.constraints["Copy Rotation"].target = bpy.data.objects[dupli.name]
    
    cobj.Lumiere.typlight = "Env"
    
#---Parent the blender lamp to the light mesh
    cobj.parent = dupli
    cobj.matrix_parent_inverse = dupli.matrix_world.inverted()  


#########################################################################################################

#########################################################################################################
class EditLight(bpy.types.Operator):
    """Edit the light : Interactive mode"""
    
    bl_description = "Edit the light :\n"+\
                     "- Target a new location\n- Rotate\n- Scale\n- Transform to grid"
    bl_idname = "object.edit_light"
    bl_label = "Add Light"
    # bl_options = {'GRAB_CURSOR', 'BLOCKING', 'UNDO', 'INTERNAL'}
    bl_options = {'REGISTER', 'UNDO'}

    #-------------------------------------------------------------------
    from_panel = bpy.props.BoolProperty(default=False)
    modif = bpy.props.BoolProperty(default=False)
    editmode = bpy.props.BoolProperty(default=False)
    dist_light = bpy.props.BoolProperty(default=False)
    scale_light = bpy.props.BoolProperty(default=False)
    strength_light = bpy.props.BoolProperty(default=False)
    rotate_light_x = bpy.props.BoolProperty(default=False)
    rotate_light_y = bpy.props.BoolProperty(default=False)
    rotate_light_z = bpy.props.BoolProperty(default=False)
    scale_light_x = bpy.props.BoolProperty(default=False)
    scale_light_y = bpy.props.BoolProperty(default=False)
    scale_gapx = bpy.props.BoolProperty(default=False)
    scale_gapy = bpy.props.BoolProperty(default=False)
    orbit = bpy.props.BoolProperty(default=False)
    custom = bpy.props.BoolProperty()
    act_light = bpy.props.StringProperty()
    lmb = False
    falloff_mode = False    
    offset = FloatVectorProperty(name="Offset", size=3,)
    reflect_angle = bpy.props.StringProperty()
    rotz = 0
    k_press = 0
    save_range =""
    #-------------------------------------------------------------------

    def check(self, context):
        return True

    def check_region(self,context,event):
        if context.area != None:
            if context.area.type == "VIEW_3D" :
                t_panel = context.area.regions[1]
                n_panel = context.area.regions[3]
                view_3d_region_x = Vector((context.area.x + t_panel.width, context.area.x + context.area.width - n_panel.width))
                view_3d_region_y = Vector((context.region.y, context.region.y+context.region.height))
                
                if (event.mouse_x > view_3d_region_x[0] and event.mouse_x < view_3d_region_x[1] and event.mouse_y > view_3d_region_y[0] and event.mouse_y < view_3d_region_y[1]): # or self.modif is True:
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
        #-------------------------------------------------------------------

    #---Find the limit of the view3d region
        self.check_region(context,event)
        try:
        #---Called from Edit icon
            if self.in_view_3d and context.area == self.lumiere_area:
            
                self.rv3d = context.region_data
                self.region = context.region            
                    
            #---Allow navigation
                
                if event.type in {'MIDDLEMOUSE'} or event.type.startswith("NUMPAD"): 
                    return {'PASS_THROUGH'}
                    
            #---Zoom Keys
                if (event.type in  {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'} and not 
                   (event.ctrl or event.shift or event.alt)):
                    return{'PASS_THROUGH'}          
                    
                if event.type == 'LEFTMOUSE':
                    self.lmb = event.value == 'PRESS'
                
                if event.value == 'RELEASE':
                    context.window.cursor_modal_set("DEFAULT")
                    
            #---RayCast the light
                if self.editmode and not self.modif: 
                    if self.lmb : 
                        raycast_light(self, obj_light.Lumiere.range, context, coord)
                        bpy.context.window.cursor_modal_set("SCROLL_XY")
                        
            else:
            #---Called from the transform panel light
                if self.modif:
                    transform_light(self, context, event, obj_light)

                else:
                    return {'PASS_THROUGH'}
            
        #---Transform the light
            if self.editmode :
                obj_light = context.active_object

                str1 ="Range: " + context.scene.Key_Distance + " || " + \
                      "Energy: " + context.scene.Key_Strength + " || "  + \
                      "Angle: " + context.scene.Key_Normal + " || " + \
                      "Invert: " + context.scene.Key_Invert + " || "    + \
                      "Fallof: " + context.scene.Key_Falloff + " || " + \
                      "Orbit: " + context.scene.Key_Orbit + " || "
                str2 =" "
                if obj_light.Lumiere.typlight in ("Panel"):
                    str2 = "Scale: " + context.scene.Key_Scale + "+Mouse Move ||" + \
                           "Scale X: " + context.scene.Key_Scale_X + " || " + \
                           "Scale Y: " + context.scene.Key_Scale_Y + " || "
                elif obj_light.Lumiere.typlight in ("Area"):
                    str2 = "Scale: " + context.scene.Key_Scale + "+Mouse Move ||" + \
                           "Scale X: " + context.scene.Key_Scale_X + " || " + \
                           "Scale Y: " + context.scene.Key_Scale_Y + " || "
                elif obj_light.Lumiere.typlight in ("Spot"):
                    str2 = "Scale Cone: " + context.scene.Key_Scale + " || " + \
                           "Softness: " + context.scene.Key_Scale_X + " || " + \
                           "Blend Cone: " + context.scene.Key_Scale_Y + " || "
                elif obj_light.Lumiere.typlight in ("Sky"):
                    str2 = "Turbidity: " + context.scene.Key_Scale 
                else:
                    str2 = "Softness: " + context.scene.Key_Scale 
                text_header = str1 + str2 + " || Confirm: RMB"
                context.area.header_text_set(text_header)
                
                transform_light(self, context, event, obj_light)
                
                if event.type =='RIGHTMOUSE':
                    if obj_light['pixel_select']: 
                        obj_light['pixel_select'] = False
                    else:
                        if self.orbit:
                            obj_light.constraints['Track To'].influence = 0
                            obj_light.location = self.initial_location
                            remove_constraint(self, context, obj_light.data.name)   
                        # else:
                            # picker = object_picker(self, context, coord)
                            # if picker is not None: 
                                # if "Lumiere" in bpy.data.objects[picker].data.name : 
                                    # return {'PASS_THROUGH'}

                        context.area.header_text_set()
                        context.window.cursor_modal_set("DEFAULT")
                        self.remove_handler()
                        return {'FINISHED'}
                        
                if event.type in {'ESC'}:
                    context.area.header_text_set()
                    context.window.cursor_modal_set("DEFAULT")
                    self.remove_handler()
                    if self.orbit:
                        obj_light.constraints['Track To'].influence = 0
                        obj_light.location = self.initial_location
                        remove_constraint(self, context, obj_light.data.name)   
                        return {'FINISHED'}
                else:
                    return {'RUNNING_MODAL'}

        #---Undo before creating the light
            if event.type in {'RIGHTMOUSE', 'ESC'}:
                context.area.header_text_set()
                context.window.cursor_modal_set("DEFAULT")
                self.remove_handler()
                return{'FINISHED'}

            return {'PASS_THROUGH'}
        except Exception as error:
            if event.type not in {'RIGHTMOUSE', 'ESC'}:
                print("Error to report : ", error)
                context.window.cursor_modal_set("DEFAULT")
                context.area.header_text_set()
                self.remove_handler()
            return {'FINISHED'}

    def execute (self, context):
        for ob in context.scene.objects:
            if ob.type != 'EMPTY' and ob.data.name.startswith("Lumiere"):
                ob.select = False
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        row = layout.row(align = True)
        row1 = row.split(align=True)
        row1.label("Shading")
        row2 = row.split(align=True)
        
    def remove_handler(self):
        if self._handle:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
        self._handle = None
        
    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode == 'OBJECT'
        
    def invoke(self, context, event):

        if context.space_data.type == 'VIEW_3D':

            args = (self, context, event)
            context.area.header_text_set("Add light: CTRL+LMB || Confirm: ESC or RMB")
            if self.editmode or self.custom or self.from_panel:
                context.scene.objects.active = bpy.data.objects[self.act_light] 
                context.area.header_text_set("Edit light: LMB || Confirm: ESC or RMB")
            obj_light = context.active_object
                
            if self.from_panel:
                self.editmode = True
                self.modif = True
            
            if self.modif:
                self.first_mouse_x = event.mouse_x
                lamp_or_softbox = get_lamp(context, obj_light.Lumiere.lightname)
                self.save_energy = (lamp_or_softbox.scale[0] * lamp_or_softbox.scale[1]) * obj_light.Lumiere.energy
                
            self.lumiere_area = context.area
                            
            if obj_light is not None and obj_light.type != 'EMPTY' and obj_light.data.name.startswith("Lumiere") and self.editmode:
                for ob in context.scene.objects:
                    if ob.type != 'EMPTY' : 
                        ob.select = False
                        
                obj_light.select = True
                self.direction = obj_light.rotation_euler
                self.hit_world = obj_light.location
                obj_light['pixel_select'] = False

            context.window_manager.modal_handler_add(self)
            self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_callback_px, args, 'WINDOW', 'POST_PIXEL')
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "No active View3d detected !")
            return {'CANCELLED'}
    

#########################################################################################################

#########################################################################################################
def transform_light(self, context, event, obj_light):
    """
    Transform the selected light in the interactive mode
    - self.editmode true : interactive mode is on
    - self.modif true : A key has been pressed
    - self.from_panel true : call this operator from the ui panel
    """
    
#---Get the lamp or the softbox link to the dupli
    lamp_or_softbox = get_lamp(context, obj_light.Lumiere.lightname)
    if obj_light.Lumiere.typlight == "Panel":
        softbox = get_lamp(context, obj_light.Lumiere.lightname)
    elif obj_light.Lumiere.typlight != "Env":
        lamp = bpy.data.lamps[lamp_or_softbox.data.name]

#---Projector
    if obj_light.Lumiere.projector:
        projector = context.scene.objects["PROJECTOR_" + obj_light.data.name]
        if obj_light.Lumiere.projector_close:
            base_projector = context.scene.objects["BASE_PROJECTOR_" + obj_light.data.name]
        
    if event.type == 'LEFTMOUSE' and self.modif : 
        self.dist_light = False
        self.scale_light = False
        self.scale_light_x = False
        self.scale_light_y = False
        self.rotate_light_x = False
        self.rotate_light_y = False
        self.rotate_light_z = False
        self.strength_light = False 
        self.scale_gapy = False
        self.scale_gapx = False
        self.k_press = 0
        if self.orbit:
            for c in obj_light.constraints:
                if c.type=='TRACK_TO':
                    remove_constraint(self, context, obj_light.data.name)
                    self.orbit = False  
        self.modif = False

        if self.from_panel:
            self.editmode = False
            self.from_panel = False
            context.area.header_text_set()
            context.window.cursor_modal_set("DEFAULT")
            self.remove_handler()
            return {'FINISHED'}         
    
#---Start the modifications
    if self.editmode and not self.lmb :
        if event.type == 'MOUSEMOVE' :
            self.click_pos=[event.mouse_region_x,event.mouse_region_y]
        #---Precision mode :
            if event.shift:
                precision = 6
            else:
                precision = 1

        #---range : update_range
            if self.dist_light :
                self.modif = True
                bpy.context.window.cursor_modal_set("SCROLL_X")
                delta = event.mouse_x - self.first_mouse_x
                save_range = obj_light.Lumiere.range
                
                obj_light.Lumiere.range += ((math.sqrt(obj_light.location.x**2 + obj_light.location.y**2 + obj_light.location.z**2)*(delta*.01)) / precision)

            #---Keep aspect ratio 
                if obj_light.Lumiere.ratio and obj_light.Lumiere.typlight in ("Panel", "Pencil"):
                    softbox.scale[0] = (obj_light.Lumiere.range * softbox.scale[0]) / save_range
                    softbox.scale[1] = (obj_light.Lumiere.range * softbox.scale[1]) / save_range
                    obj_light.Lumiere.energy = self.save_energy / (softbox.scale[0] * softbox.scale[1])

                hit_world = Vector(obj_light['hit']) + (obj_light.Lumiere.range * Vector(obj_light['dir']))
                obj_light.location = Vector((hit_world[0], hit_world[1], hit_world[2]))

        #---Scale on X and Y axis
            elif self.scale_light:
                self.modif = True
                context.window.cursor_modal_set("SCROLL_X")
                delta = event.mouse_x - self.first_mouse_x

                if obj_light.Lumiere.typlight in ("Panel", "Pencil"):
                    softbox.scale[0] += (math.sqrt(softbox.dimensions.x**2 + softbox.dimensions.y**2 + softbox.dimensions.z**2)*(delta*.01)) / precision
                    softbox.scale[1] += (math.sqrt(softbox.dimensions.x**2 + softbox.dimensions.y**2 + softbox.dimensions.z**2)*(delta*.01)) / precision
                    if softbox.scale[0] < 0.0001:
                        softbox.scale[0] = 0.0001
                    if softbox.scale[1] < 0.0001:
                        softbox.scale[1] = 0.0001

                    if obj_light.Lumiere.ratio:
                        obj_light.Lumiere.energy = self.save_energy / (softbox.scale[0] * softbox.scale[1])

                    if obj_light.Lumiere.projector:
                        self.lightname = obj_light.Lumiere.lightname
                        update_projector_scale_min_x(self, context)
                        update_projector_scale_min_y(self, context)

                elif obj_light.Lumiere.typlight == "Spot":
                    lamp.spot_size += delta * .05 / precision
                elif obj_light.Lumiere.typlight == "Point":
                    lamp.shadow_soft_size += delta * .05 / precision
                elif obj_light.Lumiere.typlight == "Sun" :
                    lamp.shadow_soft_size += delta * .05 / precision
                elif obj_light.Lumiere.typlight =="Sky" :
                    lamp.shadow_soft_size += delta * .002 / precision
                #---Stick to the maximum of turbidity in the Sky texture
                    if lamp.shadow_soft_size > .5:
                        lamp.shadow_soft_size = .5
                    bpy.data.worlds['Lumiere_world'].node_tree.nodes["Sky Texture"].turbidity += delta * .05 / precision
                
                elif obj_light.Lumiere.typlight == "Area":
                    
                    lamp.size += delta * .01
                    lamp.size_y += delta * .01
                    if lamp.size < 0.01:
                        lamp.size = 0.01
                    if lamp.size_y < 0.01:
                        lamp.size_y = 0.01

                    if obj_light.Lumiere.projector:
                        self.lightname = obj_light.Lumiere.lightname
                        update_projector_scale_min_x(self, context)
                        update_projector_scale_min_y(self, context)
                            
        #---Scale on X 
            elif self.scale_light_x:
                self.modif = True
                context.window.cursor_modal_set("SCROLL_X")
                delta = event.mouse_x - self.first_mouse_x
                if obj_light.Lumiere.typlight == "Panel":                   
                    softbox.scale[0] += (math.sqrt(softbox.dimensions.x**2 + softbox.dimensions.y**2 + softbox.dimensions.z**2)*(delta*.01)) / precision
                    if softbox.scale[0] < 0.0001:
                        softbox.scale[0] = 0.0001
                        
                    if obj_light.Lumiere.ratio:
                        obj_light.Lumiere.energy = self.save_energy / (softbox.scale[0] * softbox.scale[1])
                        
                    if obj_light.Lumiere.projector:
                        self.lightname = obj_light.Lumiere.lightname
                        update_projector_scale_min_x(self, context)
                            
                elif obj_light.Lumiere.typlight == "Spot" :
                    lamp.shadow_soft_size += delta * .05 / precision
                    
                elif obj_light.Lumiere.typlight == "Area":
                    lamp.size += delta * .01
                    if lamp.size < 0.01:
                        lamp.size = 0.01

                    if obj_light.Lumiere.projector:
                        self.lightname = obj_light.Lumiere.lightname
                        update_projector_scale_min_x(self, context)

        #---Scale on Y 
            elif self.scale_light_y:
                self.modif = True
                context.window.cursor_modal_set("SCROLL_X")
                delta = event.mouse_x - self.first_mouse_x
                if obj_light.Lumiere.typlight == "Panel":
                    softbox.scale[1] += (math.sqrt(softbox.dimensions.x**2 + softbox.dimensions.y**2 + softbox.dimensions.z**2)*(delta*.01)) / precision
                    if softbox.scale[1] < 0.0001:
                        softbox.scale[1] = 0.0001

                    if obj_light.Lumiere.ratio:
                        obj_light.Lumiere.energy = self.save_energy / (softbox.scale[0] * softbox.scale[1])

                    if obj_light.Lumiere.projector:
                        self.lightname = obj_light.Lumiere.lightname
                        update_projector_scale_min_y(self, context)
                                
                elif obj_light.Lumiere.typlight == "Spot" :
                    lamp.spot_blend += delta * .05 / precision  
                    
                elif obj_light.Lumiere.typlight == "Area":
                    lamp.size_y += delta * .01
                    if lamp.size_y < 0.01:
                        lamp.size_y = 0.01
                
                    if obj_light.Lumiere.projector:
                        self.lightname = obj_light.Lumiere.lightname
                        update_projector_scale_min_y(self, context)
                                                
        #---Rotate 'X' axis
            elif self.rotate_light_x:
                self.modif = True
                context.window.cursor_modal_set("SCROLL_X")
                delta = event.mouse_x - self.first_mouse_x 
                rotmat = Matrix.Rotation(math.radians(-(delta / precision)), 4, 'X')
                obj_light.matrix_world *= rotmat
                                                                    
        #---Rotate 'Y' axis
            elif self.rotate_light_y:
                self.modif = True
                context.window.cursor_modal_set("SCROLL_X")
                delta = event.mouse_x - self.first_mouse_x 
                rotmat = Matrix.Rotation(math.radians(-(delta / precision)), 4, 'Y')
                obj_light.matrix_world *= rotmat
                            
        #---Rotate 'Z' axis
            elif self.rotate_light_z:
                self.modif = True
                context.window.cursor_modal_set("SCROLL_X")
                delta = event.mouse_x - self.first_mouse_x 
                rotmat = Matrix.Rotation(math.radians(-(delta / precision)), 4, 'Z')
                obj_light.matrix_world *= rotmat

        #---Energy
            elif self.strength_light:
                self.modif = True
                context.window.cursor_modal_set("SCROLL_X")
                delta = event.mouse_x - self.first_mouse_x
                if obj_light.Lumiere.typlight == "Panel":
                    softbox = get_lamp(context, obj_light.Lumiere.lightname)
                    obj_light.Lumiere.energy += (math.sqrt(softbox.dimensions.x**2 + softbox.dimensions.y**2 + softbox.dimensions.z**2)*(delta*.01)) / precision 
                elif obj_light.Lumiere.typlight == "Sun":
                    obj_light.Lumiere.energy += (delta * 0.1 / precision)
                elif obj_light.Lumiere.typlight =="Sky" :
                    obj_light.Lumiere.energy += delta * 0.02 / precision
                else:
                    obj_light.Lumiere.energy += delta * 2 / precision
                                        
        #---Scale Gap Y - Only for the Grid shape
            elif self.scale_gapy:
                self.modif = True
                context.window.cursor_modal_set("SCROLL_X")
                delta = event.mouse_x - self.first_mouse_x
                obj_light.Lumiere.gapy += delta*.1 / precision

        #---Scale Gap X - Only for the Grid shape
            elif self.scale_gapx :
                self.modif = True
                context.window.cursor_modal_set("SCROLL_X")
                delta = event.mouse_x - self.first_mouse_x                    
                obj_light.Lumiere.gapx += delta*.1 / precision

        #---Orbit mode
            elif self.orbit:
                self.modif = True
                context.window.cursor_modal_set("HAND")
                update_constraint(self, context, event, obj_light.data.name)

            self.first_mouse_x = event.mouse_x

        #---End of the modifications
            if self.modif == False and not event.ctrl:
                context.window.cursor_modal_set("DEFAULT")

#---Begin Interactive
    if self.editmode :
    #---Distance of the light from the object
        if (getattr(event, context.scene.Key_Distance)):
            self.first_mouse_x = event.mouse_x
            self.dist_light = not self.dist_light
            lamp_or_softbox = get_lamp(context, obj_light.Lumiere.lightname)
            self.save_energy = (lamp_or_softbox.scale[0] * lamp_or_softbox.scale[1]) * obj_light.Lumiere.energy
            
    #---Strength of the light 
        elif event.type == context.scene.Key_Strength and event.value == 'PRESS':
            self.first_mouse_x = event.mouse_x
            self.strength_light = not self.strength_light

    #---Gap of the Grid on Y or X
        elif (getattr(event, context.scene.Key_Gap)):
            if event.type == context.scene.Key_Scale_Y and event.value == 'PRESS' and obj_light.Lumiere.nbrow > 1:
                self.first_mouse_x = event.mouse_x
                self.scale_gapy = not self.scale_gapy
            elif event.type == context.scene.Key_Scale_X and event.value == 'PRESS' and obj_light.Lumiere.nbcol > 1:
                self.first_mouse_x = event.mouse_x
                self.scale_gapx = not self.scale_gapx

    #---Scale the light
        elif event.type == context.scene.Key_Scale and event.value == 'PRESS':
            self.first_mouse_x = event.mouse_x
            lamp_or_softbox = get_lamp(context, obj_light.Lumiere.lightname)
            self.save_energy = (lamp_or_softbox.scale[0] * lamp_or_softbox.scale[1]) * obj_light.Lumiere.energy
            self.scale_light = not self.scale_light

    #---Scale the light on X axis
        elif event.type == context.scene.Key_Scale_X and event.value == 'PRESS' \
            and obj_light.Lumiere.typlight in ("Panel", "Spot", "Area"):
            self.first_mouse_x = event.mouse_x
            lamp_or_softbox = get_lamp(context, obj_light.Lumiere.lightname)
            self.save_energy = lamp_or_softbox.scale[0] * obj_light.Lumiere.energy
            self.scale_light_x = not self.scale_light_x

    #---Scale the light on Y axis
        elif event.type == context.scene.Key_Scale_Y and event.value == 'PRESS'\
            and obj_light.Lumiere.typlight in ("Panel", "Spot", "Area"):
            self.first_mouse_x = event.mouse_x
            lamp_or_softbox = get_lamp(context, obj_light.Lumiere.lightname)
            self.save_energy = lamp_or_softbox.scale[1] * obj_light.Lumiere.energy
            self.scale_light_y = not self.scale_light_y

    #---Orbit mode
        elif event.type == context.scene.Key_Orbit and event.value == 'PRESS':
            self.orbit = not self.orbit
            if self.orbit:
                self.initial_mouse = Vector((event.mouse_x, event.mouse_y, 0.0))
                self.initial_location = obj_light.location.copy()
                target_constraint(self, context, obj_light.data.name)
            else:   
                remove_constraint(self, context, obj_light.data.name)                   
            
    #---Change the view based on the normal of the object
        elif event.type == context.scene.Key_Normal and event.value == 'PRESS': 
            reflect_angle_idx = int(obj_light.Lumiere.reflect_angle)+1
            if reflect_angle_idx > 1:
                reflect_angle_idx = 0
            obj_light.Lumiere.reflect_angle = str(reflect_angle_idx)
            self.reflect_angle = "View" if reflect_angle_idx == 0 else "Normal"
            
    #---Invert the raycast 
        elif event.type == context.scene.Key_Invert and event.value == 'PRESS': 
            obj_light.Lumiere.invert_ray = not obj_light.Lumiere.invert_ray

    #---Rotate the light on the local axis.
        elif event.type == context.scene.Key_Rotate and event.value == 'PRESS':
            self.k_press += 1
            if self.k_press > 3:
                self.k_press = 1

            self.first_mouse_x = event.mouse_x
        #---Rotate Z
            if self.k_press == 1:
                self.rotate_light_z = True
                self.rotate_light_y = False
                self.rotate_light_x = False
        #---Rotate Y
            elif self.k_press == 2:
                self.rotate_light_z = False
                self.rotate_light_y = True
                self.rotate_light_x = False
        #---Rotate X
            elif self.k_press == 3:
                self.rotate_light_z = False
                self.rotate_light_y = False
                self.rotate_light_x = True

        
    #---Type of Fallof
        elif event.type == context.scene.Key_Falloff and event.value == 'PRESS':
            self.falloff_mode = True
            self.key_start = time.time()
            fallidx = int(obj_light.Lumiere.typfalloff)+1
            if fallidx > 2:
                fallidx = 0
            obj_light.Lumiere.typfalloff = str(fallidx)

    #---Add a row.
        elif event.type == 'UP_ARROW' and event.value == 'PRESS': 
            obj_light.Lumiere.nbrow += 1 

    #---Remove a row.
        elif event.type == 'DOWN_ARROW' and event.value == 'PRESS': 
            obj_light.Lumiere.nbrow -= 1 
            if obj_light.Lumiere.nbrow < 1: 
                obj_light.Lumiere.nbrow = 1
            
    #---Add a column.
        elif event.type == 'RIGHT_ARROW' and event.value == 'PRESS': 
            obj_light.Lumiere.nbcol += 1 

    #---Remove a column.
        elif event.type == 'LEFT_ARROW'  and event.value == 'PRESS': 
            obj_light.Lumiere.nbcol -= 1 
            if obj_light.Lumiere.nbcol < 1: 
                obj_light.Lumiere.nbcol = 1 

#########################################################################################################

#########################################################################################################
class CreateLight(bpy.types.Operator):
    """Create a new light: \n- Use CTRL + Left mouse button on an object to create a new light"""
    bl_description = "Create a new light: \n- Use CTRL + Left mouse button on an object to create a new light"
    bl_idname = "object.create_light"
    bl_label = "Add Light"
    bl_options = {"UNDO"}

    #-------------------------------------------------------------------
    from_panel = bpy.props.BoolProperty(default=False)
    modif = bpy.props.BoolProperty(default=False)
    editmode = bpy.props.BoolProperty(default=False)
    dist_light = bpy.props.BoolProperty(default=False)
    scale_light = bpy.props.BoolProperty(default=False)
    strength_light = bpy.props.BoolProperty(default=False)
    rotate_light_x = bpy.props.BoolProperty(default=False)
    rotate_light_y = bpy.props.BoolProperty(default=False)
    rotate_light_z = bpy.props.BoolProperty(default=False)
    scale_light_x = bpy.props.BoolProperty(default=False)
    scale_light_y = bpy.props.BoolProperty(default=False)
    scale_gapx = bpy.props.BoolProperty(default=False)
    scale_gapy = bpy.props.BoolProperty(default=False)
    orbit = bpy.props.BoolProperty(default=False)
    custom = bpy.props.BoolProperty()
    act_light = bpy.props.StringProperty()
    
    lmb = False
    falloff_mode = False    
    reflect_angle = bpy.props.StringProperty()
    offset = FloatVectorProperty(name="Offset", size=3,)
    rotz = 0
    save_range =""
    #-------------------------------------------------------------------
    
    def check_region(self,context,event):
        if context.area != None:
            if context.area.type == "VIEW_3D" :
                t_panel = context.area.regions[1]
                n_panel = context.area.regions[3]
                view_3d_region_x = Vector((context.area.x + t_panel.width, context.area.x + context.area.width - n_panel.width))
                view_3d_region_y = Vector((context.region.y, context.region.y+context.region.height))
                
                if (event.mouse_x > view_3d_region_x[0] and event.mouse_x < view_3d_region_x[1] and event.mouse_y > view_3d_region_y[0] and event.mouse_y < view_3d_region_y[1]): # or self.modif is True:
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
        #-------------------------------------------------------------------

    #---Find the limit of the view3d region
        self.check_region(context,event)
        try:
            if self.in_view_3d and context.area == self.lumiere_area:
            
                self.rv3d = context.region_data
                self.region = context.region
                
            #---Allow navigation
                if event.type in {'MIDDLEMOUSE'} or event.type.startswith("NUMPAD"): 
                    return {'PASS_THROUGH'}
                    
            #---Zoom Keys
                if (event.type in  {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'} and not 
                   (event.ctrl or event.shift or event.alt)):
                    return{'PASS_THROUGH'}          
                    
                if event.type == 'LEFTMOUSE':
                    self.lmb = event.value == 'PRESS'
                
                if event.value == 'RELEASE':
                    context.window.cursor_modal_set("DEFAULT")
                    
            #---Create Lights     
                if (event.ctrl) and event.value == 'PRESS': 
                    context.window.cursor_modal_set("CROSSHAIR")
                    if event.type == 'LEFTMOUSE':
                        self.dist_light = False
                        self.scale_gapy = False
                        self.scale_gapx = False
                        self.scale_light = False
                        self.scale_light_x = False
                        self.scale_light_y = False
                        self.strength_light = False
                        self.rotate_light_z = False
                        self.orbit = False
                        if self.custom:
                            obj_light = context.scene.objects.active
                            obj_light = create_light_custom(self, context, obj_light)
                        else:
                        #---Softbox panel
                            if context.scene.Lumiere.typlight == "Panel":
                                obj_light = create_softbox(self, context)

                        #---Default blender lamp
                        
                        #---Point
                            elif context.scene.Lumiere.typlight == "Point":
                                obj_light = create_light_point(self, context)
                        
                        #---Sun
                            elif context.scene.Lumiere.typlight == "Sun":
                                obj_light = create_light_sun(self, context)
                        
                        #---Spot
                            elif context.scene.Lumiere.typlight == "Spot":
                                obj_light = create_light_spot(self, context)   
                        
                        #---Area
                            elif context.scene.Lumiere.typlight == "Area":
                                obj_light = create_light_area(self, context)
                        
                        #---Sky
                            elif context.scene.Lumiere.typlight == "Sky":
                                obj_light = create_light_sky(self, context)
                                obj_light.Lumiere.energy = 2    
                        
                        #---Environment 
                            elif context.scene.Lumiere.typlight == "Env":
                                obj_light = create_light_env(self, context)
                                obj_light.Lumiere.energy = 1
                                                
                        #---Import 
                            elif context.scene.Lumiere.typlight == "Import":
                                bpy.ops.object.import_light()

                        
                    #---Raycast the light
                        raycast_light(self, obj_light.Lumiere.range, context, coord)
                        self.editmode = True

            #---RayCast the light
                elif self.editmode is True and self.modif is False : 
                    if self.lmb : 
                        raycast_light(self, obj_light.Lumiere.range, context, coord)
                        bpy.context.window.cursor_modal_set("SCROLL_XY")
                        
            else:
                if self.modif:
                    transform_light(self, context, event, obj_light)

                else:
                    return {'PASS_THROUGH'}
            
        #---Transform the light
            if self.editmode :
                obj_light = context.active_object

                str1 ="Range: " + context.scene.Key_Distance + " || " + \
                      "Energy: " + context.scene.Key_Strength + " || "  + \
                      "Reflect Angle: " + context.scene.Key_Normal + " || " + \
                      "Fallof: " + context.scene.Key_Falloff + " || " + \
                      "Orbit: " + context.scene.Key_Orbit + " || "
                str2 =" "
                if obj_light.Lumiere.typlight in ("Panel"):
                    str2 = "Scale: " + context.scene.Key_Scale + "+Mouse Move ||" + \
                           "Scale X: " + context.scene.Key_Scale_X + " || " + \
                           "Scale Y: " + context.scene.Key_Scale_Y + " || "
                elif obj_light.Lumiere.typlight in ("Area"):
                    str2 = "Scale: " + context.scene.Key_Scale + "+Mouse Move ||" + \
                           "Scale X: " + context.scene.Key_Scale_X + " || " + \
                           "Scale Y: " + context.scene.Key_Scale_Y + " || "
                elif obj_light.Lumiere.typlight in ("Spot"):
                    str2 = "Scale Cone: " + context.scene.Key_Scale + " || " + \
                           "Softness: " + context.scene.Key_Scale_X + " || " + \
                           "Blend Cone: " + context.scene.Key_Scale_Y + " || "
                elif obj_light.Lumiere.typlight in ("Sky"):
                    str2 = "Turbidity: " + context.scene.Key_Scale 
                else:
                    str2 = "Softness: " + context.scene.Key_Scale 
                text_header = str1 + str2 + " || Confirm: RMB"
                context.area.header_text_set(text_header)
                
                transform_light(self, context, event, obj_light)
                
                if event.type =='RIGHTMOUSE':
                    if obj_light['pixel_select']: 
                        obj_light['pixel_select'] = False
                    else:
                        if self.orbit:
                            obj_light.constraints['Track To'].influence = 0
                            obj_light.location = self.initial_location
                            remove_constraint(self, context, obj_light.data.name)   
                        # else:
                            # picker = object_picker(self, context, coord)
                            # if picker is not None: 
                                # if "Lumiere" in bpy.data.objects[picker].data.name : 
                                    # return {'PASS_THROUGH'}

                        context.area.header_text_set()
                        context.window.cursor_modal_set("DEFAULT")
                        self.remove_handler()
                        return {'FINISHED'}
                        
                elif event.type in {'ESC'}:
                    context.area.header_text_set()
                    context.window.cursor_modal_set("DEFAULT")
                    self.remove_handler()
                    if self.orbit:
                        obj_light.constraints['Track To'].influence = 0
                        obj_light.location = self.initial_location
                        remove_constraint(self, context, obj_light.data.name)   
                        return {'FINISHED'}
                else:
                    return {'RUNNING_MODAL'}

        #---Undo before creating the light
            if event.type in {'RIGHTMOUSE', 'ESC'}:
                context.area.header_text_set()
                context.window.cursor_modal_set("DEFAULT")
                self.remove_handler()
                return{'FINISHED'}

            return {'PASS_THROUGH'}
        except Exception as error:
            if event.type not in {'RIGHTMOUSE', 'ESC'}:
                print("Error to report : ", error)
                context.window.cursor_modal_set("DEFAULT")
                context.area.header_text_set()
                self.remove_handler()
            return {'FINISHED'}

    def execute (self, context):
        for ob in context.scene.objects:
            if ob.type != 'EMPTY' and ob.data.name.startswith("Lumiere"):
                ob.select = False
        return {'FINISHED'}

    def remove_handler(self):
        if self._handle:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
        self._handle = None
        
    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode == 'OBJECT'
        
    def invoke(self, context, event):

        if context.space_data.type == 'VIEW_3D':
            args = (self, context, event)
            context.area.header_text_set("Add light: CTRL+LMB || Confirm: ESC or RMB")

            obj_light = context.active_object

            self.lumiere_area = context.area

            context.window_manager.modal_handler_add(self)
            self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_callback_px, args, 'WINDOW', 'POST_PIXEL')
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "No active View3d detected !")
            return {'CANCELLED'}
    

#########################################################################################################

#########################################################################################################
def update_sky(self, context):
    """Update the sky node with from the targeted angle"""
    
#---Get the duplivert parent of the sun lamp 
    dupli = context.active_object

#---Get the lamp or the softbox link to the duplivert
    lamp = get_lamp(context, dupli.Lumiere.lightname)
    
#---Credits : https://www.youtube.com/watch?v=YXso7kNzxIU
    xAng = bpy.data.objects[dupli.name].rotation_euler[0]
    yAng = bpy.data.objects[dupli.name].rotation_euler[1]
    zAng = bpy.data.objects[dupli.name].rotation_euler[2]
    
    vec = Vector((0.0,0.0,1.0))
    xMat = Matrix(((1.1,0.0,0.0), (0.0, math.cos(xAng), -math.sin(xAng)), (0.0, math.sin(xAng), math.cos(xAng))))
    yMat = Matrix(((math.cos(yAng), 0.0, math.sin(yAng)), (0.0, 1.0, 0.0), (-math.sin(yAng), 0.0, math.cos(yAng))))
    zMat = Matrix(((math.cos(zAng), -math.sin(zAng), 0.0), (math.sin(zAng), math.cos(zAng), 0.0), (0.0, 0.0, 1.0)))
    
    vec = xMat * vec
    vec = yMat * vec
    vec = zMat * vec

    bpy.data.worlds['Lumiere_world'].node_tree.nodes['Sky Texture'].sun_direction = vec 
    blackbody = lamp.data.node_tree.nodes['Blackbody']
    #4000 -> HORIZON // 5780 -> Daylight
    blackbody.inputs[0].default_value = 4000 + (1780 * vec.z)     

#########################################################################################################

#########################################################################################################
def reset_options(self, context):
    """Reset the options for HDRI or reflection maps"""
    
    for ob in bpy.data.objects:
        if ob.data.name == self.lightname:
            cobj = ob
    
#---Environment Light
    if cobj.Lumiere.typlight == "Env":
        world = context.scene.world
        hdri_bright = world.node_tree.nodes['Bright/Contrast']
        hdri_gamma = world.node_tree.nodes['Gamma']
        hdri_hue = world.node_tree.nodes['Hue Saturation Value']
        img_bright = world.node_tree.nodes['Bright/Contrast.001']
        img_gamma = world.node_tree.nodes['Gamma.001']
        img_hue = world.node_tree.nodes['Hue Saturation Value.001']             
    
    elif cobj.Lumiere.typlight in ("Panel"):
        mat_name, mat = get_mat_name("SOFTBOX_" + cobj.data.name)
        img_bright = mat.node_tree.nodes['Bright/Contrast']
        img_gamma = mat.node_tree.nodes['Gamma']
        img_hue = mat.node_tree.nodes['Hue Saturation Value']
        repeat_u = mat.node_tree.nodes['Math']
        repeat_v = mat.node_tree.nodes['Math.002']      
    
    if cobj.Lumiere.hdri_reset:
        cobj.Lumiere.hdri_bright = hdri_bright.inputs['Bright'].default_value = 0
        cobj.Lumiere.hdri_contrast = hdri_bright.inputs['Contrast'].default_value = 0
        cobj.Lumiere.hdri_gamma = hdri_gamma.inputs['Gamma'].default_value = 1
        cobj.Lumiere.hdri_hue = hdri_hue.inputs['Hue'].default_value = 0.5
        cobj.Lumiere.hdri_saturation = hdri_hue.inputs['Saturation'].default_value = 1
        cobj.Lumiere.hdri_value = hdri_hue.inputs['Value'].default_value = 1
        
    if cobj.Lumiere.img_reset:
        cobj.Lumiere.img_bright = img_bright.inputs['Bright'].default_value = 0
        cobj.Lumiere.img_contrast = img_bright.inputs['Contrast'].default_value = 0
        cobj.Lumiere.img_gamma = img_gamma.inputs['Gamma'].default_value = 1
        cobj.Lumiere.img_hue = img_hue.inputs['Hue'].default_value = 0.5
        cobj.Lumiere.img_saturation = img_hue.inputs['Saturation'].default_value = 1
        cobj.Lumiere.img_value = img_hue.inputs['Value'].default_value = 1
        if cobj.Lumiere.typlight == "Panel":
            repeat_u.inputs[1].default_value = 1
            repeat_v.inputs[1].default_value = 1

    if cobj.Lumiere.projector_img_reset:
        projector = bpy.data.objects["PROJECTOR_" + cobj.data.name]
        mat_name, mat = get_mat_name(projector.data.name)
        img_text = mat.node_tree.nodes['Image Texture']
        saturation = mat.node_tree.nodes['Mix']
        contrast = mat.node_tree.nodes['Bright/Contrast']
        gamma = mat.node_tree.nodes['Gamma']
        invert = mat.node_tree.nodes['Invert']
        repeat_u = mat.node_tree.nodes["Repeat_Texture"].inputs[1]
        repeat_v = mat.node_tree.nodes["Repeat_Texture"].inputs[2]

        
        cobj.Lumiere.projector_img_saturation = saturation.inputs['Fac'].default_value = 0
        cobj.Lumiere.projector_img_gamma = gamma.inputs['Gamma'].default_value = 1
        cobj.Lumiere.projector_img_bright = contrast.inputs['Bright'].default_value = 0
        cobj.Lumiere.projector_img_contrast = contrast.inputs['Contrast'].default_value = 0
        cobj.Lumiere.projector_img_invert = invert.inputs['Fac'].default_value = 0
        repeat_u.default_value = 1
        repeat_v.default_value = 1
#########################################################################################################

#########################################################################################################
def update_rotation_hdri(self, context):
    """Update the rotation of the environment image texture"""
    
    cobj = get_object(context, self.lightname)
    world = context.scene.world
    mapping = world.node_tree.nodes['Mapping']
    mapping2 = world.node_tree.nodes['Mapping.001']
    
    # hit_world = Vector(cobj['hit']) + (cobj.Lumiere.range * Vector(cobj['dir']))
    # cobj.location = Vector((hit_world[0], hit_world[1], hit_world[2]))    
    
    if cobj.Lumiere.rotation_lock_hdri:
        mapping2.rotation[2] += -(mapping.rotation[2] - -math.radians(cobj.Lumiere.hdri_rotation))

    mapping.rotation[2] = -math.radians(cobj.Lumiere.hdri_rotation)
    
#########################################################################################################

#########################################################################################################
def update_rotation_hdri_lock(self, context):
    """Lock / Unlock the rotatin of the environment image texture"""
    
    cobj = get_object(context, self.lightname)
    world = context.scene.world
    mapping = world.node_tree.nodes['Mapping']
    mapping2 = world.node_tree.nodes['Mapping.001']
    
    if cobj.Lumiere.rotation_lock_hdri == False:
        if round(-math.degrees(mapping2.rotation[2]), 2) != round(cobj.Lumiere.img_rotation, 2) :
            cobj.Lumiere.img_rotation = -math.degrees(mapping2.rotation[2])

#########################################################################################################

#########################################################################################################
def update_rotation_img(self, context):
    """Update the rotation of the background image texture"""
    
    cobj = get_object(context, self.lightname)
    world = context.scene.world
    mapping = world.node_tree.nodes['Mapping']
    mapping2 = world.node_tree.nodes['Mapping.001']
    if cobj.Lumiere.rotation_lock_img:
        mapping.rotation[2] += -(mapping2.rotation[2] - -math.radians(cobj.Lumiere.img_rotation))
    mapping2.rotation[2] = -math.radians(cobj.Lumiere.img_rotation)
    
#########################################################################################################

#########################################################################################################
def update_rotation_img_lock(self, context):
    """Lock / Unlock the rotatin of the background image texture"""
    
    cobj = get_object(context, self.lightname)
    world = context.scene.world
    mapping = world.node_tree.nodes['Mapping']
    mapping2 = world.node_tree.nodes['Mapping.001']
    
    if cobj.Lumiere.rotation_lock_img == False:
        if round(-math.degrees(mapping.rotation[2]), 2) != round(cobj.Lumiere.hdri_rotation, 2) :
            cobj.Lumiere.hdri_rotation = -math.degrees(mapping.rotation[2])

#########################################################################################################

#########################################################################################################
def update_lamp(self, context, cobj):
    """Update the material nodes of the blender lights"""
    
    mat = bpy.data.lamps["LAMP_" + self.lightname]
        
    falloff = mat.node_tree.nodes["Light Falloff"]
    emit = mat.node_tree.nodes["Emission"]
    emit.inputs[0].default_value = cobj.Lumiere.lightcolor
    mat.node_tree.nodes["Light Falloff"].inputs[0].default_value = cobj.Lumiere.energy
    mat.node_tree.links.new(falloff.outputs[int(cobj.Lumiere.typfalloff)], emit.inputs[1])

    if cobj.Lumiere.texture_type == "Gradient":
        colramp = mat.node_tree.nodes['ColorRamp']
        colramp.color_ramp.interpolation = cobj.Lumiere.gradinterpo
        mat.node_tree.links.new(colramp.outputs[0], emit.inputs['Color'])
    else:
        if mat.node_tree.nodes['ColorRamp'].outputs['Color'].links:
            mat.node_tree.links.remove(mat.node_tree.nodes['ColorRamp'].outputs['Color'].links[0])
    
    if cobj.Lumiere.typlight in ("Sun", "Sky"):
        # falloff = mat.node_tree.nodes["Light Falloff"]
        emit = mat.node_tree.nodes["Emission"]
        if emit.inputs[1].links:
            mat.node_tree.links.remove(emit.inputs[1].links[0])
                        
                        
        # if falloff.outputs['Color'].links:
            # mat.node_tree.links.remove(falloff.outputs['Color'].links[0])
        # mat.node_tree.links.new(falloff.outputs[0], emit.inputs[1])
#########################################################################################################

#########################################################################################################
def update_mat(self, context):
    """Update the material nodes of the lights"""
    
#---Get the duplivert
    cobj = get_object(context, self.lightname)

    if cobj.type != 'EMPTY' and cobj.data.name.startswith("Lumiere"):

        if cobj.Lumiere.typlight == "Env":
            if cobj.Lumiere.hdri_reset == False and cobj.Lumiere.img_reset == False:
            #---Environment Light
                world = context.scene.world
                env_output = world.node_tree.nodes['World Output']
                env_mix = world.node_tree.nodes['Mix Shader']
                hdr_text = world.node_tree.nodes['Environment Texture']
                hdri_bright = world.node_tree.nodes['Bright/Contrast']
                hdri_gamma = world.node_tree.nodes['Gamma']
                hdri_hue = world.node_tree.nodes['Hue Saturation Value']
                img_text = world.node_tree.nodes['Environment Texture.001']
                img_bright = world.node_tree.nodes['Bright/Contrast.001']
                img_gamma = world.node_tree.nodes['Gamma.001']
                img_hue = world.node_tree.nodes['Hue Saturation Value.001']             
                background1 = world.node_tree.nodes['Background']
                background2 = world.node_tree.nodes['Background.001']
                lightpath = world.node_tree.nodes['Light Path']
                math_path = world.node_tree.nodes['Math']
                mix = world.node_tree.nodes['Mix Shader']
                mapping = world.node_tree.nodes['Mapping']
                mapping2 = world.node_tree.nodes['Mapping.001']
                    
                if cobj.Lumiere.hdri_name != "":    
                    hdr_text.image = bpy.data.images[cobj.Lumiere.hdri_name]
                    world.node_tree.links.new(hdr_text.outputs[0], hdri_bright.inputs[0])
                    world.node_tree.links.new(hdri_hue.outputs[0], background1.inputs[0])
                    world.node_tree.links.new(lightpath.outputs[0], math_path.inputs[0])
                    world.node_tree.links.new(lightpath.outputs[3], math_path.inputs[1])
                    world.node_tree.links.new(math_path.outputs[0], mix.inputs[0])
                    hdri_bright.inputs['Bright'].default_value = cobj.Lumiere.hdri_bright
                    hdri_bright.inputs['Contrast'].default_value = cobj.Lumiere.hdri_contrast
                    hdri_gamma.inputs['Gamma'].default_value = cobj.Lumiere.hdri_gamma
                    hdri_hue.inputs['Hue'].default_value = cobj.Lumiere.hdri_hue
                    hdri_hue.inputs['Saturation'].default_value = cobj.Lumiere.hdri_saturation
                    hdri_hue.inputs['Value'].default_value = cobj.Lumiere.hdri_value
                else:
                #--- Remove image HDRI links
                    cobj.Lumiere.rotation_lock_img = False
                    for i in range(len(hdri_hue.outputs['Color'].links)):
                        world.node_tree.links.remove(hdri_hue.outputs['Color'].links[i-1])
            
            #---HDRI for background         
                if cobj.Lumiere.hdri_background:
                    world.node_tree.links.new(background1.outputs[0], env_output.inputs[0])

                else:
                    world.node_tree.links.new(env_mix.outputs[0], env_output.inputs[0])

            #---Image Background 
                if cobj.Lumiere.img_name != "" and not cobj.Lumiere.hdri_background: 
                    img_text.image = bpy.data.images[cobj.Lumiere.img_name]
                    world.node_tree.links.new(img_text.outputs[0], background2.inputs[0])
                    world.node_tree.links.new(lightpath.outputs[0], math_path.inputs[0])
                    world.node_tree.links.new(lightpath.outputs[3], math_path.inputs[1])
                    if cobj.Lumiere.back_reflect:
                        math_path.operation = 'ADD'
                    else:
                        math_path.operation = 'SUBTRACT'
                    world.node_tree.links.new(math_path.outputs[0], mix.inputs[0])
                    world.node_tree.links.new(img_text.outputs[0], img_bright.inputs[0])
                    world.node_tree.links.new(img_hue.outputs[0], background2.inputs[0])
                    img_bright.inputs['Bright'].default_value = cobj.Lumiere.img_bright
                    img_bright.inputs['Contrast'].default_value = cobj.Lumiere.img_contrast
                    img_gamma.inputs['Gamma'].default_value = cobj.Lumiere.img_gamma
                    img_hue.inputs['Hue'].default_value = cobj.Lumiere.img_hue
                    img_hue.inputs['Saturation'].default_value = cobj.Lumiere.img_saturation
                    img_hue.inputs['Value'].default_value = cobj.Lumiere.img_value                  
                else:
                #--- Remove image background links
                    cobj.Lumiere.rotation_lock_hdri = False
                    for i in range(len(img_hue.outputs['Color'].links)):
                        world.node_tree.links.remove(img_hue.outputs['Color'].links[i-1])                       
                
                #---Color background for reflection
                    if cobj.Lumiere.back_reflect:
                        math_path.operation = 'ADD'
                    else:
                        math_path.operation = 'SUBTRACT'

            else:
                if cobj.Lumiere.hdri_reset: 
                    cobj.Lumiere.hdri_reset = False
                if cobj.Lumiere.img_reset: 
                    cobj.Lumiere.img_reset = False                      
        
        elif cobj.Lumiere.typlight == "Panel":
        #---Panel Light 
            mat_name, mat = get_mat_name("SOFTBOX_" + cobj.data.name)
            emit = mat.node_tree.nodes["Emission"]
            emit.inputs[0].default_value = cobj.Lumiere.lightcolor
            mat.diffuse_color = (cobj.Lumiere.lightcolor[0], cobj.Lumiere.lightcolor[1], cobj.Lumiere.lightcolor[2])
            mat.alpha = 0.5
            diffuse = mat.node_tree.nodes["Diffuse BSDF"]
            diffuse.inputs[0].default_value = cobj.Lumiere.lightcolor
            img_text = mat.node_tree.nodes['Image Texture']
            img_bright = mat.node_tree.nodes['Bright/Contrast']
            img_gamma = mat.node_tree.nodes['Gamma']
            img_hue = mat.node_tree.nodes['Hue Saturation Value']                   
            invert = mat.node_tree.nodes['Invert']
            invert.inputs[0].default_value = 1
            mat.node_tree.nodes["Random_Color"].inputs[1].default_value = cobj.Lumiere.random_color 
            random_energy = mat.node_tree.nodes["Random_Energy"]
            random_energy.inputs[0].default_value = cobj.Lumiere.energy
            mix_color_texture = mat.node_tree.nodes["Mix_Color_Texture"]
            falloff = mat.node_tree.nodes["Light Falloff"]
            falloff.inputs[0].default_value = cobj.Lumiere.energy
            mat.node_tree.links.new(falloff.outputs[int(cobj.Lumiere.typfalloff)],  emit.inputs[1])
            mix1 = mat.node_tree.nodes["Mix Shader"]
            colramp = mat.node_tree.nodes['ColorRamp']
            coord = mat.node_tree.nodes['Texture Coordinate']
            mapping = mat.node_tree.nodes['Mapping']

            if cobj.Lumiere.rotate_ninety:
                mapping.rotation[2] = math.radians(90)
            else:
                mapping.rotation[2] = 0
                
        #---Image Texture options
            if cobj.Lumiere.img_name != "" and cobj.Lumiere.texture_type =="Texture" :
                combine = mat.node_tree.nodes["Combine RGB"]
                sepRGB =  mat.node_tree.nodes['Separate RGB']
                mat.node_tree.links.new(coord.outputs[0], mapping.inputs[0])
                mat.node_tree.links.new(mapping.outputs[0],  sepRGB.inputs[0])                  
                mat.node_tree.links.new(combine.outputs[0], img_text.inputs['Vector'])
                img_text.image = bpy.data.images[cobj.Lumiere.img_name]
                img_bright.inputs['Bright'].default_value = cobj.Lumiere.img_bright
                img_bright.inputs['Contrast'].default_value = cobj.Lumiere.img_contrast
                img_gamma.inputs['Gamma'].default_value = cobj.Lumiere.img_gamma    
                img_hue.inputs['Hue'].default_value = cobj.Lumiere.img_hue
                img_hue.inputs['Saturation'].default_value = cobj.Lumiere.img_saturation
                img_hue.inputs['Value'].default_value = cobj.Lumiere.img_value          
                mat.node_tree.links.new(img_hue.outputs[0], emit.inputs[0])
                mat.node_tree.links.new(img_hue.outputs[0], invert.inputs[1])
                invert.inputs[0].default_value = 0  
                
                if invert.inputs['Fac'].links:
                    mat.node_tree.links.remove(invert.inputs['Fac'].links[0])
                    
                if cobj.Lumiere.img_reset: 
                    cobj.Lumiere.img_reset = False  
                    
            #---Random
                if cobj.Lumiere.random_energy:
                    mat.node_tree.links.new(mat.node_tree.nodes["Mix_Color_Texture"].outputs[0], emit.inputs[0])
                    mat.node_tree.links.new(img_hue.outputs[0], mat.node_tree.nodes["Mix_Color_Texture"].inputs[1])
                    mat.node_tree.links.new(colramp.outputs[0], mat.node_tree.nodes["Mix_Color_Texture"].inputs[2])
                    mat.node_tree.links.new(random_energy.outputs[0], falloff.inputs[0])
                    mat.node_tree.links.new(colramp.outputs[0], random_energy.inputs[1])
                    mat.node_tree.links.new(mat.node_tree.nodes["Random_Color"].outputs[0], colramp.inputs[0])
                    
                else:
                    mat.node_tree.links.new(img_hue.outputs[0], emit.inputs[0])
                    if mat.node_tree.nodes['Random_Energy'].outputs['Value'].links:
                        mat.node_tree.links.remove(random_energy.outputs['Value'].links[0])
                        
            else:
                if invert.inputs['Color'].links:
                    mat.node_tree.links.remove(invert.inputs['Color'].links[0])                     
                if img_hue.outputs['Color'].links:
                    mat.node_tree.links.remove(img_hue.outputs['Color'].links[0])
                    
            if cobj.Lumiere.reflector:
            #---Link Diffuse 
                mat.node_tree.links.new(diffuse.outputs[0], mix1.inputs[2])
                
            #---Transparent Node to black
                mat.node_tree.nodes["Transparent BSDF"].inputs[0].default_value = (0,0,0,1)     

            #---Remove links
                if img_hue.outputs['Color'].links:
                    mat.node_tree.links.remove(img_hue.outputs['Color'].links[0])
                    mat.node_tree.links.remove(invert.inputs['Color'].links[0])
                    
                if invert.inputs['Fac'].links:
                    mat.node_tree.links.remove(invert.inputs['Fac'].links[0])
            else:
            #---Link Emit 
                mat.node_tree.links.new(emit.outputs[0], mix1.inputs[2])

            #---Transparent Node to white
                mat.node_tree.nodes["Transparent BSDF"].inputs[0].default_value = (1,1,1,1)
                
        #---Gradients
            if cobj.Lumiere.texture_type == "Gradient" and not cobj.Lumiere.reflector:              
                sepRGB =  mat.node_tree.nodes['Separate RGB']
                grad = mat.node_tree.nodes['Gradient Texture']
                mat.node_tree.links.new(mapping.outputs[0],  grad.inputs[0])
                mat.node_tree.links.new(grad.outputs[0],  sepRGB.inputs[0])                 
                linear_grad = mat.node_tree.nodes['Gradient Texture.001']
                geom = mat.node_tree.nodes['Geometry']
                combRGB = mat.node_tree.nodes['Combine RGB'] 

                mat.node_tree.links.new(colramp.outputs[0], emit.inputs['Color'])
                mat.node_tree.links.new(colramp.outputs[1], invert.inputs['Fac'])
                
                if cobj.Lumiere.typgradient != "NONE" :
                    mat.node_tree.nodes['Gradient Texture'].gradient_type = cobj.Lumiere.typgradient
                    mat.node_tree.links.new(combRGB.outputs[0], linear_grad.inputs['Vector'])
                    mat.node_tree.links.new(linear_grad.outputs[0], colramp.inputs[0])
                
                #---Gradients links
                    if img_hue.outputs['Color'].links:
                        mat.node_tree.links.remove(img_hue.outputs['Color'].links[0])                       
                    if cobj.Lumiere.typgradient in ("LINEAR", "DIAGONAL") : #LINEAR - DIAGONAL
                        mat.node_tree.links.new(coord.outputs[0], mapping.inputs[0])
                    elif cobj.Lumiere.typgradient in ("QUADRATIC", "EASING") : #QUAD - EASING
                        mat.node_tree.links.new(geom.outputs[5], mapping.inputs[0])
                    elif cobj.Lumiere.typgradient in ("SPHERICAL", "QUADRATIC_SPHERE", "RADIAL") : #SPHERICAL - QUADRATIC_SPHERE - RADIAL
                        mat.node_tree.links.new(coord.outputs[3], mapping.inputs[0])    
            #---Only colors
                else:
                    mat.node_tree.links.new(mat.node_tree.nodes["Random_Color"].outputs[0], colramp.inputs[0])  

            #---Random
                if cobj.Lumiere.random_energy:
                    mat.node_tree.links.new(random_energy.outputs[0], falloff.inputs[0])
                    mat.node_tree.links.new(colramp.outputs[0], random_energy.inputs[1])
                    if cobj.Lumiere.typgradient != "NONE":
                        mat.node_tree.links.new(mat.node_tree.nodes["Mix_Random_Color"].outputs[0], colramp.inputs[0])
                else:
                    if mat.node_tree.nodes['Random_Energy'].outputs['Value'].links:
                        mat.node_tree.links.remove(random_energy.outputs['Value'].links[0])
            else:
                if invert.inputs['Fac'].links:
                    mat.node_tree.links.remove(invert.inputs['Fac'].links[0])
                    
        #---Color
            if cobj.Lumiere.texture_type == "Color" and not cobj.Lumiere.reflector:

            #---Random
                if cobj.Lumiere.random_energy:
                    mat.node_tree.nodes["Mix_Color_Texture"].inputs[1].default_value = cobj.Lumiere.lightcolor
                    mat.node_tree.links.new(mat.node_tree.nodes["Mix_Color_Texture"].outputs[0], emit.inputs[0])
                    mat.node_tree.links.new(colramp.outputs[0], mat.node_tree.nodes["Mix_Color_Texture"].inputs[2])
                    
                    mat.node_tree.links.new(random_energy.outputs[0], falloff.inputs[0])
                    mat.node_tree.links.new(colramp.outputs[0], random_energy.inputs[1])
                    mat.node_tree.links.new(mat.node_tree.nodes["Random_Color"].outputs[0], colramp.inputs[0])
                    
                else:
                    if mat.node_tree.nodes['Random_Energy'].outputs['Value'].links:
                        mat.node_tree.links.remove(random_energy.outputs['Value'].links[0])
                    if emit.inputs[0].links:
                        mat.node_tree.links.remove(emit.inputs[0].links[0])

    #---Blender Lamps
        else:

        #---Get the lamp or the softbox link to the duplivert
            lamp = get_lamp(context, cobj.Lumiere.lightname)
            
        #---Get the material nodes of the lamp
            mat = lamp.data
            
            if cobj.Lumiere.typlight in ("Sky"):
                emit = mat.node_tree.nodes["Emission"]
                emit.inputs[0].default_value = cobj.Lumiere.lightcolor
                emit.inputs[1].default_value = cobj.Lumiere.energy   
            else:     
                update_lamp(self, context, cobj)

#########################################################################################################

#########################################################################################################
def get_object(context, lightname):
    """Return the object with this name"""

    for ob in context.scene.objects:
        if ob.type != 'EMPTY' and ob.Lumiere.lightname == lightname:
            cobj = ob

    return(cobj)

#########################################################################################################

#########################################################################################################
def add_driver(source, target, prop, dataPath,index = -1, negative = False, func = ''):
    """ Add driver to source prop (at index), driven by target dataPath """

    if index != -1:
        d = source.driver_add(prop, index).driver
    else:
        d = source.driver_add(prop).driver

    v = d.variables.new()
    v.name                 = prop
    v.targets[0].id        = target
    v.targets[0].data_path = dataPath

    d.expression = func + "(" + v.name + ")" if func else v.name
    d.expression = d.expression if not negative else "-1 * " + d.expression 
#########################################################################################################

#########################################################################################################
def get_lamp(context, lightname):
    """Return the lamp with this name"""
    
    cobj = get_object(context, lightname)
    if cobj.Lumiere.typlight == "Panel":
        for ob in context.scene.objects:
            if ob.type != 'EMPTY' and ob.data.name == "SOFTBOX_" + cobj.data.name:
                cobj = ob           
    elif cobj.Lumiere.typlight != "Env":
        for ob in context.scene.objects:
            if ob.type != 'EMPTY' and ob.data.name == "LAMP_" + cobj.data.name:
                cobj = ob 
    elif cobj.Lumiere.typlight == "Env":    
        for ob in context.scene.objects:
            if ob.type != 'EMPTY' and ob.data.name == "WORLD_" + cobj.data.name :
                cobj = ob
    return(cobj)
#########################################################################################################

#########################################################################################################
def get_delete_lamp(context, lightname):
    """Change to option : return the lamp with this name"""
    
    cobj = get_object(context, lightname)

    if cobj.Lumiere.typlight == "Panel":
        for ob in bpy.data.objects:
            if ob.type != 'EMPTY' and ob.data.name == "SOFTBOX_" + cobj.data.name:
                cobj = ob           
    elif cobj.Lumiere.typlight != "Env":
        for ob in bpy.data.objects:
            if ob.type != 'EMPTY' and ob.data.name == "LAMP_" + cobj.data.name:
                cobj = ob 
    elif cobj.Lumiere.typlight == "Env":    
        for ob in bpy.data.objects:
            if ob.type != 'EMPTY' and ob.data.name == "WORLD_" + cobj.data.name:
                cobj = ob

    return(cobj)
#########################################################################################################

#########################################################################################################
def show_hide_light(self, context):
    """Show / Hide this light"""
    obj_light = get_object(context, self.lightname)
    
#---Environment background
    if obj_light.Lumiere.typlight in ("Env", "Sky"):
        if not obj_light.Lumiere.show:
            bpy.data.worlds['Lumiere_world'].use_nodes = False
        else:
            bpy.data.worlds['Lumiere_world'].use_nodes = True

#---Mesh light or blender lamps
    if not obj_light.hide:
        obj_light.hide = True
        obj_light.hide_render = True
        lamp_or_softbox = get_lamp(context, obj_light.Lumiere.lightname)
        bpy.data.objects[lamp_or_softbox.name].hide = True
        bpy.data.objects[lamp_or_softbox.name].hide_render = False      
        if obj_light.Lumiere.projector:
            bpy.data.objects["PROJECTOR_" + obj_light.data.name].hide = True
            bpy.data.objects["PROJECTOR_" + obj_light.data.name].hide_render = True     
            if obj_light.Lumiere.projector_close:
                bpy.data.objects["BASE_PROJECTOR_" + obj_light.data.name].hide = True
                bpy.data.objects["BASE_PROJECTOR_" + obj_light.data.name].hide_render = True        
                
    else:
        obj_light.hide = False
        obj_light.hide_render = False
        lamp_or_softbox = get_lamp(context, obj_light.Lumiere.lightname)
        bpy.data.objects[lamp_or_softbox.name].hide = False
        bpy.data.objects[lamp_or_softbox.name].hide_render = False
        if obj_light.Lumiere.projector:
            bpy.data.objects["PROJECTOR_" + obj_light.data.name].hide = False
            bpy.data.objects["PROJECTOR_" + obj_light.data.name].hide_render = False
            if obj_light.Lumiere.projector_close:
                bpy.data.objects["BASE_PROJECTOR_" + obj_light.data.name].hide = False
                bpy.data.objects["BASE_PROJECTOR_" + obj_light.data.name].hide_render = False       
#########################################################################################################

#########################################################################################################
def select_only(self, context):
    """Show only this light and hide all the other"""
    cobj = get_object(context, self.lightname)

#---Active only the visible light
    context.scene.objects.active = bpy.data.objects[cobj.name] 

#---Deselect and hide all the lights in the scene and show the active light
    for ob in bpy.context.scene.objects:
            ob.select = False
            if ob.type != 'EMPTY' and ob.data.name.startswith("Lumiere") and (ob.name != cobj.name) and cobj.Lumiere.show:
                if cobj.Lumiere.select_only:
                    if ob.Lumiere.show: ob.Lumiere.show = False
                else:
                    if not ob.Lumiere.show: ob.Lumiere.show = True

#---Select only the visible light
    cobj.select = True
#########################################################################################################

#########################################################################################################
def update_projector_taper(self, context):
    """Update the projector thickness"""
    obj_light = get_object(context, self.lightname)
        
    if obj_light.Lumiere.projector:
        projector = bpy.data.objects["PROJECTOR_" + obj_light.data.name]
        projector.scale.x = obj_light.Lumiere.projector_taper * obj_light.Lumiere.projector_scale_x 
        projector.scale.y = obj_light.Lumiere.projector_taper * obj_light.Lumiere.projector_scale_y

#########################################################################################################

#########################################################################################################
def update_projector_scale_min_x(self, context):
    """Update the minimum X scale of the projector"""
    obj_light = get_object(context, self.lightname)
    lamp_or_softbox = get_lamp(context, obj_light.Lumiere.lightname)
    
    if obj_light.Lumiere.typlight == "Panel":
        min_scale_x = lamp_or_softbox.dimensions.x / 2
        
    elif obj_light.Lumiere.typlight == "Area":
        lamp = bpy.data.lamps[lamp_or_softbox.data.name]
        min_scale_x = lamp.size/2
    else:
        min_scale_x = 0.00001
        
    bpy.types.Object.Lumiere[1]['type'].projector_scale_x = FloatProperty(
                                 name="Scale X",
                                 description="Scale the projector on X",
                                 min=min_scale_x, max=1000.0,
                                 soft_min=0.0, soft_max=1000.0,
                                 default=1,
                                 precision=2,
                                 step=1,    
                                 subtype='DISTANCE',
                                 unit='LENGTH', update=update_projector_scale)

    if obj_light.Lumiere.projector_scale_x < min_scale_x:
        obj_light.Lumiere.projector_scale_x = min_scale_x   
#########################################################################################################

#########################################################################################################
def update_projector_scale_min_y(self, context):
    """Update the minimum Y scale of the projector"""
    obj_light = get_object(context, self.lightname)
    lamp_or_softbox = get_lamp(context, obj_light.Lumiere.lightname)
    
    if obj_light.Lumiere.typlight == "Panel":
        min_scale_y = lamp_or_softbox.dimensions.y / 2
        
    elif obj_light.Lumiere.typlight == "Area":
        lamp = bpy.data.lamps[lamp_or_softbox.data.name]
        min_scale_y = lamp.size_y/2
    else:
        min_scale_y = 0.00001   

    bpy.types.Object.Lumiere[1]['type'].projector_scale_y = FloatProperty(
                                 name="Scale Y",
                                 description="Scale the projector on Y",
                                 min=min_scale_y, max=1000.0,
                                 soft_min=0.0, soft_max=1000.0,
                                 default=1,
                                 precision=2,
                                 step=1,    
                                 subtype='DISTANCE',
                                 unit='LENGTH', update=update_projector_scale)
                                 
    if obj_light.Lumiere.projector_scale_y < min_scale_y:
        obj_light.Lumiere.projector_scale_y = min_scale_y   
#########################################################################################################

#########################################################################################################
def update_projector_scale(self, context):
    """Update the scale of the projector"""

    obj_light = get_object(context, self.lightname)

    if obj_light.Lumiere.projector:
        projector = bpy.data.objects["PROJECTOR_" + obj_light.data.name]
        projector.scale.x = obj_light.Lumiere.projector_taper * obj_light.Lumiere.projector_scale_x
        projector.scale.y = obj_light.Lumiere.projector_taper * obj_light.Lumiere.projector_scale_y 

        if obj_light.Lumiere.projector_close:
            base_projector = bpy.data.objects["BASE_PROJECTOR_" + obj_light.data.name]
            base_projector.scale.x = obj_light.Lumiere.projector_scale_x 
            base_projector.scale.y = obj_light.Lumiere.projector_scale_y 
            
#########################################################################################################

#########################################################################################################
def update_type_light(self, context):
    """Change the selected light to a new one"""

    obj_light = get_object(context, self.lightname)

    if obj_light.Lumiere.typlight != obj_light.Lumiere.newtyplight:
            
    #---Get the lamp or the softbox link to the duplivert
        lamp_or_softbox = get_lamp(context, obj_light.Lumiere.lightname)    
        oldtyplight = obj_light.Lumiere.typlight
        oldtype = lamp_or_softbox.type
        if lamp_or_softbox.data.name.startswith("LAMP"):
            oldlight = "lamp"
        else:
            oldlight = "mesh"
                    
    #---Softbox panel
        if obj_light.Lumiere.newtyplight == "Panel":
            obj_light.Lumiere.typlight = obj_light.Lumiere.newtyplight
            context.scene.objects.unlink(lamp_or_softbox)
            obj_light = create_softbox(self, context, newlight = True)

    #---Default blender lamp
    
    
    #---Point
        elif obj_light.Lumiere.newtyplight == "Point":
            if oldtyplight != "Env":
                obj_light.Lumiere.typlight = obj_light.Lumiere.newtyplight

            if lamp_or_softbox.type == "MESH":
                context.scene.objects.unlink(lamp_or_softbox)
                lamp = get_delete_lamp(context,obj_light.Lumiere.lightname)
                lamp.parent = None
                if lamp.data.name in bpy.data.lamps:
                    context.scene.objects.link(lamp)
                    lamp.data.type = 'POINT'
                else:
                    obj_light = create_light_point(self, context, newlight = True)
                    lamp = get_lamp(context, obj_light.Lumiere.lightname)
                    create_lamp_nodes(self, context, lamp)
                
                lamp_or_softbox.user_remap(lamp)
                lamp.parent = obj_light
                
            else:
                lamp_or_softbox.data.type = "POINT"
            
            
    #---Sun
        elif obj_light.Lumiere.newtyplight == "Sun":
            if oldtyplight != "Env":
                obj_light.Lumiere.typlight = obj_light.Lumiere.newtyplight

            if lamp_or_softbox.type == "MESH":
                context.scene.objects.unlink(lamp_or_softbox)
                lamp = get_delete_lamp(context, obj_light.Lumiere.lightname)
                lamp.parent = None
                if lamp.data.name in bpy.data.lamps:
                    context.scene.objects.link(lamp)
                    lamp.data.type = 'SUN'
                else:
                    obj_light = create_light_sun(self, context, newlight = True)
                    lamp = get_lamp(context, obj_light.Lumiere.lightname)
                    create_lamp_nodes(self, context, lamp)

                lamp_or_softbox.user_remap(lamp)
                lamp.parent = obj_light
                    
            else:
                lamp_or_softbox.data.type = "SUN"
                

                
    #---Spot
        elif obj_light.Lumiere.newtyplight == "Spot":
            if oldtyplight != "Env":
                obj_light.Lumiere.typlight = obj_light.Lumiere.newtyplight

            if lamp_or_softbox.type == "MESH":
                context.scene.objects.unlink(lamp_or_softbox)
                lamp = get_delete_lamp(context, obj_light.Lumiere.lightname)
                lamp.parent = None
                if lamp.data.name in bpy.data.lamps:
                    context.scene.objects.link(lamp)
                    lamp.data.type = 'SPOT'
                else:
                    obj_light = create_light_spot(self, context, newlight = True)
                    lamp = get_lamp(context, obj_light.Lumiere.lightname)
                    create_lamp_nodes(self, context, lamp)
                
                lamp_or_softbox.user_remap(lamp)
                lamp.parent = obj_light
                
            else:
                lamp_or_softbox.data.type = "SPOT"
                

    #---Area
        elif obj_light.Lumiere.newtyplight == "Area":
            if oldtyplight != "Env":
                obj_light.Lumiere.typlight = obj_light.Lumiere.newtyplight

            if lamp_or_softbox.type == "MESH":
                context.scene.objects.unlink(lamp_or_softbox)
                lamp = get_delete_lamp(context, obj_light.Lumiere.lightname)
                lamp.parent = None
                if lamp.data.name in bpy.data.lamps:
                    context.scene.objects.link(lamp)
                    lamp.data.type = 'AREA'
                    lamp.data.shape = 'RECTANGLE'
                else:
                    obj_light = create_light_area(self, context, newlight = True)
                    lamp = get_lamp(context, obj_light.Lumiere.lightname)
                    create_lamp_nodes(self, context, lamp)
                
                lamp_or_softbox.user_remap(lamp)
                lamp.parent = obj_light
                
            else:
                lamp_or_softbox.data.type = "AREA"
                lamp_or_softbox.data.shape = 'RECTANGLE'


    #---Environment Background
        if oldtyplight == "Env":
            obj_light.Lumiere.typlight = oldtyplight

            if oldtype != "MESH":
                context.scene.objects.unlink(lamp_or_softbox)
                lamp = get_delete_lamp(context, obj_light.Lumiere.lightname)    
                lamp.parent = None
            #---Create widget
                create_light_env_widget(self, context, obj_light)
                lamp = get_lamp(context, obj_light.Lumiere.lightname)
                lamp.parent = obj_light

        update_mat(self, context)
    
#########################################################################################################

#########################################################################################################
def update_projector(self, context):
    """Update the projector of the active light"""

    obj_light = get_object(context, self.lightname)

    if obj_light.Lumiere.projector:
        projector = bpy.data.objects["PROJECTOR_" + obj_light.data.name]
        projector.location.z = - obj_light.Lumiere.projector_range
                        
def update_projector_smooth(self, context):
    """Update the roundness of the projector"""

    obj_light = get_object(context, self.lightname)

    if obj_light.Lumiere.typlight != "Env" and obj_light.Lumiere.projector:
        projector = bpy.data.objects["PROJECTOR_" + obj_light.data.name]
        projector.modifiers["Bevel"].width = obj_light.Lumiere.projector_smooth
            

def update_close_projector(self, context):
    """Close or open the projector"""
    obj_light = get_object(context, self.lightname)         
    
    if obj_light.Lumiere.projector_close: 
        projector = bpy.data.objects["PROJECTOR_" + obj_light.data.name]
        create_base_projector(self, context, obj_light.data.name)
        update_projector_scale(self, context)
        context.scene.objects.active = bpy.data.objects[obj_light.name]
        
        if obj_light.Lumiere.typlight == "Panel":
            mat_name, mat = get_mat_name("SOFTBOX_" + obj_light.data.name)
            emit = mat.node_tree.nodes["Emission"]
            output = mat.node_tree.nodes["Material Output"]
            mat.node_tree.links.new(emit.outputs[0], output.inputs[0])
    else:
    #---Remove the base projector   
        for ob in bpy.context.scene.objects:
            ob.select = False
        base_projector = bpy.data.objects["BASE_PROJECTOR_" + obj_light.data.name]
        bpy.data.objects[base_projector.name].select = True
        bpy.data.objects.remove(base_projector, do_unlink=True)
        
        if obj_light.Lumiere.typlight == "Panel":
            mat_name, mat = get_mat_name("SOFTBOX_" + obj_light.data.name)
            mix = mat.node_tree.nodes["Mix Shader.001"]
            output = mat.node_tree.nodes["Material Output"]
            mat.node_tree.links.new(mix.outputs[0], output.inputs[0])

#########################################################################################################

#########################################################################################################                                   
def update_softbox_smooth(self, context):
    """Update the smooth value for edges of the softbox"""
    
    obj_light = get_lamp(context, self.lightname)
    dupli = get_object(context, self.lightname)
    obj_light.modifiers["Bevel"].width = dupli.Lumiere.softbox_smooth

#########################################################################################################

#########################################################################################################                                   
def update_projector_mat(self, context):
    """Update the cycles material nodes for the projector"""
    
    obj_light = get_object(context, self.lightname) 

    projector = bpy.data.objects["PROJECTOR_" + obj_light.data.name]
    mat_name, mat = get_mat_name(projector.data.name)
    img_text = mat.node_tree.nodes['Image Texture']
    saturation = mat.node_tree.nodes['Mix']
    contrast = mat.node_tree.nodes['Bright/Contrast']
    gamma = mat.node_tree.nodes['Gamma']
    invert = mat.node_tree.nodes['Invert']
    transparent = mat.node_tree.nodes['Transparent BSDF.001']

    saturation.inputs['Fac'].default_value = obj_light.Lumiere.projector_img_saturation
    gamma.inputs['Gamma'].default_value = obj_light.Lumiere.projector_img_gamma
    contrast.inputs['Bright'].default_value = obj_light.Lumiere.projector_img_bright
    contrast.inputs['Contrast'].default_value = obj_light.Lumiere.projector_img_contrast
    invert.inputs['Fac'].default_value = obj_light.Lumiere.projector_img_invert
    
    if obj_light.Lumiere.projector_img_reset: 
        obj_light.Lumiere.projector_img_reset = False

    if obj_light.Lumiere.projector_options == "Gradient":
        colramp = mat.node_tree.nodes['ColorRamp']
        coord = mat.node_tree.nodes['Texture Coordinate']
        geom = mat.node_tree.nodes['Geometry']
        mapping = mat.node_tree.nodes['Mapping']
        projector_typgradient =  obj_light.Lumiere.projector_typgradient
        mat.node_tree.nodes['Gradient Texture'].gradient_type = projector_typgradient
        mat.node_tree.links.new(colramp.outputs[0], transparent.inputs['Color'])
        
    #---Gradients links
        if obj_light.Lumiere.projector_typgradient in ("LINEAR", "DIAGONAL") : #LINEAR - DIAGONAL
            mat.node_tree.links.new(coord.outputs[0], mapping.inputs[0])
        elif obj_light.Lumiere.projector_typgradient in ("QUADRATIC", "EASING") : #QUAD - EASING
            mat.node_tree.links.new(geom.outputs[5], mapping.inputs[0])
        elif obj_light.Lumiere.projector_typgradient in ("SPHERICAL", "QUADRATIC_SPHERE", "RADIAL") : #SPHERICAL - QUADRATIC_SPHERE - RADIAL
            mat.node_tree.links.new(coord.outputs[3], mapping.inputs[0])    
                
    elif obj_light.Lumiere.projector_options == "Texture":
        if obj_light.Lumiere.projector_img_name != "":
            img_text.image = bpy.data.images[obj_light.Lumiere.projector_img_name]
            mat.node_tree.links.new(invert.outputs[0], transparent.inputs['Color'])
        else:
            if transparent.inputs['Color'].links:
                mat.node_tree.links.remove(transparent.inputs['Color'].links[0])
    else:
        if transparent.inputs['Color'].links:
            mat.node_tree.links.remove(transparent.inputs['Color'].links[0])
                        
#########################################################################################################

#########################################################################################################
def add_remove_projector(self, context):
    """Add or remove the front projector and the back projector"""
    
    obj_light = get_object(context, self.lightname) 
    
    if obj_light.Lumiere.projector:
    #---Add a projector 
        projector = create_projector(self, context, obj_light.data.name)
        context.scene.objects.active = bpy.data.objects[obj_light.name]
        update_projector(self, context)
        update_projector_smooth(self, context)

    else:
    #---Remove the projector    
        for ob in bpy.context.scene.objects:
            ob.select = False
        projector = bpy.data.objects["PROJECTOR_" + obj_light.data.name]
        bpy.data.objects[obj_light.name].Lumiere.projector_img_name = ""
        bpy.data.objects[projector.name].select = True
        bpy.data.objects.remove(projector, do_unlink=True)
            
    #---Remove the base projector
        if obj_light.Lumiere.projector_close :
            obj_light.Lumiere.projector_close = False           

#########################################################################################################

#########################################################################################################
class SCENE_OT_select_target(Operator):
    """Select one only target object using eyedropper"""
    
    bl_idname = "object.select_target"
    bl_description = "Select the only object you want to target.\n"+\
                     "Will ignore all the other objects but this one."
    bl_label = "Select target"
    act_light = bpy.props.StringProperty()

    def execute(self, context):
        if self.act_light != "": 
            context.scene.objects.active = bpy.data.objects[self.act_light] 
            obj_light = context.active_object
            self.tmp_target = bpy.data.objects[self.act_light].Lumiere.objtarget
        else:
            obj_light = context.active_object
            
    def modal(self, context, event):
        context.area.tag_redraw()
        obj_light = context.active_object
        bpy.context.window.cursor_modal_set("EYEDROPPER")
        try:
            if event.type == 'MOUSEMOVE':
                self.mouse_path = (event.mouse_region_x, event.mouse_region_y)
                
            elif event.type == 'LEFTMOUSE':
                if self.picker is not None and bpy.data.objects[self.picker].data.name.startswith("Lumiere") is False:
                        obj_light.Lumiere.objtarget = self.picker 

                bpy.context.window.cursor_modal_set("DEFAULT")
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
                return {'FINISHED'}
                
            elif event.type in ('RIGHTMOUSE', 'ESC'):
                bpy.context.window.cursor_modal_set("DEFAULT")
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
                obj_light.Lumiere.objtarget = self.tmp_target
                return {'CANCELLED'}
                
            return {'RUNNING_MODAL'}
            
        except Exception as error:
            print("Error to report : ", error)      
            bpy.context.window.cursor_modal_set("DEFAULT")
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            return {'FINISHED'}

    def invoke(self, context, event):
        self.execute(context)
        args = (self, context, event)
        self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_target_ob, args, 'WINDOW', 'POST_PIXEL')
        self.mouse_path = []
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
#########################################################################################################

#########################################################################################################
class SCENE_OT_select_pixel(Operator):
    """Align the environment background with the selected pixel"""
    
    bl_idname = "object.select_pixel"
    bl_description = "Target the selected pixel from the image texture and compute the rotation.\n"+\
                     "Use this to align a sun or a lamp from your image."
    bl_label = "Select pixel"
    act_light = bpy.props.StringProperty()
    img_name = bpy.props.StringProperty()
    img_type = bpy.props.StringProperty()
    img_size_x = bpy.props.FloatProperty()
    img_size_y = bpy.props.FloatProperty()

    def remove_handler(self):
        if self._handle:
            bpy.types.SpaceImageEditor.draw_handler_remove(self._handle, 'WINDOW')
        self._handle = None
    
    def execute(self, context):
        if self.act_light != "": 
            context.scene.objects.active = bpy.data.objects[self.act_light] 
            obj_light = context.active_object
        else:
            obj_light = context.active_object
        obj_light['pixel_select'] = True
        context.area.spaces.active.image = bpy.data.images[self.img_name]
  
    def modal(self, context, event):
        context.area.tag_redraw()
        context.window.cursor_modal_set("EYEDROPPER")
        
        try:
            if context.area == self.lumiere_area:
                
            #---Allow navigation
                if event.type in {'MIDDLEMOUSE'} or event.type.startswith("NUMPAD"): 
                    return {'PASS_THROUGH'}
                    
            #---Zoom Keys
                elif (event.type in  {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'} and not 
                   (event.ctrl or event.shift or event.alt)):
                    return{'PASS_THROUGH'}  
            
                elif event.type == 'MOUSEMOVE':
                    for area in context.screen.areas:
                        if area == self.lumiere_area and area.type == 'IMAGE_EDITOR':
                            for region in area.regions:
                                if region.type == 'WINDOW':
                                    mouse_x = event.mouse_x - region.x
                                    mouse_y = event.mouse_y - region.y
                                    uv = region.view2d.region_to_view(mouse_x, mouse_y)
                                #--- Source : https://blenderartists.org/forum/showthread.php?292866-Pick-the-color-of-a-pixel-in-the-Image-Editor
                                    if not math.isnan(uv[0]): 
                                        x = int(self.img_size_x * uv[0]) % self.img_size_x
                                        y = int(self.img_size_y * uv[1]) % self.img_size_y
                                        self.mouse_path = (x,y)

                elif event.type == 'LEFTMOUSE':
                    return{'PASS_THROUGH'}  
                    
                elif event.type == 'RIGHTMOUSE':
                    obj_light = bpy.data.objects[self.act_light]
                    rot_x = ((self.mouse_path[0] * 360) / self.img_size_x) - 90
                    rot_y = ((self.mouse_path[1] * 180) / self.img_size_y)
                    if self.img_type == "HDRI":
                        obj_light.Lumiere.hdri_rotation = rot_x - 180 + math.degrees(obj_light.rotation_euler.z)
                        obj_light.Lumiere.hdri_rotationy = rot_y - 180
                        obj_light.Lumiere.hdri_pix_rot = rot_x - 180
                        obj_light.Lumiere.hdri_pix_roty = rot_y - 180
                    else:
                        obj_light.Lumiere.img_rotation = rot_x - 180 + math.degrees(obj_light.rotation_euler.z)
                        obj_light.Lumiere.img_pix_rot = rot_x - 180             
                        
                    bpy.context.window.cursor_modal_set("DEFAULT")
                    self.remove_handler()
                    if context.area.type == 'IMAGE_EDITOR':
                        context.area.type = 'VIEW_3D'
                    return {'FINISHED'}
                    
                elif event.type == 'ESC':
                    bpy.context.window.cursor_modal_set("DEFAULT")
                    context.area.header_text_set()
                    self.remove_handler()
                    if context.area.type == 'IMAGE_EDITOR':
                        context.area.type = 'VIEW_3D'   
                    return {'CANCELLED'}
                    
                return {'RUNNING_MODAL'}

        except Exception as error:
            print("Error to report : ", error)  
            bpy.context.window.cursor_modal_set("DEFAULT")
            context.area.header_text_set()
            self.remove_handler()

            return {'FINISHED'}
    

    def invoke(self, context, event):
        self.mouse_path = [0,0]
        if context.space_data.type == 'VIEW_3D':
            context.area.type = 'IMAGE_EDITOR'
            t_panel = context.area.regions[2]
            n_panel = context.area.regions[3]
            self.view_3d_region_x = Vector((context.area.x + t_panel.width, context.area.x + context.area.width - n_panel.width))

            self.execute(context)
            self.img_size = [self.img_size_x, self.img_size_y]
            args = (self, context, event)
            self.lumiere_area = context.area

            context.window_manager.modal_handler_add(self)
            self._handle = bpy.types.SpaceImageEditor.draw_handler_add(draw_target_px, args, 'WINDOW', 'POST_PIXEL')
    
        
        return {'RUNNING_MODAL'}
                
#########################################################################################################

#########################################################################################################
def export_props_light(self, context, lightname, dupliname):
    lumiere_dict = {}
    obj_light = get_lamp(context, lightname)
    dupli = bpy.data.objects[dupliname]
    dupli.select = True

    lumiere_dict[dupliname] = {}
    lumiere_dict[dupliname]['Lumiere'] = dupli["Lumiere"].to_dict()
    lumiere_dict[dupliname]['rotation'] = tuple(dupli.matrix_world.to_euler())
    lumiere_dict[dupliname]['scale'] = tuple(obj_light.scale)
    lumiere_dict[dupliname]['location'] = tuple(dupli.location)
    lumiere_dict[dupliname]['Lumiere']['definition'] = list(textwrap.wrap(dupli['Lumiere']['definition'], 50)) if "definition" in dupli['Lumiere'] else " "
    lumiere_dict[dupliname]['group'] = {}
    for group in bpy.data.objects[dupliname].users_group :
        # lumiere_dict[dupliname]['group'] = {group.name : list(textwrap.wrap(group["Lumiere"]["definition"], 50))} if "definition" in group["Lumiere"] else {group.name : " "}
        lumiere_dict[dupliname]['group'].update({group.name : list(textwrap.wrap(group['Lumiere']['definition'], 50))} if "definition" in group['Lumiere'] else {group.name : " "})
        
#--- Environment light
    if obj_light.Lumiere.typlight == "Env":
        world = bpy.data.worlds['Lumiere_world'].node_tree.nodes
        if dupli.Lumiere.hdri_name:
            lumiere_dict[dupliname]['hdri_path'] = bpy.data.images[dupli.Lumiere.hdri_name].filepath
        lumiere_dict[dupliname]['hdri_col'] = [*world['Background'].inputs[0].default_value]
        if dupli.Lumiere.img_name:
            lumiere_dict[dupliname]['img_path'] = bpy.data.images[dupli.Lumiere.img_name].filepath
        lumiere_dict[dupliname]['img_col'] = [*world['Background.001'].inputs[0].default_value]
        
    else:
        mat_name, mat = get_mat_name(obj_light.data.name)
        if obj_light.type == "LAMP":
            lamp = get_lamp(context, obj_light.data.name) 
            lumiere_dict[dupliname]['smooth'] = lamp.data.node_tree.nodes["Light Falloff"].inputs[1].default_value
        else:
            lumiere_dict[dupliname]['smooth'] = mat.node_tree.nodes['Light Falloff'].inputs[1].default_value
        #---Gradient
            if dupli.Lumiere.texture_type == "Gradient":
                lumiere_dict[dupliname]['repeat'] = mat.node_tree.nodes['Math'].inputs[1].default_value 
                colramp = mat.node_tree.nodes['ColorRamp'].color_ramp      
                lumiere_dict[dupliname]['gradient'] = {}
                lumiere_dict[dupliname]['interpolation'] = colramp.interpolation
                for i in range(len(colramp.elements)):
                    lumiere_dict[dupliname]['gradient'].update({colramp.elements[i].position: colramp.elements[i].color[:]})

    return(lumiere_dict)

#########################################################################################################

#########################################################################################################
class SCENE_OT_export_light(Operator):
    """Export the current light data in JSON format"""
    
    bl_idname = "object.export_light"
    bl_label = "Export light"
    
    act_light = bpy.props.StringProperty()
    
    def execute(self, context):
        current_file_path = __file__
        current_file_dir = os.path.dirname(__file__)
        
        if self.act_light != "": 
            context.scene.objects.active = bpy.data.objects[self.act_light] 
            obj_light = context.active_object
            
            for ob in bpy.context.scene.objects:
                    if ob.name != obj_light.name:
                        ob.select = False
                        ob.Lumiere.select_light = False
        else:
            self.act_light = context.active_object.name 
            obj_light = context.active_object
            
    #---Try to open the Lumiere export dictionary
        try:
            with open(current_file_dir + "\\" + "lumiere_dictionary.json", 'r', encoding='utf-8') as file:
                my_dict = json.load(file)
                file.close()    
        except Exception:
            print("Warning, dict empty, creating a new one.")
            my_dict = {}
                
        lumiere_dict = export_props_light(self, context, obj_light.Lumiere.lightname, self.act_light)

        my_dict.update(lumiere_dict)
        
        with open(current_file_dir + "\\" + "lumiere_dictionary.json", "w", encoding='utf-8') as file:
            json.dump(my_dict, file, sort_keys=True, indent=4, ensure_ascii=False)

        file.close()
        message = "Light exported"
        self.report({'INFO'}, message)
        return {'FINISHED'}
#########################################################################################################

#########################################################################################################
class SCENE_OT_export_group(Operator):
    """Export the current group lights in JSON format"""
    
    bl_idname = "object.export_group"
    bl_label = "Export group"
    
    act_group = bpy.props.StringProperty()
    
    def execute(self, context):
        lumiere_dict = {}
        current_file_path = __file__
        current_file_dir = os.path.dirname(__file__)
        
    #---Try to open the Lumiere export dictionary
        try:
            with open(current_file_dir + "\\" + "lumiere_dictionary.json", 'r', encoding='utf-8') as file:
                my_dict = json.load(file)
                file.close()
        except :
            print("Warning, dict empty, creating a new one.")   
            my_dict = {}
        
        if self.act_group != "": 
            if bpy.data.groups[self.act_group]:
                for ob in bpy.data.objects:
                    for group in ob.users_group:
                        if group.name == self.act_group:
                            lumiere_dict = export_props_light(self, context, ob.Lumiere.lightname, ob.name)
                            my_dict.update(lumiere_dict)
                        
            with open(current_file_dir + "\\" + "lumiere_dictionary.json", "w", encoding='utf-8') as file:
                json.dump(my_dict, file, sort_keys=True, indent=4, ensure_ascii=False)

            file.close()
            message = "Group exported"
            self.report({'INFO'}, message)
        return {'FINISHED'}
#########################################################################################################

#########################################################################################################
class GROUP_UL_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        group = data
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, "name", text="", toggle=False, emboss=False, icon_value=icon)
            layout.prop(item, "num", text="", toggle=False, emboss=False)
            layout.context_pointer_set("group", group)
        elif self.layout_type in {'GRID'}:
            pass
    
#########################################################################################################

#########################################################################################################
class ALL_LIGHTS_UL_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        object = data
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            split = layout.split(0.7)
            split.prop(item, "name", text="", toggle=False, emboss=False, icon_value=icon, icon="GROUP" if item.all_light_in_group else "BLANK1")
        elif self.layout_type in {'GRID'}:
            pass        
#########################################################################################################

########################################################################################################
# Create custom property group
class LightsProp(bpy.types.PropertyGroup):
    label = bpy.props.StringProperty()
    all_light_in_group = bpy.props.BoolProperty(default=False)
#########################################################################################################

########################################################################################################
# Create custom property group
class GroupProp(bpy.types.PropertyGroup):
    num = bpy.props.StringProperty()
#########################################################################################################

#########################################################################################################
class RemoveLightItem(bpy.types.Operator):
    bl_idname = "scene.remove_light_item"
    bl_label = "Remove Light Entry"

    light = bpy.props.StringProperty()
    
    @classmethod
    def poll(cls, context):
        return context.scene.Lumiere_all_lights_list_index >= 0

    def execute(self, context):
        settings = context.scene.Lumiere_all_lights_list    
        settings.remove(context.scene.Lumiere_all_lights_list_index)
        context.scene.Lumiere_all_lights_list_index -= 1
        self.my_dict = get_lumiere_dict(self, context)
        self.report({'INFO'}, "Light " + self.light + " deleted from the list")
        self.my_dict.pop(self.light, None)
        update_lumiere_dict(self, context, self.my_dict)
    
        return {'FINISHED'} 
#########################################################################################################

#########################################################################################################
class RemoveGroupItem(bpy.types.Operator):
    bl_idname = "scene.remove_group_item"
    bl_label = "Remove Group Entry"

    group = bpy.props.StringProperty()
    
    @classmethod
    def poll(cls, context):
        return context.scene.Lumiere_groups_list_index >= 0

    def execute(self, context):
        settings = context.scene.Lumiere_groups_list    
        print("LIST GROUP: ", settings)
        settings.remove(context.scene.Lumiere_groups_list_index)
        context.scene.Lumiere_groups_list_index -= 1
        self.my_dict = get_lumiere_dict(self, context)
        self.report({'INFO'}, "Group " + self.group + " deleted from the list")
        for key, value in self.my_dict.items():
            if self.group in value["group"]:
                value["group"].pop(self.group, None)
        update_lumiere_dict(self, context, self.my_dict)
    
        return {'FINISHED'} 
#########################################################################################################

#########################################################################################################
def get_lumiere_dict(self, context):
        
    current_file_dir = os.path.dirname(__file__)
    
#---Try to open the Lumiere export dictionary
    try:
        with open(current_file_dir + "\\" + "lumiere_dictionary.json", 'r', encoding='utf-8') as file:
            my_dict = json.loads(file.read())       
            file.close()
    except : 
        my_dict = {}

    return(my_dict)
#########################################################################################################

#########################################################################################################
def update_lumiere_dict(self, context, my_dict):
        
    current_file_dir = os.path.dirname(__file__)
        
    with open(current_file_dir + "\\" + "lumiere_dictionary.json", "w", encoding='utf-8') as file:
        json.dump(my_dict, file, sort_keys=True, indent=4, ensure_ascii=False)
    file.close()        

#########################################################################################################

#########################################################################################################
class SCENE_OT_import_management(bpy.types.Operator):
    """Manage the data from JSON file"""
    
    bl_idname = "object.manage_light"
    bl_label = "Manage library"
    
#---List of panels options 
    select_group = EnumProperty(name="", 
                                description="Display by individual light or group.\nSelected",
                                items=(
                                ("Light", "Light", "", 0),
                                ("Group", "Group", "", 1),
                                ), 
                                default="Light")
                                
    error_message = BoolProperty(default=False)
    def separator(self):
        layout = self.layout
        row = layout.row()
        row.scale_y = .15
        row.alert = True
        row.operator("object.separator", text=" ", icon='BLANK1')
        row.alert = False
        
    
    def execute(self, context):
        try:
        #---Create the list of lights or lights in group 
            if self.select_group == "Group":
                light_in_group = [key for key, value in self.my_dict.items() if self.select_item in value["group"]]

                if bpy.data.groups.get(self.select_item) is not None:
                    group_to_link = bpy.data.groups[self.select_item]
                else:
                    group_to_link = bpy.data.groups.new(self.select_item)
                
                for light in light_in_group:
                    self.add_light(context, light)
                    cobj = get_object(context, self.lightname)
                    group_to_link.objects.link(cobj)
                    
            else:
                self.add_light(context, self.select_item)
                
            return {'FINISHED'}
        except : 
            print("Nothing selected.")
            return {'PASS_THROUGH'}
            
    def check(self, context):
        return True
        
    def draw(self, context):
        scene = context.scene
        layout = self.layout

        row = layout.row(align=True)
        box = row.box()
        col = box.column()
        row = col.row(align=True)
        row.prop(self, "select_group", text=" ", expand=True)       

    #---Get a Light or a Group
        if self.select_group == "Group":
        #---Expand the groups
            if len(context.scene.Lumiere_groups_list) > 0:
                row = col.row(align=True)
                row.template_list("GROUP_UL_list", "", context.scene, "Lumiere_groups_list", context.scene, "Lumiere_groups_list_index", rows=2)
                self.select_type = "Group"
                self.select_item = scene.Lumiere_groups_list[scene.Lumiere_groups_list_index].name
            #---Remove from list
                row = col.row(align=True)
                op = row.operator("scene.remove_group_item")
                op.group = scene.Lumiere_groups_list[scene.Lumiere_groups_list_index].name
                for i, v in enumerate(self.group_dict[self.select_item]):
                    row = layout.row(align=True)
                    row.scale_y = 0.5
                    row.label(v)

                group_light = [key for key in self.my_dict.keys() if self.select_item in self.my_dict[key]["group"]]
                self.separator()
                for light in group_light:
                    row = layout.row(align=True)
                    row.scale_y = 0.5
                    row.label(light)
                
        elif self.select_group == "Light":
        #---Expand all the lights with or without group
            if len(context.scene.Lumiere_all_lights_list) > 0:
                light = scene.Lumiere_all_lights_list[scene.Lumiere_all_lights_list_index].name
                row = col.row(align=True)
                row.template_list("ALL_LIGHTS_UL_list", "",context.scene, "Lumiere_all_lights_list", context.scene, "Lumiere_all_lights_list_index", rows=2)
                self.select_type = "All"
                self.select_item = scene.Lumiere_all_lights_list[scene.Lumiere_all_lights_list_index].name
            #---Remove from list
                row = col.row(align=True)
                op = row.operator("scene.remove_light_item")
                op.light = scene.Lumiere_all_lights_list[scene.Lumiere_all_lights_list_index].name
                for i, v in enumerate(self.my_dict[light]["Lumiere"]["definition"]):
                    row = layout.row(align=True)
                    row.scale_y = 0.5
                    row.label(v)
                
    def invoke(self, context, event):
        context.scene.Lumiere_all_lights_list.clear()
        context.scene.Lumiere_groups_list.clear()
        current_file_dir = os.path.dirname(__file__)
        self.my_dict = get_lumiere_dict(self, context)
        self.group_dict = defaultdict(list)
        self.group_light = {}
        
        for key, value in self.my_dict.items():

        #---Fill the items for the light with or without group
            item = context.scene.Lumiere_all_lights_list.add()
            item.name = key     
            item.all_light_in_group = True if self.my_dict[key]["group"] else False         
            
        #---Fill the items for the light in group
            if self.my_dict[key]["group"]:
                self.group_dict.update({i:self.my_dict[key]["group"][i] for i in self.my_dict[key]["group"]})

    #---Create a list with all the groups and count them
        cnt = Counter([val for value in self.my_dict.values() for val in value["group"]])

    #---Fill the items for the groups
        for group, nbr in cnt.items():
            item = context.scene.Lumiere_groups_list.add()
            item.name = group
            item.num = str(nbr)
            
        return context.window_manager.invoke_popup(self)
        # return context.window_manager.invoke_props_dialog(self)
#########################################################################################################

#########################################################################################################
class SCENE_OT_import_light(bpy.types.Operator):
    """Import the data from JSON file"""
    
    bl_idname = "object.import_light"
    bl_label = "Import list"
    
#---List of panels options 
    select_group = EnumProperty(name="", 
                                description="List of panels options.\nSelected",
                                items=(
                                ("Light", "Light", "", 0),
                                ("Group", "Group", "", 1),
                                ), 
                                default="Light")
                                
    error_message = BoolProperty(default=False)
    def separator(self):
        layout = self.layout
        row = layout.row()
        row.scale_y = .15
        row.alert = True
        row.operator("object.separator", text=" ", icon='BLANK1')
        row.alert = False
        
    def add_light(self, context, light):

    #---Check if the light already exist
        for ob in context.scene.objects:
            if ob.name == light:
                error_message = True

        if self.my_dict[light]["Lumiere"]["typlight"] == 0:
            obj_light = create_softbox(self, context, dupli_name = light)
        elif self.my_dict[light]["Lumiere"]["typlight"] == 1:
            obj_light = create_light_point(self, context, dupli_name = light)
        elif self.my_dict[light]["Lumiere"]["typlight"] == 2:
            obj_light = create_light_sun(self, context, dupli_name = light)
        elif self.my_dict[light]["Lumiere"]["typlight"] == 3:
            obj_light = create_light_spot(self, context, dupli_name = light)
        elif self.my_dict[light]["Lumiere"]["typlight"] == 4:
            obj_light = create_light_area(self, context, dupli_name = light)
        elif self.my_dict[light]["Lumiere"]["typlight"] == 5:
            obj_light = create_light_sky(self, context, dupli_name = light)
        elif self.my_dict[light]["Lumiere"]["typlight"] == 6:
            obj_light = create_light_env(self, context, dupli_name = light)

        obj_light["Lumiere"] = self.my_dict[light]["Lumiere"]
        obj_light.Lumiere.definition = ' '.join(self.my_dict[light]["Lumiere"]["definition"])
        obj_light["Lumiere"]["lightname"] = obj_light.data.name
        obj_light.location = self.my_dict[light]["location"]
        obj_light.rotation_euler = self.my_dict[light]["rotation"]
        obj_light.scale = self.my_dict[light]["scale"]

        
    #--- Environment light
        if obj_light.Lumiere.typlight == "Env":
            world = bpy.data.worlds['Lumiere_world'].node_tree.nodes
            if "hdri_name" in self.my_dict[light]["Lumiere"]:
                bpy.data.images.load(self.my_dict[light]['hdri_path'], check_existing=True)
                bpy.data.images[self.my_dict[light]["Lumiere"]["hdri_name"]].filepath = self.my_dict[light]['hdri_path'] 
            if "img_name" in self.my_dict[light]["Lumiere"]:
                bpy.data.images.load(self.my_dict[light]['img_path'], check_existing=True)
                bpy.data.images[self.my_dict[light]["Lumiere"]["img_name"]].filepath = self.my_dict[light]['img_path']
            world['Background'].inputs[0].default_value = [*self.my_dict[light]['hdri_col']]
            world['Background.001'].inputs[0].default_value = [*self.my_dict[light]['img_col']]
        
        else:

            lamp = get_lamp(context, obj_light.data.name) 
            mat_name, mat = get_mat_name(lamp.data.name)
            if lamp.type == "LAMP":
                lamp.data.node_tree.nodes["Light Falloff"].inputs[1].default_value = self.my_dict[light]['smooth']
            else:
                mat.node_tree.nodes['Light Falloff'].inputs[1].default_value = self.my_dict[light]['smooth']    
            

        #---Gradient
            if obj_light.Lumiere.texture_type == "Gradient":
                mat.node_tree.nodes['Math'].inputs[1].default_value = self.my_dict[light]['repeat']
                colramp = mat.node_tree.nodes['ColorRamp'].color_ramp 
                colramp.interpolation = self.my_dict[light]['interpolation']
                i = 0
                for key, value in sorted(self.my_dict[light]['gradient'].items()) :
                    if i > 1:
                        colramp.elements.new(float(key))
                    colramp.elements[i].position = float(key)
                    colramp.elements[i].color[:] = value
                    i += 1
        
        self.lightname = obj_light["Lumiere"]["lightname"]
        create_lamp_grid(self, context)
        update_mat(self, context)

        
    def execute(self, context):
        
        try:
        #---Create the list of lights or lights in group 
            if self.select_group == "Group":
                light_in_group = [key for key, value in self.my_dict.items() if self.select_item in value["group"]]

                if bpy.data.groups.get(self.select_item) is not None:
                    group_to_link = bpy.data.groups[self.select_item]
                else:
                    group_to_link = bpy.data.groups.new(self.select_item)
                for light in light_in_group:
                    self.add_light(context, light)
                    cobj = get_object(context, self.lightname)
                    group_to_link.objects.link(cobj)
            else:
                self.add_light(context, self.select_item)
                    
            return {'FINISHED'}
        except : 
            print("Nothing selected.")
            return {'PASS_THROUGH'}
        
    def check(self, context):
        return True
        
    def draw(self, context):
        scene = context.scene
        layout = self.layout

        row = layout.row(align=True)
        box = row.box()
        col = box.column()
        row = col.row(align=True)
        row.prop(self, "select_group", text=" ", expand=True)       

    #---Get a Light or a Group
        if self.select_group == "Group":
        #---Expand the groups
            if len(context.scene.Lumiere_groups_list) > 0:
                row = col.row(align=True)
                row.template_list("GROUP_UL_list", "", context.scene, "Lumiere_groups_list", context.scene, "Lumiere_groups_list_index", rows=2)
                self.select_type = "Group"
                self.select_item = scene.Lumiere_groups_list[scene.Lumiere_groups_list_index].name
                # for i, v in enumerate(list(textwrap.wrap(bpy.data.groups[self.select_item]["Lumiere"]["definition"], 50))):
                
                for i, v in enumerate(self.group_dict[self.select_item]):
                    row = layout.row(align=True)
                    row.scale_y = 0.5
                    row.label(v)

                group_light = [key for key in self.my_dict.keys() if self.select_item in self.my_dict[key]["group"]]
                self.separator()
                for light in group_light:
                    row = layout.row(align=True)
                    row.scale_y = 0.5
                    row.label(light)

        elif self.select_group == "Light":
            if len(context.scene.Lumiere_all_lights_list) > 0:
        #---Expand all the lights with or without group
                light = scene.Lumiere_all_lights_list[scene.Lumiere_all_lights_list_index].name
                row = col.row(align=True)
                row.template_list("ALL_LIGHTS_UL_list", "",context.scene, "Lumiere_all_lights_list", context.scene, "Lumiere_all_lights_list_index", rows=2)
                self.select_type = "All"
                self.select_item = scene.Lumiere_all_lights_list[scene.Lumiere_all_lights_list_index].name
                for i, v in enumerate(self.my_dict[light]["Lumiere"]["definition"]):
                    row = layout.row(align=True)
                    row.scale_y = 0.5
                    row.label(v)
                
    def invoke(self, context, event):
        context.scene.Lumiere_all_lights_list.clear()
        context.scene.Lumiere_groups_list.clear()
        current_file_dir = os.path.dirname(__file__)
        self.my_dict = get_lumiere_dict(self, context)
        self.group_dict = defaultdict(list)
        self.group_light = {}
        
        for key, value in self.my_dict.items():

        #---Fill the items for the light with or without group
            item = context.scene.Lumiere_all_lights_list.add()
            item.name = key     
            item.all_light_in_group = True if self.my_dict[key]["group"] else False         
            
        #---Fill the items for the light without group
            if self.my_dict[key]["group"]:
                self.group_dict.update({i:self.my_dict[key]["group"][i] for i in self.my_dict[key]["group"]})

    #---Create a list with all the groups and count them
        cnt = Counter([val for value in self.my_dict.values() for val in value["group"]])

    #---Fill the items for the groups
        for group, nbr in cnt.items():
            item = context.scene.Lumiere_groups_list.add()
            item.name = group
            item.num = str(nbr)
            
        return context.window_manager.invoke_props_dialog(self)
        
#########################################################################################################

#########################################################################################################
class SCENE_OT_select_light(Operator):
    """Click on this widget to select this light in the scene.\n\
    (All the other objects will be unselected)"""
    
    bl_idname = "object.select_light"
    bl_label = "Select light"
    
    act_light = bpy.props.StringProperty()
    
    def execute(self, context):
        
        if self.act_light != "": 
            context.scene.objects.active = bpy.data.objects[self.act_light] 
            obj_light = context.active_object
            
            for ob in bpy.context.scene.objects:
                    if ob.name != obj_light.name:
                        ob.select = False
        else:
            self.act_light = context.active_object.name
            obj_light = context.active_object
            
        obj_light.select = True

        return {'FINISHED'}

#########################################################################################################

#########################################################################################################           
class SCENE_OT_remove_light(bpy.types.Operator):
    """Remove the selected light"""
    bl_idname = "object.remove_light"
    bl_label = "Remove light"
    bl_options = {"REGISTER"}

    act_light = bpy.props.StringProperty()
    
    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context): 
            
        if self.act_light != "": 
            context.scene.objects.active = bpy.data.objects[self.act_light] 
            obj_light = context.active_object
        else:
            self.act_light = context.active_object.name 
            obj_light = context.active_object
        
    #---Environment background : Remove nodes
        if obj_light.Lumiere.typlight in ("Env", "Sky"):
            bpy.data.worlds['Lumiere_world'].use_nodes = False

    #---Remove the projector
        if obj_light.Lumiere.projector :
            projector = bpy.data.objects["PROJECTOR_" + obj_light.data.name]
            bpy.data.objects[projector.name].select = True
            context.scene.objects.unlink(projector)
            bpy.data.objects.remove(projector, do_unlink=True)
            
        #---Remove the base projector
            if obj_light.Lumiere.projector_close :
                base_projector = bpy.data.objects["BASE_PROJECTOR_" + obj_light.data.name]
                bpy.data.objects[base_projector.name].select = True
                context.scene.objects.unlink(base_projector)
                bpy.data.objects.remove(base_projector, do_unlink=True)
                obj_light.Lumiere.projector_close = False
                
    #---Remove the light
        if obj_light.Lumiere.typlight != "Env":
        #---Get the lamp or the softbox link to the duplivert
            lamp_or_softbox = get_lamp(context, obj_light.Lumiere.lightname)
            context.scene.objects.unlink(lamp_or_softbox)
            bpy.data.objects.remove(lamp_or_softbox, do_unlink=True)
        else:
            child = obj_light.children[0]
        #---Get the lamp or widget for the environment
            context.scene.objects.unlink(child)
            bpy.data.objects.remove(child, do_unlink=True)  

    #---Remove the duplivert
        context.scene.objects.unlink(obj_light)
        bpy.data.objects.remove(obj_light, do_unlink = True)
        return {"FINISHED"}
            

#########################################################################################################

#########################################################################################################   
def items_texture_type(self, context):
    """
    Define the different items for the material choice of mesh or area lights
    """
    obj_light = get_object(context, self.lightname)
            
    if obj_light.Lumiere.typlight == "Panel":
        items = {
                ("Color", "Color", "", 0),
                ("Gradient", "Gradient", "", 1),
                ("Texture", "Texture", "", 2),
                }
    elif obj_light.Lumiere.typlight == "Area":
        items = {
                ("Color", "Color", "", 0),
                ("Gradient", "Gradient", "", 1),
                }
    else:
        items = {
                ("Color", "Color", "", 0),
                }

    return items        

#########################################################################################################

#########################################################################################################   
def items_light_type(self, context):
    """Define the different items for the light"""
    obj_light = get_object(context, self.lightname)
    
    if obj_light.Lumiere.typlight not in ("Env", "Sky"):
        items = {
                (obj_light.Lumiere.typlight, obj_light.Lumiere.typlight, "", 0),
                ("Projector", "Projector", "", 1)
                }
    else:
        if len(obj_light.children) > 0:
            child = obj_light.children[0]
            if child.type == 'LAMP':
                env_sun = child.data.type
            else:
                env_sun = ""
            items = {
                    (obj_light.Lumiere.typlight, obj_light.Lumiere.typlight, "", 0),
                    (env_sun, env_sun, "", 1)
                    }
        else:
            items = {
                    (obj_light.Lumiere.typlight, obj_light.Lumiere.typlight, "", 0),
                    }

    return items        

#########################################################################################################

#########################################################################################################   
def new_items_type_light(self, context):
    """Define the different items for the light"""
    
    obj_light = get_object(context, self.lightname)

    if obj_light.Lumiere.typlight != "Env":
        listitems = [
                ["Panel", "Panel", "", 0], 
                ["Point", "Point", "", 1], 
                ["Sun", "Sun", "", 2],     
                ["Spot", "Spot", "", 3],   
                ["Area", "Area", "", 4],    
                ]
    else:
        listitems = [
                ["None", "None", "", 0], 
                ["Sun", "Sun", "", 1],
                ]       
    for index, item in enumerate(listitems):
        if item[0] == obj_light.Lumiere.typlight:
            del listitems[index]
            if index < len(listitems):
                listitems[index][3] = index
                listitems[index] = tuple(listitems[index])
        else:
            listitems[index][3] = index
            listitems[index] = tuple(listitems[index])

    return listitems        


#########################################################################################################

#########################################################################################################   
class ERROR_OT_Message(bpy.types.Operator):

    bl_idname = "error.message"
    bl_label = "Message"

    options_dialog = EnumProperty(name="Select an option", 
                                description="List of options.\nSelected",
                                items=(
                                ("Cancel", "Cancel", "", 0),
                                ("Replace", "Replace", "", 1),
                                ("Rename", "Rename", "", 2),
                                ), 
                                default="Cancel")   
    
    my_dict = {}
    
    def execute(self, context):
        message = "This light already exist !"
        self.report({'INFO'}, message)
        return {'FINISHED'}
        
    def check(self, context):
        return True
        
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=400, height=200)
        
    def draw(self, context):
        layout = self.layout
        layout.label("This light already exist. What do you want to do ?") 
        layout.prop(self, "options_dialog", expand=True)
        
#########################################################################################################

#########################################################################################################
class GROUP_OT_show_hide_group(Operator):
    """Show / Hide all the lights of this group"""
    bl_idname = "group.show_hide_group"
    bl_label = "Show / Hide group"
    
    group = bpy.props.StringProperty()
    def execute(self, context):
        light_on_group = [obj for obj in bpy.data.groups[self.group].objects if obj.type != 'EMPTY' and obj.data.name.startswith("Lumiere") ]
        bpy.data.groups[self.group].Lumiere.show_group = not bpy.data.groups[self.group].Lumiere.show_group
        
        if self.group != "": 
            for light in light_on_group:
                self.lightname = light.Lumiere.lightname
                show_hide_light(self, context)

        return {'FINISHED'}
                
#########################################################################################################

#########################################################################################################
class GROUP_OT_light_group_remove(Operator):
    """Remove light from group"""
    bl_idname = "group.light_group_remove"
    bl_label = "Remove light from group"
    type = bpy.props.StringProperty()
    light = bpy.props.StringProperty()
    group = bpy.props.StringProperty()
    
    def execute(self, context):
        link_group = bpy.data.groups[self.group]
        if self.type == "light":
            context.scene.objects.active = bpy.data.objects[self.light] 
            obj_light = context.active_object
            obj_light.select = True
            link_group.objects.unlink(obj_light)
                
            obj_light.select = False
            context.scene.objects.active = bpy.data.objects[self.light] 
            obj_light.select = True
        else:
            if bpy.data.groups[self.group]:
                for ob in bpy.data.objects:
                    for group in ob.users_group:
                        if group.name == self.group:
                            link_group.objects.unlink(ob)
    
        return {'FINISHED'}

#########################################################################################################

#########################################################################################################
class OBJECT_OT_light_group_link(Operator):
    bl_idname = "object.light_group_link"
    bl_label = "Link light to existing group"
    """
    Link light to existing group
    """
    light = bpy.props.StringProperty()
    group = bpy.props.StringProperty()
    
    def execute(self, context):
        context.scene.objects.active = bpy.data.objects[self.light] 
        obj_light = bpy.data.objects[self.light]
        obj_light.select = True
        bpy.ops.object.group_link(group=self.group)
        obj_light.select = False
        context.scene.objects.active = bpy.data.objects[self.light] 
        obj_light.select = True
        return {'FINISHED'}
#########################################################################################################

#########################################################################################################
class OBJECT_OT_separator(Operator):
    bl_idname = "object.separator"
    bl_label = "Separator"
    """
    Separator
    """
    
    def execute(self, context):
        return {'FINISHED'}     
#########################################################################################################

#########################################################################################################
def items_list_group_add(self, context):
    """Select the group you want to add the light to."""
    items = {(group.name, group.name, "", i) for i, group in enumerate(bpy.data.groups)}

    return items        

#########################################################################################################

#########################################################################################################   
class SCENE_OT_export_popup(Operator):
    """ Export the light """
    
    bl_idname = "object.export_popup"
    bl_label = "Export"  
    
    act_name = bpy.props.StringProperty()
    grp_name = bpy.props.StringProperty()
    act_type = bpy.props.StringProperty()
    
    #source ZEFFII : https://blender.stackexchange.com/questions/44356/fighting-split-col-and-aligning-row-content/44357#44357
    def draw_props(self, labelname):
        layout = self.layout
        c = layout.column()
        row = c.row()
        split = row.split(percentage=0.25)
        c = split.column()
        c.label(labelname)
        split = split.split()
        self.column = split.column()
        
    def separator(self):
        layout = self.layout
        row = layout.row()
        row.scale_y = .15
        row.alert = True
        row.operator("object.separator", text=" ", icon='BLANK1')
        row.alert = False
        
    def execute(self, context):
        return {"FINISHED"} 
        
    def check(self, context):
        return True 
        
    def draw(self, context):
        scene = context.scene
        
        if self.act_type == "Light":
            cobj = bpy.data.objects[self.act_name]
        #---Export individual light
            self.separator()
            self.draw_props("Export")
            op = self.column.operator("object.export_light", text ="Export Light")
            op.act_light = cobj.name 
            self.light_on_group = cobj.users_group
            self.draw_props("Description")
            row = self.column.row(align=True)
            row.prop(cobj.Lumiere, "definition", text="", expand=False)

            self.separator()
            
            #---Groups
            if bpy.data.groups:
                self.draw_props("Add:")
                row = self.column.row(align=True)
                op = row.operator("object.light_group_link", text="Add to:") 
                op.light = cobj.name
                op.group = scene.Lumiere.list_group_add
                row.prop(scene.Lumiere, "list_group_add", text="", expand=False)
                for group in bpy.data.groups:
                    if group in cobj.users_group:
                        self.draw_props("Remove:")
                        row = self.column.row(align=True)
                        op = row.operator("group.light_group_remove", text="Remove from: " + group.name )
                        op.type = "light"
                        op.light = cobj.name
                        op.group = group.name
                self.draw_props("Create:")
                self.column.operator("object.group_add", text="Add to new group")       
            else:
                self.draw_props("Create:")
                self.column.operator("object.group_add", text="Add to new group")   
                
        else:
        #---Export all lights in this group
            group = bpy.data.groups[self.act_name]
            self.separator()
            self.draw_props("Export")
            op = self.column.operator("object.export_group", text ="Export Group")
            op.act_group = self.act_name
            self.draw_props("Description")
            row = self.column.row(align=True)
            row.prop(group.Lumiere, "definition", text="", expand=False)
            self.separator()
            row = self.column.row(align=True)
            op = row.operator("group.light_group_remove", text="Remove all from: " + group.name )
            op.type = "group"
            op.light = ""
            op.group = group.name
            
    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self)
        
#########################################################################################################

#########################################################################################################   

class LumiereGrp(bpy.types.PropertyGroup):
    expanded_group = BoolProperty(default=False)
    show_group = BoolProperty(default=True)  
                               
#---A short description of the group for import / export
    definition = StringProperty(
                               name="Description",
                               description="Description.",) 
                                
#-------------------------------------------------------------------------#
#-------------------------------------------------------------------------#
#-------------------------------------------------------------------------#

class LumiereScn(bpy.types.PropertyGroup):
#---List of lights sources
    typlight = EnumProperty(name="Light sources",
                            description="List of lights sources:\n"+
                            "- Panel  : Panel object with an emission shader\n"+
                            "- Point  : Emit light equally in all directions\n"+
                            "- Sun    : Emit light in a given direction\n"+
                            "- Spot   : Emit light in a cone direction\n"+
                            "- Area   : Emit light from a square or rectangular area\n"+
                            "- Sky    : Emit light from background and a sun light\n"+
                            "- Env    : Emit light from an environment image map\n"+
                            "- Import : Import your previous saved Light / Group lights\n"+
                            "Selected",
                            items=(
                            ("Panel", "Panel light", "", 0),
                            ("Point", "Point light", "", 1),
                            ("Sun", "Sun light", "", 2),
                            ("Spot", "Spot light", "", 3),
                            ("Area", "Area light", "", 4),
                            ("Sky", "Sky Background", "", 5),
                            ("Env", "Environment Background", "", 6),
                            ("Import", "Import Light", "", 7),
                            ), 
                            default='Panel')                           

#---Available groups in the scene
    list_group_add = EnumProperty(name="Groups", 
                                    description="Select the group you want to add the light to.\nSelected",
                                    items = items_list_group_add
                                    )

#-------------------------------------------------------------------------#
#-------------------------------------------------------------------------#
#-------------------------------------------------------------------------#

class LumiereObj(bpy.types.PropertyGroup):
#---Name of the light
    lightname = StringProperty(
                               name="LightName",
                               description="Light name.",)  
                               
#---A short description of the light for import / export
    definition = StringProperty(
                               name="Description",
                               description="Description.",) 
                               
#---Range of the light from the targeted object
    range = FloatProperty(
                          name="Range ",
                          description="Range from the object.",
                          min=0.001, max=100000,
                          soft_min=0.001, soft_max=100.0,
                          default=0.5,
                          precision=2,
                          subtype='DISTANCE',
                          unit='LENGTH')
                          
#---Strength of the light
    energy = FloatProperty(
                           name="Strength",
                           description="Strength of the light.",
                           min=0.001, max=9000000000.0,
                           soft_min=0.0, soft_max=100.0,
                           default=10,
                           precision=3,
                           subtype='NONE',
                           unit='NONE',
                           update=update_mat)

#---Base Color of the light
    lightcolor = FloatVectorProperty(   
                                     name = "",
                                     description="Base Color of the light.",
                                     subtype = "COLOR",
                                     size = 4,
                                     min = 0.0,
                                     max = 1.0,
                                     default = (0.8,0.8,0.8,1.0),
                                     update=update_mat) 

#---Object the light will always target
    objtarget = StringProperty(
                               name="Target",
                               description="Object the light will always target.",)

#---Type of the actual light
    typlight = EnumProperty(name="Light type", 
                            description="Type of the actual light.",
                            items=(
                            ("Panel", "Panel light", "", 0),
                            ("Point", "Point light", "", 1),
                            ("Sun", "Sun light", "", 2),
                            ("Spot", "Spot light", "", 3),
                            ("Area", "Area light", "", 4),
                            ("Sky", "Sky Background", "", 5),
                            ("Env", "Environment Background", "", 6),
                            ("Import", "Import Light", "", 7),
                            ), 
                            default='Panel')

#---Compute the reflection angle from the normal of the target or from the view of the screen.
    reflect_angle = EnumProperty(name="Reflection",
                          description="Compute the light position from the angle view or the normal of the object.\n"+\
                          "- View   : The light will be positioned from the angle of the screen 3dView and the target face of the object.\n"+\
                          "- Normal : The light will be positioned in parralel to the normal of the face of the targeted object.\n"+\
                          "Selected",
                          items=(
                          ("0", "View", "", 0),
                          ("1", "Normal", "", 1),
                          ),
                          default="0")

                          
#---List of lights to change the selected one to
    newtyplight = EnumProperty(name="Change light to:",
                               description="List of lights to change the selected one to.\nSelected",
                               items = new_items_type_light,
                               update = update_type_light
                               )

#---Available items for this type of light
    items_light_type = EnumProperty(name="Light items", 
                                    description="Available items for this type of light.\nSelected",
                                    items = items_light_type
                                    )

#---Define how light intensity decreases over distance
    typfalloff = EnumProperty(name="", 
                              description="Define how light intensity decreases over distance\n"+
                              "Quadratic: leave strength unmodified if smooth is 0.0 and corresponds to reality.\n"+
                              "Linear   : distance to the light have a slower decrease in intensity.\n"+
                              "Constant : distance to the light have no influence on its intensity.\n"+
                              "Selected",
                              items=(
                              ("0", "Quadratic falloff", "", 0),
                              ("1", "Linear falloff", "", 1),
                              ("2", "Constant falloff", "", 2),
                              ), 
                              default='0',
                              update=update_mat)     

#---Use random for color on gradients or lights in grid.
    random_color = FloatProperty(
                           name="",
                           description="Use random for color on gradients or lights in grid.",
                           min=0, max=1000.0,
                           default=0,
                           precision=2,
                           subtype='NONE',
                           unit='NONE',
                           update=update_mat)

#---Invert the direction of raycast 
    invert_ray = BoolProperty(name="Invert Direction",
                            description="Invert the direction.",
                            default=False)

#---Use random for strength on duplicate lights
    random_energy = BoolProperty(name="Use random",
                            description="Use random for strength on duplicate lights.",
                            default=False,
                            update=update_mat)

#---Apply different shape of texture gradient.          
    typgradient = EnumProperty(name="Gradient ", 
                               description="Apply different shapes of texture gradient.\n"+\
                               "NONE : Only if the gradient is used for random.\n"+
                               "LINEAR : Gradient apply from left to right.\n"+
                               "QUADRATIC : Gradient apply following the shape of the object.\n"+
                               "EASING : Gradient apply following the shape of the object as QUADRATIC but much faster.\n"+
                               "DIAGONAL : Gradient apply from top-left to bottom-right in diagonal, following the overall shape.\n"+
                               "SPHERICAL : Gradient apply in a spherical shape.\n"+
                               "QUADRATIC_SPHERE : Gradient apply in a spherical shape smoother than SPHERICAL.\n"+
                               "RADIAL : Gradient apply in a radial shape (360°) counterclockwise.\nSelected",
                               items=(
                               ("NONE", "None", "", 0),
                               ("LINEAR", "Linear", "", 1),
                               ("QUADRATIC", "Quad", "", 2),
                               ("EASING", "Easing", "", 3),
                               ("DIAGONAL", "Diagonal", "", 4),
                               ("SPHERICAL", "Spherical", "", 5),
                               ("QUADRATIC_SPHERE", "Quad Sphere", "", 6),
                               ("RADIAL", "Radial", "", 7),
                               ), 
                               default='NONE',
                               update=update_mat)  

#---Interpolation for the color stops of the gradient
    gradinterpo = EnumProperty(name="", 
                               description="Interpolation for the color stops of the gradient.",
                               items=(
                               ("EASE", "Ease", "", 1),
                               ("CARDINAL", "Cardinal", "", 2),
                               ("LINEAR", "Linear", "", 3),
                               ("B_SPLINE", "B-Spline", "", 4),
                               ("CONSTANT", "Constant", "", 5),
                                ),
                               default='LINEAR',
                               update=update_mat)

#---Expand the options panels   
    options_expand = BoolProperty(name="Show/Hide options",
                                  description="Expand the options panels.",
                                  default=False)

#---List of panels options 
    options_type = EnumProperty(name="", 
                                description="List of panels options.\nSelected",
                                items=(
                                ("Options", "Options", "", 0),
                                ("Material", "Material", "", 1),
                                ("Transform", "Transform", "", 2),
                                ), 
                                default="Options")  

#---List of texture options
    texture_type = EnumProperty(name="", 
                                description="List of texture options.\nSelected",
                                items=items_texture_type,
                                update=update_mat)                                                             

#---Smooth the edges of the panel. 1 = round
    softbox_smooth = FloatProperty(
                                name="Round",
                                description="Smooth the edges of the panel.\n0 = Square\n1 = Round",
                                min=0, max=1.0,
                                default=0.25,
                                precision=2,
                                subtype='NONE',
                                unit='NONE',
                                update=update_softbox_smooth) 

#---Number of row for the grid
    nbrow = IntProperty(name="Nbr Row",
                        description="Number of row for the grid.",
                        min=1, max=9999,
                        default=1,
                        update=create_lamp_grid) 

#---Number of column for the grid
    nbcol = IntProperty(
                        name="Nbr Column",
                        description="Number of column for the grid.",
                        min=1, max=9999,
                        default=1,
                        update=create_lamp_grid)                            

#---Gap between rows in the grid 
    gapx = FloatProperty(
                         name="Gap Row",
                         description="Gap between rows in the grid.",
                         min=0, max=9999,
                         default=1,
                         precision=3,
                         subtype='DISTANCE',
                         unit='LENGTH',
                         step=0.1,                         
                         update=create_lamp_grid) 

#---Gap between columns in the grid
    gapy = FloatProperty(
                         name="Gap Column",
                         description="Gap between columns in the grid.",
                         min=0, max=9999,
                         default=1,
                         precision=3,
                         subtype='DISTANCE',
                         unit='LENGTH',
                         step=0.1,                         
                         update=create_lamp_grid)                                                                              

#---Keep the aspect ratio when scaling or when changing the distance
    ratio = BoolProperty(
                         name="Keep ratio",
                         description="Keep the aspect ratio when scaling or when changing the distance.",
                         default=False)

#---Name of the environment image texture
    hdri_name = StringProperty(
                               name="HDRI", 
                               description="Name of the environment image texture.",
                               update=update_mat)

#---Rotation of the environment image on X axis.
    hdri_rotation = FloatProperty(
                                  name="HDRI Rotation",
                                  description="Rotation of the environment image on X axis.",
                                  min= -360, max= 360,
                                  default=0,
                                  update=update_rotation_hdri)  

#---Rotation of the environment image on Y axis.
    hdri_rotationy = FloatProperty(
                                  name="HDRI Rotation",
                                  description="Rotation of the environment image on Y axis.",
                                  min= -360, max= 360,
                                  default=0,
                                  update=update_rotation_hdri)

#---Rotation on X axis computed from the selected pixel of the image texture
    hdri_pix_rot = FloatProperty(
                                 name="Target pixel for rotation on X axis",
                                 description="Rotation computed from the selected pixel of the image texture.",
                                 min= -360, max= 360,
                                 default=0) 

#---Rotation on Y axis computed from the selected pixel of the image texture
    hdri_pix_roty = FloatProperty(
                                 name="Target pixel for rotation on Y axis",
                                 description="Rotation on Y axis computed from the selected pixel of the image texture.",
                                 min= -360, max= 360,
                                 default=0)

#---Expand the environment image options.   
    hdri_expand = BoolProperty(
                               name="Environment image options",
                               description="Expand the environment image options",
                               default=False)

#---Use the environment image texture as background and/or reflection
    hdri_background = BoolProperty(
                             description="Use the environment image texture as background / reflection\n"+
                             "Disable this if you want to use another image / color background as background and/or reflection.",
                             default=True,
                             update=update_mat) 

#---Use the image background for reflection
    back_reflect = BoolProperty(
                             description="Use the image background for reflection.",
                             default=False,
                             update=update_mat)

#---Lock the rotation of the reflection map and use the rotation of the HDRI.
    rotation_lock_hdri = BoolProperty(
                                      description="Lock the rotation of the reflection map.\n"+
                                      "The reflection map will rotate accordingly to the rotation of the environment map.",
                                      default=False,
                                      update=update_rotation_hdri_lock)

#---Lock the rotation of the HDRI map and use the rotation of the reflection map.
    rotation_lock_img = BoolProperty(
                                     description="Lock the rotation of the environment map.\n"+
                                     "The environment map will rotate accordingly to the rotation of the reflection map.",
                                     default=False,
                                     update=update_rotation_img_lock)

#---Reset the modifications of the image modifications.
    hdri_reset = BoolProperty(
                              name="Reset",
                              description="Reset the modifications of the environment image modifications.",
                              default=False,
                              update=reset_options)

#---Brightness of the environment image.
    hdri_bright = FloatProperty(
                                name="Bright",
                                description="Increase the overall brightness of the image.",
                                min=-10, max=10.0,
                                default=0,
                                precision=2,
                                update=update_mat)                      

#---Contrast of the environment image.
    hdri_contrast = FloatProperty(
                                  name="Contrast",
                                  description="Make brighter pixels brighter, but keeping the darker pixels dark.",
                                  min=-10, max=10.0,
                                  default=0,
                                  precision=2,
                                  subtype='NONE',
                                  unit='NONE',
                                  update=update_mat) 

#---Gamma of the environment image.
    hdri_gamma = FloatProperty(
                               name="Gamma",
                               description="Apply an exponential brightness factor to the image.",
                               min=0, max=10.0,
                               default=1,
                               precision=2,
                               subtype='NONE',
                               unit='NONE',
                               update=update_mat) 

#---Hue of the environment image.
    hdri_hue = FloatProperty(
                             name="Hue",
                             description="Specifies the hue rotation of the image from 0 to 1.",
                             min=0, max=1.0,
                             default=0.5,
                             precision=2,
                             subtype='NONE',
                             unit='NONE',
                             update=update_mat) 

#---Saturation of the environment image.
    hdri_saturation = FloatProperty(
                                    name="Saturation",
                                    description="A saturation of 0 removes hues from the image, resulting in a grayscale image.\n"+\
                                    "A shift greater 1.0 increases saturation.",
                                    min=0, max=2.0,
                                    default=1,
                                    precision=2,
                                    subtype='NONE',
                                    unit='NONE',
                                    update=update_mat) 

#---Value of the environment image.
    hdri_value = FloatProperty(
                               name="Value",
                               description="Value is the overall brightness of the image.\n"+\
                               "De/Increasing values shift an image darker/lighter.",
                               min=0, max=2.0,
                               default=1,
                               precision=2,
                               subtype='NONE',
                               unit='NONE',
                               update=update_mat) 

#---Name of the background image texture
    img_name = StringProperty(
                              name="Name of the background / reflection image texture",
                              update=update_mat)

#---Background rotation on X axis
    img_rotation = FloatProperty(
                                 name="Reflection Rotation",
                                 description="Reflection Rotation",
                                 min= -360, max= 360,
                                 default=0,
                                 update=update_rotation_img)

#---Rotation on X axis computed from the selected pixel of the image texture
    img_pix_rot = FloatProperty(
                                 name="Background brightest pixel Rotation",
                                 description="Rotation computed from the selected pixel of the image texture.",
                                 min= -360, max= 360,
                                 default=0) 

#---Expand the background image options.                             
    img_expand = BoolProperty(
                              name="options",
                              description="Expand the background image options.",
                              default=False)

#---Reset the modifications of the image modifications.
    img_reset = BoolProperty(
                             name="Reset",
                             description="Reset the modifications of the background image modifications.",
                             default=False,
                             update=reset_options)

#---Brightness of the background image. 
    img_bright = FloatProperty(
                               name="Bright",
                               description="Increase the overall brightness of the image.",
                               min=-10, max=10.0,
                               default=0,
                               precision=2,
                               update=update_mat)                       

#---Contrast of the background image.
    img_contrast = FloatProperty(
                                 name="Contrast",
                                 description="Make brighter pixels brighter, but keeping the darker pixels dark.",
                                 min=-10, max=10.0,
                                 default=0,
                                 precision=2,
                                 subtype='NONE',
                                 unit='NONE',
                                 update=update_mat) 

#---Gamma of the background image.
    img_gamma = FloatProperty(
                              name="Gamma",
                              description="Apply an exponential brightness factor to the image.",
                              min=0, max=10.0,
                              default=1,
                              precision=2,
                              subtype='NONE',
                              unit='NONE',
                              update=update_mat) 

#---Hue of the background image.
    img_hue = FloatProperty(
                            name="Hue",
                            description="Specifies the hue rotation of the image from 0 to 1.",
                            min=0, max=1.0,
                            default=0.5,
                            precision=2,
                            subtype='NONE',
                            unit='NONE',
                            update=update_mat) 

#---Saturation of the background image.
    img_saturation = FloatProperty(
                                   name="Saturation",
                                   description="A saturation of 0 removes hues from the image, resulting in a grayscale image.\n"+\
                                   "A shift greater 1.0 increases saturation.",
                                   min=0, max=2.0,
                                   default=1,
                                   precision=2,
                                   subtype='NONE',
                                   unit='NONE',
                                   update=update_mat) 

#---Value of the background image.
    img_value = FloatProperty(
                              name="Value",
                              description="Value is the overall brightness of the image.\n"+\
                              "Increasing values shift an image darker/lighter.",
                              min=0, max=2.0,
                              default=1,
                              precision=2,
                              subtype='NONE',
                              unit='NONE',
                              update=update_mat)  

#---Lock the rotation the light on vertical or horizontal axis.
    lock_light = EnumProperty(name="Lock rotation", 
                              description="Lock the rotation the light on vertical or horizontal axis.",
                              items=(
                              ("None", "None", "", 0),
                              ("Vertical", "Vertical", "", 1),
                              ("Horizontal", "Horizontal", "", 2),
                              ), 
                              default="None") 

#---Rotate the texture on 90°
    rotate_ninety = BoolProperty(default=False, 
                                description="Rotate the texture on 90°.",
                                update=update_mat) 

#---Change the light to a reflector (no emission)
    reflector = BoolProperty(name = "Reflector",
                             description="Change the light to a reflector (no emission).\n"+\
                             "Useful for bouncing light in shadow areas.",
                             default=False, 
                             update=update_mat)

#---Expand all the options for this light
    expanded = BoolProperty(name="",
                            description="Expand all the options for this light.",
                            default=False)

#---Show / Hide this light                      
    show = BoolProperty(name="",
                        description="Show / Hide this light.",
                        default=True, 
                        update=show_hide_light) 

#---Show only this light and hide all the others.           
    select_only = BoolProperty(name="",
                               description="Show only this light and hide all the others.",
                               default=False, 
                               update=select_only)  

#---Create a softbox in front off the light.
    projector = BoolProperty(name="",
                             description="Create a projector / softbox in front off the light.\n"+\
                             "Can be useful to softer the light or project texture effect.",
                             default=False,
                             update=add_remove_projector)

#---Expand all the options for this projector.
    projector_expand = BoolProperty(
                                 name="Show/Hide options",
                                 description="Expand all the options for this projector.",
                                 default=False)

#---Scale the projector on the X axis.
    projector_scale_x = FloatProperty(
                                 name="Scale X",
                                 description="Scale the projector on X axis.",
                                 min=0, max=1000.0,
                                 soft_min=0.0, soft_max=1000.0,
                                 default=1,
                                 precision=2,
                                 step=1,    
                                 subtype='DISTANCE',
                                 unit='LENGTH',
                                 update=update_projector_scale) 

#---Scale the projector on the Y axis.
    projector_scale_y = FloatProperty(
                                 name="Scale Y",
                                 description="Scale the projector on Y axis",
                                 min=0, max=1000.0,
                                 soft_min=0.0, soft_max=1000.0,
                                 default=1,
                                 precision=2,
                                 step=1,    
                                 subtype='DISTANCE',
                                 unit='LENGTH',
                                 update=update_projector_scale)

#---Taper the tip of the projector.
    projector_taper = FloatProperty(
                                 name="Taper",
                                 description="Taper the tip of the projector",
                                 min=0, max=1000.0,
                                 soft_min=0.0, soft_max=10.0,
                                 default=1,
                                 precision=2,
                                 step=1,    
                                 subtype='DISTANCE',
                                 unit='LENGTH',
                                 update=update_projector_taper)

#---Distance between the light and the projector.
    projector_range = FloatProperty(
                                 name="Range ",
                                 description="Distance between the light and the projector",
                                 min=0, max=1000,
                                 soft_min=0.0, soft_max=100.0,
                                 default=0.2,
                                 precision=2,
                                 step=1,    
                                 subtype='DISTANCE',
                                 unit='LENGTH',
                                 update=update_projector)

#---Name of the texture image to project.
    projector_img_name = StringProperty(name="Projector texture",
                                        description="Name of the texture image to project.",
                                        update=update_projector_mat)
    

#---Expand all the options for the image texture.
    projector_img_expand = BoolProperty(
                                     name="options",
                                     description="Expand all the options for the image texture.",
                                     default=False)

#---Initialize the options for the image texture to default.
    projector_img_reset = BoolProperty(
                                    name="Reset",
                                    description="Initialize the options for the image texture to default.",
                                    default=False,
                                    update=reset_options)   

#---Close the projector / Softbox.
    projector_close = BoolProperty(
                                    name="Close",
                                    description="Close the projector / Softbox.\n"+\
                                    "Can be useful to constraint the light.",
                                    default=False,
                                    update=update_close_projector)

#---Brightness of the image texture.
    projector_img_bright = FloatProperty(
                                      name="Brightness",
                                      description="Increase the overall brightness of the image.",
                                      min=-10, max=10.0,
                                      default=0,
                                      precision=2,
                                      update=update_projector_mat)                      

#---Contrast of the image texture. 
    projector_img_contrast = FloatProperty(
                                        name="Contrast",
                                        description="Make brighter pixels brighter, but keeping the darker pixels dark.",
                                        min=-10, max=10.0,
                                        default=0,
                                        precision=2,
                                        subtype='NONE',
                                        unit='NONE',
                                        update=update_projector_mat) 

#---Gamma of the image texture.
    projector_img_gamma = FloatProperty(
                                     name="Gamma",
                                     description="Apply an exponential brightness factor to the image.",
                                     min=0, max=10.0,
                                     default=1,
                                     precision=2,
                                     subtype='NONE',
                                     unit='NONE',
                                     update=update_projector_mat) 

#---Saturation of the image texture.
    projector_img_saturation = FloatProperty(
                                          name="Saturation",
                                          description="A saturation of 0 removes hues from the image, resulting in a grayscale image.\n"+\
                                          "A shift greater 1.0 increases saturation.",
                                          min=0, max=1.0,
                                          default=0,
                                          precision=2,
                                          subtype='NONE',
                                          unit='NONE',
                                          update=update_projector_mat) 

#---Invert colors of the image texture.
    projector_img_invert = FloatProperty(
                                      name="Invert",
                                      description="Invert the colors in the texture image, producing a negative.",
                                      min=0, max=1.0,
                                      default=0,
                                      precision=2,
                                      subtype='NONE',
                                      unit='NONE',
                                      update=update_projector_mat)              

#---Smooth the edges of the projector / softbox. 1 = round                          
    projector_smooth = FloatProperty(
                                name="Round",
                                description="Smooth the edges of the projector / softbox.\n0 = Square\n1 = Round",
                                min=0, max=1.0,
                                default=0.25,
                                precision=2,
                                subtype='NONE',
                                unit='NONE',
                                update=update_projector_smooth) 

#---List of the options for the projector texture.
    projector_options = EnumProperty(
                                    name="", 
                                    description="List of the options for the projector texture.", 
                                    items=(
                                    ("Color", "Color", "", 0),
                                    ("Texture", "Texture", "", 1),
                                    ("Gradient", "Gradient", "", 2),
                                    ), 
                                    update=update_projector_mat)            

#---List of the options for the projector texture.
    projector_typgradient = EnumProperty(
                                       name="Gradient ", 
                                       description="Apply different shapes of texture gradient.\n"+\
                                       "LINEAR : Gradient apply from left to right.\n"+
                                       "QUADRATIC : Gradient apply following the shape of the object.\n"+
                                       "EASING : Gradient apply following the shape of the object as QUADRATIC but much faster.\n"+
                                       "DIAGONAL : Gradient apply from top-left to bottom-right in diagonal, following the overall shape.\n"+
                                       "SPHERICAL : Gradient apply in a spherical shape.\n"+
                                       "QUADRATIC_SPHERE : Gradient apply in a spherical shape smoother than SPHERICAL.\n"+
                                       "RADIAL : Gradient apply in a radial shape (360°) counterclockwise.",
                                       items=(
                                       ("LINEAR", "Linear", "", 0),
                                       ("QUADRATIC", "Quad", "", 1),
                                       ("EASING", "Easing", "", 2),
                                       ("DIAGONAL", "Diagonal", "", 3),
                                       ("SPHERICAL", "Spherical", "", 4),
                                       ("QUADRATIC_SPHERE", "Quad Sphere", "", 5),
                                       ("RADIAL", "Radial", "", 6),
                                       ), 
                                       update=update_projector_mat)                 
    
#########################################################################################################

#########################################################################################################

"""
#########################################################################################################
# ENVIRONMENT MAP
#########################################################################################################
"""
class LumiereEnvPreferences(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_idname = "view3d.lumiere"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Lumiere"
    bl_label = "Lumiere"
    bl_context = "objectmode"

    @classmethod
    def poll(cls, context):
        return False
    
    @classmethod
    def poll_embedded(cls, context):
        return context.object.data.name.startswith("Lumiere")

    def draw(self, context):
        layout = self.layout
        cobj = self.cobj

        if cobj.Lumiere.items_light_type == "Env":
        #---Options 
            if cobj.Lumiere.options_type == "Options" :
                box = self.col.box()
                col = box.column(align=True)
                row = col.row(align=True)
            #---New type light
                col = box.column(align=True)                
                row = col.row(align=True)
                row.label(text="Change to :")
                row.prop(cobj.Lumiere, "newtyplight", text="")                                      
                row = box.row(align=True)
                row.prop(context.space_data, "show_world", text="Show world", toggle=True)
                col = box.column(align=True)
                row = col.row(align=True)
        
            #---Export
                row = col.row(align=True)
                op = row.operator("object.export_light", text ='Export', icon='BLANK1')
                op.act_light = cobj.name 
                
        #---Material
            elif cobj.Lumiere.options_type == "Material":
                box = self.col.box()
                col = box.column(align=True)
                row = col.row(align=True)                           
            #---HDRI Texture
                row.label(text="Environment: ")
                if cobj.Lumiere.hdri_name != "":
                    row = col.row(align=True)
                    op = row.operator("object.select_pixel", text ='Align to Pixel', icon='EYEDROPPER')
                    op.act_light = cobj.name 
                    op.img_name = cobj.Lumiere.hdri_name
                    op.img_type = "HDRI"
                    op.img_size_x = bpy.data.images[cobj.Lumiere.hdri_name].size[0]
                    op.img_size_y = bpy.data.images[cobj.Lumiere.hdri_name].size[1]
                    
                    col = box.column()
                    col = box.column(align=True)
                    
                row = col.row(align=True)
                row.prop_search(cobj.Lumiere, "hdri_name", bpy.data, "images", text='', icon='NONE')
                row.operator("image.open",text='', icon='IMASEL')
                row = col.row(align=True)
                
            #---HDRI color
                if cobj.Lumiere.hdri_name == "":
                    hdri_col = bpy.data.worlds['Lumiere_world'].node_tree.nodes['Background'].inputs[0] 
                    row.prop(hdri_col, "default_value", text="")
                else:
                #---HDRI Rotation
                    if cobj.Lumiere.rotation_lock_img and cobj.Lumiere.img_name != "":
                        row.enabled = False
                    else:
                        row.enabled = True
                        
                    row.prop(cobj.Lumiere, "hdri_rotation", text="Rotation", slider = True)

                    if cobj.Lumiere.img_name != "" and not cobj.Lumiere.hdri_background:
                        row.prop(cobj.Lumiere, "rotation_lock_hdri", text="", icon="%s" % "LOCKED" if cobj.Lumiere.rotation_lock_hdri else "UNLOCKED")
                    
                    row = col.row(align=True)
                
                #---HDRI options
                    row.label(text="Texture options:")
                    row.prop(cobj.Lumiere, "hdri_expand", text="")
                            
                    if cobj.Lumiere.hdri_expand:
                        #---Brightness
                            col = box.column(align=True)
                            row = col.row(align=True)
                            row.prop(cobj.Lumiere, "hdri_bright", text="Bright")
                        #---Contrast
                            row.prop(cobj.Lumiere, "hdri_contrast", text="Contrast")
                        #---Gamma
                            row = col.row(align=True)
                            row.prop(cobj.Lumiere, "hdri_gamma", text="Gamma")  
                        #---Hue
                            row.prop(cobj.Lumiere, "hdri_hue", text="Hue")  
                        #---Saturation
                            row = col.row(align=True)
                            row.prop(cobj.Lumiere, "hdri_saturation", text="Saturation")            
                        #---Value
                            row.prop(cobj.Lumiere, "hdri_value", text="Value")
                        #---Mirror / Equirectangular
                            row = col.row(align=True)
                            hdri_img = bpy.data.worlds['Lumiere_world'].node_tree.nodes['Environment Texture']
                            row.prop(hdri_img, "projection", text="")
                        #---Reset values
                            row = col.row(align=True)
                            row.prop(cobj.Lumiere, "hdri_reset", text="Reset options", toggle=True)
            #---Hdri for background
                row = col.row(align=True)
                row.prop(cobj.Lumiere, "hdri_background", text='Hdri for background', toggle=True)

            #---Background Texture
                if not cobj.Lumiere.hdri_background:
                    col = box.column(align=True)
                    row = col.row(align=True)
                    row.label(text="Background:")
                    if cobj.Lumiere.img_name != "":
                        row = col.row(align=True)
                        op = row.operator("object.select_pixel", text ='Align to Pixel', icon='EYEDROPPER')
                        op.act_light = cobj.name 
                        op.img_name = cobj.Lumiere.img_name
                        op.img_type = "IMG"
                        op.img_size_x = bpy.data.images[cobj.Lumiere.img_name].size[0]
                        op.img_size_y = bpy.data.images[cobj.Lumiere.img_name].size[1]
                        col = box.column()
                        col = box.column(align=True)
                    
                    row = col.row(align=True)
                    
                    row.prop_search(cobj.Lumiere, "img_name", bpy.data, "images", text="")
                    row.operator("image.open",text='', icon='IMASEL')
                    row = col.row(align=True)
                    
                #---Background color
                    if cobj.Lumiere.img_name == "":
                        back_col = bpy.data.worlds['Lumiere_world'].node_tree.nodes['Background.001'].inputs[0] 
                        row.prop(back_col, "default_value", text="")    

                    else:
                    #---Background Rotation
                        if cobj.Lumiere.rotation_lock_hdri and cobj.Lumiere.hdri_name != "":
                            row.enabled = False
                        else:
                            row.enabled = True                          
                        
                        row.prop(cobj.Lumiere, "img_rotation", text="Rotation", slider = True)
                        if cobj.Lumiere.hdri_name != "": 
                            row.prop(cobj.Lumiere, "rotation_lock_img", text="", icon="%s" % "LOCKED" if cobj.Lumiere.rotation_lock_img else "UNLOCKED")
                    
                        row = col.row(align=True)
                    #---Background options
                        row.label(text="Texture options:")
                        row.prop(cobj.Lumiere, "img_expand", text="")
                        
                        if cobj.Lumiere.img_expand:
                        #---Brightness
                            col = box.column(align=True)
                            row = col.row(align=True)
                            row.prop(cobj.Lumiere, "img_bright", text="Bright")
                        #---Contrast
                            row.prop(cobj.Lumiere, "img_contrast", text="Contrast")
                        #---Gamma
                            row = col.row(align=True)
                            row.prop(cobj.Lumiere, "img_gamma", text="Gamma")   
                        #---Hue
                            row.prop(cobj.Lumiere, "img_hue", text="Hue")   
                        #---Saturation
                            row = col.row(align=True)
                            row.prop(cobj.Lumiere, "img_saturation", text="Saturation")                             
                        #---Value
                            row.prop(cobj.Lumiere, "img_value", text="Value")
                        #---Blur
                            row = col.row(align=True)
                            reflection_blur = bpy.data.worlds['Lumiere_world'].node_tree.nodes['Mix.001'].inputs[0] 
                            row.prop(reflection_blur, "default_value", text="Blur", slider = True)
                        #---Mirror / Equirectangular
                            row = col.row(align=True)
                            back_img = bpy.data.worlds['Lumiere_world'].node_tree.nodes['Environment Texture.001']
                            row.prop(back_img, "projection", text="")
                        #---Reset values
                            row = col.row(align=True)
                            row.prop(cobj.Lumiere, "img_reset", text="Reset options", toggle=True)
                
                #---Background for reflection
                    row = col.row(align=True)
                    row.prop(cobj.Lumiere, "back_reflect", text='Background for reflection', toggle=True)

            elif cobj.Lumiere.options_type == "Transform":
                box = self.col.box()
                col = box.column(align=True)
                row = col.row(align=True)
                row.label(text="Change to :")
                row.prop(cobj.Lumiere, "newtyplight", text="")  
        else:
            self.lamp = cobj.children[0]
            LumiereLampForEnvPreferences.draw(self, context)
"""
#########################################################################################################
# SUN FOR ENVIRONMENT
#########################################################################################################
"""
class LumiereLampForEnvPreferences(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_idname = "view3d.lumiere"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Lumiere"
    bl_label = "Lumiere"
    bl_context = "objectmode"

    @classmethod
    def poll(cls, context):
        return False
    
    @classmethod
    def poll_embedded(cls, context):
        return context.object.data.name.startswith("Lumiere")

    def draw(self, context):
        layout = self.layout
        cobj = self.cobj
        lamp = self.lamp

        if cobj.Lumiere.options_type == "Options":
            box = self.col.box()
            col = box.column(align=True)                
            row = col.row(align=True)

            row.prop(lamp.data.cycles, "use_multiple_importance_sampling", text='MIS', toggle=True)
            row.prop(lamp.data.cycles, "cast_shadow", text='Shadow', toggle=True)
            row.prop(lamp.cycles_visibility, "diffuse", text='Diff', toggle=True)
            row.prop(lamp.cycles_visibility, "glossy", text='Spec', toggle=True)
        
    #---Material
        elif cobj.Lumiere.options_type == "Material":
        #---New box
            box = self.col.box()
            col = box.column()
            row = col.row()

        #---Lamps color option
            emit = lamp.data.node_tree.nodes["Emission"]
            row.label(text="Color :")
            row.prop(emit.inputs[0], "default_value", text="")
            row = col.row()
            row.label(text="Strength :")
            row.prop(emit.inputs[1], "default_value", text="")
            
        #---Scale               
            row = col.row()
            row.label(text="Shadow :")
            row.prop(lamp.data, "shadow_soft_size", text="")
    
        elif cobj.Lumiere.options_type == "Transform":
            box = self.col.box()
            
        #---Range
            col = box.column(align=True)                
            row = col.row(align=True)
            op = row.operator("object.edit_light", text="Range", icon='NONE')
            op.act_light = cobj.name 
            op.from_panel = True
            op.dist_light = True

"""
#########################################################################################################
# PROJECTOR
#########################################################################################################
"""
class LumiereProjectorPreferences(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_idname = "view3d.lumiere"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Lumiere"
    bl_label = "Lumiere"
    bl_context = "objectmode"

    @classmethod
    def poll(cls, context):
        return False
    
    @classmethod
    def poll_embedded(cls, context):
        return context.object.data.name.startswith("Lumiere")

    def draw(self, context):
        layout = self.layout
        cobj = self.cobj
        lamp = self.lamp
        row = self.row
    
        row.label(text="Add Projector: " if not cobj.Lumiere.projector else "Remove Projector: " )
        row.prop(cobj.Lumiere, "projector", icon ="ZOOMIN" if not cobj.Lumiere.projector else "X", text='', icon_only=True, emboss=False)

        if cobj.Lumiere.projector :
            box = self.col.box()
            col = box.column(align=True)                
            row = col.row(align=True)
            
        #---Get the name of the projector
            projector = bpy.data.objects["PROJECTOR_" + cobj.data.name]

        #---Options 
            if cobj.Lumiere.options_type == "Options":
                row.prop(cobj.Lumiere, "projector_smooth") 
                row = col.row(align=True)
                row.prop(projector.modifiers["Bevel"], "segments", text="Segments")
                row = col.row(align=True)               
                row.prop(projector.cycles_visibility, "diffuse", text='Diff', toggle=True)
                row.prop(projector.cycles_visibility, "glossy", text='Spec', toggle=True)

        #---Transform 
            if cobj.Lumiere.options_type == "Transform":

            #---Close projector 
                row.label(text="Close projector: ")
                row.prop(cobj.Lumiere, "projector_close", text="") 
                col = box.column(align=True)
            #---Scale
                row = col.row(align=True)
                row.prop(cobj.Lumiere, "projector_scale_x", text="Scale X")
                row = col.row(align=True)   
                row.prop(cobj.Lumiere, "projector_scale_y", text="Scale Y")
                
            #---Range
                col = box.column(align=True)
                row = col.row(align=True)   
                row.prop(cobj.Lumiere, "projector_range")
                row = col.row(align=True)   
                row.prop(cobj.Lumiere, "projector_taper")                   
        #---Materials
            elif cobj.Lumiere.options_type == "Material":
                row.prop(cobj.Lumiere, "projector_options", text=" ", expand=True)
                col = box.column()
                row = col.row(align=True)
                
            #---Color material
                if cobj.Lumiere.projector_options == "Color":
                    color = projector.data.materials['Mat_PROJECTOR_' + cobj.data.name].node_tree.nodes['Transparent BSDF.001'].inputs['Color']
                    col.prop(color, "default_value", text="")
                
            #---Texture file material
                elif cobj.Lumiere.projector_options == "Texture":
                    row.prop_search(cobj.Lumiere, "projector_img_name", bpy.data, "images", text="")
                    row.operator("image.open",text='', icon='IMASEL')
                    row = col.row(align=True)                               
                    if cobj.Lumiere.projector_img_name != "":
                        row.label(text="Texture options:")
                        row.prop(cobj.Lumiere, "projector_img_expand", text="")
                        if cobj.Lumiere.projector_img_expand:
                            col = box.column(align=True)
                            row = col.row(align=True)
                            row.prop(cobj.Lumiere, "projector_img_saturation") 
                            row = col.row(align=True)
                            row.prop(cobj.Lumiere, "projector_img_gamma")
                            row.prop(cobj.Lumiere, "projector_img_bright") 
                            row = col.row(align=True)
                            pattern_group = bpy.data.node_groups.get('Repeat_Texture')
                            repeat_u = projector.data.materials['Mat_PROJECTOR_' + cobj.data.name].node_tree.nodes[pattern_group.name].inputs[1] 
                            repeat_v = projector.data.materials['Mat_PROJECTOR_' + cobj.data.name].node_tree.nodes[pattern_group.name].inputs[2] 
                            row.prop(repeat_u, "default_value", text="Repeat U")                                                
                            row.prop(cobj.Lumiere, "projector_img_contrast")                            
                            row = col.row(align=True)
                            row.prop(repeat_v, "default_value", text="Repeat V")                                                
                            row.prop(cobj.Lumiere, "projector_img_invert")
                            row = col.row(align=True)
                            row.prop(cobj.Lumiere, "projector_img_reset", text="Reset options", toggle=True)
            
            #---Gradient material
                elif cobj.Lumiere.projector_options == "Gradient":
                    pattern_group = bpy.data.node_groups.get('Repeat_Gradient')
                    repeat_u = projector.data.materials['Mat_PROJECTOR_' + cobj.data.name].node_tree.nodes[pattern_group.name].inputs[1] 
                    repeat_v = projector.data.materials['Mat_PROJECTOR_' + cobj.data.name].node_tree.nodes[pattern_group.name].inputs[2] 
                    row.prop(cobj.Lumiere, "projector_typgradient", text="")
                    row.prop(repeat_u, "default_value", text="Repeat U")                                                
                
                    colramp = projector.data.materials['Mat_PROJECTOR_' + cobj.data.name].node_tree.nodes['ColorRamp']                          
                    col.template_color_ramp(colramp, "color_ramp", expand=False)

        
            
"""
#########################################################################################################
# LAMPS
#########################################################################################################
"""
class LumiereLampPreferences(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_idname = "view3d.lumiere"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Lumiere"
    bl_label = "Lumiere"
    bl_context = "objectmode"

    @classmethod
    def poll(cls, context):
        return False
    
    @classmethod
    def poll_embedded(cls, context):
        return context.object.data.name.startswith("Lumiere")

    def draw(self, context):
        layout = self.layout
        cobj = self.cobj
        lamp = self.lamp
        
        if cobj.Lumiere.options_type == "Options":
            box = self.col.box()
            col = box.column(align=True)                
            row = col.row(align=True)
            
        #---Target object search list
            row.prop_search(cobj.Lumiere, "objtarget", bpy.data, "objects")
            op = row.operator("object.select_target", text ='', icon='EYEDROPPER')
            op.act_light = cobj.name 

            col = box.column(align=True)
            row = col.row(align=True)

            #---Reflection from the Normal or View
            row.label(text="Reflection: ")
            row.prop(cobj.Lumiere, "reflect_angle", text="") 
            
            col = box.column(align=True)
            row = col.row(align=True)
            
            #---Invert the ray 
            row.label(text="Invert: ")
            row.prop(cobj.Lumiere, "invert_ray", text="")                                           
            row = col.row(align=True)           
            
            col = box.column(align=True)
            row = col.row(align=True)

            #---Falloff
            split = row.split(0.6, align=True)
            split.prop(cobj.Lumiere, "typfalloff") 
                
            #---Smooth
            smooth = lamp.data.node_tree.nodes["Light Falloff"].inputs[1]
            split.prop(smooth, "default_value", text="Smooth")
            col = box.column(align=True)
            row = col.row(align=True)
            row.prop(lamp.data.cycles, "use_multiple_importance_sampling", text='MIS', toggle=True)
            row.prop(lamp.data.cycles, "cast_shadow", text='Shadow', toggle=True)
            row.prop(lamp.cycles_visibility, "diffuse", text='Diff', toggle=True)
            row.prop(lamp.cycles_visibility, "glossy", text='Spec', toggle=True)
            row = col.row(align=True)
                    
    #---Material
        elif cobj.Lumiere.options_type == "Material":
        #---New box
            box = self.col.box()
            col = box.column(align=True)
            row = col.row(align=True)
            
            if cobj.Lumiere.typlight in ("Area"):
                row.prop(cobj.Lumiere, "texture_type", text=" ", expand=True)
            
            #---Gradient
                if cobj.Lumiere.texture_type == "Gradient":
                    
                    colramp = lamp.data.node_tree.nodes['ColorRamp']

                #---Color ramp template
                    col.template_color_ramp(colramp, "color_ramp", expand=False)
                    col = box.column()
                    row = col.row(align=True)

                #---Add Random 
                    row.prop(cobj.Lumiere, "random_energy", text="Add random")                                          
                    row = col.row(align=True)
                    
                #---Random colors
                    if cobj.Lumiere.random_energy:
                        row.prop(cobj.Lumiere, "random_color", text="Random")
                                                                
            #---Color
                elif cobj.Lumiere.texture_type == "Color" :
                    col = box.column(align=True)
                    row = col.row(align=True)
                    row.prop(cobj.Lumiere, "lightcolor")
                        
                            
        #---Lamps color option
            else:
                row.prop(cobj.Lumiere, "lightcolor")

        elif cobj.Lumiere.options_type == "Transform":
            box = self.col.box()
            
            if cobj.Lumiere.typlight != "Sky":
                col = box.column(align=True)
                row = col.row(align=True)
                row.label(text="Change to :")
                row.prop(cobj.Lumiere, "newtyplight", text="")  
            
        #---Range
            col = box.column(align=True)                
            row = col.row(align=True)
            op = row.operator("object.edit_light", text="Range", icon='NONE')
            op.act_light = cobj.name 
            op.from_panel = True
            op.dist_light = True

        #-----------------------------------#
        #GRID
        #-----------------------------------#
            if cobj.Lumiere.typlight != "Sky":
                col = box.column(align=True)                
                row = col.row(align=True)
                
            #---Row
                row.prop(cobj.Lumiere, "nbrow", text='Row')

            #---Gap Y
                op = row.operator("object.edit_light", text="Gap", icon='NONE')
                op.act_light = cobj.name 
                op.from_panel = True
                op.scale_gapy = True
                
            #---Column
                row = col.row(align=True)
                row.prop(cobj.Lumiere, "nbcol", text='Col')
                
            #---Gap X
                op = row.operator("object.edit_light", text="Gap", icon='NONE')
                op.act_light = cobj.name 
                op.from_panel = True
                op.scale_gapx = True

            #-----------------------------------#
            #SCALE
            #-----------------------------------#           
            if cobj.Lumiere.typlight in ("Spot", "Area") :
                split = box.split()
                col1 = split.column(align=True)
                
                row = col1.row(align=True)
                row.alignment = 'CENTER'
                row.label(text="Scale: ")
                row = col1.row(align=True)  
                
            #---Scale
                op = col1.operator("object.edit_light", text="Scale X/Y", icon='NONE')
                op.act_light = cobj.name 
                op.from_panel = True
                op.scale_light = True
            
            #---Scale X
                op = col1.operator("object.edit_light", text="Shadow size" if cobj.Lumiere.typlight == "Spot" else "Scale X", icon='NONE')
                op.act_light = cobj.name 
                op.from_panel = True
                op.scale_light_x = True

            #---Scale Y
                op = col1.operator("object.edit_light", text="Blend" if cobj.Lumiere.typlight == "Spot" else "Scale Y", icon='NONE')
                op.act_light = cobj.name 
                op.from_panel = True
                op.scale_light_y = True

            #-----------------------------------#
            #ROTATE
            #-----------------------------------#
                col2 = split.column(align=True)
                row = col2.row(align=True)
                row.alignment = 'CENTER'
                row.label(text="Rotation: ")
                row = col2.row(align=True)
                
            #---Rotate X
                op = col2.operator("object.edit_light", text="Rotate X", icon='NONE')
                op.act_light = cobj.name 
                op.from_panel = True
                op.rotate_light_x = True
                
            #---Rotate Y
                op = col2.operator("object.edit_light", text="Rotate Y", icon='NONE')
                op.act_light = cobj.name 
                op.from_panel = True
                op.rotate_light_y = True

            #---Rotate Z
                op = col2.operator("object.edit_light", text="Rotate Z", icon='NONE')
                op.act_light = cobj.name 
                op.from_panel = True
                op.rotate_light_z = True
                row = col.row(align=True)
                
            #---Lock Light
                col = box.column(align=True)                
                row = col1.row(align=True)
                row.label(text="Lock light:")
                row = col2.row(align=True)
                row.prop(cobj.Lumiere, "lock_light", text="")   
            
            else:
            #---Scale
                col = box.column(align=True)                
                row = col.row(align=True)
                op = col.operator("object.edit_light", text="Scale", icon='NONE')
                op.act_light = cobj.name 
                op.from_panel = True
                op.scale_light = True

                
"""
#########################################################################################################
# SOFTBOX
#########################################################################################################
"""
class LumiereSoftboxPreferences(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_idname = "view3d.lumiere"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Lumiere"
    bl_label = "Lumiere"
    bl_context = "objectmode"

    @classmethod
    def poll(cls, context):
        return False
    
    @classmethod
    def poll_embedded(cls, context):
        return context.object.data.name.startswith("Lumiere")

    def draw(self, context):
        layout = self.layout
        cobj = self.cobj
        softbox = self.lamp
        softbox_mat = self.softbox_mat

        if cobj.Lumiere.options_type == "Options":
            box = self.col.box()

            col = box.column(align=True)
            row = col.row(align=True)

        #---Reflection from the Normal or View
            row.label(text="Reflection: ")
            row.prop(cobj.Lumiere, "reflect_angle", text="") 
            
            col = box.column(align=True)
            row = col.row(align=True)
            
            #---Invert the ray
            row.label(text="Invert: ")
            row.prop(cobj.Lumiere, "invert_ray", text="")                                           
            row = col.row(align=True)   
            
        #---Smooth softbox  
            col = box.column(align=True)                                    
            row = col.row(align=True)                                   
            row.label(text="Roundness : ")
            row.prop(cobj.Lumiere, "softbox_smooth", text="", slider=False)
            
        #---Segments
            row = col.row(align=True)                                   
            row.label(text="Segments : ")
            row.prop(softbox.modifiers["Bevel"], "segments", text="", slider=False)
            row = col.row(align=True)                                   

        #---Target object search list
            col = box.column()              
            row = col.row(align=True)
            row.prop_search(cobj.Lumiere, "objtarget", bpy.data, "objects")
            op = row.operator("object.select_target", text ='', icon='EYEDROPPER')
            op.act_light = cobj.name 

            col = box.column(align=True)
            row = col.row(align=True)

            if not cobj.Lumiere.reflector :
            #---Falloff / Smooth
                #---Falloff
                split = row.split(0.6, align=True)
                split.prop(cobj.Lumiere, "typfalloff") 
                    
                #---Smooth
                smooth = softbox_mat.node_tree.nodes["Light Falloff"].inputs[1]
                split.prop(smooth, "default_value", text="Smooth")
                
            row = col.row(align=True)

            row.prop(softbox_mat.cycles, "sample_as_light", text='MIS', toggle=True)
            row.prop(softbox.cycles_visibility, "diffuse", text='Diff', toggle=True)
            row.prop(softbox.cycles_visibility, "glossy", text='Spec', toggle=True)
            row = col.row(align=True)
            
        elif cobj.Lumiere.options_type == "Transform":
            box = self.col.box()
            
        #---Ratio 
            col = box.column(align=True)                
            row = col.row(align=True)
            row.label(text="Keep ratio : ")
            row.prop(cobj.Lumiere, "ratio", text='')
            row = col.row(align=True)

        #---New type light
            col = box.column(align=True)                
            row = col.row(align=True)
            row.label(text="Change to :")
            row.prop(cobj.Lumiere, "newtyplight", text="")
            
        #---Range
            col = box.column(align=True)                
            row = col.row(align=True)
            op = row.operator("object.edit_light", text="Range", icon='NONE')
            op.act_light = cobj.name 
            op.from_panel = True
            op.dist_light = True
            
        #-----------------------------------#
        #GRID
        #-----------------------------------#
            col = box.column(align=True)                
            row = col.row(align=True)       
            
        #---Row
            row.prop(cobj.Lumiere, "nbrow", text='Row')

        #---Gap Y
            op = row.operator("object.edit_light", text="Gap", icon='NONE')
            op.act_light = cobj.name 
            op.from_panel = True
            op.scale_gapy = True
            
        #---Column          
            row = col.row(align=True)
            row.prop(cobj.Lumiere, "nbcol", text='Col')
            
        #---Gap X
            op = row.operator("object.edit_light", text="Gap", icon='NONE')
            op.act_light = cobj.name 
            op.from_panel = True
            op.scale_gapx = True
            
        #-----------------------------------#
        #SCALE
        #-----------------------------------#
            split = box.split()
            col1 = split.column(align=True)
            
            row = col1.row(align=True)
            row.alignment = 'CENTER'
            row.label(text="Scale: ")
            row = col1.row(align=True)  
            
        #---Scale
            op = row.operator("object.edit_light", text="X/Y", icon='NONE')
            op.act_light = cobj.name 
            op.from_panel = True
            op.scale_light = True

        #---Scale X
            row = row.row(align=True)
            op = row.operator("object.edit_light", text="X", icon='NONE')
            op.act_light = cobj.name 
            op.from_panel = True
            op.scale_light_x = True

        #---Scale Y
            op = row.operator("object.edit_light", text="Y", icon='NONE')
            op.act_light = cobj.name 
            op.from_panel = True
            op.scale_light_y = True

        #-----------------------------------#
        #ROTATE
        #-----------------------------------#
            col2 = split.column(align=True)
            row = col2.row(align=True)
            row.alignment = 'CENTER'
            row.label(text="Rotation: ")
            row = col2.row(align=True)
        
        #---Rotate X
            op = row.operator("object.edit_light", text="X", icon='NONE')
            op.act_light = cobj.name 
            op.from_panel = True
            op.rotate_light_x = True
            
        #---Rotate Y
            op = row.operator("object.edit_light", text="Y", icon='NONE')
            op.act_light = cobj.name 
            op.from_panel = True
            op.rotate_light_y = True

        #---Rotate Z
            op = row.operator("object.edit_light", text="Z", icon='NONE')
            op.act_light = cobj.name 
            op.from_panel = True
            op.rotate_light_z = True

        #---Lock Light
            col = box.column(align=True)                
            row = col1.row(align=True)
            row.label(text="Lock light:")
            row = col2.row(align=True)
            row.prop(cobj.Lumiere, "lock_light", text="")
            
        elif cobj.Lumiere.options_type == "Material":
            box = self.col.box()
            col = box.column(align=True)
            row = col.row(align=True)
            row.prop(cobj.Lumiere, "texture_type", text=" ", expand=True)

            
        #---Gradient
            if cobj.Lumiere.texture_type == "Gradient":
                repeat_u = softbox_mat.node_tree.nodes["Math"].inputs[1]
                col = box.column(align=True)
                row = col.row(align=True)
                row.prop(cobj.Lumiere, "typgradient", text="")
                colramp = softbox_mat.node_tree.nodes['ColorRamp']                          
                mapping = softbox_mat.node_tree.nodes['Mapping']                            

            #---Repeat gradient
                row.prop(repeat_u, "default_value", text="Repeat")
                
            #---Rotate 90°
                row.prop(cobj.Lumiere, "rotate_ninety", text="", icon="FILE_REFRESH")
                col = box.column()
                row = col.row(align=True)
                    
            #---Color ramp template
                col.template_color_ramp(colramp, "color_ramp", expand=False)
                col = box.column()
                row = col.row(align=True)

            #---Add Random for grid
                if cobj.Lumiere.nbrow > 1 or cobj.Lumiere.nbcol > 1:
                    row.prop(cobj.Lumiere, "random_energy", text="Add random")                                          
                    row = col.row(align=True)
                
                # row.prop(mapping, "rotation", text="Rotate")
                
            #---Random colors
                if cobj.Lumiere.random_energy:
                    row.prop(cobj.Lumiere, "random_color", text="Random")
                    
        #---Image Texture
            elif cobj.Lumiere.texture_type == "Texture":
                col = box.column(align=True)
                row = col.row(align=True)
            
            #---Image texture name
                row.prop_search(cobj.Lumiere, "img_name", bpy.data, "images", text="")
                row.operator("image.open",text='', icon='IMASEL')
                
            #---Rotate 90°
                row.prop(cobj.Lumiere, "rotate_ninety", text="", icon="FILE_REFRESH")               
                row = col.row(align=True)
            
            #---Select image texture options
                if cobj.Lumiere.img_name != "":
                    row.label(text="Texture options:")
                    row.prop(cobj.Lumiere, "img_expand", text="")
                
            #---Texture options expanded
                repeat_u = softbox_mat.node_tree.nodes["Math"].inputs[1] 
                repeat_v = softbox_mat.node_tree.nodes["Math.002"].inputs[1] 
            
                row = col.row(align=True)                                   
                if cobj.Lumiere.img_expand and cobj.Lumiere.img_name != "":
                #---Brightness
                    col = box.column(align=True)
                    row = col.row(align=True)
                    row.prop(cobj.Lumiere, "img_bright", text="Bright")
                #---Contrast
                    row.prop(cobj.Lumiere, "img_contrast", text="Contrast")
                #---Gamma
                    row = col.row(align=True)
                    row.prop(cobj.Lumiere, "img_gamma", text="Gamma")   
                #---Hue
                    row.prop(cobj.Lumiere, "img_hue", text="Hue")   
                #---Repeat image on U
                    row = col.row(align=True)
                    row.prop(repeat_u, "default_value", text="Repeat U")
                #---Saturation
                    row.prop(cobj.Lumiere, "img_saturation", text="Saturation")                             
                #---Repeat image on U/V
                    row = col.row(align=True)
                    row.prop(repeat_v, "default_value", text="Repeat V")
                #---Value
                    row.prop(cobj.Lumiere, "img_value", text="Value")
                #---Reset values
                    row = col.row(align=True)
                    row.prop(cobj.Lumiere, "img_reset", text="Reset options", toggle=True)
                    row = col.row(align=True)
                    row.prop(cobj.Lumiere, "random_energy")
                    if cobj.Lumiere.random_energy:
                        row = col.row(align=True)
                        mix_color_texture = softbox.data.materials['Mat_SOFTBOX_' + cobj.data.name].node_tree.nodes['Mix_Color_Texture']                        
                        row = col.row(align=True)                                                   

                    #---Mix Random colors
                        row.prop(mix_color_texture.inputs[0], "default_value", text="Mix color")
                        row.prop(mix_color_texture, "blend_type", text="")
                        row = col.row(align=True)
                        row.prop(cobj.Lumiere, "random_color", text="Random")                                           
        #---Color
            elif cobj.Lumiere.texture_type == "Color" :
                col = box.column(align=True)
                row = col.row(align=True)
                row.prop(cobj.Lumiere, "lightcolor")
                    
            #---Reflector
                if cobj.Lumiere.typlight == "Panel":
                    row = col.row(align=True)
                    row.prop(cobj.Lumiere, "reflector", text='Reflector', toggle=True)
                #---Mix Random colors
                    if cobj.Lumiere.nbrow > 1 or cobj.Lumiere.nbcol > 1:
                        row = col.row(align=True)
                        row.prop(cobj.Lumiere, "random_energy")
                        
                        if cobj.Lumiere.random_energy:
                            row = col.row(align=True)
                            mix_color_texture = softbox.data.materials['Mat_SOFTBOX_' + cobj.data.name].node_tree.nodes['Mix_Color_Texture']                        
                            row = col.row(align=True)                                                   
                            row.prop(mix_color_texture.inputs[0], "default_value", text="Mix color")
                            row.prop(mix_color_texture, "blend_type", text="")
                            row = col.row(align=True)
                            row.prop(cobj.Lumiere, "random_color", text="Random")           

"""
#########################################################################################################
# LIGHT PARAMETER
#########################################################################################################
"""
class LumiereLightParameterPreferences(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_idname = "view3d.lumiere"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Lumiere"
    bl_label = "Lumiere"
    bl_context = "objectmode"

    @classmethod
    def poll(cls, context):
        return False
    
    @classmethod
    def poll_embedded(cls, context):
        return context.object.data.name.startswith("Lumiere")

    def draw(self, context):
        layout = self.layout
        object = self.object
        box = self.box
        
        if object.Lumiere.typlight == "Panel":
            self.softbox_mat = bpy.data.materials["Mat_SOFTBOX_" + object.data.name]
            for ob in context.scene.objects:
                if ob.type != 'EMPTY' and ob.data.name == "SOFTBOX_" + object.data.name:
                    softbox_obj = ob 
                    
        self.lamp = get_lamp(context, object.data.name) 
        lamp = get_lamp(context, object.data.name) 
        
        split = box.split(.17)

        if object.type != 'EMPTY' and object.data.name.startswith("Lumiere") :
            self.cobj = bpy.context.scene.objects[object.name]
            cobj = bpy.context.scene.objects[object.name]

            col = split.column(align=True)
            bsplit = col.row()
            bsplit.scale_y = .8
            
        #---Tweak the light (edit mode)
            op = bsplit.operator("object.edit_light", icon='ACTION_TWEAK', text='', emboss=False)
            op.editmode = True
            op.act_light = cobj.name   
            
        #---Select only this light and hide all the other
            bsplit.prop(cobj.Lumiere, "select_only", icon='%s' % 'GHOST_DISABLED' if cobj.Lumiere.show else 'GHOST_ENABLED', text='', emboss=False)

        #---Expand the light options
            bsplit = col.row()
            bsplit.prop(cobj.Lumiere, "expanded",icon="TRIA_DOWN" if cobj.Lumiere.expanded else "TRIA_RIGHT",icon_only=True, emboss=False)
        
        #---If the light is not hide
            if cobj.Lumiere.show :
                
            #--Hide the light
                bsplit.prop(cobj.Lumiere, "show", text='', icon='OUTLINER_OB_LAMP', icon_only=True, emboss=False)

            #---Scale the selection button by half
                split = split.split(.05, align=True)
                col = split.column(align=True)
                bsplit2 = col.row(align=True)
                bsplit2.scale_y = 1.7

            #---Alert if the light is selected  
                if (context.scene.objects.active == cobj) :
                    bsplit2.alert = True
                    
            #---Select the light
                op = bsplit2.operator("object.select_light", text ='', icon='BLANK1')
                op.act_light = cobj.name 

            #---End of the alert 
                bsplit2.alert = False
                
        #---If the light is hide : hide the selector widget
            else:
                bsplit.prop(cobj.Lumiere, "show", icon='%s' % 'OUTLINER_OB_LAMP' if cobj.Lumiere.show else 'LAMP', text='', emboss=False, translate=False)
            
            split = split.split(align=True)
            col = split.column(align=True)
            row = col.row(align=True)
            if cobj.Lumiere.texture_type == "Reflector" :
                bsplit3 = row.split(0.9, align=True)
            elif cobj.Lumiere.texture_type == "Gradient" :
                bsplit3 = row
            elif cobj.Lumiere.texture_type == "Texture" : 
                bsplit3 = row
            elif cobj.Lumiere.typlight == "Env" and cobj.Lumiere.hdri_name != "":
                bsplit3 = row
            else:
                bsplit3 = row.split(0.9, align=True)

            if bpy.context.active_object == cobj: 
                split.alert = True
                
            bsplit3.prop(cobj, "name", text='')

        #---Icon Color 
            if cobj.Lumiere.typlight != "Env":
                if cobj.Lumiere.texture_type == "Reflector" :
                    bsplit3.prop(cobj.Lumiere, "lightcolor")
                elif cobj.Lumiere.texture_type == "Gradient" : 
                    bsplit3.label(text="",icon='COLORSET_10_VEC')
                elif cobj.Lumiere.texture_type == "Texture" : 
                    bsplit3.label(text="",icon='FILE_IMAGE')
                else:
                    bsplit3.prop(cobj.Lumiere, "lightcolor")
            else:
                if cobj.Lumiere.hdri_name == "":
                    hdri_col = bpy.data.worlds['Lumiere_world'].node_tree.nodes['Background'].inputs[0] 
                    bsplit3.prop(hdri_col, "default_value", text="")
                else:
                    bsplit3.label(text="",icon='FILE_IMAGE')

            row = col.row(align=True)
            if (context.scene.objects.active == cobj) :
                row = row.split(0.9, align=True)
                
        #---Light strength
            row.scale_y = .7
            if cobj.Lumiere.typlight != "Env":
                row.prop(cobj.Lumiere, "energy", text='', slider = True)
            else:
                hdr_back = bpy.data.worlds['Lumiere_world'].node_tree.nodes['Background'].inputs['Strength']    
                row.prop(hdr_back, "default_value", text="Strength", slider = False)
                
        #---Remove the selected light
            if (context.scene.objects.active == cobj) :
                row.operator("object.remove_light", text="", icon='PANEL_CLOSE').act_light = cobj.name

                        
        #---Menu items
            if cobj.Lumiere.expanded:
                col = box.column(align=True)                
                row = col.row(align=True)
                row.prop(cobj.Lumiere, "items_light_type", text="")
            #---Export light 
                op = row.operator("object.export_popup", text="", icon="EXPORT")
                op.act_type = "Light"
                op.act_name = cobj.name

                row = col.row(align=True)
                row.prop(cobj.Lumiere, "options_type", text=" ", expand=True)
                row = col.row(align=True)
                self.row = row
                self.col = box.column()
                if cobj.Lumiere.items_light_type != "Projector":
                    #---Type light
                    if cobj.Lumiere.typlight == "Panel":
                        LumiereSoftboxPreferences.draw(self, context)
                        
                    elif cobj.Lumiere.typlight == "Env":
                        LumiereEnvPreferences.draw(self, context)
                        
                    else:                           
                        LumiereLampPreferences.draw(self, context)
            
            #---projector 
                elif cobj.Lumiere.items_light_type == "Projector":
                    LumiereProjectorPreferences.draw(self, context)
                            
"""
#########################################################################################################
# UI
#########################################################################################################
"""     
class LumierePreferences(bpy.types.Panel):
    bl_idname = "view3d.lumiere"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Lumiere"
    bl_label = "Lumiere"
    bl_context = "objectmode"
    
    @classmethod
    def poll(cls, context):
        return (context.mode == 'OBJECT')
        
    def draw(self, context):
        scene = context.scene
        cobj = context.active_object
        layout = self.layout
        row = layout.row(align=True)
        objects_on_layer = []
        objects_on_group = []
        self.group = ""
        pcoll = Lumiere_custom_icons["Lumiere"]

#----------------------------------
# ADD LIGHTS
#----------------------------------                    
        col = row.column(align=True)
        row = col.row(align=True)
    
    #---List of lights to import or create
        row.prop(scene.Lumiere, "typlight", text="")
        
    #---Import or create depending on the choice in the list
        if context.scene.Lumiere.typlight == "Import":
            row.operator("object.import_light", text ='Import', icon='BLANK1')
            row.operator("object.manage_light", text ='', icon='COLLAPSEMENU')
        else:
            row.operator("object.create_light", text="New", icon='BLANK1')

        row = col.row(align=True)
#----------------------------------
# EDIT MODE
#----------------------------------         
        g = -1
        dct_group = defaultdict(list)
    #---For each Group
        for layer in bpy.data.scenes[scene.name].layers:
            g += 1
            for group in bpy.data.groups:
                light_on_group = [obj for obj in group.objects if obj.type != 'EMPTY' and obj.layers[g] and layer == True and obj.data.name.startswith("Lumiere") ]
                if light_on_group != [] and layer == True : 
                    dct_group[group].append(light_on_group)
                    objects_on_group.extend(light_on_group)
                    
    #---For each layer
        l = -1  
        for layer in bpy.data.scenes[scene.name].layers:
            l += 1
            light_on_layer = [obj for obj in context.scene.objects if not obj.users_group and  obj.type != 'EMPTY' and obj.layers[l] and layer == True and obj.data.name.startswith("Lumiere")]
            if layer == True and light_on_layer != []: 
                objects_on_layer.extend(light_on_layer)
            
        """
        #########################################################################################################
        #########################################################################################################
        # GROUPS
        #########################################################################################################
        #########################################################################################################
        """                 
                
        col = layout.column()
    #---For each group of lights
        for group in dct_group:
            self.group = group
            list_group = [item for it in dct_group[group] for item in it]
            
            row = layout.row(align=True)
            box = row.box()
            col = box.column()
            row = col.row(align=True)
    
        #---Expand group
            row.prop(group.Lumiere, "expanded_group", icon="TRIA_DOWN" if group.Lumiere.expanded_group else "TRIA_RIGHT", icon_only=True, emboss=False)

        #---Hide / Show group
            op = row.operator("group.show_hide_group", text='', icon="OUTLINER_OB_LAMP" if group.Lumiere.show_group else "LAMP", emboss=False)
            op.group = group.name

        #---Group name
            row.prop(group, "name", text='')

        #---Export light or group popup menu
            op = row.operator("object.export_popup", text="", icon="EXPORT")
            op.act_type = "Group"
            op.act_name = group.name
            
        #---If the light is in this current group
            if group.Lumiere.expanded_group:
                col = box.column(align=True)                
                row = col.row(align=True)
                row.scale_y = .15
                row.operator("object.separator", text=" ", icon='BLANK1')

                for self.object in group.objects:
                    if self.object in list(set(list_group)):
                        self.box = box
                        LumiereLightParameterPreferences.draw(self, context)
                        col = box.column(align=True)                
                        row = col.row(align=True)
                        row.scale_y = .15
                        row.alert = True
                        row.operator("object.separator", text=" ", icon='BLANK1')
                        row.alert = False
        """
        #########################################################################################################
        #########################################################################################################
        # LIGHTS
        #########################################################################################################
        #########################################################################################################
        """
        
        col = layout.column()
    #---For each light on the selected layer(s)
        for self.object in list(set(objects_on_layer)):
            col = layout.column()
            box = col.box()     
            self.box = box
            LumiereLightParameterPreferences.draw(self, context)
            cobj = self.cobj

#########################################################################################################

#########################################################################################################
# global variable to store icons in
Lumiere_custom_icons = {}

def register():
    #--- Begin icons
    import bpy.utils.previews
    pcoll = bpy.utils.previews.new()
    icons_dir = os.path.join(os.path.dirname(__file__), "icons")

    Lumiere_icons = {
                    "round" : "round.png",
                    "segments" : "segments.png",
                    }
        
    for key, f in Lumiere_icons.items():
        pcoll.load(key, os.path.join(icons_dir, f), 'IMAGE')

    Lumiere_custom_icons["Lumiere"] = pcoll
    #--- End icons
    
    bpy.utils.register_module(__name__)
    bpy.types.Group.Lumiere = bpy.props.PointerProperty(type=LumiereGrp)
    bpy.types.Scene.Lumiere = bpy.props.PointerProperty(type=LumiereScn)
    bpy.types.Object.Lumiere = bpy.props.PointerProperty(type=LumiereObj)
    bpy.types.Scene.Lumiere_groups_list = CollectionProperty(type=GroupProp)
    bpy.types.Scene.Lumiere_groups_list_index = bpy.props.IntProperty()
    bpy.types.Scene.Lumiere_all_lights_list = CollectionProperty(type=LightsProp)
    bpy.types.Scene.Lumiere_all_lights_list_index = bpy.props.IntProperty()
    update_panel(None, bpy.context)
    
def unregister():
    for pcoll in Lumiere_custom_icons.values():
        bpy.utils.previews.remove(pcoll)
    Lumiere_custom_icons.clear()
    del bpy.types.Scene.Lumiere_groups_list
    del bpy.types.Scene.Lumiere_groups_list_index
    del bpy.types.Scene.Lumiere_all_lights_list
    del bpy.types.Scene.Lumiere_all_lights_list_index
    del bpy.types.Scene.Lumiere
    del bpy.types.Object.Lumiere
    bpy.utils.unregister_module(__name__)   
    
if __name__ == "__main__":
    register()
