bl_info = {
    "name": "Library Manager",
    "author": "Carlos Silva",
    "version": (1, 0),
    "blender": (5, 1, 0),
    "location": "View3D > Library Manager ",
    "description": "Manage and track linked data blocks and libraries.",
    "category": "Interface",
}

import bpy
import importlib

# Import your scripts
from . import properties
from . import operators
from . import ui
from . import utils

# Import the handler specifically for the append/remove logic
from .utils import auto_update_linked_handler

# Force reload sub-modules for fast updates during development
importlib.reload(properties)
importlib.reload(operators)
importlib.reload(ui)
importlib.reload(utils)

def register():
    # 1. Properties MUST be first
    properties.register()
    
    # 2. Operators second
    operators.register()
    
    # 3. UI last (depends on the above)
    ui.register()
    
    # 4. Add the Handler
    if auto_update_linked_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(auto_update_linked_handler)

def unregister():
    # 1. Remove the Handler first
    if auto_update_linked_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(auto_update_linked_handler)
    
    # 2. Unregister in REVERSE order (Note the indentation here!)
    ui.unregister()
    operators.unregister()
    properties.unregister()

if __name__ == "__main__":
    register()