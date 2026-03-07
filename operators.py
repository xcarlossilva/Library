import bpy
import os
import subprocess
from bpy_extras.io_utils import ImportHelper
from .utils import auto_update_linked_handler, select_instances_internal, update_linked_items_list

# =========================================================================
# PF = PREFERENCES
# WI = WINDOW
# VW = VIEW
# SP = SETUP
# LIST AND ITEMS
# IT = ITEM
# =========================================================================


def absolute_path(relpath):
    return os.path.abspath(bpy.path.abspath(relpath))
    
 
# =========================================================================
# BLENDER PREFERENCES
# =========================================================================


class WM_OT_library_prefs(bpy.types.Operator):
    bl_idname = "wm.library_prefs"
    bl_label = "Library Prefs Setup"
    bl_description = "Open the file library prefs setup"
    
    def execute(self, context):
        bpy.ops.screen.userpref_show(section='FILE_PATHS')
        return {'FINISHED'}

class WM_OT_set_asset_import_link(bpy.types.Operator):
    bl_idname = "wm.set_asset_import_link"
    bl_label = "Set Import to Link"
    bl_description = "Changes the Prefs import method to Link"
    
    @classmethod
    def poll(cls, context):
        # The button is clickable ONLY if the method is NOT already 'LINK'
        prefs = context.preferences.filepaths
        if prefs.asset_libraries:
            return prefs.asset_libraries[1].import_method != 'LINK'
        return False
          
    def execute(self, context):
        prefs = context.preferences.filepaths
        for lib in prefs.asset_libraries:
            lib.import_method = 'LINK'
        return {'FINISHED'}
        
class WM_OT_toggle_relative_path(bpy.types.Operator):
    """Toggles the Global Relative Path Preference"""
    bl_idname = "wm.toggle_relative_path"
    bl_label = "Set Libraries to Relative"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        prefs = bpy.context.preferences.filepaths
        if not prefs.asset_libraries:
            return False
        
        # Clickable if at least one library is NOT relative
        return any(not lib.use_relative_path for lib in prefs.asset_libraries)

    def execute(self, context):
        prefs = context.preferences.filepaths
        for lib in prefs.asset_libraries:
            lib.use_relative_path = True
            
        prefs.use_relative_paths = True
        context.area.tag_redraw()
        return {'FINISHED'}


# =========================================================================
# ASSET LINK / BROWSER
# =========================================================================

    
class WM_OT_link_files(bpy.types.Operator):
    bl_idname = "wm.link_files"
    bl_label = "Link Files"
    bl_description = "Open the file browser to link new files to the scene"
    
    def execute(self, context):
        bpy.ops.wm.link('INVOKE_DEFAULT')
        return {'FINISHED'}

class WM_OT_show_asset_browser(bpy.types.Operator):
    bl_idname = "wm.show_asset_browser"
    bl_label = "Toggle Asset Browser"
    bl_description = "Opens or closes the Asset Browser area"
    bl_options = {'REGISTER', 'UNDO'}
    # configurable split factor

    factor: bpy.props.FloatProperty(default=0.4, min=0.1, max=0.9)

    def execute(self, context):
        window = context.window
        screen = context.screen

        # --- CASE: CLOSE ---
        asset_area = next((a for a in screen.areas
                           if a.type == 'FILE_BROWSER' and a.ui_type == 'ASSETS'), None)
        if asset_area:
            asset_area.type = 'VIEW_3D'
            with context.temp_override(window=window, screen=screen, area=asset_area):
                bpy.ops.screen.area_close()
                self.report({'INFO'}, "Asset Browser closed → 3D View restored")
            return {'FINISHED'}

        # --- CASE: OPEN ---
        view_3d = next((a for a in screen.areas if a.type == 'VIEW_3D'), None)
        if view_3d:
            # Close all bottom neighbors first
            bottom_neighbors = [a for a in screen.areas
                                if a.y < view_3d.y and a.x == view_3d.x and a.width == view_3d.width]
            for neighbor in bottom_neighbors:
                with context.temp_override(window=window, screen=screen, area=neighbor):
                    bpy.ops.screen.area_close()

            # Now split fresh at the desired factor
            old_areas = set(screen.areas)
            with context.temp_override(window=window, screen=screen, area=view_3d):
                bpy.ops.screen.area_split(direction='HORIZONTAL', factor=self.factor)

            new_area = (set(screen.areas) - old_areas).pop()
            new_area.type = 'FILE_BROWSER'
            new_area.ui_type = 'ASSETS'
            self.report({'INFO'}, f"Bottom areas reset → Asset Browser opened at {int(self.factor*100)}% height")
            return {'FINISHED'}

        return {'CANCELLED'}



    # def execute(self, context):
        # screen = context.screen

        # # --- CASE: CLOSE ---
        # asset_area = next((a for a in screen.areas
                           # if a.type == 'FILE_BROWSER' and a.ui_type == 'ASSETS'), None)

        # if asset_area:
            # # Switch back to 3D View and close the area
            # asset_area.type = 'VIEW_3D'
            # with context.temp_override(screen=screen, area=asset_area):
                # bpy.ops.screen.area_close()
            # return {'FINISHED'}

        # # --- CASE: OPEN ---
        # view_3d = next((a for a in screen.areas if a.type == 'VIEW_3D'), None)
        # if view_3d:
            # old_areas = set(screen.areas)

            # with context.temp_override(screen=screen, area=view_3d):
                # bpy.ops.screen.area_split(direction='HORIZONTAL', factor=0.4)

            # new_area = (set(screen.areas) - old_areas).pop()
            # new_area.type = 'FILE_BROWSER'
            # new_area.ui_type = 'ASSETS'
            # return {'FINISHED'}

        # return {'CANCELLED'}
       # 2. Setup for split
        def set_asset_mode():
            # Find the NEW area by comparing current areas to the original list
            new_areas = [a for a in screen.areas if a not in original_areas]
            
            if new_areas:
                target = new_areas[0]
                target.ui_type = 'ASSETS'
                
                # UI Cleanup
                if target.spaces.active.type == 'FILE_BROWSER':
                    params = getattr(target.spaces.active, "params", None)
                    if params:
                        params.show_navigation_column = False
                return None
            
            return 0.05 # Retry if the split hasn't registered yet

        bpy.app.timers.register(set_asset_mode, first_interval=0.01)
        return {'FINISHED'}

class WM_OT_set_asset_browser_import_link(bpy.types.Operator):
    bl_idname = "wm.set_asset_browser_import_link"
    bl_label = "Set Import to Link Asset Browser"
    bl_description = "Changes the Asset Browser import method to Link"

    @classmethod
    def poll(cls, context):
        # 1. Find the Asset Browser area
        asset_area = next((a for a in context.screen.areas if a.ui_type == 'ASSETS'), None)
        
        if asset_area:
            space = asset_area.spaces.active
            params = getattr(space, "params", None)
            
            if params:
                # The button is CLICKABLE only if the method is NOT already 'LINK'
                return params.import_method != 'LINK'
        
        # If no Asset Browser is open, we disable the button
        return False
   
    def execute(self, context):
        asset_area = next((a for a in context.screen.areas if a.ui_type == 'ASSETS'), None)
        
        if asset_area:
            space = asset_area.spaces.active
            params = getattr(space, "params", None)
            
            if params:
                params.import_method = 'LINK'
                self.report({'INFO'}, "Import Method: LINK")
                return {'FINISHED'}
            
        self.report({'WARNING'}, "Asset Browser not found")
        return {'CANCELLED'} 


# =========================================================================
# LIST ACTIONS - HIDE AND UNHIDE MAIN ITEM
# =========================================================================

class WM_OT_show_outliner_vertical(bpy.types.Operator):
    bl_idname = "wm.show_outliner_vertical"
    bl_label = "Toggle Outliner Vertical"
    bl_description = "Opens or closes the Outliner in a vertical side panel"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        screen = context.screen
        
        # 1. Identify the left-side Outliner (x < 10)
        left_outliner = next((a for a in screen.areas if a.ui_type == 'OUTLINER' and a.x < 10), None)

        # --- CASE: CLOSE ---
        if left_outliner:
            left_outliner.ui_type = 'VIEW_3D'
            with context.temp_override(screen=screen, area=left_outliner):
                bpy.ops.screen.area_close()
            return {'FINISHED'}

        # --- CASE: OPEN ---
        view_3d = next((a for a in screen.areas if a.type == 'VIEW_3D'), None)
        
        if view_3d:
            old_areas = set(screen.areas)
            
            with context.temp_override(screen=screen, area=view_3d):
                bpy.ops.screen.area_split(direction='VERTICAL', factor=0.2)
            
            def configure_outliner():
                new_areas = [a for a in screen.areas if a not in old_areas]
                
                if new_areas:
                    target = min(new_areas, key=lambda a: a.x)
                    target.ui_type = 'OUTLINER'
                    
                    space = target.spaces.active
                    if space and space.type == 'OUTLINER':
                        space.display_mode = 'LIBRARIES'
                        
                        # FIND THE WINDOW REGION
                        # Outliner operators require 'WINDOW' region to poll()
                        target_region = next((r for r in target.regions if r.type == 'WINDOW'), None)
                        
                        if target_region:
                            with context.temp_override(area=target, region=target_region):
                                # Now the operator has the correct Area AND Region context
                                try:
                                    bpy.ops.outliner.show_one_level()
                                except Exception as e:
                                    print(f"Outliner sync delay: {e}")
                return None

            bpy.app.timers.register(configure_outliner, first_interval=0.01) # Slightly longer delay for stability
                
        return {'FINISHED'}

class WM_OT_refresh_libraries(bpy.types.Operator):
    """Force an update of the library list based on scene contents"""
    bl_idname = "wm.refresh_libraries"
    bl_label = "Refresh Libraries List"

    def execute(self, context):
        update_linked_items_list(bpy.context.scene, bpy.context)
        return {'FINISHED'}


# =========================================================================
# LIST ACTIONS - HIDE AND UNHIDE MAIN ITEM
# =========================================================================


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
        first_lib = next((i for i in scene.linked_assets_list if i.is_library), None)
        if first_lib:
            target_state = not first_lib.is_expanded
            for item in scene.linked_assets_list:
                if item.is_library: item.is_expanded = target_state
        return {'FINISHED'}


# =========================================================================
# LIST ITEMS: LINKED FILES ACTIONS
# =========================================================================


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

class WM_OT_relocate_library(bpy.types.Operator, ImportHelper):
    """Changes the source path of the selected library"""
    bl_idname = "wm.relocate_library"
    bl_label = "Relocate Library"
    filter_glob: bpy.props.StringProperty(default="*.blend", options={'HIDDEN'})
    library_name: bpy.props.StringProperty()

    def execute(self, context):
        library = bpy.data.libraries.get(self.library_name)
        if library:
            library.filepath = self.filepath
            update_linked_items_list(context.scene, context)
            return {'FINISHED'}
        return {'CANCELLED'}


# =========================================================================
# OBJECT: VIEW & SELECTION
# =========================================================================


class OBJECT_OT_ToggleAllLinked(bpy.types.Operator):
    """Expands or collapses all libraries in the list"""
    bl_idname = "object.toggle_all_linked"
    bl_label = "Global Toggle"

    def execute(self, context):
        scene = context.scene
        first_lib = next((i for i in scene.linked_assets_list if i.is_library), None)
        if first_lib:
            target_state = not first_lib.is_expanded
            for item in scene.linked_assets_list:
                if item.is_library: item.is_expanded = target_state
        return {'FINISHED'}

class OBJECT_OT_SelectLinkedFromList(bpy.types.Operator):
    """Selects objects in the scene belonging to the chosen list item"""
    bl_idname = "object.select_linked_from_list"
    bl_label = "Select Instances"

    def execute(self, context):
        idx = context.scene.linked_assets_index
        bpy.ops.wm.reveal_all_objects()
        
        if idx < 0 or idx >= len(context.scene.linked_assets_list):
            return {'CANCELLED'}
            
        item = context.scene.linked_assets_list[idx]
        
        # 1. Capture the count from the internal function
        from .utils import select_instances_internal
        count = select_instances_internal(context.scene, context, item)
        
        # 2. Create the report message
        if count > 0:
            msg = f"Selected {count} object(s) from '{item.name}'"
            self.report({'INFO'}, msg)
        else:
            self.report({'WARNING'}, f"No visible instances of '{item.name}' found in this view layer.")

        return {'FINISHED'}

class OBJECT_OT_FocusLinkedFromList(bpy.types.Operator):
    """Selects objects and frames them in the 3D viewport"""
    bl_idname = "object.focus_linked_from_list"
    bl_label = "Focus Instances"
    bl_options = {'REGISTER', 'UNDO'}
   
    def execute(self, context):
        scene = context.scene
        bpy.ops.wm.reveal_all_objects()
        # Ensure we have a valid index
        if scene.linked_assets_index >= len(scene.linked_assets_list):
            return {'CANCELLED'}
            
        item = scene.linked_assets_list[scene.linked_assets_index]

        from .utils import select_instances_internal
        success = select_instances_internal(scene, context, item)

        if success:
            # Find the correct area and region to focus
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    for region in area.regions:
                        if region.type == 'WINDOW':
                            # --- THE FIX FOR BLENDER 4.0+ / 5.x ---
                            override = {'area': area, 'region': region}
                            with context.temp_override(**override):
                                bpy.ops.view3d.view_selected(use_all_regions=False)
                            # --------------------------------------
                            return {'FINISHED'}
        
        self.report({'WARNING'}, "No visible objects found to focus.")
        return {'CANCELLED'}

class WM_OT_reveal_all_objects(bpy.types.Operator):
    """Enable all global selection and visibility filters in the viewport"""
    bl_idname = "wm.reveal_all_objects"
    bl_label = "Reveal All Restrictions"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # 1. Clear individual object restrictions (Eye and Arrow in Outliner)
        for obj in context.scene.objects:
            obj.hide_viewport = False
            obj.hide_select = False

        # 2. Target the 'Object Type Visibility' (The Popover from your image)
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        # Ensure Master Overlays are on
                        space.overlay.show_overlays = True
                        
                        # --- DYNAMIC FIX FOR ALL TYPES ---
                        # This replaces the long list of manual properties
                        for attr in dir(space):
                            if attr.startswith("show_object_"):
                                try:
                                    setattr(space, attr, True)
                                except:
                                    # Skip read-only or non-boolean properties
                                    continue
                        
                        # Ensure selection highlighting is also enabled
                        if hasattr(space.overlay, "show_selection"):
                            space.overlay.show_selection = True

        return {'FINISHED'}


# =========================================================================
# OPERATORS: FILE MANAGEMENT
# =========================================================================
 
 
class WM_OT_cleanup_libraries(bpy.types.Operator):
    bl_idname = "wm.cleanup_libraries"
    bl_label = "Clean Up Broken Links"
    bl_description = "Remove all the broken linked files at once"
    bl_options = {'REGISTER', 'UNDO'}
    
    def invoke(self, context, event):
        """Opens a small 'OK?' popup at the mouse position before executing"""
        return context.window_manager.invoke_confirm(self, event)
    
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
    
class WM_OT_missing_files(bpy.types.Operator):
    bl_idname = "wm.missing_files"
    bl_label = "Missing Files"
    bl_description = "Open the file browser to search for missing external dependencies"
    
    def execute(self, context):
        bpy.ops.file.find_missing_files('INVOKE_DEFAULT')
        return {'FINISHED'} 


class WM_OT_path_relative(bpy.types.Operator):
    bl_idname = "wm.path_relative"
    bl_label = "Relative Paths"
    bl_description = "Convert all external linked paths to relative"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            # 1. Run the built-in Blender command
            bpy.ops.file.make_paths_relative()
            
            # 2. Trigger your custom list update to refresh the "is_broken" status
            from .utils import update_linked_items_list
            update_linked_items_list(context.scene)
            
            self.report({'INFO'}, "All paths converted to relative")
            
            # --- THE FIX: Return a set ---
            return {'FINISHED'} 
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to convert paths: {e}")
            return {'CANCELLED'}

class WM_OT_path_absolute(bpy.types.Operator):
    bl_idname = "wm.path_absolute"
    bl_label = "Make Paths Absolute"
    bl_description = "Convert all external linked paths to absolute (full system paths)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            # 1. Run the built-in Blender command for absolute paths
            bpy.ops.file.make_paths_absolute()
            
            # 2. Refresh your UI list to reflect any changes in 'is_broken' status
            # This ensures the warning icons update immediately
            from .utils import update_linked_items_list
            update_linked_items_list(context.scene)
            
            self.report({'INFO'}, "All paths converted to absolute")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to convert paths: {e}")
            return {'CANCELLED'}


classes = (
    WM_OT_library_prefs,
    WM_OT_set_asset_import_link,
    WM_OT_toggle_relative_path,
    WM_OT_set_asset_browser_import_link,
    
    WM_OT_link_files,
    WM_OT_show_asset_browser,
    
    WM_OT_toggle_linked_category,
    WM_OT_toggle_all_linked_categories,
    
    WM_OT_show_outliner_vertical,
    WM_OT_refresh_libraries,
    
    WM_OT_reload_library,
    WM_OT_open_library,
    WM_OT_delete_library,
    WM_OT_relocate_library,   
    
    OBJECT_OT_ToggleAllLinked,
    OBJECT_OT_SelectLinkedFromList,
    OBJECT_OT_FocusLinkedFromList,
    

    WM_OT_cleanup_libraries,
    WM_OT_missing_files,
    WM_OT_path_relative,
    WM_OT_path_absolute,
    
    WM_OT_reveal_all_objects,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)