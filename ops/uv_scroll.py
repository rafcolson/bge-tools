import bpy
from . import utils as ut

TOOL_NAME = "bge_tools_uv_scroll"
LABEL_UV_MAP = "UV Map:"
LABEL_SPRITES = "Sprites:"
LABEL_SEQUENCE = "Sequence:"

PROP_NAME_SPRITES_X = "SPRITES_X"
PROP_NAME_SPRITES_Y = "SPRITES_Y"
PROP_NAME_SEQUENCE = "SEQUENCE"
PROP_NAME_LOOP = "LOOP"
PROP_NAME_PINGPONG = "PINGPONG"
PROP_NAME_LINKED = "LINKED"

PROP_SPRITES_X_DEFAULT = 8
PROP_SPRITES_Y_DEFAULT = 8
PROP_SEQUENCE_DEFAULT = "0-63"
PROP_SKIP_DEFAULT = 0
PROP_LOOP_DEFAULT = -1
PROP_PINGPONG_DEFAULT = False
PROP_LINKED_DEFAULT = True

ERR_MSG_WRONG_OBJECT = "Selected object not suited for this application"
ERR_MSG_WRONG_LAYER = "Selected object not in active layer"
ERR_MSG_NO_OBJECT_SELECTED = "No object selected"

class UVScroll(bpy.types.Operator):
	
	bl_description = "Manages animation of a sprite sheet for the Blender Game Engine"
	bl_idname = "bge_tools.uv_scroll"
	bl_label = "BGE-Tools: UV Scroll"
	bl_options = {"REGISTER", "UNDO"}
	
	prop_uv_texture_name = bpy.props.StringProperty(name="UV Map", description="UV Map to be scrolled")
	prop_sprites_x = bpy.props.IntProperty(name="X", description="Number of sprites horizontally (X)", min=1)
	prop_sprites_y = bpy.props.IntProperty(name="Y", description="Number of sprites horizontally (Y)", min=1)
	prop_sequence = bpy.props.StringProperty(name="", description="Animation sequence. Example: \'0*2, 1-5, 7\' gives \'0, 0, 0, 1, 2, 3, 4, 5, 7\'")
	prop_skip = bpy.props.IntProperty(name="Skip", description="Number of logic tics to skip", min=0)
	prop_loop = bpy.props.IntProperty(name="Loop", description="Loop count; -1 infinite", min=-1)
	prop_pingpong = bpy.props.BoolProperty(name="Pingpong", description="Reverse the sequence with every loop")
	prop_linked = bpy.props.BoolProperty(name="Linked", description="Whether the mesh should be unique")
	
	def invoke(self, context, event):
		
		def init():
			object = context.object
			sensors = object.game.sensors
			properties = object.game.properties
			self.uv_textures = object.data.uv_textures
			self.prop_uv_texture_name = self.uv_textures[0].name if self.uv_textures else ""
			self.prop_sequence = properties[PROP_NAME_SEQUENCE].value if PROP_NAME_SEQUENCE in properties else PROP_SEQUENCE_DEFAULT
			self.prop_sprites_x = properties[PROP_NAME_SPRITES_X].value if PROP_NAME_SPRITES_X in properties else PROP_SPRITES_X_DEFAULT
			self.prop_sprites_y = properties[PROP_NAME_SPRITES_Y].value if PROP_NAME_SPRITES_Y in properties else PROP_SPRITES_Y_DEFAULT
			module_name = TOOL_NAME + "_update"
			self.prop_skip = sensors[module_name].tick_skip if module_name in sensors else PROP_SKIP_DEFAULT
			self.prop_loop = properties[PROP_NAME_LOOP].value if PROP_NAME_LOOP in properties else PROP_LOOP_DEFAULT
			self.prop_pingpong = properties[PROP_NAME_PINGPONG].value if PROP_NAME_PINGPONG in properties else PROP_PINGPONG_DEFAULT
			self.prop_linked = properties[PROP_NAME_LINKED].value if PROP_NAME_LINKED in properties else PROP_LINKED_DEFAULT
			self.duplicate = object.data in [o.data for o in bpy.data.objects if o != object]
			self.error = None
			
		if context.object:
			if context.object.data:
				if context.object in context.selected_editable_objects:
					init()
				else:
					self.error = ERR_MSG_WRONG_LAYER
			else:
				self.error = ERR_MSG_WRONG_OBJECT
		else:
			self.error = ERR_MSG_NO_OBJECT_SELECTED
			
		return context.window_manager.invoke_props_dialog(self, width=480)
		
	def draw(self, context):
		layout = self.layout
		box = layout.box()
		
		if self.error:
			box.label(self.error, icon="ERROR")
			return
			
		row = box.row()
		split = row.split(0.25, True)
		col = split.column()
		col.label(LABEL_UV_MAP)
		
		split = split.split()
		row = split.row(True)
		row.prop_search(self, "prop_uv_texture_name",  context.object.data, "uv_textures", "")
		row.operator("mesh.uv_texture_remove", text="", icon="ZOOMOUT")
		row.operator("mesh.uv_texture_add", text="", icon="ZOOMIN")
		
		row = box.row(True)
		split = row.split(0.25, True)
		col = split.column()
		col.label(LABEL_SEQUENCE)
		
		split = split.split()
		row = split.row(True)
		row.prop(self, "prop_sequence")
		
		row = box.row(True)
		split = row.split(0.25, True)
		col = split.column()
		col.label(LABEL_SPRITES)
		
		split = split.split()
		row = split.row(True)
		row.prop(self, "prop_sprites_x")
		row.prop(self, "prop_sprites_y")
		
		row = box.row(True)
		row.prop(self, "prop_skip")
		row.prop(self, "prop_loop")
		row.prop(self, "prop_pingpong", toggle=True)
		
		if self.duplicate or not self.prop_linked:
			row.prop(self, "prop_linked", toggle=True)
			
		row.operator("bge_tools.uv_scroll_clear", text="", icon="X")
		
	def execute(self, context):
		
		if self.error:
			return {"CANCELLED"}
			
		def generate_game_logic():
			ut.add_game_property(context.object, PROP_NAME_SEQUENCE, self.prop_sequence)
			ut.add_game_property(context.object, PROP_NAME_SPRITES_X, self.prop_sprites_x)
			ut.add_game_property(context.object, PROP_NAME_SPRITES_Y, self.prop_sprites_y)
			ut.add_game_property(context.object, PROP_NAME_LOOP, self.prop_loop)
			ut.add_game_property(context.object, PROP_NAME_PINGPONG, self.prop_pingpong)
			ut.add_game_property(context.object, PROP_NAME_LINKED, self.prop_linked)
			ut.remove_logic(context.object, TOOL_NAME)
			ut.add_text(self.bl_idname, True, TOOL_NAME)
			ut.add_logic_python(context.object, TOOL_NAME, "update", True, tick_skip=self.prop_skip)
			
		def update_uv_texture():
			
			if not self.prop_uv_texture_name:
				return
				
			if self.prop_uv_texture_name not in self.uv_textures:
				return
				
			uv_texture = self.uv_textures[self.prop_uv_texture_name]
			uv_texture.active = True
			uv_texture.active_render = True
			bpy.ops.object.mode_set(mode="EDIT")
			bpy.ops.mesh.select_all(action="SELECT")
			area_type = context.area.type
			context.area.type = "IMAGE_EDITOR"
			bpy.ops.uv.reset()
			bpy.ops.uv.select_all(action="SELECT")
			bpy.ops.uv.cursor_set(location=(0.0, 0.0))
			context.space_data.pivot_point = "CURSOR"
			bpy.ops.transform.resize(value=[1 / self.prop_sprites_x, 1 / self.prop_sprites_y, 1])
			context.area.type = area_type
			bpy.ops.uv.select_all(action="DESELECT")
			bpy.ops.mesh.select_all(action="DESELECT")
			bpy.ops.object.mode_set(mode="OBJECT")
			
		generate_game_logic()
		update_uv_texture()
		
		return {"PASS_THROUGH"}
		
class UVScrollClear(bpy.types.Operator):
	
	bl_description = "Clear"
	bl_idname = "bge_tools.uv_scroll_clear"
	bl_label = "BGE-Tools: UV Scroll Clear"
	bl_options = {"INTERNAL"}
	
	def execute(self, context):
		prop_names = [
			PROP_NAME_SPRITES_X,
			PROP_NAME_SPRITES_Y,
			PROP_NAME_SEQUENCE,
			PROP_NAME_LOOP,
			PROP_NAME_PINGPONG,
			PROP_NAME_LINKED
		]
		ut.remove_game_properties(context.object, prop_names)
		ut.remove_logic(context.object, TOOL_NAME)
		ut.remove_text(TOOL_NAME)
		
		return {"FINISHED"}
		
def register():
	bpy.utils.register_class(UVScroll)
	bpy.utils.register_class(UVScrollClear)
	
def unregister():
	bpy.utils.unregister_class(UVScroll)
	bpy.utils.unregister_class(UVScrollClear)
	
if __name__ == "__main__":
	register()
	