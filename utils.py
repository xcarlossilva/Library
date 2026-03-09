import bpy
import os

    
def update_linked_items_list(scene=None, context=None):
    """Rebuilds the list from Library data, ensuring assets persist after scene deletion."""
    
    if scene is None: 
        scene = bpy.context.scene
    
    # Prevents recursion errors
    if scene.get("is_updating_linked_list", False):
        return None
        
    scene.is_updating_linked_list = True

    try:
        # --- 1. STORE CURRENT STATE ---
        selected_name = ""
        if 0 <= scene.linked_assets_index < len(scene.linked_assets_list):
            selected_name = scene.linked_assets_list[scene.linked_assets_index].name

        expansion_states = {
            item.lib_path: item.is_expanded 
            for item in scene.linked_assets_list if item.is_library
        }

        # --- 2. RESET LIST ---
        scene.linked_assets_list.clear()
        lib_groups = {}

        # --- 3. SCAN ALL LIBRARIES & THEIR ASSETS ---
        # This part ensures that even if 0 instances exist in the scene, 
        # the asset remains visible in the UI list.
        for lib in bpy.data.libraries:
            abs_path = bpy.path.abspath(lib.filepath)
            lib_groups[lib.name] = {
                "path": lib.filepath, 
                "assets": set(),
                "is_broken": not os.path.exists(abs_path)
            }

            # Deep Scan: Find Collections in THIS library marked as Assets
            for coll in bpy.data.collections:
                if coll.library == lib and coll.asset_data:
                    lib_groups[lib.name]["assets"].add((coll.name, True))

            # Deep Scan: Find Objects in THIS library marked as Assets
            for obj_data in bpy.data.objects:
                if obj_data.library == lib and obj_data.asset_data:
                    lib_groups[lib.name]["assets"].add((obj_data.name, False))

        # --- 4. SCAN SCENE FOR ACTIVE USAGE ---
        # We build a lookup set to determine which items are 'Ghosts'
        assets_in_scene = set()
        for obj in scene.objects:
            # Check for Collection Instances (Empties)
            if obj.instance_collection:
                assets_in_scene.add(obj.instance_collection.name)
            
            # Check for Direct Object Links (Mesh/Data)
            if obj.library:
                assets_in_scene.add(obj.name)
            if obj.data and obj.data.library:
                assets_in_scene.add(obj.data.name)

        # --- 5. REBUILD THE UI COLLECTION ---
        for lib_name in sorted(lib_groups.keys()):
            data = lib_groups[lib_name]
            
            # Add Library Header
            parent = scene.linked_assets_list.add()
            parent.name = lib_name
            parent.is_library = True
            parent.lib_path = data["path"]
            parent.is_expanded = expansion_states.get(data["path"], False)
            parent.is_broken = data["is_broken"]
            
            # Library header status: ghost if no child assets are in the scene
            lib_in_use = any(name in assets_in_scene for name, is_c in data["assets"])
            parent.is_empty_link = not lib_in_use

            # Add Asset Sub-items
            for asset_name, is_coll in sorted(data["assets"]):
                child = scene.linked_assets_list.add()
                child.name = asset_name
                child.is_collection = is_coll
                child.is_library = False
                child.lib_path = data["path"]
                child.is_broken = data["is_broken"]
                
                # If it's in the scene, it's a solid item. If not, it's a ghost.
                child.is_empty_link = asset_name not in assets_in_scene

        # --- 6. RESTORE SELECTION ---
        num_items = len(scene.linked_assets_list)
        new_index = 0
        if selected_name and num_items > 0:
            for i, item in enumerate(scene.linked_assets_list):
                if item.name == selected_name:
                    new_index = i
                    break
        
        scene.linked_assets_index = min(new_index, num_items - 1) if num_items > 0 else 0

    except Exception as e:
        print(f"Library Manager Error: {e}")
    
    finally:
        scene.is_updating_linked_list = False


def select_instances_internal(scene, context, item):
    # 1. Clear current selection to start fresh
    bpy.ops.object.select_all(action='DESELECT')
    
    count = 0
    target_name = item.name # This is the name from your UI list
    
    # 2. Iterate through all objects in the current View Layer
    for obj in context.view_layer.objects:
        is_match = False
        
        # --- CHECK CATEGORY 1: Linked Data (Lights, Meshes, Cameras, etc.) ---
        if obj.data:
            # Check if this data comes from the specific library file
            if obj.data.library and obj.data.library.name == target_name:
                is_match = True
            # Check if the data name itself matches (for appended/local items)
            elif obj.data.name == target_name:
                is_match = True
                
        # --- CHECK CATEGORY 2: Collection Instances (The 'Empty' group) ---
        if not is_match and obj.instance_type == 'COLLECTION' and obj.instance_collection:
            if obj.instance_collection.name == target_name:
                is_match = True
            # Also check if the collection itself is linked from the target library
            elif obj.instance_collection.library and obj.instance_collection.library.name == target_name:
                is_match = True

        # --- CHECK CATEGORY 3: Object-Level Library Link ---
        if not is_match and obj.library and obj.library.name == target_name:
            is_match = True

        # 3. If any of the above matched, select the object
        if is_match:
            obj.select_set(True)
            # Make the last one found the 'Active' object for framing
            context.view_layer.objects.active = obj
            count += 1
            
    return count
   

@bpy.app.handlers.persistent
def auto_update_linked_handler(scene, depsgraph):
    """Triggers list refresh when the scene geometry changes"""
    if any(update.is_updated_geometry for update in depsgraph.updates):
        update_linked_items_list(bpy.context.scene, bpy.context)
        
        # We use a Timer to call the update 0.1 seconds later.
        # This prevents the "Context is Read Only" error common in Handlers.
        if not bpy.app.timers.is_registered(update_linked_items_list):
            bpy.app.timers.register(lambda: update_linked_items_list(scene), first_interval=0.1)
