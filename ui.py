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
    bl_category = 'Library Manager'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        # You can leave this empty or add your main list here
        layout.label(text="Link Assets")

class VIEW3D_PT_library_preferences(bpy.types.Panel):
    bl_label = "Setup"
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
    bl_label = "Assets / Library "
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
        layout.operator("wm.link_files", text="Link Assets", icon="LINK_BLEND")
        layout.operator("wm.show_asset_browser", text="Asset Browser", icon="ASSET_MANAGER")
        layout.operator("wm.set_asset_browser_import_link", icon=icon, text=text,depress=is_link)

class VIEW3D_PT_libraries_list(bpy.types.Panel):
    """Creates a Panel in the 3D Viewport under the Item tab listing library file paths"""
    bl_label = "Scene Linked Assets"
    bl_idname = "VIEW3D_PT_libraries_list"
    bl_parent_id = "VIEW3D_PT_library_main" # <--- THIS LINKS THEM
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}

    
    def draw(self, context):
        layout = self.layout
        scene = context.scene 
        
        
        layout.operator("wm.show_outliner_vertical", text="Library Outline", icon="OUTLINER")
        layout.operator("wm.refresh_libraries", text="Add / Refresh - List", icon="FILE_REFRESH")
       
   #===========================================================
   # !!!!! Report message if the scene does not have linked assets !!!!! 
   #===========================================================
       
       # 1. Check if list is empty first
        if not scene.linked_assets_list:
            # Create a box to house the message
            box = layout.box()
            
            # Add vertical padding at the top
            col = box.column()
            col.scale_y = 2.0
            
            # Create a row and set alignment to CENTER
            row = col.row()
            row.alignment = 'CENTER'
            
            # Display the text (Icons removed as requested)
            row.label(text="No linked assets found.",icon='ERROR')
            
            row = col.row()
            row.alignment = 'CENTER'
            row.label(text="Link an Asset to see the list.")

            return
  
        # 2. Get a safe index for the UI to use right now
        # We DON'T write to scene.linked_assets_index here. 
        # We just calculate a safe number for the calculation below.
        safe_index = min(max(0, scene.linked_assets_index), len(scene.linked_assets_list) - 1)

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
        row.label(text="Linked Assets List")
        first_lib = next((i for i in scene.linked_assets_list if i.is_library), None)
        glob_icon = 'FULLSCREEN_EXIT' if (first_lib and first_lib.is_expanded) else 'FULLSCREEN_ENTER'
        row.operator("object.toggle_all_linked", text="", icon=glob_icon, emboss=False)

        # Main List Display
        layout.template_list("VIEW3D_UL_libraries", "", scene, "linked_assets_list", scene, "linked_assets_index")
        
        # 4. Use the safe_index to get the item for the buttons below
        item = scene.linked_assets_list[safe_index]
        
        # Context-Sensitive Selection Buttons
        if len(scene.linked_assets_list) > 0 and scene.linked_assets_index >= 0:
            if len(scene.linked_assets_list) > 0:
                # Clamp the index so it never exceeds the list size
                if scene.linked_assets_index >= len(scene.linked_assets_list):
                    scene.linked_assets_index = len(scene.linked_assets_list) - 1
    
            # Safely get the item now
            item = scene.linked_assets_list[scene.linked_assets_index]
            
            row = layout.row(align=True)
            row.operator("object.select_linked_from_list", text="Select Item", icon='RESTRICT_SELECT_OFF')
            row.operator("object.focus_linked_from_list", text="Focus Item", icon='GRID')

            layout.operator("wm.cleanup_libraries", text="Clean Broken Files", icon="TRASH")

         # 1. Get the current selection from the list
        idx = scene.linked_assets_index
        list_items = scene.linked_assets_list

        if idx >= 0 and idx < len(list_items):
            selected_item = list_items[idx]
            
            # Identify the target library
            target_lib_name = ""
            is_main_library_selected = selected_item.is_library
            
            if is_main_library_selected:
                target_lib_name = selected_item.name
            else:
                # User selected a sub-item: Search backwards for parent
                for i in range(idx - 1, -1, -1):
                    if list_items[i].is_library:
                        target_lib_name = list_items[i].name
                        break
            
            # 2. Draw the UI Elements
            if target_lib_name:
                lib_data = bpy.data.libraries.get(target_lib_name)
                if lib_data:
                    # --- TITLE (Outside the box) ---
                    # Using LINK_BLEND which is the correct icon for .blend libraries
                    layout.label(text=f"Asset Path: {target_lib_name}")

                    # --- ACTION BOX ---
                    box = layout.box()
                    # Set the box to be greyed out if a sub-item is selected
                    box.enabled = is_main_library_selected
                    
                    # File path property
                    box.prop(lib_data, "filepath", text="")
                    
                    # Relocate Button
                    op = box.operator("wm.relocate_library", text="Relocate Library")
                    op.library_name = lib_data.name



class VIEW3D_PT_external_data(bpy.types.Panel):
    """Creates a Panel in the 3D Viewport under the Item tab listing library file paths"""
    bl_label = "Resources and Data"
    bl_idname = "VIEW3D_PT_external_data"
    bl_parent_id = "VIEW3D_PT_library_main" # <--- THIS LINKS THEM
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        
        # Access the global 'Automatically Pack Resources' setting
        is_autopack = context.blend_data.use_autopack
        
        # Define text based on the state
        btn_text_pack = "Auto Pack ON" if is_autopack else "Auto Pack Resources"
        btn_icon_pack = 'CHECKBOX_HLT' if is_autopack else "CHECKBOX_DEHLT"
        
        # Since import_method is an ENUM, you usually set it via operator or prop
        # 1. Global Auto-Pack Toggle
        layout.label(text="Resources - Pack / Unpack ")
        col = layout.column(align=True)
        col.prop(context.blend_data, "use_autopack", text=btn_text_pack, toggle=True,icon=btn_icon_pack,)

 
        # 2. Packing Operators
        col = layout.column(align=True)
        col.operator("file.pack_all", text="Pack Resources")
        col.operator("file.unpack_all", text="Unpack Resources")
        
        layout.separator()
        
        # 3. Linked Library Packing
        col = layout.column(align=True)
        col.operator("file.pack_libraries", text="Pack Linked Libraries")
        col.operator("file.unpack_libraries", text="Unpack Linked Libraries")
        
        # layout.separator()
        layout.label(text="Paths - Relative/Absolute")
        # 4. Path Management (Relative vs Absolute)
        col = layout.column(align=True)
        col.operator("file.make_paths_relative", text="Make Paths Relative", icon='LINKED')
        col.operator("file.make_paths_absolute", text="Make Paths Absolute", icon='UNLINKED')
        
        # layout.separator()
        layout.label(text="Fix - Missing files")
        # 5. Missing File Tools (Most Important for Library Managers)
        col = layout.column(align=True)
        col.operator("file.report_missing_files", text="Report Missing Files")
        col.operator("file.find_missing_files", text="Find Missing Files")
        
        layout.separator()
        

 
class VIEW3D_UL_libraries(bpy.types.UIList):
    """UIList that handles assets and libraries with ghost status"""
    bl_idname = "VIEW3D_UL_libraries"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)

        if item.is_library:
            # 1. Indicator Icons (Broken vs Ghost)
            if item.is_broken:
                row.label(text="", icon='ERROR')
            elif item.is_empty_link:
                row.label(text="", icon='GHOST_DISABLED')
            
            # 2. Expand Toggle
            row.prop(item, "is_expanded", text="", emboss=False, 
                     icon='TRIA_DOWN' if item.is_expanded else 'TRIA_RIGHT')
            
            row.label(text=item.name)
            
            # if item.is_empty_link:
                # row.label(text="", translate=False)
            
            # Utility buttons
            button_row = row.row(align=True)
            if not item.is_broken:
                op = button_row.operator("wm.reload_library", text="", icon="FILE_REFRESH", emboss=False)
                op.library_name = item.name
                
                op = button_row.operator("wm.open_library", text="", icon="BLENDER", emboss=False)
                op.library_name = item.name
            
            del_op = button_row.operator("wm.delete_library", text="", icon="TRASH", emboss=False)
            del_op.library_name = item.name
                
        else:
            # --- CHILD ASSETS ---
            row.separator(factor=2.0)
            
            # FIX: Define icon_type before using it!
            icon_type = 'OUTLINER_COLLECTION' if item.is_collection else 'OBJECT_DATA'
            
            if item.is_broken:
                row.label(text=item.name, icon='CANCEL')
                row.enabled = False
            else:
                # Use ghost icon if parent library has no instances in scene
                sub_icon = 'GHOST_ENABLED' if item.is_empty_link else icon_type
                
                # Draw the Asset Name
                row.label(text=item.name, icon=sub_icon)
                
                # NEW: Add the Place Asset button (Pseudo-Drag substitute)
                # This button will spawn the asset at the 3D Cursor
                place_op = row.operator("wm.place_linked_asset", text="", icon='ADD', emboss=False)
                place_op.asset_name = item.name
                place_op.is_collection = item.is_collection

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
    VIEW3D_PT_external_data,
    VIEW3D_UL_libraries,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)