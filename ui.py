import bpy
import os  # <--- Add this line
from .utils import absolute_path, clamp_library_index

class VIEW3D_PT_library_main(bpy.types.Panel):
    bl_label = "Library Manager"
    bl_idname = "VIEW3D_PT_library_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Item'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        # You can leave this empty or add your main list here
        layout.label(text="Link Assets")

class VIEW3D_PT_library_preferences(bpy.types.Panel):
    bl_label = "Asset / Library Setup"
    bl_idname = "VIEW3D_PT_library_preferences"
    bl_parent_id = "VIEW3D_PT_library_main" # <--- THIS LINKS THEM
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'} # Starts collapsed like your image

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        prefs = context.preferences.filepaths
  # We read the current state of the Global Preference
# Check the GLOBAL preference (plural 's')
        if prefs.asset_libraries:   
            is_relative = all(lib.use_relative_path for lib in prefs.asset_libraries)
            btn_text = "Relative Path" if is_relative else "Set Relative"
            btn_icon = 'CHECKBOX_HLT' if is_relative else "ERROR"     
        
        if prefs.asset_libraries:
            lib = prefs.asset_libraries[1]
            is_currently_linked = (lib.import_method == 'LINK')
            btn_texto = "Linked!" if is_currently_linked else "Set Linked" 
            btn_icono = 'CHECKBOX_HLT' if is_currently_linked else "ERROR"
        
        # Everything inside here appears when the "Preferences" arrow is clicked
        layout.operator("wm.library_prefs", text="Blender Prefs", icon="PREFERENCES")
        row = layout.row(align=True)
        row.operator("wm.set_asset_import_link", text=btn_texto , icon=btn_icono,depress=is_currently_linked)
        row.operator("wm.toggle_relative_path", text=btn_text, icon=btn_icon,depress=is_relative)
           
class VIEW3D_PT_assetbrowser_preferences(bpy.types.Panel):
    bl_label = "Assets"
    bl_idname = "VIEW3D_PT_assetbrowser_preferences"
    bl_parent_id = "VIEW3D_PT_library_main" # <--- THIS LINKS THEM
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'} # Starts collapsed like your image

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        # We find the asset area again just to decide on the icon/blue state
        asset_area = next((a for a in context.screen.areas if a.ui_type == 'ASSETS'), None)
        is_link = False
        
        if asset_area:
            params = getattr(asset_area.spaces.active, "params", None)
            if params:
                is_link = (params.import_method == 'LINK')

        # Logic for a toggle-style appearance
        icon = 'CHECKBOX_HLT'  if is_link else 'ERROR'
        text = 'Linked!' if is_link else 'FORCE set Linked'
        
        # If the poll above is False, this button grays out automatically
        layout.operator("wm.link_files", text="Link Files", icon="LINK_BLEND")
        layout.operator("wm.show_asset_browser", text="Asset Browser", icon="ASSET_MANAGER")
        layout.operator("wm.set_asset_browser_import_link", icon=icon, text=text,depress=is_link)

class VIEW3D_PT_libraries_list(bpy.types.Panel):
    """Creates a Panel in the 3D Viewport under the Item tab listing library file paths"""
    bl_label = "Scene linked files"
    bl_idname = "VIEW3D_PT_libraries_list"
    bl_parent_id = "VIEW3D_PT_library_main" # <--- THIS LINKS THEM
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}

    
    def draw(self, context):
        layout = self.layout
        scene = context.scene 
        
        layout.operator("wm.show_outliner_vertical", text="Library Outline", icon="OUTLINER")

# Check if there are any linked libraries in the blend file
        if not bpy.data.libraries:
            box = layout.box()
            box.label(text="No libraries linked in this project", icon='CANCEL')
            # Optional: Add a button to open the file browser to link one
            # box.operator("wm.link", text="Link a Library", icon='LINK_BLEND')
            return
        
# We use bpy.data as the 'dataptr' because 'libraries' lives there
        layout.template_list("VIEW3D_UL_libraries",   "", bpy.data, "libraries", scene,  "libraries_index")
        
        row = layout.row(align=True)
        row.operator("wm.select_linked_objects", text="Select Asset", icon="RESTRICT_SELECT_OFF")
        row.operator("wm.refresh_libraries", text="Refresh List", icon="FILE_REFRESH")
        
        layout.label(text="Edit linked files")
        row = layout.row(align=True)
        row.operator("wm.missing_files", text="Fix Missing files", icon="LIBRARY_DATA_BROKEN")
        row.operator("wm.cleanup_libraries", text="Clean Broken Links", icon="TRASH")
        
        
                
        has_libraries = clamp_library_index(scene)

        # --- Draw Item Data Info Panel ---
        if has_libraries:   
            selected_library = bpy.data.libraries[scene.libraries_index]
            
            # Filepath field 
            row = layout.row()
            row.prop(selected_library,"filepath",text="")


class VIEW3D_UL_libraries(bpy.types.UIList):
    """UIList for displaying main libraries with buttons"""
    bl_idname = "VIEW3D_UL_libraries"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        library = item
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            icon_name = 'LINKED' if os.path.exists(absolute_path(library.filepath)) else 'ERROR'
            
            row = layout.row(align=True)
            split = row.split(factor=0.8, align=True) 

            # 1. Name 
            name_col = split.column(align=True)
            name_col.prop(library, "name", text="", emboss=False, icon=icon_name)

            # 2. Buttons 
            button_col = split.column(align=True)
            filepath_abs = absolute_path(library.filepath)

            if os.path.exists(filepath_abs):
                button_row = button_col.row(align=True)
                
                op = button_row.operator("wm.reload_library", text="", icon="FILE_REFRESH", emboss=False)
                op.library_name = library.name
                
                op = button_row.operator("wm.open_library", text="", icon="BLENDER", emboss=False)
                op.library_name = library.name
                
                op = button_row.operator("wm.delete_library", text="", icon="TRASH", emboss=False)
                op.library_name = library.name
            else:
                 button_col.label(text="", icon='QUESTION')


                    
        # Add your relative path toggle here
classes = (
    VIEW3D_UL_libraries,
    # VIEW3D_UL_linked_items,
    VIEW3D_PT_library_main,
    VIEW3D_PT_library_preferences,
    VIEW3D_PT_assetbrowser_preferences,
    # VIEW3D_PT_libraries_list,
    # VIEW3D_PT_libraries_list,
)

def register():
    bpy.utils.register_class(MyLibraryItem)
    bpy.utils.register_class(MySceneProps)
    bpy.types.Scene.my_scene_props = bpy.props.PointerProperty(type=MySceneProps)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)