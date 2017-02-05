bl_info = {
	"name": "Raco's BGE Tools",
	"author": "Raf Colson",
	"version": (0, 0, 1),
	"blender": (2, 78, 0),
	"location": "SpaceBar Search -> BGE-Tools: UV Scroll",
	"description": "Tools for the Blender Game Engine",
	"warning": "",
	"wiki_url": "https://github.com/rafcolson/bge-tools/wiki",
	"tracker_url": "https://github.com/rafcolson/bge-tools/issues",
	"category": "Game Engine"
}

from . import ops

def register():
	for m in ops.modules:
		m.register()

def unregister():
	for m in ops.modules:
		m.unregister()
