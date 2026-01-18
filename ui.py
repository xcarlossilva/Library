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
        # You can leave this empty or add your main list here
        layout.label(text="Main Content Area")
        layout.label(text="Assets link Setup ")
        layout.operator("wm.link_files", text="Link Files", icon="LINK_BLEND")

# 2. THE SUB-PANEL (The "Preferences" toggle)
class VIEW3D_PT_library_preferences(bpy.types.Panel):
    bl_label = "Preferences"
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
        is_relative = prefs.use_relative_paths
        btn_text = "Relative Path" if is_relative else "Relative Path"
        btn_icon = 'CHECKBOX_HLT' if is_relative else "CHECKBOX_DEHLT"     
        # Everything inside here appears when the "Preferences" arrow is clicked
        row = layout.row(align=True)
        row.operator("wm.library_prefs", text="Setup", icon="PREFERENCES")
        row.operator("wm.set_asset_import_link", text="Link Method", icon="LINKED")
        row.operator("wm.toggle_relative_path", text=btn_text, icon=btn_icon,depress=is_relative)

class VIEW3D_PT_assetbrowser_preferences(bpy.types.Panel):
    bl_label = "Asset Browser"
    bl_idname = "VIEW3D_PT_assetbrowser_preferences"
    bl_parent_id = "VIEW3D_PT_library_main" # <--- THIS LINKS THEM
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'} # Starts collapsed like your image

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        row = layout.row(align=True)
        row.operator("wm.toggle_asset_browser", text="Asset Browser")
        row.operator("wm.set_asset_browser_import_link", text="Link Method")


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
                    
class VIEW3D_UL_linked_items(bpy.types.UIList):
    """UIList for displaying linked objects/collections with categories (FIXED)"""
    bl_idname = "VIEW3D_UL_linked_items"

    ICON_TO_NAME = {
        'OUTLINER_COLLECTION': 'Collection',
        'OBJECT_DATA': 'Object',
        'MESH_DATA': 'Mesh',
        'MATERIAL': 'Material'
    }

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        scene = context.scene
        
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            
            # --- Draw a Category Header ---
            if item.is_category:
                
                category_name_parts = item.name.split(' ')
                category_name = category_name_parts[0] if category_name_parts else ""
                
                category_state = next((c for c in scene.linked_categories if c.name == category_name), None)

                if category_state:
                    # Draw a button with disclosure triangle
                    row = layout.row(align=True)
                    op = row.operator(
                        "wm.toggle_linked_category", 
                        text="", 
                        icon='RIGHTARROW' if category_state.is_expanded else 'DOWNARROW_HLT', 
                        emboss=False
                    )
                    op.category_name = category_name
                    
                    # Category Name and Count
                    row.label(text=item.name, icon=item.icon)
                else:
                    layout.label(text=item.name, icon=item.icon)
                    
            # --- Draw a Data Block Item ---
            else:
                row = layout.row()
                row.separator() # Add an indent
                row.label(text="", icon='BLANK1')
                row.label(text=item.name, icon=item.icon)
                
    # Method to handle item filtering for the UI List search field (FIXED)
        def filter_items(self, context, data, propname):
                items = getattr(data, propname)
                search_term = context.scene.linked_items_search.lower()
                
                filtered_indices = []

                if search_term:
                    for i, item in enumerate(items):
                        if search_term in item.name.lower():
                            filtered_indices.append(i)
                else:
                    filtered_indices = list(range(len(items))) # Returns all items if no search term

                # ... (Parent category inclusion logic remains here) ...
                
                final_indices = set(filtered_indices)
                for index in filtered_indices:
                    item = items[index]
                    if not item.is_category:
                        for i in range(index - 1, -1, -1):
                            if items[i].is_category:
                                final_indices.add(i)
                                break
                
                return sorted(list(final_indices)), []

class VIEW3D_PT_libraries_list(bpy.types.Panel):
    """Creates a Panel in the 3D Viewport under the Item tab listing library file paths"""
    bl_label = "Library Manager"
    bl_idname = "VIEW3D_PT_libraries_list"
    bl_parent_id = "VIEW3D_PT_library_main" # <--- THIS LINKS THEM
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}

    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        # prefs = context.preferences.filepaths
  # # We read the current state of the Global Preference
        # is_relative = prefs.use_relative_paths
        # btn_text = "Relative Path" if is_relative else "Relative Path"
        # btn_icon = 'CHECKBOX_HLT' if is_relative else "CHECKBOX_DEHLT"           
      

        # layout.label(text="Assets link Setup ")
        # layout.operator("wm.link_files", text="Link Files", icon="LINK_BLEND")
# The 'built-in' way to create a toggle header
        # Draw content only if expanded
    
        # box = layout.box()
        # box.label ( text="Asset Browser")
        # row = box.row(align=True)
        # row.operator("wm.toggle_asset_browser", text="Asset Browser", icon='ASSET_MANAGER')
        # row.operator("wm.set_asset_browser_import_link", text="Link Method", icon='LINKED')
                
 
        layout.label(text="Linked files in the scene:", icon='LINKED')
# Check if there are any linked libraries in the blend file
        if not bpy.data.libraries:
            box = layout.box()
            box.label(text="No libraries linked in this project", icon='CANCEL')
            # Optional: Add a button to open the file browser to link one
            # box.operator("wm.link", text="Link a Library", icon='LINK_BLEND')
            return
                
        # If libraries exist, show the UI List

        
        # We use bpy.data as the 'dataptr' because 'libraries' lives there
        layout.template_list("VIEW3D_UL_libraries",   "", bpy.data, "libraries", scene,  "libraries_index")
        
        row = layout.row(align=True)
        row.operator("wm.refresh_libraries", text="Refresh List", icon="FILE_REFRESH")
        
        layout.label(text="Edit linked files")
        row = layout.row(align=True)
        row.operator("wm.missing_files", text="Missing files", icon="LIBRARY_DATA_BROKEN")
        row.operator("wm.cleanup_libraries", text="Clean Broken Links", icon="TRASH")
        
        

                
        has_libraries = clamp_library_index(scene)

        # --- Draw Item Data Info Panel ---
        if has_libraries:
            selected_library = bpy.data.libraries[scene.libraries_index]
            
            # Filepath field 
            row = layout.row()
            row.prop(selected_library,"filepath",text="")

            # Dropdown Toggle for the entire linked list 
            layout.separator()
            box = layout.box()
            
            # Header Row for Linked Data Blocks
            row_header = box.row(align=True)
            row_header.prop(
                scene, 
                "linked_list_expanded", 
                text="Linked Data Blocks:", 
                icon='DOWNARROW_HLT' if scene.linked_list_expanded else 'RIGHTARROW',
                emboss=False
            )
            
            # Global Expand/Collapse Button
            if scene.linked_items:
                row_header.operator(
                    "wm.toggle_all_linked_categories",
                    text="",
                    icon='FULLSCREEN_EXIT' if all(c.is_expanded for c in scene.linked_categories) else 'FULLSCREEN_ENTER',
                    emboss=False
                )

            
            if scene.linked_list_expanded:
                if scene.linked_items:
                    
                    # Linked Items List (with integrated search field)
                    box.template_list(
                        "VIEW3D_UL_linked_items", 
                        "", 
                        scene, 
                        "linked_items", 
                        scene, 
                        "linked_items_index"
                    )
                    
                    # --- Selection Button ---
                    
                    # 1. Get the selected item
                    selected_item = scene.linked_items[scene.linked_items_index] if scene.linked_items_index >= 0 and scene.linked_items_index < len(scene.linked_items) else None
                    
                    # 2. Check if the button should be drawn
                    # The button is hidden if the selected item is a material (icon == 'MATERIAL')
                    if selected_item and not selected_item.is_category and selected_item.icon != 'MATERIAL':
                        row = box.row()
                        row.operator("wm.select_linked_objects", text="Select Objects Using Data", icon='VIEW_ORTHO')
                    
                else:
                    box.label(text="No Objects, Collections, or Materials linked.", icon='INFO')
                    
            else:
                layout.label(text="Select a library to see linked items.")
# 1. YOUR MAIN PANEL

        # Add your relative path toggle here
classes = (
    VIEW3D_UL_libraries,
    VIEW3D_UL_linked_items,
    VIEW3D_PT_library_main,
    VIEW3D_PT_library_preferences,
    VIEW3D_PT_assetbrowser_preferences,
    VIEW3D_PT_libraries_list,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)