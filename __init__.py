bl_info = {
    "name": "Library Manager",
    "author": "Your Name",
    "version": (1, 0),
    "blender": (5, 0, 0),
    "location": "View3D > Item > Library Manager ",
    "description": "Manage and track linked data blocks and libraries.",
    "category": "Interface",
}

import bpy
import importlib

def register():
    # 1. Dynamically import modules inside register
    from . import properties, operators, ui, utils
    
    # 2. Force reload sub-modules for fast updates
    importlib.reload(properties)
    importlib.reload(operators)
    importlib.reload(ui)
    importlib.reload(utils)

    # 3. Define classes (Ensure all names match your file contents)
    classes = (
        properties.LinkedCategory,
        properties.LinkedItem,
        operators.WM_OT_link_files,
        operators.WM_OT_library_prefs,
        operators.WM_OT_toggle_asset_browser,
        operators.WM_OT_set_asset_import_link,
        operators.WM_OT_toggle_linked_category,
        operators.WM_OT_toggle_all_linked_categories,
        operators.WM_OT_select_linked_objects,
        operators.WM_OT_reload_library,
        operators.WM_OT_open_library,
        operators.WM_OT_delete_library,
        operators.WM_OT_cleanup_libraries,
        operators.WM_OT_refresh_libraries,
        operators.WM_OT_missing_files,
        ui.VIEW3D_UL_libraries,
        ui.VIEW3D_UL_linked_items,
        ui.VIEW3D_PT_libraries_list,
        # menu.WM_MT_asset_import_modes,
    )

    for cls in classes:
        bpy.utils.register_class(cls)
    
    # 4. Register Scene Properties
    bpy.types.Scene.libraries_index = bpy.props.IntProperty(
        name="Index for libraries", 
        update=operators.update_linked_items_list
    )
    bpy.types.Scene.linked_categories = bpy.props.CollectionProperty(type=properties.LinkedCategory)
    bpy.types.Scene.linked_items = bpy.props.CollectionProperty(type=properties.LinkedItem)
    bpy.types.Scene.linked_items_index = bpy.props.IntProperty(name="Index for linked items")
    bpy.types.Scene.linked_list_expanded = bpy.props.BoolProperty(name="Expanded", default=True)
    bpy.types.Scene.linked_items_search = bpy.props.StringProperty(name="Search", default="")

def unregister():
    # Local imports for unregistering
    from . import properties, operators, ui
    
    classes = (
        properties.LinkedCategory,
        properties.LinkedItem,
        operators.WM_OT_link_files,
        operators.WM_OT_library_prefs,
        operators.WM_OT_toggle_asset_browser,
        operators.WM_OT_set_asset_import_link,
        operators.WM_OT_toggle_linked_category,
        operators.WM_OT_toggle_all_linked_categories,
        operators.WM_OT_select_linked_objects,
        operators.WM_OT_reload_library,
        operators.WM_OT_open_library,
        operators.WM_OT_delete_library,
        operators.WM_OT_cleanup_libraries,
        operators.WM_OT_refresh_libraries,
        operators.WM_OT_missing_files,
        ui.VIEW3D_UL_libraries,
        ui.VIEW3D_UL_linked_items,
        ui.VIEW3D_PT_libraries_list,
        # menu.WM_MT_asset_import_modes,
    )

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    # Clean up properties
    del bpy.types.Scene.libraries_index
    del bpy.types.Scene.linked_categories
    del bpy.types.Scene.linked_items
    del bpy.types.Scene.linked_items_index
    del bpy.types.Scene.linked_list_expanded
    del bpy.types.Scene.linked_items_search

if __name__ == "__main__":
    register()