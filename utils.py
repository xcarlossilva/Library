import bpy
import os

    
def update_linked_items_list(scene=None, context=None):
    """Rebuilds the UI list while maintaining selection and expansion states."""
    
    # 1. Setup & Fallback
    if scene is None:
        scene = bpy.context.scene
    
    # 2. Safety Lock: Prevent recursion if the handler triggers during an update
    if scene.get("is_updating_linked_list", False):
        return None
        
    scene.is_updating_linked_list = True

    try:
        # 3. STORE STATE: Remember what was selected and expanded before clearing
        selected_name = ""
        if 0 <= scene.linked_assets_index < len(scene.linked_assets_list):
            selected_name = scene.linked_assets_list[scene.linked_assets_index].name

        expansion_states = {
            item.lib_path: item.is_expanded 
            for item in scene.linked_assets_list if item.is_library
        }

        # 4. CLEAR: Wipe the list to start fresh
        scene.linked_assets_list.clear()
        lib_groups = {}

        # 5. SCAN: Find all linked Collections and Objects
        for obj in scene.objects:
            lib = None
            asset_info = None

            # Case A: Linked Collections (Instances/Empties)
            if obj.type == 'EMPTY' and obj.instance_collection and obj.instance_collection.library:
                coll = obj.instance_collection
                lib = coll.library
                asset_info = (coll.name, True) # (Name, IsCollection)

            # Case B: Linked Objects (Directly linked meshes/lights/etc)
            elif obj.library and obj.data:
                lib = obj.library
                asset_info = (obj.data.name, False)

            if lib and asset_info:
                lib_name = lib.name
                if lib_name not in lib_groups:
                    # Resolve the path to absolute so os.path can find it
                    abs_path = bpy.path.abspath(lib.filepath)
                    is_broken = not os.path.exists(abs_path)
                    
                    lib_groups[lib_name] = {
                    "path": lib.filepath, 
                    "assets": set(),
                    "is_broken": is_broken
                    }
                lib_groups[lib_name]["assets"].add(asset_info)

        # 6. REBUILD: Add the data back to the CollectionProperty
        for lib_name in sorted(lib_groups.keys()):
            data = lib_groups[lib_name]
            
            # Add Library Header
            parent = scene.linked_assets_list.add()
            parent.name = lib_name
            parent.is_library = True
            parent.lib_path = data["path"]
            parent.is_expanded = expansion_states.get(data["path"], False)
            parent.is_broken = data["is_broken"]

            # Add Child Assets
            for asset_name, is_coll in sorted(data["assets"]):
                child = scene.linked_assets_list.add()
                child.name = asset_name
                child.asset_id = asset_name
                child.is_collection = is_coll
                child.is_library = False
                child.lib_path = data["path"]

        # 7. RESTORE SELECTION: Find the item we had selected before the refresh
        new_index = 0
        if selected_name:
            for i, item in enumerate(scene.linked_assets_list):
                if item.name == selected_name:
                    new_index = i
                    break
        
        # 8. CLAMP & APPLY: Final safety check for the index
        if len(scene.linked_assets_list) > 0:
            scene.linked_assets_index = min(new_index, len(scene.linked_assets_list) - 1)
        else:
            scene.linked_assets_index = 0

    except Exception as e:
        print(f"Library Manager Update Error: {e}")
    
    finally:
        # 9. UNLOCK: Always release the lock so the next update can run
        scene.is_updating_linked_list = False
    
    return None # Required for Blender Timers


def select_instances_internal(scene, context, item):
    """Helper to select objects in the 3D view based on list selection"""
    bpy.ops.object.select_all(action='DESELECT')
    found = False
    for obj in scene.objects:
        match = False
        if item.is_library:
            lib = obj.instance_collection.library if (obj.type == 'EMPTY' and obj.instance_collection) else obj.library
            if lib and lib.filepath == item.lib_path:
                match = True
        else:
            if item.is_collection:
                if obj.type == 'EMPTY' and obj.instance_collection and obj.instance_collection.name == item.asset_id:
                    match = True
            else:
                if obj.data and obj.data.name == item.asset_id:
                    match = True
        
        if match:
            obj.select_set(True)
            context.view_layer.objects.active = obj
            found = True
    return found
   

@bpy.app.handlers.persistent
def auto_update_linked_handler(scene, depsgraph):
    """Triggers list refresh when the scene geometry changes"""
    if any(update.is_updated_geometry for update in depsgraph.updates):
        update_linked_items_list(bpy.context.scene, bpy.context)
        
        # We use a Timer to call the update 0.1 seconds later.
        # This prevents the "Context is Read Only" error common in Handlers.
        if not bpy.app.timers.is_registered(update_linked_items_list):
            bpy.app.timers.register(lambda: update_linked_items_list(scene), first_interval=0.1)
