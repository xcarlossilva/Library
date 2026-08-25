import bpy
import os

def absolute_path(relpath):
    return os.path.abspath(bpy.path.abspath(relpath))

def clamp_library_index(scene):
    library_count = len(bpy.data.libraries)
    if library_count == 0:
        scene.libraries_index = 0
        return False
    if scene.libraries_index >= library_count:
        scene.libraries_index = library_count - 1
    return True

def update_linked_items_list(self, context):
    scene = context.scene
    if not bpy.data.libraries or scene.libraries_index >= len(bpy.data.libraries):
        scene.linked_items.clear()
        return
    
    selected_library = bpy.data.libraries[scene.libraries_index]
    scene.linked_items.clear()
    
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