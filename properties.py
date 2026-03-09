import bpy

# =========================================================================
# DATA STRUCTURES
# =========================================================================

class LinkedAssetItem(bpy.types.PropertyGroup):
    """Data container for items displayed in the UI List"""
    name: bpy.props.StringProperty() # Added this - UI Lists need a name property
    is_library: bpy.props.BoolProperty()
    is_expanded: bpy.props.BoolProperty(default=False)
    lib_path: bpy.props.StringProperty()
    asset_id: bpy.props.StringProperty()
    is_broken: bpy.props.BoolProperty(default=False) # <--- Add this
    is_collection: bpy.props.BoolProperty()
    # In your properties.py or wherever your list item is defined:
    is_empty_link: bpy.props.BoolProperty(name="Is Empty Link", default=False)
# =========================================================================
# REGISTRATION
# =========================================================================

classes = (
    LinkedAssetItem,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # This is the "Extra Step" that fixes your property error:
    bpy.types.Scene.linked_assets_list = bpy.props.CollectionProperty(type=LinkedAssetItem)
    bpy.types.Scene.linked_assets_index = bpy.props.IntProperty()
    bpy.types.Scene.is_updating_linked_list = bpy.props.BoolProperty(default=False)

def unregister():
    # Clean up properties
    del bpy.types.Scene.linked_assets_list
    del bpy.types.Scene.linked_assets_index
    del bpy.types.Scene.is_updating_linked_list
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)