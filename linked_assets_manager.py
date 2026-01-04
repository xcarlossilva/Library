import bpy
import os
import subprocess
import re

# -------------------------------------------------------------------
# --- PROPERTY GROUPS ---
# -------------------------------------------------------------------

class LinkedCategory(bpy.types.PropertyGroup):
    """Stores the state (expanded/collapsed) for each data type category."""
    name: bpy.props.StringProperty()
    is_expanded: bpy.props.BoolProperty(default=True)

class LinkedItem(bpy.types.PropertyGroup):
    """
    Temporary storage for linked item name and icon.
    Used for both Category Headers and actual Data Blocks.
    """
    name: bpy.props.StringProperty()
    icon: bpy.props.StringProperty()
    
    # Flags for UI drawing and logic
    is_category: bpy.props.BoolProperty(default=False)
    # Stores the data type icon (e.g., 'MESH_DATA') for the category this item belongs to.
    category_icon: bpy.props.StringProperty() 


# -------------------------------------------------------------------
# --- Helper Functions ---
# -------------------------------------------------------------------

def absolute_path(relpath):
    """Converts a relative path (stored in the .blend) to an absolute system path."""
    return os.path.abspath(bpy.path.abspath(relpath))

def clamp_library_index(scene):
    """Ensures the scene.libraries_index is a valid index for bpy.data.libraries."""
    library_count = len(bpy.data.libraries)
    if library_count == 0:
        if scene.libraries_index != 0:
            scene.libraries_index = 0
        return False
    
    if scene.libraries_index >= library_count:
        scene.libraries_index = library_count - 1
    
    return True

# -------------------------------------------------------------------
# --- UPDATE FUNCTION (Uses direct object comparison, standard structure) ---
# -------------------------------------------------------------------

def update_linked_items_list(self, context):
    """
    Populates scene.linked_items, including category headers and items. 
    The visible list is later filtered by the UIList.
    """
    scene = context.scene
    
    # This check clears the list if no valid library is selected (or if the list is empty)
    if not bpy.data.libraries or scene.libraries_index >= len(bpy.data.libraries):
        scene.linked_items.clear()
        scene.linked_items_index = 0 
        return
        
    selected_library = bpy.data.libraries[scene.libraries_index]
    
    # This is the expected clear before repopulation
    scene.linked_items.clear()
    
    # 1. Define Categories and get linked items
    data_definitions = [
        ('Collection', 'OUTLINER_COLLECTION', bpy.data.collections),
        ('Object', 'OBJECT_DATA', bpy.data.objects),
        ('Mesh', 'MESH_DATA', bpy.data.meshes),
        ('Material', 'MATERIAL', bpy.data.materials)
    ]
    
    linked_items_by_category = {}
    
    for category_name, icon_name, collection in data_definitions:
        items = []
        for item in collection:
            # Reverted/Working Logic: Direct object comparison
            if getattr(item, 'library', None) == selected_library:
                items.append((item.name, icon_name))
        
        items.sort(key=lambda item: item[0])
        
        if items:
            linked_items_by_category[category_name] = {'icon': icon_name, 'items': items}

    # 2. Manage Category Expansion States
    if isinstance(self, bpy.types.Scene):
        current_states = {c.name: c.is_expanded for c in self.linked_categories}
        self.linked_categories.clear()
    else:
        current_states = {}

    for category_name, cat_data in linked_items_by_category.items():
        new_cat = scene.linked_categories.add()
        new_cat.name = category_name
        new_cat.is_expanded = current_states.get(category_name, True)

    # 3. Add to the final UI list (scene.linked_items)
    for category_name, cat_data in linked_items_by_category.items():
        icon_name = cat_data['icon']
        items = cat_data['items']
        
        category_state = next(c for c in scene.linked_categories if c.name == category_name)
        
        # Add the Category Header
        header = scene.linked_items.add()
        header.name = f"{category_name} ({len(items)})" 
        header.icon = icon_name 
        header.is_category = True
        header.category_icon = icon_name 
        
        # Add the Items (only if expanded)
        if category_state.is_expanded:
            for name, icon in items:
                item = scene.linked_items.add()
                item.name = name
                item.icon = icon
                item.category_icon = icon_name 
    
    # Reset the active index to prevent 'IndexError' 
    if scene.linked_items_index >= len(scene.linked_items):
        scene.linked_items_index = 0
                

# -------------------------------------------------------------------
# --- PANEL (MODIFIED) ---
# -------------------------------------------------------------------

class VIEW3D_PT_libraries_list(bpy.types.Panel):
    """Creates a Panel in the 3D Viewport under the Item tab listing library file paths"""
    bl_label = "Manage Linked Library"
    bl_idname = "VIEW3D_PT_libraries_list"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Item'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        has_libraries = clamp_library_index(scene)
        
        layout.label(text="Linked files in the scene:")
        
        # Primary Library List
        layout.template_list("VIEW3D_UL_libraries", "", bpy.data, "libraries", scene, "libraries_index")
        
        row = layout.row(align=True)
        row.operator("wm.refresh_libraries", text="Refresh List", icon="FILE_REFRESH")
        
        row = layout.row(align=True)
        row.operator("wm.refresh_libraries", text="Missing Files", icon="FILE_REFRESH")
        row.operator("wm.cleanup_libraries", text="Clean Broken Links", icon="TRASH")
        
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

# -------------------------------------------------------------------
# --- UI LISTS DRAWING (FIXED filter_items) ---
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
                        icon='DOWNARROW_HLT' if category_state.is_expanded else 'RIGHTARROW', 
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

# -------------------------------------------------------------------
# --- OPERATORS (UNMODIFIED) ---
# -------------------------------------------------------------------

class WM_OT_toggle_linked_category(bpy.types.Operator):
    bl_idname = "wm.toggle_linked_category"
    bl_label = "Toggle Linked Data Category"
    category_name: bpy.props.StringProperty()
    
    def execute(self, context):
        scene = context.scene
        category = next((c for c in scene.linked_categories if c.name == self.category_name), None)
        if category:
            category.is_expanded = not category.is_expanded
            update_linked_items_list(scene, context) 
            return {'FINISHED'}
        self.report({'WARNING'}, f"Category '{self.category_name}' not found.")
        return {'CANCELLED'}

class WM_OT_toggle_all_linked_categories(bpy.types.Operator):
    bl_idname = "wm.toggle_all_linked_categories"
    bl_label = "Expand/Collapse All Linked Categories"
    
    def execute(self, context):
        scene = context.scene
        if not scene.linked_categories:
            self.report({'INFO'}, "No categories available to toggle.")
            return {'CANCELLED'}
        should_expand = not all(c.is_expanded for c in scene.linked_categories)
        for category in scene.linked_categories:
            category.is_expanded = should_expand
        update_linked_items_list(scene, context)
        action = "Expanded" if should_expand else "Collapsed"
        self.report({'INFO'}, f"{action} all categories.")
        return {'FINISHED'}


class WM_OT_select_linked_objects(bpy.types.Operator):
    """
    Selects only visible scene objects (Objects and Empties) that use the 
    currently selected linked data block (Mesh, Material, Collection, or Object).
    """
    bl_idname = "wm.select_linked_objects"
    bl_label = "Select Users of Linked Data"
    
    @classmethod
    def poll(cls, context):
        scene = context.scene
        
        # Ensure an item is selected and it's not a category header
        if not scene.linked_items or len(scene.linked_items) <= scene.linked_items_index < 0:
            return False
            
        selected_item = scene.linked_items[scene.linked_items_index]
        if selected_item.is_category:
            return False

        # Ensure the selected item is one of the types we can use for selection
        allowed_types = {'OBJECT_DATA', 'OUTLINER_COLLECTION', 'MESH_DATA', 'MATERIAL'}
        return selected_item.icon in allowed_types

    def execute(self, context):
        scene = context.scene
        selected_item = scene.linked_items[scene.linked_items_index] 
        data_name = selected_item.name
        data_type_icon = selected_item.icon
        
        data_block = None
        # 1. Get the actual Data Block from Blender data collections
        if data_type_icon == 'OBJECT_DATA':
            data_block = bpy.data.objects.get(data_name)
        elif data_type_icon == 'OUTLINER_COLLECTION':
            data_block = bpy.data.collections.get(data_name)
        elif data_type_icon == 'MESH_DATA':
            data_block = bpy.data.meshes.get(data_name)
        elif data_type_icon == 'MATERIAL':
            data_block = bpy.data.materials.get(data_name)

        if not data_block:
            self.report({'ERROR'}, f"Selected data block '{data_name}' not found in current scene data.")
            return {'CANCELLED'}

        # Deselect all objects first
        bpy.ops.object.select_all(action='DESELECT')
        selected_count = 0
        
        # Store objects to select after iteration
        objects_to_select = []

        # 2. Iterate and check for usage by scene objects
        for obj in context.scene.objects:
            is_user = False
            
            # Case 1: Linked Object (e.g., camera, light, empty)
            if data_type_icon == 'OBJECT_DATA' and obj == data_block:
                is_user = True
            
            # Case 2: Linked Collection (used by Collection Instance object/Empty)
            elif data_type_icon == 'OUTLINER_COLLECTION':
                if obj.instance_type == 'COLLECTION' and obj.instance_collection == data_block:
                    is_user = True
            
            # Case 3: Linked Mesh Data (used by Mesh Objects)
            elif data_type_icon == 'MESH_DATA':
                if obj.type == 'MESH' and obj.data == data_block:
                    is_user = True
            
            # Case 4: Linked Material (used by any object/data that holds materials)
            elif data_type_icon == 'MATERIAL':
                # Check obj's data block (e.g., Mesh, Curve) for the material
                if obj.data and data_block in getattr(obj.data, 'materials', []):
                    is_user = True
                # Fallback/alternative check (for linked materials in object slots)
                elif data_block in obj.material_slots:
                    is_user = True
            
            # 3. Queue object if it's a user and is visible/selectable
            if is_user:
                # IMPORTANT: Only select if the object is visible (not hidden)
                if not obj.hide_get() and not obj.hide_viewport and not obj.hide_select:
                    objects_to_select.append(obj)

        # 4. Apply Selection and Handle Errors
        for obj in objects_to_select:
            try:
                # This is the line that throws the error if the object is filtered out 
                # of the active View Layer (e.g., via the Outliner's visibility toggles or View Layer settings).
                obj.select_set(True)
                selected_count += 1
            except RuntimeError:
                # We skip selection for this object but continue the loop.
                continue

        # 5. Provide Feedback
        if selected_count > 0:
            # Set the last successfully selected object as active
            active_objects = [o for o in context.scene.objects if o.select_get()]
            if active_objects:
                context.view_layer.objects.active = active_objects[-1]
            self.report({'INFO'}, f"Selected {selected_count} object(s) using linked data '{data_name}'.")
        else:
            # CUSTOM MESSAGE REQUESTED: "The objects was not found in the scene"
            self.report({'WARNING'}, "The objects was not found in the scene.")
            
        return {'FINISHED'}

class WM_OT_reload_library(bpy.types.Operator):
    bl_idname = "wm.reload_library"
    bl_label = "Reload Library"
    library_name: bpy.props.StringProperty() 
    
    def execute(self, context):
        library = bpy.data.libraries.get(self.library_name)
        if not library:
            self.report({'ERROR'}, f"Library data block not found: {self.library_name}")
            return {'CANCELLED'}
        
        try:
            library.reload()
            self.report({'INFO'}, f"Reloaded: {self.library_name}")
            update_linked_items_list(context.scene, context)
            
        except RuntimeError as e:
            self.report({'ERROR'}, f"Reload failed for {self.library_name}: {e}")
            
        return {'FINISHED'}

class WM_OT_open_library(bpy.types.Operator):
    bl_idname = "wm.open_library"
    bl_label = "Open Library in New Window"
    
    library_name: bpy.props.StringProperty()
    
    def execute(self, context):
        library = bpy.data.libraries.get(self.library_name)
        if not library:
            self.report({'ERROR'}, f"Library data block not found: {self.library_name}")
            return {'CANCELLED'}
        
        filepath_abs = absolute_path(library.filepath)
        
        if not os.path.exists(filepath_abs):
            self.report({'ERROR'}, f"File not found at: {filepath_abs}")
            return {'CANCELLED'}
            
        try:
            blender_executable = bpy.app.binary_path
            subprocess.Popen([blender_executable, filepath_abs])
            self.report({'INFO'}, f"Launched new instance for: {self.library_name}")
        except Exception as e:
            self.report({'ERROR'}, f"Open failed for {self.library_name}. Check if the file path is correct: {e}")
            return {'CANCELLED'}
            
        return {'FINISHED'}

class WM_OT_delete_library(bpy.types.Operator):
    bl_idname = "wm.delete_library"
    bl_label = "Delete Library"
    library_name: bpy.props.StringProperty()
    
# --- THIS TRIGGER THE CONFIRMATION WINDOW ---
    def invoke(self, context, event):
        """Opens a small 'OK?' popup at the mouse position before executing"""
        return context.window_manager.invoke_confirm(self, event)
       
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
                
            update_linked_items_list(context.scene, context)
            
        except RuntimeError as e:
            self.report({'ERROR'}, f"Failed to delete library '{self.library_name}': {e}")
            
        return {'FINISHED'}
    
class WM_OT_cleanup_libraries(bpy.types.Operator):
    bl_idname = "wm.cleanup_libraries"
    bl_label = "Clean Up Broken Links"
    
    def execute(self, context):
        count = 0
        libraries_to_delete = []
        
        for library in bpy.data.libraries:
            filepath_abs = absolute_path(library.filepath)
            if not os.path.exists(filepath_abs):
                libraries_to_delete.append(library)
        
        for library in libraries_to_delete:
            bpy.data.libraries.remove(
                library, 
                do_unlink=True,  
                do_id_user=True  
            )
            count += 1
            
        if count > 0:
            update_linked_items_list(context.scene, context)
            self.report({'INFO'}, f"Successfully cleaned up {count} broken library link(s).")
        else:
            self.report({'INFO'}, "No broken library links found to clean up.")

        return {'FINISHED'}

class WM_OT_refresh_libraries(bpy.types.Operator):
    bl_idname = "wm.refresh_libraries"
    bl_label = "Refresh Libraries List"
    def execute(self, context):
        update_linked_items_list(context.scene, context) 
        self.report({'INFO'}, "Libraries list refreshed")
        return {'FINISHED'}
    
# -------------------------------------------------------------------
# --- REGISTRATION ---
# -------------------------------------------------------------------

def update_linked_items_search_callback(self, context):
    """Callback function for the search field to refresh the UI List display."""
    pass

def register():
    # Register all classes
    bpy.utils.register_class(LinkedCategory)
    bpy.utils.register_class(LinkedItem)
    bpy.utils.register_class(WM_OT_toggle_linked_category)
    bpy.utils.register_class(WM_OT_toggle_all_linked_categories) 
    bpy.utils.register_class(VIEW3D_UL_linked_items)
    bpy.utils.register_class(WM_OT_cleanup_libraries)
    bpy.utils.register_class(WM_OT_select_linked_objects)
    bpy.utils.register_class(VIEW3D_PT_libraries_list)
    bpy.utils.register_class(VIEW3D_UL_libraries)
    bpy.utils.register_class(WM_OT_reload_library)
    bpy.utils.register_class(WM_OT_open_library) 
    bpy.utils.register_class(WM_OT_delete_library)
    bpy.utils.register_class(WM_OT_refresh_libraries)
    
    # Register Properties
    if not hasattr(bpy.types.Scene, 'libraries_index'):
        # The update function is correctly referenced here in the global scope
        bpy.types.Scene.libraries_index = bpy.props.IntProperty(
            name="Index for libraries", 
            default=0,
            update=update_linked_items_list
        )

    # CATEGORY STATE PROPERTY
    if not hasattr(bpy.types.Scene, 'linked_categories'):
        bpy.types.Scene.linked_categories = bpy.props.CollectionProperty(type=LinkedCategory)
    
    if not hasattr(bpy.types.Scene, 'linked_items'):
        bpy.types.Scene.linked_items = bpy.props.CollectionProperty(type=LinkedItem)
        bpy.types.Scene.linked_items_index = bpy.props.IntProperty(name="Index for linked items", default=0)
        
    if not hasattr(bpy.types.Scene, 'linked_list_expanded'):
        bpy.types.Scene.linked_list_expanded = bpy.props.BoolProperty(
            name="Linked List Expanded",
            description="Toggle visibility of the linked data blocks list",
            default=True
        )

    # SEARCH PROPERTY
    if not hasattr(bpy.types.Scene, 'linked_items_search'):
        bpy.types.Scene.linked_items_search = bpy.props.StringProperty(
            name="Filter linked items",
            description="Search linked data blocks by name",
            default="",
            update=update_linked_items_search_callback 
        )


def unregister():
    # Unregister properties first
    if hasattr(bpy.types.Scene, 'linked_items_search'):
        del bpy.types.Scene.linked_items_search

    if hasattr(bpy.types.Scene, 'linked_list_expanded'):
        del bpy.types.Scene.linked_list_expanded
        
    if hasattr(bpy.types.Scene, 'linked_items'):
        del bpy.types.Scene.linked_items
        del bpy.types.Scene.linked_items_index
        
    if hasattr(bpy.types.Scene, 'linked_categories'):
        del bpy.types.Scene.linked_categories
    
    if hasattr(bpy.types.Scene, 'libraries_index'):
        del bpy.types.Scene.libraries_index

    # Unregister classes (in reverse order)
    bpy.utils.unregister_class(WM_OT_refresh_libraries)
    bpy.utils.unregister_class(WM_OT_cleanup_libraries)
    bpy.utils.unregister_class(WM_OT_delete_library)
    bpy.utils.unregister_class(WM_OT_open_library)
    bpy.utils.unregister_class(WM_OT_reload_library)
    bpy.utils.unregister_class(VIEW3D_UL_libraries)
    bpy.utils.unregister_class(VIEW3D_PT_libraries_list)
    bpy.utils.unregister_class(WM_OT_select_linked_objects)
    bpy.utils.unregister_class(WM_OT_toggle_all_linked_categories)
    bpy.utils.unregister_class(WM_OT_toggle_linked_category)
    bpy.utils.unregister_class(VIEW3D_UL_linked_items)
    bpy.utils.unregister_class(LinkedCategory)
    bpy.utils.unregister_class(LinkedItem)
    

if __name__ == "__main__":
    try:
        unregister()
    except Exception:
        pass
    register()
