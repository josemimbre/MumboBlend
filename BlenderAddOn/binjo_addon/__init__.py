

import os
import numpy as np
from timeit import default_timer as timer

from . import binjo_utils
from . import binjo_model_LU
from . import binjo_animation
from . binjo_model_bin import ModelBIN
from . binjo_bin_handler import BINjo_ModelBIN_Handler
from . binjo_dicts import Dicts

from . binjo_model_bin_vertex_seg import ModelBIN_VtxElem
from . binjo_model_bin_collision_seg import ModelBIN_ColSeg, ModelBIN_TriElem
from . binjo_model_bin_texture_seg import ModelBIN_TexElem
from . binjo_model_bin_displaylist_seg import ModelBIN_DLSeg


import bpy
from mathutils import Matrix, Vector
from bpy_extras.io_utils import ImportHelper
from bpy.app.handlers import persistent
# https://docs.blender.org/api/current/bpy_types_enum_items/operator_return_items.html
# https://docs.blender.org/api/current/bpy_types_enum_items/wm_report_items.html#rna-enum-wm-report-items
# http://www.network-science.de/ascii/

bl_info = {
    "name": "BINjo-Kazooie",
    "blender": (3, 4, 1),
    "category": "Object",
}
bin_handler = None
last_armature_obj = None
last_bone_seg = None
version_num = "0.1.3"



#===========================================================================================================
#    __  __            __        __           ______                     __   _                    
#   / / / /____   ____/ /____ _ / /_ ___     / ____/__  __ ____   _____ / /_ (_)____   ____   _____
#  / / / // __ \ / __  // __ `// __// _ \   / /_   / / / // __ \ / ___// __// // __ \ / __ \ / ___/
# / /_/ // /_/ // /_/ // /_/ // /_ /  __/  / __/  / /_/ // / / // /__ / /_ / // /_/ // / / /(__  ) 
# \____// .___/ \__,_/ \__,_/ \__/ \___/  /_/     \__,_//_/ /_/ \___/ \__//_/ \____//_/ /_//____/  
#      /_/  
#===========================================================================================================

def highlight_invis_changed(self, context):
    # and check for object and active-mat existence
    if (context.active_object is None):
        return
    target_object = context.active_object
    color_attribute = target_object.data.color_attributes["import_Color"]
    for face in target_object.data.polygons:
        if ("INVIS" in target_object.data.materials[face.material_index].name):
            # if the toggle is active
            if (context.scene.binjo_props.highlight_invis):
                # pure collision tris will be drawn in magenta
                color_attribute.data[face.loop_indices[0]].color = (1.0, 0, 1.0, 1.0)
                color_attribute.data[face.loop_indices[1]].color = (1.0, 0, 1.0, 1.0)
                color_attribute.data[face.loop_indices[2]].color = (1.0, 0, 1.0, 1.0)
            else:
                # otherwise make them gray and fully transparent
                color_attribute.data[face.loop_indices[0]].color = (0.7, 0.7, 0.7, 0.0)
                color_attribute.data[face.loop_indices[1]].color = (0.7, 0.7, 0.7, 0.0)
                color_attribute.data[face.loop_indices[2]].color = (0.7, 0.7, 0.7, 0.0)

disable_collision_update_function = False
def collision_changed(self, context):
    # only update the materials collision dict, if this wasnt disabled
    global disable_collision_update_function
    if (not disable_collision_update_function):
        # and check for object and active-mat existence
        if (context.active_object is not None):
            mat = context.active_object.active_material
            if (mat is not None):
                for idx, key in enumerate(mat["Collision_Flags"].keys()):
                    mat["Collision_Flags"][key] = bool(context.scene.binjo_props.collision_checkboxes[idx])
                mat["Collision_Disabled"] = bool(context.scene.binjo_props.collision_disabled[0])
                mat["Visibility_Disabled"] = bool(context.scene.binjo_props.visibility_disabled[0])
                mat["Collision_SFX"] = Dicts.COLLISION_SFX[context.scene.binjo_props.SFX_value_enum]

def RGBA_changed(self, context):
    # only update the materials collision dict, if this wasnt disabled
    global disable_collision_update_function
    if (not disable_collision_update_function):
        # update the selected RGBA display
        context.scene.binjo_props.custom_color_picker[0] = float(context.scene.binjo_props.color_picker_R / 255)
        context.scene.binjo_props.custom_color_picker[1] = float(context.scene.binjo_props.color_picker_G / 255)
        context.scene.binjo_props.custom_color_picker[2] = float(context.scene.binjo_props.color_picker_B / 255)
        context.scene.binjo_props.custom_color_picker[3] = float(context.scene.binjo_props.color_picker_A / 255)

@persistent
def general_update_function(scene):
    context = bpy.context

    # this update has to be hidden, to not trigger infinite-loops
    global disable_collision_update_function
    disable_collision_update_function = True

    if (context.active_object is not None):
        mat = context.active_object.active_material
        if (mat is not None):
            # update all the flags
            for idx, key in enumerate(mat["Collision_Flags"].keys()):
                context.scene.binjo_props.collision_checkboxes[idx] = bool(mat["Collision_Flags"][key])
            # as well as the collision- and visibility-disabled states
            context.scene.binjo_props.collision_disabled[0] = bool(mat["Collision_Disabled"])
            context.scene.binjo_props.visibility_disabled[0] = bool(mat["Visibility_Disabled"])
            # and the collision SFX
            context.scene.binjo_props.SFX_value_enum = Dicts.COLLISION_SFX_REV[mat["Collision_SFX"]]
            # update the selected RGBA display
            context.scene.binjo_props.color_picker_R = round(255 * context.scene.binjo_props.custom_color_picker[0])
            context.scene.binjo_props.color_picker_G = round(255 * context.scene.binjo_props.custom_color_picker[1])
            context.scene.binjo_props.color_picker_B = round(255 * context.scene.binjo_props.custom_color_picker[2])
            context.scene.binjo_props.color_picker_A = round(255 * context.scene.binjo_props.custom_color_picker[3])

    disable_collision_update_function = False



#===========================================================================================================
#     ____   ____ __  __            ____                                   __   _            
#    / __ ) / __ \\ \/ /           / __ \ _____ ____   ____   ___   _____ / /_ (_)___   _____
#   / __  |/ /_/ / \  /  ______   / /_/ // ___// __ \ / __ \ / _ \ / ___// __// // _ \ / ___/
#  / /_/ // ____/  / /  /_____/  / ____// /   / /_/ // /_/ //  __// /   / /_ / //  __/(__  ) 
# /_____//_/      /_/           /_/    /_/    \____// .___/ \___//_/    \__//_/ \___//____/  
#                                                  /_/                                    
#===========================================================================================================

# Properties are data elements that show up in the GUI Panel
class BINJO_Properties(bpy.types.PropertyGroup):
    rom_path: bpy.props.StringProperty(
        name="",
        description="Path to ROM",
        default="",
        maxlen=1024,
        subtype='FILE_PATH'
    )
    export_path: bpy.props.StringProperty(
        name="",
        description="Path to Store Exports",
        default="",
        maxlen=1024,
        subtype='DIR_PATH'
    )
    model_filename: bpy.props.StringProperty(
        name="",
        description="Internal Model Filename",
        default="",
        maxlen=1024,
        subtype='NONE'
    )
    force_model_A : bpy.props.BoolProperty(
        name="Force only Model-A",
        description="Force everything to export into a singular Model-BIN.",
        default = False
    )
    scale_factor : bpy.props.IntProperty(
        name="",
        description="The Model is downscaled by this factor on Import, and upscaled on Export",
        default = 100,
        min = 1,
        max = 1000
    )
    custom_color_picker: bpy.props.FloatVectorProperty(
        name = "RGBA",
        description="Color Picker for solid shading",
        subtype='COLOR_GAMMA',
        size=4,
        default=(1.0, 1.0, 1.0, 1.0),
        min= 0.0, # these only refer to the brightness slider
        max = 1.0
    )
    color_picker_R: bpy.props.IntProperty(
        name = "R",
        description="R Value of current RGBA Shade",
        default=255,
        min= 0,
        max = 255,
        update = RGBA_changed
    )
    color_picker_G: bpy.props.IntProperty(
        name="G",
        description="G Value of current RGBA Shade",
        default=255,
        min=0,
        max=255,
        update = RGBA_changed
    )
    color_picker_B: bpy.props.IntProperty(
        name="B",
        description="B Value of current RGBA Shade",
        default=255,
        min=0,
        max=255,
        update = RGBA_changed
    )
    color_picker_A: bpy.props.IntProperty(
        name="A",
        description="A Value of current RGBA Shade",
        default=255,
        min=0,
        max=255,
        update = RGBA_changed
    )
    enable_color_shading : bpy.props.BoolProperty(
        name="Use Color",
        description="Apply the selected Color when using the BINjo shading",
        default = True
    )
    enable_alpha_shading : bpy.props.BoolProperty(
        name="Use Alpha",
        description="Apply the selected Alpha when using the BINjo shading",
        default = True
    )
    highlight_invis : bpy.props.BoolProperty(
        name="Highlight INVIS Mats",
        description="Highlight all the INVIS (Collision-Only) Materials in Magenta",
        default = False,
        update = highlight_invis_changed
    )
    collision_disabled : bpy.props.BoolVectorProperty(
        name="Collision Disabled",
        description="Materials with disabled Collision will not be part of the Collision-Model at all; They're strictly visual-only.",
        size=1,
        default = (False,) * 1,
        update = collision_changed
    )
    visibility_disabled : bpy.props.BoolVectorProperty(
        name="Visibility Disabled",
        description="Materials with disabled Visibility will not be drawn at all; They're strictly collision-only.",
        size=1,
        default = (False,) * 1,
        update = collision_changed
    )
    collision_checkboxes : bpy.props.BoolVectorProperty(
        name="Collision Flags",
        description="Set the Collision Flags of the Selected Material.",
        size=len(Dicts.COLLISION_FLAGS.keys()),
        default = (False,) * len(Dicts.COLLISION_FLAGS.keys()),
        update = collision_changed
    )
    show_all_coll_flags : bpy.props.BoolProperty(
        name="Show all Coll Flags",
        description="Show ALL Collision Flags, including unknown ones and guesses.",
        default = False
    )
    model_filename_enum : bpy.props.EnumProperty(
        name="Model File Name Enum",
        description="Internal Model Filename Enum",
        default="(0x01) TTC - Treasure Trove Cove",
        items = [(name, name, "") for name in binjo_model_LU.map_model_lookup.keys()]
    )
    object_filename_enum : bpy.props.EnumProperty(
        name="Object File Name Enum",
        description="Internal Object Model (character/prop/enemy) Filename Enum",
        items = [(name, name, "") for name in binjo_model_LU.object_model_lookup.keys()]
    )
    animation_enum : bpy.props.EnumProperty(
        name="Animation Enum",
        description="Internal Animation Filename Enum",
        items = [(name, name, "") for name in binjo_model_LU.animation_lookup.keys()]
    )
    SFX_value_enum : bpy.props.EnumProperty(
        name="SFX Value",
        description="SFX Value Enum to determine Surface Sound",
        default="Normal",
        items = [(key, key, "") for key in Dicts.COLLISION_SFX.keys()],
        update = collision_changed
    )
    


#===========================================================================================================
#     ____   ____ __  __            ____                       __     
#    / __ ) / __ \\ \/ /           / __ \ ____ _ ____   ___   / /_____
#   / __  |/ /_/ / \  /  ______   / /_/ // __ `// __ \ / _ \ / // ___/
#  / /_/ // ____/  / /  /_____/  / ____// /_/ // / / //  __// /(__  ) 
# /_____//_/      /_/           /_/     \__,_//_/ /_/ \___//_//____/  
#                                                             
#===========================================================================================================

# PT elements are GUI Panels to collect and arrange Features + Props
class BINJO_PT_import_export_panel(bpy.types.Panel):
    """ GUI Panel for stuff """
    bl_label = "BINjo Import / Export"      # Panel Headline
    bl_space_type = "VIEW_3D"               # Editting View under which to find the Panel
    bl_region_type = "UI"                   #
    bl_category = 'Tool'                    # Which Tab the Panel is located under
    bl_options = {'HEADER_LAYOUT_EXPAND'}   #
    
    def draw(self, context):
        layout = self.layout

        # import from ROM
        row = layout.row()
        row.label(text="Source ROM :")
        row = layout.row()
        row.prop(context.scene.binjo_props, "rom_path", text="")

        row = layout.row()
        row.label(text="Targetted Map :")
        row = layout.row()
        row.operator("conversion.search_map", text=context.scene.binjo_props.model_filename_enum, icon='VIEWZOOM')

        row = layout.row()
        row.operator("conversion.from_rom")
        row = layout.row()
        row.operator("conversion.from_bin")
        row = layout.row()
        row.label(text="Scale Factor :")
        row.prop(context.scene.binjo_props, "scale_factor")

        # import a non-map object (character/prop/enemy, ...) from ROM
        layout.split()
        layout.split()
        row = layout.row()
        row.label(text="Targetted Object :")
        row = layout.row()
        row.operator("conversion.search_object", text=context.scene.binjo_props.object_filename_enum, icon='VIEWZOOM')

        row = layout.row()
        row.operator("conversion.object_from_rom")

        # apply an animation (rotation + translation only, see ANIMATION_NOTES.md)
        # to the skeleton of the last imported model
        layout.split()
        layout.split()
        row = layout.row()
        row.label(text="Animation :")
        row = layout.row()
        row.operator("conversion.search_animation", text=context.scene.binjo_props.animation_enum, icon='VIEWZOOM')

        row = layout.row()
        row.operator("conversion.apply_animation")

        # export
        layout.split()
        layout.split()
        row = layout.row()
        row.label(text="Set Export Path :")
        row = layout.row()
        row.prop(context.scene.binjo_props, "export_path", text="")

        row = layout.row()
        row.operator("conversion.to_bin")
        row = layout.row()
        row.prop(context.scene.binjo_props, "force_model_A")

blender_icons_dict = {
    'NONE': 0, 'QUESTION': 1, 'ERROR': 2, 'CANCEL': 3, 'TRIA_RIGHT': 4,
    'TRIA_DOWN': 5, 'TRIA_LEFT': 6, 'TRIA_UP': 7, 'ARROW_LEFTRIGHT': 8, 'PLUS': 9,
    'DISCLOSURE_TRI_RIGHT': 10, 'DISCLOSURE_TRI_DOWN': 11, 'RADIOBUT_OFF': 12, 'RADIOBUT_ON': 13, 'MENU_PANEL': 14,
    'BLENDER': 15, 'GRIP': 16, 'DOT': 17, 'COLLAPSEMENU': 18, 'X': 19,
    'DUPLICATE': 20, 'TRASH': 21, 'COLLECTION_NEW': 22, 'OPTIONS': 23, 'NODE': 24,
    'NODE_SEL': 25, 'WINDOW': 26, 'WORKSPACE': 27, 'RIGHTARROW_THIN': 28, 'BORDERMOVE': 29,
    'VIEWZOOM': 30, 'ADD': 31, 'REMOVE': 32, 'PANEL_CLOSE': 33, 'COPY_ID': 34,
    'EYEDROPPER': 35, 'CHECKMARK': 36, 'AUTO': 37, 'CHECKBOX_DEHLT': 38, 'CHECKBOX_HLT': 39,
    'UNLOCKED': 40, 'LOCKED': 41, 'UNPINNED': 42, 'PINNED': 43, 'SCREEN_BACK': 44,
    'RIGHTARROW': 45, 'DOWNARROW_HLT': 46, 'FCURVE_SNAPSHOT': 47, 'OBJECT_HIDDEN': 48, 'TOPBAR': 49,
    "INSET": 157, "IMAGES": 159
}
class BINJO_PT_RGBA_shader_panel(bpy.types.Panel):
    """ GUI Panel for stuff """
    bl_label = "BINjo RGBA Shader"          # Panel Headline
    bl_space_type = "VIEW_3D"               # Editting View under which to find the Panel
    bl_region_type = "UI"                   #
    bl_category = 'Tool'                    # Which Tab the Panel is located under
    bl_options = {'HEADER_LAYOUT_EXPAND'}   #
    
    def draw(self, context):
        layout = self.layout

        # flat shader
        row = layout.row()
        row.prop(context.scene.binjo_props, "custom_color_picker", text="Solid Shade")
        row = layout.row()
        row.prop(context.scene.binjo_props, "color_picker_R")
        row.prop(context.scene.binjo_props, "color_picker_G")
        row = layout.row()
        row.prop(context.scene.binjo_props, "color_picker_B")
        row.prop(context.scene.binjo_props, "color_picker_A")
        row = layout.row()
        row.operator("object.copy_selected_shade", icon_value=blender_icons_dict["EYEDROPPER"])
        
        layout.split()
        row = layout.row()
        row.prop(context.scene.binjo_props, "enable_color_shading")
        row.prop(context.scene.binjo_props, "enable_alpha_shading")
        row = layout.row()
        row.operator("object.shade_selected_faces")
        row = layout.row()
        row.operator("object.shade_selected_verts")

# PT elements are GUI Panels to collect and arrange Features + Props
class BINJO_PT_material_panel(bpy.types.Panel):
    bl_label = "BINjo Tools"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = 'material'
    bl_options = {"HIDE_HEADER"} # this forces the panel to the top in the stack as a side-effect

    def draw(self, context):
        layout = self.layout

        # general mat tools
        box = layout.box()
        
        inner_box = box.box()
        head_row = inner_box.row()
        head_row.label(text="BINjo Material Collision Editor")
        
        mat = None
        if (context.active_object is not None):
            mat = context.active_object.active_material

            row = box.row()
            row.operator("material.create_mat")
            row.operator("object.convert_materials")

            row = box.row()
            row.prop(context.scene.binjo_props, "highlight_invis")
            row = box.row()
            row.prop(context.scene.binjo_props, "show_all_coll_flags", text="Show ALL Collision Flags")

            inner_box = box.box()
            row = inner_box.row()
            # check if any mat is selected
            if (mat is None):
                row.label(text="No Material is selected.")
                return
            # and if the selected mat is a Binjo one
            if (mat.get("BINjo_Version", None) is None):
                row.label(text="Selected Material is not a BINjo Mat.")
                return
            
            row.label(text=f"Selected Material: {mat.name}")

            row = box.row()
            row.prop(context.scene.binjo_props, "collision_disabled", index=0, text="Disable Collision")
            row.prop(context.scene.binjo_props, "visibility_disabled", index=0, text="Disable Visibility")

            sfx_row = box.row()
            sfx_row.prop(context.scene.binjo_props, "SFX_value_enum", text="Sound Effect")

            element_row = box.row()
            element_columns = (element_row.column(), element_row.column())
            
            # determine how many rows will be needed for the display
            if (context.scene.binjo_props.show_all_coll_flags):
                # the +1 is basically like calling ceil() except without calling it
                display_row_cnt = ((len(Dicts.COLLISION_FLAGS.keys()) + 1) // 2)
            if (not context.scene.binjo_props.show_all_coll_flags):
                display_row_cnt = 5

            displayed_elements = 0
            for idx, key in enumerate(mat["Collision_Flags"].keys()):
                # if the toggle to show all flags is OFF, skip those that should be skipped
                if ((not context.scene.binjo_props.show_all_coll_flags) and ("UNK" in key or "(" in key)):
                    continue
                # if the element is the SFX value, skip it (handled further up in sfx_row)
                if (key == "SFX Value"):
                    continue
                # draw the element
                element_columns[displayed_elements // display_row_cnt].prop(
                    context.scene.binjo_props, "collision_checkboxes",
                    index=idx, text=key
                )
                displayed_elements += 1
            
            row = box.row()
            row.operator("material.change_mat_img")

        # if (context.scene.binjo_props.show_all_coll_flags == True):



#===========================================================================================================
#     ______                           __ 
#    / ____/_  __ ____   ____   _____ / /_
#   / __/  | |/_// __ \ / __ \ / ___// __/
#  / /___ _>  < / /_/ // /_/ // /   / /_  
# /_____//_/|_|/ .___/ \____//_/    \__/  
#             /_/    
#===========================================================================================================

class BINJO_OT_export_to_BIN(bpy.types.Operator):
    """Export the model to a BIN File"""
    bl_idname = "conversion.to_bin"
    bl_label = "Export to BIN"
    bl_options = {'REGISTER'}

    def execute(self, context):                 # execute() is called when running the operator.
        export_timer_start = timer()
        export_timer = timer()

        if (not os.path.isdir(context.scene.binjo_props.export_path)):
            self.report({'ERROR'}, "Export Path is not set to a viable Directory !")
            return {'CANCELLED'}
        if (not os.access(context.scene.binjo_props.export_path, (os.R_OK & os.W_OK))):
            self.report({'ERROR'}, "Incorrect Permissions for Export Path Directory !")
            return {'CANCELLED'}

        global bin_handler
        new_ModelBin_A = ModelBIN()
        new_ModelBin_B = ModelBIN()

        # grab the targetted object (NOTE: should grab every object later... ugh)
        if (context.active_object is None):
            self.report({'ERROR'}, "No Object selected to be exported !")
            return {'CANCELLED'}

        target_object = context.active_object
        color_attribute = target_object.data.color_attributes[0]
        uv_layer = target_object.data.uv_layers[0]
        # remember current mode, and set it to OBJECT for the time being
        original_mode = target_object.mode
        bpy.ops.object.mode_set(mode='OBJECT')



        print("Converting Material-Textures into TexSeg Data + Building TexSeg...")
        # first, create a list that tracks actually used materials within the model to avoid unneccessary exports
        loaded_materials = target_object.data.materials
        loaded_mat_cnt = len(loaded_materials)
        material_is_used = [False] * loaded_mat_cnt
        for face in target_object.data.polygons:
            # filter out materials that are not BINjo-related
            binjo_version = loaded_materials[face.material_index].get("BINjo_Version", None)
            if (binjo_version is None):
                continue
            # otherwise mark the material as being used
            material_is_used[face.material_index] = True

        tex_list = []
        material_tex_index_dict = {}
        # Create a BK Texture for every used Material (if it has an Image assigned) and create a Dict
        for idx, mat in enumerate(loaded_materials):
            # skip it, if it's not actually being used
            if (not material_is_used[idx]):
                continue
            # materials that dont rock a texture get (-1)
            if (mat.node_tree.nodes["TEX"].image is None):
                material_tex_index_dict[mat.name] = -1
                continue
            # create a tex object from the image data linked to this material
            # this hurts a LOOOT...
            tex = ModelBIN_TexElem.build_from_IMG(mat.node_tree.nodes["TEX"].image)
            # and add it to our list if it is new
            if (tex not in tex_list):
                tex_list.append(tex)
            # finally, add the material to our dictionary to find the tex-index easily later
            material_tex_index_dict[mat.name] = tex_list.index(tex)
        # this is also kinda stupid for A/B Model split but can be fixed later
        new_ModelBin_A.TexSeg.populate_from_elements(tex_list)
        new_ModelBin_B.TexSeg.populate_from_elements(tex_list)
        
        print(f"({timer() - export_timer:.3f}s) -- Done.")
        export_timer = timer()



        print("Extracting granular Model Information + Building VtxSeg, DLSeg, ColSeg...")
        # sort every face into its own sub-list, to sepperate them by Material
        # (this makes building the DLs easier)
        polygon_list_list = [ [] for __ in range(loaded_mat_cnt)]

        for face in target_object.data.polygons:
            # catch if the user tries to convert a non-triangulated model
            if (len(face.vertices) > 3):
                self.report({'ERROR'}, f"Some Face in your Mesh is not triangular (vertex-count: {len(face.vertices)}) !")
                bpy.ops.object.mode_set(mode=original_mode)
                return { 'CANCELLED' }
            # completely ignoring loose geometry (vtx_cnt < 3)
            if (len(face.vertices) < 3):
                continue
            # otherwise we are good
            polygon_list_list[face.material_index].append(face)
            
        extracted_vertices_A = []
        extracted_vertices_B = []
        DL_command_list_A = []
        DL_command_list_B = []
        collision_tris_A = []
        collision_tris_B = []

        # now we can iterate over the sorted lists
        for polygon_list in polygon_list_list:
            # if the list is empty, it features an unused material
            if (len(polygon_list) == 0):
                continue
            rep_poly = polygon_list[0]

            # filter out materials that are not actually being used
            # (Non-Binjo Materials will also be fitlered out here as a side-effect)
            if (not material_is_used[rep_poly.material_index]):
                continue

            # figure out which mat is assigned to this list
            assigned_mat = target_object.data.materials[rep_poly.material_index]
            
            # and gather the collision-type from it
            coll_type = ModelBIN_ColSeg.get_colltype_from_mat(assigned_mat)

            # as well as the tex_id through the material-dict from before
            tex_id = material_tex_index_dict[assigned_mat.name]
            tex_contains_transparency = False
            if (tex_id >= 0):
                # ATTENTION: this will 100% break when I clean up the A/B split some more...
                tex = new_ModelBin_A.TexSeg.tex_elements[tex_id]
                tex_contains_transparency = tex.contains_transparency
                # this is stupid, but good enough for now
                setup_commands_A = ModelBIN_DLSeg.build_setup_commands(tex, mode=0)
                setup_commands_B = ModelBIN_DLSeg.build_setup_commands(tex, mode=0)
                DL_command_list_A.extend(setup_commands_A)
                DL_command_list_B.extend(setup_commands_B)

            # this list will hold just a couple of same-tex tris, so I can bunch them
            # up and send them to the DL one big VTX-load + TRI-N command-chunk
            buffered_tris_A = []
            buffered_tris_B = []
            for polygon in polygon_list:

                vtx_triplet = []
                for (vertex_idx, loop_idx) in zip(polygon.vertices, polygon.loop_indices):
                    # get the XYZ coord containers, RGBA shade containers and UV coord containers
                    coords = target_object.data.vertices[vertex_idx].co
                    rgba   = color_attribute.data[loop_idx].color
                    uvs    = uv_layer.data[loop_idx].uv
                    # and extract the individual values (and correct the coordinate system)
                    x, y, z = [round(coord * context.scene.binjo_props.scale_factor) for coord in coords]
                    x, y, z = x, z, -y
                    r, g, b, a = [round(255 * channel) for channel in rgba]
                    u_transf, v_transf = uvs.x, uvs.y
                    # to build a vertex from them
                    vtx = ModelBIN_VtxElem.build_from_model_data(x, y, z, r, g, b, a, u_transf, v_transf)
                    if (tex_id >= 0):
                        vtx.reverse_UV_transforms(tex.width, tex.height)
                    vtx_triplet.append(vtx)

                face_contains_transparency = False
                for vtx in vtx_triplet:
                    if (vtx.a < 0xFF):
                        face_contains_transparency = True
                        break
                
                # try to realign the UVs if they extend too far 
                success = binjo_utils.realign_vtx_UVs(vtx_triplet, tex.width, tex.height)
                if (success != 0):
                    self.report({'ERROR'}, "UVs of a Face are extending too much !")
                    return {'CANCELLED'}

                if (
                    context.scene.binjo_props.force_model_A or \
                    (not tex_contains_transparency and not face_contains_transparency)
                ):
                    # add the triplet to the list of extracted verts
                    extracted_vertices_A.extend(vtx_triplet)

                    # then build a tri from the newest 3 vertices
                    tri = ModelBIN_TriElem()
                    vtx_cnt_A = len(extracted_vertices_A)
                    tri.build_from_parameters((vtx_cnt_A - 3), (vtx_cnt_A - 2), (vtx_cnt_A - 1), coll_type=coll_type, tex_id=tex_id)
                    tri.vtx_1 = vtx_triplet[0]
                    tri.vtx_2 = vtx_triplet[1]
                    tri.vtx_3 = vtx_triplet[2]

                    # if the previously determined coll-type is not None, add it to the collision tris
                    if (coll_type is not None):
                        collision_tris_A.append(tri)
                    # and if it has a valid tex_id, create the aforementioned DL command chunk for the buffered tris
                    print(tex_id, assigned_mat["Visibility_Disabled"])
                    if (tex_id >= 0 and not assigned_mat["Visibility_Disabled"]):
                        buffered_tris_A.append(tri)
                        print("hello DL ?")
                        # if we reached 10 buffered tris, we dump them into a tri-drawing chunk and flush it
                        # (the DL VTX-Buffer can hold 0x20==32 verts; 10 tris have 30 verts)
                        if (len(buffered_tris_A) == 10): 
                            DL_command_list_A.extend(ModelBIN_DLSeg.build_tri_drawing_commands(buffered_tris_A))
                            buffered_tris_A = []
                else:
                    # add the triplet to the list of extracted verts
                    extracted_vertices_B.extend(vtx_triplet)

                    # then build a tri from the newest 3 vertices
                    tri = ModelBIN_TriElem()
                    vtx_cnt_B = len(extracted_vertices_B)
                    tri.build_from_parameters((vtx_cnt_B - 3), (vtx_cnt_B - 2), (vtx_cnt_B - 1), coll_type=coll_type, tex_id=tex_id)
                    tri.vtx_1 = vtx_triplet[0]
                    tri.vtx_2 = vtx_triplet[1]
                    tri.vtx_3 = vtx_triplet[2]

                    # if the previously determined coll-type is not None, add it to the collision tris
                    if (coll_type is not None):
                        collision_tris_B.append(tri)
                    # and if it has a valid tex_id, create the aforementioned DL command chunk for the buffered tris
                    if (tex_id >= 0 and not assigned_mat["Visibility_Disabled"]):
                        buffered_tris_B.append(tri)
                        # if we reached 10 buffered tris, we dump them into a tri-drawing chunk and flush it
                        # (the DL VTX-Buffer can hold 0x20==32 verts; 10 tris have 30 verts)
                        if (len(buffered_tris_B) == 10): 
                            DL_command_list_B.extend(ModelBIN_DLSeg.build_tri_drawing_commands(buffered_tris_B))
                            buffered_tris_B = []

            # now the polygon loop is over; check if some buffered tris are left over
            if (tex_id >= 0 and len(buffered_tris_A) > 0 and not assigned_mat["Visibility_Disabled"]):
                DL_command_list_A.extend(ModelBIN_DLSeg.build_tri_drawing_commands(buffered_tris_A))
            if (tex_id >= 0 and len(buffered_tris_B) > 0 and not assigned_mat["Visibility_Disabled"]):
                DL_command_list_B.extend(ModelBIN_DLSeg.build_tri_drawing_commands(buffered_tris_B))
        
        # use the count of extracted A-model VTXs to determine if we need a A-Model at all
        # (this is moreso just a sanity check incase some User tries something silly like creating an only-alpha map...)
        if (len(extracted_vertices_A) > 0):
            # build the VTX-Seg from the extracted vertices
            new_ModelBin_A.VtxSeg.populate_from_vtx_list(extracted_vertices_A)
            # + the Collision-Seg from the collected collision tris
            new_ModelBin_A.ColSeg.populate_from_collision_tri_list(collision_tris_A)
            # + the DL-Seg from the constructed DL-command list
            new_ModelBin_A.DLSeg.populate_from_command_list(DL_command_list_A)
            # we can also build the GeoLayout Segment in this very crude default way...
            new_ModelBin_A.GeoSeg.build_from_minmax(
                min_x=new_ModelBin_A.VtxSeg.min_x, 
                min_y=new_ModelBin_A.VtxSeg.min_y,
                min_z=new_ModelBin_A.VtxSeg.min_z,
                max_x=new_ModelBin_A.VtxSeg.max_x,
                max_y=new_ModelBin_A.VtxSeg.max_y,
                max_z=new_ModelBin_A.VtxSeg.max_z
            )
            # and export Model-A
            new_ModelBin_A.export_to_BIN(filename=f"{context.scene.binjo_props.export_path}/test_A.bin")

        # use the count of extracted B-model VTXs to determine if we need a B-Model at all
        if (len(extracted_vertices_B) > 0):
            new_ModelBin_B.VtxSeg.populate_from_vtx_list(extracted_vertices_B)
            new_ModelBin_B.ColSeg.populate_from_collision_tri_list(collision_tris_B)
            new_ModelBin_B.DLSeg.populate_from_command_list(DL_command_list_B)
            new_ModelBin_B.GeoSeg.build_from_minmax(
                min_x=new_ModelBin_B.VtxSeg.min_x, 
                min_y=new_ModelBin_B.VtxSeg.min_y,
                min_z=new_ModelBin_B.VtxSeg.min_z,
                max_x=new_ModelBin_B.VtxSeg.max_x,
                max_y=new_ModelBin_B.VtxSeg.max_y,
                max_z=new_ModelBin_B.VtxSeg.max_z
            )
            new_ModelBin_B.export_to_BIN(filename=f"{context.scene.binjo_props.export_path}/test_B.bin")

        print(f"({timer() - export_timer:.3f}s) -- Done.")
        export_timer = timer()

        # reset object to original mode, export the collected data to BIN
        bpy.ops.object.mode_set(mode=original_mode)
        print(f"FULL TIME: {timer() - export_timer_start:.3f}s")
        return { 'FINISHED' }



#===========================================================================================================
#     ____                                __ 
#    /  _/____ ___   ____   ____   _____ / /_
#    / / / __ `__ \ / __ \ / __ \ / ___// __/
#  _/ / / / / / / // /_/ // /_/ // /   / /_  
# /___//_/ /_/ /_// .___/ \____//_/    \__/  
#                /_/  
#===========================================================================================================


# Builds a rest-pose Armature from a parsed Bone Segment. This is NOT wired up
# to deform the imported mesh (no vertex groups / weights are assigned) -
# the real game does not tie vertices to bones the way this addon's other
# segments are understood; see ANIMATION_NOTES.md (untracked, not in the repo)
# for the reverse-engineering trail. This just gives a positioned, correctly
# parented skeleton to look at / measure against the mesh.
def build_armature_from_bones(bone_seg, scale_factor, name="import_Skeleton"):
    # bone.parent_ID is a 0-based index into bone_seg.bone_list (file order),
    # NOT another bone's internal_ID - confirmed against animMtxList_setBoned
    # in the decomp (code_630D0.c), which uses the equivalent field as a
    # direct index into its own matrix array ("mlMtxSet(&start_ptr[s0->mtx_id])"),
    # and empirically: interpreting it as an internal_ID lookup produced
    # self-referencing/mutually-cyclic "parents" on Banjo's own rig, while
    # the array-index reading resolves all 60 bones to one clean root with
    # zero exceptions. 0xFFFF means no parent (root).

    # bone.x/y/z are already absolute (armature-space) positions, NOT offsets
    # relative to the parent - confirmed by comparing the raw, unaccumulated
    # bone coordinates against the model's own vertex bounding box (they
    # match almost exactly). parent_ID only decides Blender bone parenting
    # (outliner hierarchy / which bone's transform a child inherits when
    # posed later), not position.
    world_pos_by_id = {bone.internal_ID: (bone.x, bone.y, bone.z) for bone in bone_seg.bone_list}

    armature_data = bpy.data.armatures.new("import_Armature")
    armature_obj = bpy.data.objects.new(name, armature_data)
    bpy.context.scene.collection.objects.link(armature_obj)

    prev_active = bpy.context.view_layer.objects.active
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode='EDIT')

    MIN_BONE_LENGTH = 0.05
    edit_bone_by_id = {}
    for bone in bone_seg.bone_list:
        edit_bone = armature_data.edit_bones.new(f"bone_{bone.internal_ID}")
        pos = world_pos_by_id[bone.internal_ID]
        # same axis swap/flip as ModelBIN.arrange_mesh_data() (BK's coord
        # system doesn't match Blender's - Y/Z are swapped, and Z is flipped)
        edit_bone.head = (pos[0] / scale_factor, -pos[2] / scale_factor, pos[1] / scale_factor)
        edit_bone_by_id[bone.internal_ID] = edit_bone

    for bone in bone_seg.bone_list:
        edit_bone = edit_bone_by_id[bone.internal_ID]
        if (bone.parent_ID != 0xFFFF and bone.parent_ID < len(bone_seg.bone_list)):
            parent_bone = bone_seg.bone_list[bone.parent_ID]
            edit_bone.parent = edit_bone_by_id[parent_bone.internal_ID]

        # Always use a small fixed-length tail instead of pointing it at a
        # child's head: some parent/child pairs in this data are unrelated
        # detail bones (teeth, beak, ...) sitting far apart in space rather
        # than a visually continuous limb segment, which produced huge
        # diagonal "spike" bones when the tail followed the first child.
        # This is a reference skeleton, not a posed rig, so each bone just
        # needs to mark its own position correctly.
        edit_bone.tail = (edit_bone.head[0], edit_bone.head[1], edit_bone.head[2] + MIN_BONE_LENGTH)

    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.objects.active = prev_active

    # store on the object itself (not just a Python global) so it survives
    # addon reloads / reopening the .blend file, unlike last_armature_obj/
    # last_bone_seg below (kept as a same-session shortcut/fallback only)
    armature_obj["binjo_scaling_factor"] = bone_seg.scaling_factor

    global last_armature_obj, last_bone_seg
    last_armature_obj = armature_obj
    last_bone_seg = bone_seg
    return armature_obj


# Assigns each vertex to a rigid (weight 1.0, no blending - see
# ANIMATION_NOTES.md, untracked) vertex group matching the bone that the
# GeoLayout tree draws it under (ModelBIN.vertex_bone_assignments, built by
# build_complete_tri_list() while walking the DisplayList), then adds an
# Armature modifier so posing/animating armature_obj actually deforms the mesh.
def assign_vertex_groups_from_bones(mesh_obj, armature_obj, bone_seg, vertex_bone_assignments):
    vertex_group_by_bone_idx = {}
    for vtx_idx, bone_idx in vertex_bone_assignments.items():
        if (bone_idx is None):
            continue
        if (bone_idx not in vertex_group_by_bone_idx):
            bone_name = f"bone_{bone_seg.bone_list[bone_idx].internal_ID}"
            vertex_group_by_bone_idx[bone_idx] = mesh_obj.vertex_groups.new(name=bone_name)
        vertex_group_by_bone_idx[bone_idx].add([vtx_idx], 1.0, 'REPLACE')

    modifier = mesh_obj.modifiers.new(name="Armature", type='ARMATURE')
    modifier.object = armature_obj


class BINJO_OT_create_model_from_bin_handler(bpy.types.Operator):
    # this OP is hidden - used by the others
    bl_label = ""
    bl_idname = "conversion.from_bin_handler"
    bl_options = {'REGISTER'}

    def execute(self, context):       
        global bin_handler
        scene = context.scene
        import_timer_start = timer()

        print("Creating new Object...")
        # setting up a new mesh for the scene
        new_mesh_name = bpy.data.meshes.new("import_Mesh").name
        new_obj_name = bpy.data.objects.new("import_Object", bpy.data.meshes[new_mesh_name]).name

        # this line essentially just divides every coord by the scale factor through a nested list-comprehension
        vertices    = [[(coord / context.scene.binjo_props.scale_factor) for coord in coordlist] for coordlist in bin_handler.model_object.vertex_coord_list]
        edges       = []
        faces       = bin_handler.model_object.face_idx_list
        bpy.data.meshes[new_mesh_name].from_pydata(vertices, edges, faces)

        # create over-arching layer/attribute elements
        new_UV_name = bpy.data.objects[new_obj_name].data.uv_layers.new(name="import_UV").name
        new_col_attr_name = bpy.data.meshes[new_mesh_name].attributes.new(
            name='import_Color',
            domain='CORNER',
            type='BYTE_COLOR'
        ).name

        # now create actual materials from the mat-names
        for binjo_mat in bin_handler.model_object.mat_list:

            mat = bpy.data.materials.new(binjo_mat.name)
            set_mat_to_default(mat)
            # assign the parsed Tex after defaulting the mat
            tex_node = mat.node_tree.nodes["TEX"]
            tex_node.image = binjo_mat.Blender_IMG
            if (tex_node.image is not None):
                if (not os.path.isdir(context.scene.binjo_props.export_path)):
                    self.report({'WARNING'}, "Export Path is not set to a viable Directory - Not saving tmp Images...")
                elif (not os.access(context.scene.binjo_props.export_path, (os.R_OK & os.W_OK))):
                    self.report({'WARNING'}, "Incorrect Permissions for Export Path Directory !")
                else:
                    tex_node.image.filepath_raw = f"{context.scene.binjo_props.export_path}/{tex_node.image.name}"
                    tex_node.image.save()
            # also parse the collision properties and assign them correctly after defaulting
            mat["Collision_Disabled"] = bool("NOCOLL" in mat.name)
            mat["Visibility_Disabled"] = bool("INVIS" in mat.name)
            mat["Collision_Flags"] = ModelBIN_ColSeg.get_collision_flag_dict(
                initial_value=ModelBIN_ColSeg.get_colltype_from_mat_name(mat.name)
            )
            mat["Collision_SFX"] = ModelBIN_ColSeg.get_SFX_from_mat_name(mat.name)

            # and add it to the mat-list
            bpy.data.objects[new_obj_name].data.materials.append(mat)

        # since Im not creating new data, I can hold a ref to these now
        UV_layer = bpy.data.objects[new_obj_name].data.uv_layers[new_UV_name]
        col_attr = bpy.data.meshes[new_mesh_name].attributes[new_col_attr_name]

        for (face, tri) in zip(bpy.data.meshes[new_mesh_name].polygons, bin_handler.model_object.complete_tri_list):
            # set material index of the face according to the data within tri
            face.material_index = tri.mat_index
            # and set the UV coords of the face through the loop indices
            UV_layer.data[face.loop_indices[0]].uv = (tri.vtx_1.transformed_U, tri.vtx_1.transformed_V)
            UV_layer.data[face.loop_indices[1]].uv = (tri.vtx_2.transformed_U, tri.vtx_2.transformed_V)
            UV_layer.data[face.loop_indices[2]].uv = (tri.vtx_3.transformed_U, tri.vtx_3.transformed_V)
            
            # aswell as the RGBA shades
            if ("INVIS" in bpy.data.objects[new_obj_name].data.materials[face.material_index].name):
                # if the toggle is active
                if (context.scene.binjo_props.highlight_invis):
                    # pure collision tris will be drawn in magenta
                    col_attr.data[face.loop_indices[0]].color = (1.0, 0, 1.0, 1.0)
                    col_attr.data[face.loop_indices[1]].color = (1.0, 0, 1.0, 1.0)
                    col_attr.data[face.loop_indices[2]].color = (1.0, 0, 1.0, 1.0)
                else:
                    # otherwise make them gray and fully transparent
                    col_attr.data[face.loop_indices[0]].color = (0.7, 0.7, 0.7, 0.0)
                    col_attr.data[face.loop_indices[1]].color = (0.7, 0.7, 0.7, 0.0)
                    col_attr.data[face.loop_indices[2]].color = (0.7, 0.7, 0.7, 0.0)
            else:
                # others get their vertex RGBA values assigned (regardless of textured or not)
                col_attr.data[face.loop_indices[0]].color = (tri.vtx_1.r/255, tri.vtx_1.g/255, tri.vtx_1.b/255, tri.vtx_1.a/255)
                col_attr.data[face.loop_indices[1]].color = (tri.vtx_2.r/255, tri.vtx_2.g/255, tri.vtx_2.b/255, tri.vtx_2.a/255)
                col_attr.data[face.loop_indices[2]].color = (tri.vtx_3.r/255, tri.vtx_3.g/255, tri.vtx_3.b/255, tri.vtx_3.a/255)

        scene.collection.objects.link(bpy.data.objects[new_obj_name])

        if (bin_handler.model_object.BoneSeg.valid):
            armature_obj = build_armature_from_bones(bin_handler.model_object.BoneSeg, context.scene.binjo_props.scale_factor)
            assign_vertex_groups_from_bones(
                bpy.data.objects[new_obj_name],
                armature_obj,
                bin_handler.model_object.BoneSeg,
                bin_handler.model_object.vertex_bone_assignments
            )

        # just some names to check if neccessary
        print([e.name for e in bpy.data.materials[0].node_tree.nodes["Principled BSDF"].inputs])
        print(f"({timer() - import_timer_start:.3f}s) -- Done.")

        return { 'FINISHED' }



# init the bin-handler with data from ROM, grab a BIN from that ROM and convert it to a model
class BINJO_OT_import_from_ROM(bpy.types.Operator):
    """Import a model from a selected ROM"""    # Use this as a tooltip for menu items and buttons.
    bl_idname = "conversion.from_rom"           # Unique identifier for buttons and menu items to reference.
    bl_label = "Import from ROM"                # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}           # Enable undo for the operator.

    def execute(self, context):                 # execute() is called when running the operator.
        global bin_handler
        scene = context.scene

        if (bin_handler is None or bin_handler.ROM_name != scene.binjo_props.rom_path):
            bin_handler = BINjo_ModelBIN_Handler(rom_filename=scene.binjo_props.rom_path)
        bin_handler.load_model_file_from_ROM(scene.binjo_props.model_filename_enum)

        if (bin_handler.model_object is None):
            self.report({'ERROR'}, "No Model-Object could be pulled from the ROM !")
            return {'CANCELLED'}
        
        bpy.ops.conversion.from_bin_handler()
        return {'FINISHED'}



# init the bin-handler with data from ROM, grab a non-map Model-BIN (character/prop/enemy, ...) and convert it to a model
class BINJO_OT_import_object_from_ROM(bpy.types.Operator):
    """Import a character/prop/enemy model from a selected ROM"""
    bl_idname = "conversion.object_from_rom"
    bl_label = "Import Object from ROM"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        global bin_handler
        scene = context.scene

        if (bin_handler is None or bin_handler.ROM_name != scene.binjo_props.rom_path):
            bin_handler = BINjo_ModelBIN_Handler(rom_filename=scene.binjo_props.rom_path)
        bin_handler.load_object_file_from_ROM(scene.binjo_props.object_filename_enum)

        if (bin_handler.model_object is None):
            self.report({'ERROR'}, "No Model-Object could be pulled from the ROM !")
            return {'CANCELLED'}

        bpy.ops.conversion.from_bin_handler()
        return {'FINISHED'}



# searchable popup for model_filename_enum (plain EnumProperty dropdowns don't support
# type-to-filter on their own; this is Blender's documented way to add it)
class BINJO_OT_search_map(bpy.types.Operator):
    """Search Maps by Name"""
    bl_idname = "conversion.search_map"
    bl_label = "Search Map"
    bl_property = "map_search_enum"

    map_search_enum : bpy.props.EnumProperty(
        name="Search Map",
        items = [(name, name, "") for name in binjo_model_LU.map_model_lookup.keys()]
    )

    def execute(self, context):
        context.scene.binjo_props.model_filename_enum = self.map_search_enum
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.invoke_search_popup(self)
        return {'FINISHED'}



# searchable popup for object_filename_enum, same reasoning as BINJO_OT_search_map
class BINJO_OT_search_object(bpy.types.Operator):
    """Search Objects by Name"""
    bl_idname = "conversion.search_object"
    bl_label = "Search Object"
    bl_property = "object_search_enum"

    object_search_enum : bpy.props.EnumProperty(
        name="Search Object",
        items = [(name, name, "") for name in binjo_model_LU.object_model_lookup.keys()]
    )

    def execute(self, context):
        context.scene.binjo_props.object_filename_enum = self.object_search_enum
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.invoke_search_popup(self)
        return {'FINISHED'}



# searchable popup for animation_enum, same reasoning as BINJO_OT_search_map
class BINJO_OT_search_animation(bpy.types.Operator):
    """Search Animations by Name"""
    bl_idname = "conversion.search_animation"
    bl_label = "Search Animation"
    bl_property = "animation_search_enum"

    animation_search_enum : bpy.props.EnumProperty(
        name="Search Animation",
        items = [(name, name, "") for name in binjo_model_LU.animation_lookup.keys()]
    )

    def execute(self, context):
        context.scene.binjo_props.animation_enum = self.animation_search_enum
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.invoke_search_popup(self)
        return {'FINISHED'}



# linearly samples a list of AnimationKeyframe (sorted by frame) at an
# arbitrary frame - a simplification of the game's real Catmull-Rom curves
# (see ANIMATION_NOTES.md, untracked), used only to combine 3 independently-
# timed rotation curves (pitch/yaw/roll) into one quaternion per bone
def _sample_curve(keyframes, frame):
    if (not keyframes):
        return 0.0
    if (frame <= keyframes[0].frame):
        return keyframes[0].value
    if (frame >= keyframes[-1].frame):
        return keyframes[-1].value
    for i in range(0, len(keyframes) - 1):
        a, b = keyframes[i], keyframes[i + 1]
        if (a.frame <= frame <= b.frame):
            if (b.frame == a.frame):
                return a.value
            t = (frame - a.frame) / (b.frame - a.frame)
            return a.value + t * (b.value - a.value)
    return keyframes[-1].value


# reads the selected .anim.bin from ROM and bakes it into a Blender Action on
# the skeleton of the last imported model (rotation + translation only; see
# ANIMATION_NOTES.md, untracked, for why scale isn't applied and how the
# component layout / units were derived)
class BINJO_OT_apply_animation(bpy.types.Operator):
    """Apply the selected Animation to the last imported model's Armature"""
    bl_idname = "conversion.apply_animation"
    bl_label = "Apply Animation to Skeleton"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        global bin_handler, last_armature_obj, last_bone_seg

        # prefer the active/selected object so this still works after an
        # addon reload or reopening the .blend (which wipes last_armature_obj,
        # a plain Python global); fall back to last_armature_obj for
        # same-session convenience if nothing suitable is selected
        armature_obj = context.active_object
        if (armature_obj is None or armature_obj.type != 'ARMATURE'):
            armature_obj = last_armature_obj
        if (armature_obj is None):
            self.report({'ERROR'}, "No skeleton to animate - select an imported Armature (or import a model with bones) first !")
            return {'CANCELLED'}
        if ("binjo_scaling_factor" in armature_obj):
            scaling_factor = armature_obj["binjo_scaling_factor"]
        elif (last_bone_seg is not None and last_armature_obj is armature_obj):
            scaling_factor = last_bone_seg.scaling_factor
        else:
            self.report({'ERROR'}, f"\"{armature_obj.name}\" wasn't built by this addon (missing scaling factor) !")
            return {'CANCELLED'}

        if (bin_handler is None or bin_handler.ROM_data is None):
            self.report({'ERROR'}, "No ROM data loaded - import from ROM first !")
            return {'CANCELLED'}

        anim_name = context.scene.binjo_props.animation_enum
        anim_data = binjo_utils.extract_model(bin_handler.ROM_data, anim_name, lookup=binjo_model_LU.animation_lookup)
        if (anim_data is None):
            self.report({'ERROR'}, f"Could not extract Animation \"{anim_name}\" from the ROM !")
            return {'CANCELLED'}

        anim_file = binjo_animation.AnimationFile()
        anim_file.populate_from_data(anim_data)

        action = bpy.data.actions.new(anim_name)
        if (armature_obj.animation_data is None):
            armature_obj.animation_data_create()
        armature_obj.animation_data.action = action

        # keyframe_insert() (rather than building action.fcurves by hand) is
        # the API that stays compatible across Blender's old direct-fcurves
        # Action storage and the newer layered Action system (4.4+), which
        # dropped the plain .fcurves attribute this used to rely on.
        prev_active = context.view_layer.objects.active
        context.view_layer.objects.active = armature_obj

        # group elements by bone, and rotation components together (they have
        # to be combined into one matrix per frame - see the long comment
        # below on why this can't just be 3 independent Euler channels)
        elements_by_bone = {}
        for elem in anim_file.elements:
            elements_by_bone.setdefault(elem.bone_id, {})[elem.component] = elem

        for bone_id, components in elements_by_bone.items():
            bone_name = f"bone_{bone_id}"
            if (bone_name not in armature_obj.pose.bones):
                continue
            pose_bone = armature_obj.pose.bones[bone_name]

            # --- translation (components 6/7/8): the curve values are deltas
            # in ARMATURE space (same axis swap/flip as everything else built
            # from Model-BIN coordinates), but pose_bone.location is defined
            # in the BONE's own LOCAL rest orientation, not armature space -
            # every bone here was built with the same arbitrary tail
            # direction (see build_armature_from_bones), so its local axes
            # don't line up with the armature's. Combine the 3 (independently
            # timed) curves into one armature-space vector per frame, same
            # resampling approach as rotation below, then rotate that vector
            # into the bone's local space via the inverse of its rest
            # orientation before assigning it to .location.
            x_elem = components.get(binjo_animation.TRANSLATION_X)
            y_elem = components.get(binjo_animation.TRANSLATION_Y)
            z_elem = components.get(binjo_animation.TRANSLATION_Z)
            if (x_elem or y_elem or z_elem):
                frames = sorted(set(
                    [kf.frame for kf in (x_elem.keyframes if x_elem else [])] +
                    [kf.frame for kf in (y_elem.keyframes if y_elem else [])] +
                    [kf.frame for kf in (z_elem.keyframes if z_elem else [])]
                ))
                local_to_armature = pose_bone.bone.matrix_local.to_3x3()
                armature_to_local = local_to_armature.inverted()
                for frame in frames:
                    game_dx = scaling_factor * (_sample_curve(x_elem.keyframes, frame) if x_elem else 0.0) / context.scene.binjo_props.scale_factor
                    game_dy = scaling_factor * (_sample_curve(y_elem.keyframes, frame) if y_elem else 0.0) / context.scene.binjo_props.scale_factor
                    game_dz = scaling_factor * (_sample_curve(z_elem.keyframes, frame) if z_elem else 0.0) / context.scene.binjo_props.scale_factor
                    # same (x,y,z) -> (x,-z,y) swap/flip as arrange_mesh_data()
                    armature_space_delta = Vector((game_dx, -game_dz, game_dy))
                    pose_bone.location = armature_to_local @ armature_space_delta
                    pose_bone.keyframe_insert(data_path="location", frame=frame)

            # --- rotation (components 0/1/2 = pitch/yaw/roll): the game
            # composes these as R = Rx(-pitch) . Ry(-yaw) . Rz(-roll) (each
            # mlMtxRot* left-multiplies the running matrix by a NEGATIVE-angle
            # rotation about its axis - verified against the exact row-mixing
            # arithmetic in mlmtx.c, not just the call order). Conjugating by
            # the same coordinate change used for position/mesh
            # (arrange_mesh_data's x,-z,y) gives, numerically verified:
            #   R_blender = Rx(-pitch) . Rz(-yaw) . Ry(roll)
            # Rather than trust a Blender Euler-order STRING to reproduce this
            # (easy to get backwards - two earlier attempts at this were wrong),
            # build the matrix directly with mathutils and keyframe the
            # resulting quaternion. That also means the 3 curves (which have
            # independent keyframe times) have to be resampled onto a shared
            # set of frames first - done with simple linear interpolation,
            # a simplification of the game's real Catmull-Rom curves.
            pitch_elem = components.get(binjo_animation.ROTATION_X)
            yaw_elem   = components.get(binjo_animation.ROTATION_Y)
            roll_elem  = components.get(binjo_animation.ROTATION_Z)
            if (pitch_elem or yaw_elem or roll_elem):
                frames = sorted(set(
                    [kf.frame for kf in (pitch_elem.keyframes if pitch_elem else [])] +
                    [kf.frame for kf in (yaw_elem.keyframes if yaw_elem else [])] +
                    [kf.frame for kf in (roll_elem.keyframes if roll_elem else [])]
                ))
                pose_bone.rotation_mode = 'QUATERNION'
                for frame in frames:
                    pitch = np.radians(_sample_curve(pitch_elem.keyframes, frame) if pitch_elem else 0.0)
                    yaw   = np.radians(_sample_curve(yaw_elem.keyframes, frame) if yaw_elem else 0.0)
                    roll  = np.radians(_sample_curve(roll_elem.keyframes, frame) if roll_elem else 0.0)
                    R = (
                        Matrix.Rotation(-pitch, 4, 'X') @
                        Matrix.Rotation(-yaw, 4, 'Z') @
                        Matrix.Rotation(roll, 4, 'Y')
                    )
                    pose_bone.rotation_quaternion = R.to_quaternion()
                    pose_bone.keyframe_insert(data_path="rotation_quaternion", frame=frame)

        context.view_layer.objects.active = prev_active
        context.scene.frame_start = anim_file.start_frame
        context.scene.frame_end = anim_file.end_frame
        self.report({'INFO'}, f"Applied \"{anim_name}\" ({len(anim_file.elements)} curves) to {armature_obj.name}")
        return {'FINISHED'}



# init the bin-handler without data, and convert an external BIN to a model
class BINJO_OT_import_from_BIN(bpy.types.Operator, ImportHelper):
    """Import a model from a selected BIN directly"""
    bl_idname = "conversion.from_bin"
    bl_label = "Import from BIN"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        global bin_handler

        if (bin_handler is None):
            bin_handler = BINjo_ModelBIN_Handler(rom_filename=None)
        bin_handler.load_model_file_from_BIN(self.filepath)

        if (bin_handler.model_object is None):
            self.report({'ERROR'}, "No Model-Object could be pulled from the ROM !")
            return {'CANCELLED'}
        
        bpy.ops.conversion.from_bin_handler()
        return {'FINISHED'}




#===========================================================================================================
#     ____   ____ __  __            ____                             __                    
#    / __ ) / __ \\ \/ /           / __ \ ____   ___   _____ ____ _ / /_ ____   _____ _____
#   / __  |/ /_/ / \  /  ______   / / / // __ \ / _ \ / ___// __ `// __// __ \ / ___// ___/
#  / /_/ // ____/  / /  /_____/  / /_/ // /_/ //  __// /   / /_/ // /_ / /_/ // /   (__  ) 
# /_____//_/      /_/            \____// .___/ \___//_/    \__,_/ \__/ \____//_/   /____/  
#                                     /_/           
#===========================================================================================================

class BINJO_OT_dump_images(bpy.types.Operator):
    """Dump all the currently loaded Image Objects"""
    bl_idname = "conversion.dump_images"
    bl_label = "Dump Images"
    bl_options = {'REGISTER'}

    def execute(self, context):
        path = context.scene.binjo_props.export_path
        if (path == ""):
            return { 'CANCELLED' }
        if (not os.isdir(path)):
            return { 'CANCELLED' }
        global bin_handler
        if (bin_handler is None):
            return { 'CANCELLED' }
        bin_handler.dump_image_files_to(path=path)
        return {'FINISHED'}
        


class BINJO_OT_convert_all_mats_to_binjo(bpy.types.Operator):
    """Convert ALL Materials of the selected Object into BINjo Default ones"""
    bl_idname = "object.convert_materials"
    bl_label = "Convert all Materials"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # check for object and active-mat existence
        target_object = context.active_object
        if (target_object is None):
            self.report({'ERROR'}, "No Object selected !")
            return {'CANCELLED'}
                
        # create over-arching layer/attribute elements

        # if there is a color attr already, keep it and rename it for consistency
        if (len(target_object.data.color_attributes) > 0):
            target_object.data.color_attributes[0].name = "import_Color"
            color_attribute = target_object.data.color_attributes[0]
        # otherwise, create a new one
        else:
            color_attribute = target_object.data.color_attributes.new(name='import_Color', domain='CORNER', type='BYTE_COLOR')
            for idx in range(0, len(color_attribute.data)):
                color_attribute.data[idx].color = (1.0, 1.0, 1.0, 1.0)
        
        # same for UVs
        if (len(target_object.data.uv_layers) > 0):
            target_object.data.uv_layers[0].name = "import_UV"
        else:
            target_object.data.uv_layers.new(name="import_UV")
        
        for mat in target_object.data.materials:
            # only convert mats that dont match the current binjo version
            if (mat.get("BINjo_Version", None) != version_num):
                set_mat_to_default(mat)

        return {'FINISHED'}

class BINJO_OT_change_mat_img(bpy.types.Operator, ImportHelper):
    """Change the Image of the currently selected Material"""
    bl_idname = "material.change_mat_img"
    bl_label = "Change Material Image"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # check for object and active-mat existence
        if (context.active_object is None):
            self.report({'ERROR'}, "No Object selected !")
            return {'CANCELLED'}
        mat = context.active_object.active_material
        if (mat is None):
            self.report({'ERROR'}, "No Material selected !")
            return {'CANCELLED'}
            
        mat.node_tree.nodes["TEX"].image = bpy.data.images.load(self.filepath)
        mat.node_tree.nodes["TEX"].image.filepath_raw = f"{self.filepath}"

        print(self.filepath)
        return {'FINISHED'}
        
class BINJO_OT_shade_selected_verts(bpy.types.Operator):
    """Shade all currently selected Vertices (may bleed into connected Faces)"""
    bl_idname = "object.shade_selected_verts"
    bl_label = "Shade Selected Verts"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # check for object and active-mat existence
        target_object = context.active_object
        if (target_object is None):
            self.report({'ERROR'}, "No Object selected !")
            return {'CANCELLED'}
        
        original_mode = target_object.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # get the assigned color attribute data and the vertex-list
        vertex_list  = target_object.data.vertices
        color_data   = target_object.data.color_attributes[0].data
        new_rgba_vec = context.scene.binjo_props.custom_color_picker

        for face in target_object.data.polygons:
            for (vertex_idx, loop_idx) in zip(face.vertices, face.loop_indices):
                # if the vtx is not selected, skip it
                if (not vertex_list[vertex_idx].select):
                    continue
                if (context.scene.binjo_props.enable_color_shading):
                    color_data[loop_idx].color[0] = new_rgba_vec[0]
                    color_data[loop_idx].color[1] = new_rgba_vec[1]
                    color_data[loop_idx].color[2] = new_rgba_vec[2]
                if (context.scene.binjo_props.enable_alpha_shading):
                    color_data[loop_idx].color[3] = new_rgba_vec[3]

        bpy.ops.object.mode_set(mode=original_mode)
        return {'FINISHED'}

class BINJO_OT_shade_selected_faces(bpy.types.Operator):
    """Shade all currently selected Faces"""
    bl_idname = "object.shade_selected_faces"
    bl_label = "Shade Selected Faces"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # check for object and active-mat existence
        target_object = context.active_object
        if (target_object is None):
            self.report({'ERROR'}, "No Object selected !")
            return {'CANCELLED'}
        
        original_mode = target_object.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # get the assigned color attribute data
        color_data   = target_object.data.color_attributes[0].data
        new_rgba_vec = context.scene.binjo_props.custom_color_picker

        for face in target_object.data.polygons:
            # if the face is not selected, skip it
            if (not face.select):
                continue
            for loop_idx in face.loop_indices:
                if (context.scene.binjo_props.enable_color_shading):
                    color_data[loop_idx].color[0] = new_rgba_vec[0]
                    color_data[loop_idx].color[1] = new_rgba_vec[1]
                    color_data[loop_idx].color[2] = new_rgba_vec[2]
                if (context.scene.binjo_props.enable_alpha_shading):
                    color_data[loop_idx].color[3] = new_rgba_vec[3]

        bpy.ops.object.mode_set(mode=original_mode)
        return {'FINISHED'}
        
class BINJO_OT_copy_selected_shade(bpy.types.Operator):
    """Copy the (mean) RGBA-Shade of all selected Elements"""
    bl_idname = "object.copy_selected_shade"
    bl_label = "Get RGBA from Selected"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # check for object and active-mat existence
        target_object = context.active_object
        if (target_object is None):
            self.report({'ERROR'}, "No Object selected !")
            return {'CANCELLED'}
        
        original_mode = target_object.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # get the assigned color attribute data and the vertex-list
        vertex_list  = target_object.data.vertices
        color_data   = target_object.data.color_attributes[0].data

        selected_vert_shades = []
        for face in target_object.data.polygons:
            for (vertex_idx, loop_idx) in zip(face.vertices, face.loop_indices):
                # if the vtx is not selected, skip it
                if (vertex_list[vertex_idx].select):
                    selected_vert_shades.append(color_data[loop_idx].color)
        new_rgba_vec = np.mean(selected_vert_shades, axis=0)

        context.scene.binjo_props.custom_color_picker = new_rgba_vec

        bpy.ops.object.mode_set(mode=original_mode)
        return {'FINISHED'}











def set_mat_to_default(mat):
    # first, retain (potential) old images, and remove old nodes
    # pulled from BBMat4.1
    old_image = None
    if (mat.use_nodes):
        for old_node in mat.node_tree.nodes:
            if old_node.type == "TEX_IMAGE":
                old_image = old_node.image
                break
        for old_node in mat.node_tree.nodes:
            # keep these 2 intact (also keeps BSDF settings that arent defaulted)
            if (old_node.name == "Principled BSDF" or old_node.name == "Material Output"):
                continue
            mat.node_tree.nodes.remove(old_node)
        
    # setting internal parameters within the mat
    mat.use_nodes = True
    # "blend_method" (pre-4.2) got replaced by "surface_render_method" (4.2+); "shadow_method" got removed entirely in 4.3+
    if (hasattr(mat, "surface_render_method")):
        mat.surface_render_method = "DITHERED" # "DITHERED" == Dithered Transparency
    else:
        mat.blend_method = "HASHED" # "HASHED" == Dithered Transparency
    if (hasattr(mat, "shadow_method")):
        mat.shadow_method = "NONE"
    mat.use_backface_culling = True
    # setting exposed parameters within the mat
    # the Principled BSDF "Specular" input got renamed to "Specular IOR Level" in Blender 4.0+
    principled_bsdf = mat.node_tree.nodes["Principled BSDF"]
    specular_input = principled_bsdf.inputs.get("Specular IOR Level", principled_bsdf.inputs.get("Specular"))
    specular_input.default_value = 0
            
    # texture node (NOTE that this will also assign "None" if the mat doesnt have an image)
    tex_node = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex_node.name = "TEX"
    tex_node.location = [-600, +300]
    # using the old_image (it may be None, but that's fine)
    tex_node.image = old_image
        
    # color node (RGB+A)
    color_node = mat.node_tree.nodes.new("ShaderNodeVertexColor")
    color_node.name = "RGBA"
    new_x = (tex_node.location[0] + tex_node.width - color_node.width)
    color_node.location = (new_x, 0)
    color_node.layer_name = "import_Color" # this name is what's connecting the node to the attribute

    # mixer-node (texture * RGB)                  
    mix_node_1 = mat.node_tree.nodes.new("ShaderNodeMixRGB")
    mix_node_1.blend_type = "MULTIPLY"
    mix_node_1.location = (-275, +300)
    mix_node_1.inputs["Fac"].default_value = 1.0

    # link tex and color nodes to mixer
    mat.node_tree.links.new(tex_node.outputs["Color"], mix_node_1.inputs["Color1"])
    mat.node_tree.links.new(color_node.outputs["Color"], mix_node_1.inputs["Color2"])
    # link mixer to base-color input in main-material node
    mat.node_tree.links.new(mix_node_1.outputs["Color"], mat.node_tree.nodes[0].inputs["Base Color"])
    
    # and link color node's alpha output to mat alpha input
    mat.node_tree.links.new(color_node.outputs["Alpha"], mat.node_tree.nodes[0].inputs["Alpha"])

    mat["Collision_Disabled"] = False
    mat["Visibility_Disabled"] = False
    mat["Collision_Flags"] = ModelBIN_ColSeg.get_collision_flag_dict(0x0000_0000)
    mat["Collision_Flags"]["Use Default SFXs"] = True
    mat["Collision_SFX"] = Dicts.COLLISION_SFX["Normal"]
    mat["BINjo_Version"] = version_num



class BINJO_OT_create_mat(bpy.types.Operator, ImportHelper):
    """Create a new BINjo Material"""
    bl_idname = "material.create_mat"
    bl_label = "New Material"
    bl_options = {'REGISTER'}

    def execute(self, context):
        # check for object and active-mat existence
        target_object = context.active_object
        if (target_object is None):
            self.report({'ERROR'}, "No Object selected !")
            return {'CANCELLED'}

        # if there is a color attr already, keep it and rename it for consistency
        if (len(target_object.data.color_attributes) > 0):
            target_object.data.color_attributes[0].name = "import_Color"
            color_attribute = target_object.data.color_attributes[0]
        # otherwise, create a new one
        else:
            color_attribute = target_object.data.color_attributes.new(name='import_Color', domain='CORNER', type='BYTE_COLOR')
            for idx in range(0, len(color_attribute.data)):
                color_attribute.data[idx].color = (1.0, 1.0, 1.0, 1.0)
        
        # same for UVs
        if (len(target_object.data.uv_layers) > 0):
            target_object.data.uv_layers[0].name = "import_UV"
        else:
            target_object.data.uv_layers.new(name="import_UV")

        mat = bpy.data.materials.new("new_mat")
        set_mat_to_default(mat)
        # assign the loaded Tex after defaulting the mat
        mat.node_tree.nodes["TEX"].image = bpy.data.images.load(self.filepath)
        mat.node_tree.nodes["TEX"].image.filepath_raw = self.filepath

        # and add it to the mat-list
        target_object.data.materials.append(mat)
        return {'FINISHED'}


# class list to abstract / loopify the reg() und unreg() funcs
classes = [
    BINJO_Properties,
    BINJO_PT_import_export_panel,
    BINJO_PT_RGBA_shader_panel,
    BINJO_PT_material_panel,
    BINJO_OT_create_model_from_bin_handler,
    BINJO_OT_import_from_ROM,
    BINJO_OT_import_object_from_ROM,
    BINJO_OT_search_map,
    BINJO_OT_search_object,
    BINJO_OT_search_animation,
    BINJO_OT_apply_animation,
    BINJO_OT_import_from_BIN,
    BINJO_OT_export_to_BIN,
    BINJO_OT_dump_images,
    BINJO_OT_change_mat_img,
    BINJO_OT_shade_selected_verts,
    BINJO_OT_shade_selected_faces,
    BINJO_OT_copy_selected_shade,
    BINJO_OT_create_mat,
    BINJO_OT_convert_all_mats_to_binjo
]

def register():
    for entry in classes:
        try:
            bpy.utils.register_class(entry)
        except ValueError:
            bpy.utils.unregister_class(entry)
            bpy.utils.register_class(entry)
    # and create a props object
    bpy.types.Scene.binjo_props = bpy.props.PointerProperty(type=BINJO_Properties)
    bpy.app.handlers.depsgraph_update_pre.append(general_update_function)

def unregister():
    for entry in reversed(classes):
        try:
            bpy.utils.unregister_class(entry)
        except ValueError:
            pass
    # and delete the props object
    del bpy.types.Scene.binjo_props
    bpy.app.handlers.depsgraph_update_pre.remove(general_update_function)

# This allows you to run the script directly from Blender's Text editor
# to test the add-on without having to install it.
if __name__ == "__main__":
    register()