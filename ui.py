import bpy
import os  # <--- Add this line
import subprocess
from bpy_extras.io_utils import ImportHelper
from .utils import auto_update_linked_handler, select_instances_internal, update_linked_items_list
    
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
        
    # 1. Check if list is empty first
        if not scene.linked_assets_list:
            layout.label(text="No linked assets found.", icon='INFO')
            return

        # 2. Get a safe index for the UI to use right now
        # We DON'T write to scene.linked_assets_index here. 
        # We just calculate a safe number for the calculation below.
        safe_index = min(max(0, scene.linked_assets_index), len(scene.linked_assets_list) - 1)
            
 
        
        layout.operator("wm.show_outliner_vertical", text="Library Outline", icon="OUTLINER")
        
    # # SAFETY: If properties aren't registered yet, stop drawing and show a message
        # if not hasattr(scene, "linked_items"):
            # layout.label(text="Addon not fully loaded...", icon='ERROR')
            # return
            
# Check if there are any linked libraries in the blend file
        if not bpy.data.libraries:
            box = layout.box()
            box.label(text="No libraries linked in this project", icon='CANCEL')
            # Optional: Add a button to open the file browser to link one
            # box.operator("wm.link", text="Link a Library", icon='LINK_BLEND')
            return
        
        # Header with Global Expansion Toggle
        row = layout.row(align=True)
        row.label(text="Linked Libraries", icon='LIBRARY_DATA_DIRECT')
        first_lib = next((i for i in scene.linked_assets_list if i.is_library), None)
        glob_icon = 'FULLSCREEN_EXIT' if (first_lib and first_lib.is_expanded) else 'FULLSCREEN_ENTER'
        row.operator("object.toggle_all_linked", text="", icon=glob_icon, emboss=False)

        # Main List Display
        layout.template_list("VIEW3D_UL_libraries", "", scene, "linked_assets_list", scene, "linked_assets_index")
        
        # 4. Use the safe_index to get the item for the buttons below
        item = scene.linked_assets_list[safe_index]
        layout.operator("wm.refresh_libraries", text="Refresh List", icon="FILE_REFRESH")
        
        # Context-Sensitive Selection Buttons
        if len(scene.linked_assets_list) > 0 and scene.linked_assets_index >= 0:
            if len(scene.linked_assets_list) > 0:
                # Clamp the index so it never exceeds the list size
                if scene.linked_assets_index >= len(scene.linked_assets_list):
                    scene.linked_assets_index = len(scene.linked_assets_list) - 1
    
            # Safely get the item now
            item = scene.linked_assets_list[scene.linked_assets_index]
            
            col = layout.column(align=True)
            col.operator("object.select_linked_from_list", text=f"Select {item.name}", icon='RESTRICT_SELECT_OFF')
            col.operator("object.focus_linked_selection", text="Focus View", icon='GRID')
            # col.operator("wm.select_linked_objects", text="Select Asset", icon="RESTRICT_SELECT_OFF")
        
        # row = layout.row(align=True)
        # row.operator("wm.select_linked_objects", text="Select Asset", icon="RESTRICT_SELECT_OFF")

        # Library Path Management Box
        if item.is_library:
            lib_data = bpy.data.libraries.get(item.name)
            if lib_data:
                box = layout.box()
                box.label(text="ASSET PATH", icon='FILE_BLEND')
                row = box.row(align=True)
                row.prop(lib_data, "filepath", text="")
                op = row.operator("wm.relocate_library", text="", icon='FILE_ALIAS')
                op.library_name = lib_data.name
        
        layout.label(text="Edit linked files")
        row = layout.row(align=True)
        row.operator("wm.missing_files", text="Fix Missing files", icon="LIBRARY_DATA_BROKEN")
        row.operator("wm.cleanup_libraries", text="Clean Broken Links", icon="TRASH")
        
     

class VIEW3D_UL_libraries(bpy.types.UIList):
    """UIList that truly collapses and expands sub-items"""
    bl_idname = "VIEW3D_UL_libraries"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        # We don't need complex logic here anymore because filter_items 
        # will handle whether the item is even sent to this function.
        
        row = layout.row(align=True)

        if item.is_library:
            # Handle the folder icon/warning
            main_icon = 'ERROR' if item.is_broken else 'ERROR'
            
            # Library Header
            icon_type = 'DISCLOSURE_TRI_DOWN' if item.is_expanded else 'DISCLOSURE_TRI_RIGHT'
            row.prop(item, "is_expanded", text="", icon=icon_type, emboss=False)
            # row.label(text=item.name)
            
            if item.is_broken:
                row.label(text= item.name, icon='CANCEL_LARGE')
            else:
                row.label(text=item.name)
            
               
            # Right-aligned utility buttons
            button_row = row.row(align=True)
            
            if item.is_broken:
                row.operator("wm.relocate_library", text="", icon='FILE_ALIAS')
            else:
                op = button_row.operator("wm.reload_library", text="", icon="FILE_REFRESH", emboss=False)
                op.library_name = item.name

                op = button_row.operator("wm.open_library", text="", icon="BLENDER", emboss=False)
                op.library_name = item.name
            
            op = button_row.operator("wm.delete_library", text="", icon="TRASH", emboss=False)
            op.library_name = item.name
                
        else:
            # Child items
            row.separator(factor=2.0)
            # If the library is broken, the children should probably look "disabled"
            sub_icon = 'CANCEL' if item.is_broken else ('OUTLINER_COLLECTION' if item.is_collection else 'OBJECT_DATA')
            row.enabled = not item.is_broken # Disable clicking on items from missing files
            row.label(text=item.name, icon=sub_icon)

    def filter_items(self, context, data, propname):
        """This function physically removes items from the list view"""
        items = getattr(data, propname)
        
        # Default: Show everything
        filter_flags = [self.bitflag_filter_item] * len(items)
        
        # Loop through all items to check if they should be hidden
        for index, item in enumerate(items):
            if not item.is_library:
                # Find the library this item belongs to by looking upwards
                parent_library = None
                for i in range(index - 1, -1, -1):
                    if items[i].is_library and items[i].lib_path == item.lib_path:
                        parent_library = items[i]
                        break
                
                # If the parent is collapsed, FLIP THE FLAG to hide it
                if parent_library and not parent_library.is_expanded:
                    filter_flags[index] &= ~self.bitflag_filter_item

        return filter_flags, []


classes = (
    VIEW3D_PT_library_main,
    VIEW3D_PT_library_preferences,
    VIEW3D_PT_assetbrowser_preferences,
    VIEW3D_PT_libraries_list,
    VIEW3D_UL_libraries,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)