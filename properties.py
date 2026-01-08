import bpy

class LinkedCategory(bpy.types.PropertyGroup):
    is_expanded: bpy.props.BoolProperty(default=True)

class LinkedItem(bpy.types.PropertyGroup):
    icon: bpy.props.StringProperty()
    is_category: bpy.props.BoolProperty(default=False)
    category_icon: bpy.props.StringProperty()

classes = (LinkedCategory, LinkedItem)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)