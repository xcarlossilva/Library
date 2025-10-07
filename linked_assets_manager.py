import bpy
import os

def absolute_path(relpath):
    return os.path.abspath(bpy.path.abspath(relpath))

class VIEW3D_PT_libraries_list(bpy.types.Panel):
    """Creates a Panel in the 3D Viewport under the Item tab listing library file paths"""
    bl_label = "Library File Paths"
    bl_idname = "VIEW3D_PT_libraries_list"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Item'

    def draw(self, context):
        layout = self.layout
        layout.label(text="Library File Paths in Scene:")
        layout.template_list("VIEW3D_UL_libraries", "", bpy.data, "libraries", context.scene, "libraries_index")
        layout.operator("wm.refresh_libraries", text="Refresh List", icon="FILE_REFRESH")
        
        # Add the editable field below the refresh button
        if bpy.data.libraries:
            selected_library = bpy.data.libraries[context.scene.libraries_index]
            row = layout.row()
            row.prop(selected_library, "filepath", text="Filepath")

class VIEW3D_UL_libraries(bpy.types.UIList):
    """UIList for displaying libraries"""
    bl_idname = "VIEW3D_UL_libraries"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        library = item
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            icon = 'FILE_FOLDER' if os.path.exists(absolute_path(library.filepath)) else 'ERROR'
            layout.label(text=library.name, icon=icon)
            
            if os.path.exists(absolute_path(library.filepath)):
                row = layout.row(align=True)
                op = row.operator("wm.reload_library", text="", icon="FILE_REFRESH", emboss=False)
                op.filepath = library.filepath
                op = row.operator("wm.open_library", text="", icon="BLENDER", emboss=False)
                op.filepath = library.filepath
                op = row.operator("wm.delete_library", text="", icon="X", emboss=False)
                op.filepath = library.filepath

class WM_OT_reload_library(bpy.types.Operator):
    """Reload Library"""
    bl_idname = "wm.reload_library"
    bl_label = "Reload Library"
    
    filepath: bpy.props.StringProperty()

    def execute(self, context):
        try:
            library = next(lib for lib in bpy.data.libraries if lib.filepath == self.filepath)
            library.reload()
            self.report({'INFO'}, f"Reloaded: {self.filepath}")
        except StopIteration:
            self.report({'ERROR'}, f"Library not found: {self.filepath}")
        return {'FINISHED'}

class WM_OT_open_library(bpy.types.Operator):
    """Open Library"""
    bl_idname = "wm.open_library"
    bl_label = "Open Library"
    
    filepath: bpy.props.StringProperty()

    def execute(self, context):
        try:
            library = next(lib for lib in bpy.data.libraries if lib.filepath == self.filepath)
            bpy.ops.wm.path_open(filepath=library.filepath)
            self.report({'INFO'}, f"Opened: {self.filepath}")
        except StopIteration:
            self.report({'ERROR'}, f"Library not found: {self.filepath}")
        return {'FINISHED'}

class WM_OT_delete_library(bpy.types.Operator):
    """Delete Library"""
    bl_idname = "wm.delete_library"
    bl_label = "Delete Library"
    
    filepath: bpy.props.StringProperty()

    def execute(self, context):
        try:
            library = next(lib for lib in bpy.data.libraries if lib.filepath == self.filepath)
            bpy.data.libraries.remove(library)
            self.report({'INFO'}, f"Deleted: {self.filepath}")
        except StopIteration:
            self.report({'ERROR'}, f"Library not found: {self.filepath}")
        return {'FINISHED'}

class WM_OT_refresh_libraries(bpy.types.Operator):
    """Refresh Libraries List"""
    bl_idname = "wm.refresh_libraries"
    bl_label = "Refresh Libraries List"

    def execute(self, context):
        # No need to clear libraries, just refresh the UI
        self.report({'INFO'}, "Libraries list refreshed")
        return {'FINISHED'}

def register():
    bpy.utils.register_class(VIEW3D_PT_libraries_list)
    bpy.utils.register_class(VIEW3D_UL_libraries)
    bpy.utils.register_class(WM_OT_reload_library)
    bpy.utils.register_class(WM_OT_open_library)
    bpy.utils.register_class(WM_OT_delete_library)
    bpy.utils.register_class(WM_OT_refresh_libraries)
    bpy.types.Scene.libraries_index = bpy.props.IntProperty(name="Index for libraries", default=0)

def unregister():
    bpy.utils.unregister_class(VIEW3D_PT_libraries_list)
    bpy.utils.unregister_class(VIEW3D_UL_libraries)
    bpy.utils.unregister_class(WM_OT_reload_library)
    bpy.utils.unregister_class(WM_OT_open_library)
    bpy.utils.unregister_class(WM_OT_delete_library)
    bpy.utils.unregister_class(WM_OT_refresh_libraries)
    del bpy.types.Scene.libraries_index

if __name__ == "__main__":
    register()
