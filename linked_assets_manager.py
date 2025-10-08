import bpy
import os

# --- Helper Functions ---

def absolute_path(relpath):
    """Converts a relative path (stored in the .blend) to an absolute system path."""
    return os.path.abspath(bpy.path.abspath(relpath))

def clamp_library_index(scene):
    """Ensures the scene.libraries_index is a valid index for bpy.data.libraries."""
    library_count = len(bpy.data.libraries)
    if library_count == 0:
        if scene.libraries_index != 0:
            scene.libraries_index = 0  # <--- Only modify if necessary
        return False
    
    # Clamp the index to the valid range [0, count - 1]
    if scene.libraries_index >= library_count:
        scene.libraries_index = library_count - 1 # <--- Always modify if out of range
    
    return True

# -------------------------------------------------------------------
# --- UPDATE FUNCTION (CRITICAL FIX FOR THE ERROR) ---
# -------------------------------------------------------------------

def update_linked_items_list(self, context):
    """Populates scene.linked_items whenever the libraries_index changes."""
    scene = context.scene
    
    if not bpy.data.libraries or scene.libraries_index >= len(bpy.data.libraries):
        scene.linked_items.clear()
        return
        
    selected_library = bpy.data.libraries[scene.libraries_index]
    
    # CRITICAL: CLEAR AND REPOPULATE THE COLLECTION HERE
    scene.linked_items.clear()
    
    data_collections = [
        ('OBJECT_DATA', bpy.data.objects), 
        ('OUTLINER_COLLECTION', bpy.data.collections), 
        ('MESH_DATA', bpy.data.meshes), 
        ('MATERIAL', bpy.data.materials)
    ]
    
    linked_items_list = []
    for icon_name, collection in data_collections:
        for item in collection:
            # Check if the item is linked from the selected library
            if getattr(item, 'library', None) == selected_library:
                linked_items_list.append((item.name, icon_name))

    linked_items_list.sort(key=lambda item: item[0])
    
    for name, icon in linked_items_list:
        new_item = scene.linked_items.add()
        new_item.name = name
        new_item.icon = icon

# -------------------------------------------------------------------
# --- TEMPORARY PROPERTY GROUPS ---
# -------------------------------------------------------------------

class LinkedItem(bpy.types.PropertyGroup):
    """Temporary storage for linked item name and icon."""
    name: bpy.props.StringProperty()
    icon: bpy.props.StringProperty()

# -------------------------------------------------------------------
# --- PANEL (No Data Modification in Draw) ---
# -------------------------------------------------------------------

class VIEW3D_PT_libraries_list(bpy.types.Panel):
    """Creates a Panel in the 3D Viewport under the Item tab listing library file paths"""
    bl_label = "Library File Paths"
    bl_idname = "VIEW3D_PT_libraries_list"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Item'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        has_libraries = clamp_library_index(scene)
        
        layout.label(text="Library File Paths in Scene:")
        
        # Primary Library List
        layout.template_list("VIEW3D_UL_libraries", "", bpy.data, "libraries", scene, "libraries_index")
        
        row = layout.row(align=True)
        row.operator("wm.refresh_libraries", text="Refresh List", icon="FILE_REFRESH")
        row.operator("wm.cleanup_libraries", text="Clean Broken Links", icon="TRASH") # <--- NEW BUTTON
        
        # ... (rest of the draw method)
        
        # --- Draw Item Data Info Panel ---
        if has_libraries:
            selected_library = bpy.data.libraries[scene.libraries_index]
            
            # Filepath field (The item data info)
            row = layout.row()
            row.prop(selected_library, "filepath", text="Filepath")

            # --- Draw the Scrollable List ---
            layout.separator()
            box = layout.box()
            box.label(text="Linked Data Blocks:", icon='LINKED')
            
            # The list is populated by the update function whenever 'libraries_index' changes.
            if scene.linked_items:
                box.template_list(
                    "VIEW3D_UL_linked_items", 
                    "", 
                    scene,                     
                    "linked_items",            
                    scene,                     
                    "linked_items_index"       
                )
            else:
                box.label(text="No Objects, Collections, or Materials linked.", icon='INFO')
                
        else:
            layout.label(text="Select a library to see linked items.")

# -------------------------------------------------------------------
# --- UI LISTS DRAWING ---
# -------------------------------------------------------------------

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
                
                op = button_row.operator("wm.delete_library", text="", icon="X", emboss=False)
                op.library_name = library.name
            else:
                 button_col.label(text="", icon='QUESTION')


class VIEW3D_UL_linked_items(bpy.types.UIList):
    """UIList for displaying linked objects/collections (the scrollable part)"""
    bl_idname = "VIEW3D_UL_linked_items"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row()
            row.label(text=item.name, icon=item.icon)

# -------------------------------------------------------------------
# --- OPERATORS ---
# -------------------------------------------------------------------

class WM_OT_reload_library(bpy.types.Operator):
    """Reload Library"""
    bl_idname = "wm.reload_library"
    bl_label = "Reload Library"
    library_name: bpy.props.StringProperty() 
    
    def execute(self, context):
        library = bpy.data.libraries.get(self.library_name)
        if not library:
            self.report({'ERROR'}, f"Library data block not found: {self.library_name}")
            return {'CANCELLED'}
        
        try:
            # 1. Reload the library data from the external file
            library.reload()
            self.report({'INFO'}, f"Reloaded: {self.library_name}")
            
            # 2. CRITICAL STEP: Manually update the linked items list 
            #    to reflect the newly reloaded collection content.
            update_linked_items_list(context.scene, context)
            
        except RuntimeError as e:
            self.report({'ERROR'}, f"Reload failed for {self.library_name}: {e}")
            
        return {'FINISHED'}

class WM_OT_open_library(bpy.types.Operator):
    """Open Library"""
    bl_idname = "wm.open_library"
    bl_label = "Open Library"
    library_name: bpy.props.StringProperty()
    def execute(self, context):
        library = bpy.data.libraries.get(self.library_name)
        if not library:
            self.report({'ERROR'}, f"Library data block not found: {self.library_name}")
            return {'CANCELLED'}
        try:
            bpy.ops.wm.path_open(filepath=library.filepath)
            self.report({'INFO'}, f"Opened: {self.library_name}")
        except RuntimeError as e:
            self.report({'ERROR'}, f"Open failed for {self.library_name}: {e}")
        return {'FINISHED'}

class WM_OT_delete_library(bpy.types.Operator):
    """Force Delete Linked Library and all associated data blocks"""
    bl_idname = "wm.delete_library"
    bl_label = "Force Delete Library"
    library_name: bpy.props.StringProperty() 

    def execute(self, context):
        library = bpy.data.libraries.get(self.library_name)
        
        if library is None:
             self.report({'WARNING'}, f"Library data block not found (Name: {self.library_name}). Already deleted?")
             return {'FINISHED'}
             
        filepath_abs = absolute_path(library.filepath)
        is_broken = not os.path.exists(filepath_abs)
        
        try:
            bpy.data.libraries.remove(
                library, 
                do_unlink=True,  
                do_id_user=True  
            )
            
            if is_broken:
                self.report({'INFO'}, f"Cleaned up and deleted broken Library: {self.library_name}")
            else:
                self.report({'INFO'}, f"Force Deleted Library: {self.library_name}")
                
            # CRITICAL: Manually update the linked list after deletion
            update_linked_items_list(context.scene, context)
            
        except RuntimeError as e:
            self.report({'ERROR'}, f"Failed to delete library '{self.library_name}': {e}")
            
        return {'FINISHED'}
    
class WM_OT_cleanup_libraries(bpy.types.Operator):
    """Finds and deletes all libraries whose source file is missing (broken links)."""
    bl_idname = "wm.cleanup_libraries"
    bl_label = "Clean Up Broken Links"
    
    def execute(self, context):
        count = 0
        libraries_to_delete = []
        
        # 1. Identify broken libraries
        for library in bpy.data.libraries:
            filepath_abs = absolute_path(library.filepath)
            if not os.path.exists(filepath_abs):
                libraries_to_delete.append(library)
        
        # 2. Delete identified libraries
        for library in libraries_to_delete:
            bpy.data.libraries.remove(
                library, 
                do_unlink=True,  
                do_id_user=True  
            )
            count += 1
            
        # 3. Update the UI list immediately
        if count > 0:
            update_linked_items_list(context.scene, context)
            self.report({'INFO'}, f"Successfully cleaned up {count} broken library link(s).")
        else:
            self.report({'INFO'}, "No broken library links found to clean up.")

        return {'FINISHED'}

class WM_OT_refresh_libraries(bpy.types.Operator):
    """Refresh Libraries List"""
    bl_idname = "wm.refresh_libraries"
    bl_label = "Refresh Libraries List"
    def execute(self, context):
        # Manually trigger the update function to refresh the linked items list on demand
        # This ensures the lower panel data is populated after the refresh operation.
        update_linked_items_list(context.scene, context) 
        self.report({'INFO'}, "Libraries list refreshed")
        return {'FINISHED'}
    
# -------------------------------------------------------------------
# --- REGISTRATION ---
# -------------------------------------------------------------------

def register():
    # NEW CLASSES
    bpy.utils.register_class(LinkedItem)
    bpy.utils.register_class(VIEW3D_UL_linked_items)
    bpy.utils.register_class(WM_OT_cleanup_libraries) # <--- ADD THIS
    
    
    # EXISTING CLASSES
    bpy.utils.register_class(VIEW3D_PT_libraries_list)
    bpy.utils.register_class(VIEW3D_UL_libraries)
    bpy.utils.register_class(WM_OT_reload_library)
    bpy.utils.register_class(WM_OT_open_library)
    bpy.utils.register_class(WM_OT_delete_library)
    bpy.utils.register_class(WM_OT_refresh_libraries)
    
    # PROPERTIES: Registering with the UPDATE function
    if not hasattr(bpy.types.Scene, 'libraries_index'):
        bpy.types.Scene.libraries_index = bpy.props.IntProperty(
            name="Index for libraries", 
            default=0,
            update=update_linked_items_list # <--- The Index change triggers data population
        )

    if not hasattr(bpy.types.Scene, 'linked_items'):
        bpy.types.Scene.linked_items = bpy.props.CollectionProperty(type=LinkedItem)
        bpy.types.Scene.linked_items_index = bpy.props.IntProperty(name="Index for linked items", default=0)
        
    # CRITICAL: We DO NOT call update_linked_items_list(bpy.context.scene, bpy.context) 
    # directly here. It will be triggered automatically when the panel first draws, 
    # or by the user clicking 'Refresh List'.


def unregister():
    # Unregister properties first
    if hasattr(bpy.types.Scene, 'linked_items'):
        del bpy.types.Scene.linked_items
        del bpy.types.Scene.linked_items_index
    
    if hasattr(bpy.types.Scene, 'libraries_index'):
        del bpy.types.Scene.libraries_index

    # Unregister classes (in reverse order)
    bpy.utils.unregister_class(WM_OT_refresh_libraries)
    bpy.utils.unregister_class(WM_OT_cleanup_libraries) # <--- ADD THIS
    bpy.utils.unregister_class(WM_OT_delete_library)
    bpy.utils.unregister_class(WM_OT_open_library)
    bpy.utils.unregister_class(WM_OT_reload_library)
    bpy.utils.unregister_class(VIEW3D_UL_libraries)
    bpy.utils.unregister_class(VIEW3D_PT_libraries_list)
    bpy.utils.unregister_class(VIEW3D_UL_linked_items)
    bpy.utils.unregister_class(LinkedItem)
    

if __name__ == "__main__":
    try:
        unregister()
    except Exception:
        pass
    register()
