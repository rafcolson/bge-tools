import bpy
import os

p = bpy.props
j = os.path.join

class UVScroll(bpy.types.Operator):
	
	bl_description = "Manages animation of a sprite sheet for the Blender Game Engine"
	bl_idname = "bge_tools.uv_scroll"
	bl_label = "BGE-Tools: UV Scroll"
	bl_options = {"REGISTER", "UNDO"}
	
	tool_name = "bge_tools_uv_scroll"
	script_name = tool_name + ".py"
	module_name = tool_name + ".main"
	script_path = j("bge-tools", "gen", script_name)
	
	err_msg_wrong_object = "Selected object not suited for this application"
	err_msg_wrong_layer = "Selected object not in active layer"
	err_msg_no_object_selected = "No object selected"
	
	sprites_default = (8, 8)
	sequence_default = "0-63"
	skip_default = 0
	loop_default = -1
	pingpong_default = False
	unlink_default = False
	
	uv_tex_name = p.StringProperty(name="UV Map", description="UV Map to be modified")
	sprites = p.IntVectorProperty(name="Sprites", description="Number of sprites horizontally (X) and vertically (Y)", min=1, subtype="XYZ", size=2)
	sequence = p.StringProperty(name="Sequence", description="Animation sequence. Example: \'0*2, 1-5, 7\' gives \'0, 0, 0, 1, 2, 3, 4, 5, 7\'")
	skip = p.IntProperty(name="Skip", description="Number of logic tics to skip", min=0)
	loop = p.IntProperty(name="Loop", description="Loop count; -1 infinite", min=-1)
	pingpong = p.BoolProperty(name="Pingpong", description="Reverse the sequence with every loop")
	unlink = p.BoolProperty(name="Unlink", description="Give the object a unique mesh in game")
	clear = p.BoolProperty(name="Clear", description="Clear Game Properties, Logic Bricks and Internal Script, and UV Map if selected")
	
	def invoke(self, context, event):
		
		def init(self, uv_textures, object_props):
			self.sprites = [int(s) for s in object_props["sprites"].value.replace(" ", "").split(",")] if "sprites" in object_props else self.sprites_default
			self.sequence = object_props["sequence"].value if "sequence" in object_props else self.sequence_default
			sensors = self.object.game.sensors
			self.skip = sensors[self.tool_name].tick_skip if self.tool_name in sensors else self.skip_default
			self.loop = object_props["loop"].value if "loop" in object_props else self.loop_default
			self.pingpong = object_props["pingpong"].value if "pingpong" in object_props else self.pingpong_default
			self.unlink = object_props["unlink"].value if "unlink" in object_props else self.unlink_default
			self.uv_tex_name = uv_textures[0].name if uv_textures else ""
			
		self.object = context.object
		if self.object:
			self.mesh = self.object.data
			if self.mesh:
				if self.object in context.selected_editable_objects:
					init(self, self.mesh.uv_textures, self.object.game.properties)
					l = list(bpy.data.objects)
					l.remove(self.object)
					self.linked = True if self.mesh in [o.data for o in l] else False
					self.error = None
				else:
					self.error = err_msg_wrong_layer
			else:
				self.error = err_msg_wrong_object
		else:
			self.error = err_msg_no_object_selected
			
		return context.window_manager.invoke_props_dialog(self, width=400)
		
	def draw(self, context):
		layout = self.layout
		box = layout.box()
		col = box.column()
		row = col.row()
		
		if self.error:
			row.label(self.error, icon="ERROR")
			return
			
		row.prop_search(self, "uv_tex_name",  self.mesh, "uv_textures")
		row.operator("mesh.uv_texture_add", text="", icon="ZOOMIN")
		
		row = col.row()
		row.prop(self, "sprites")
		
		row = col.row()
		row.prop(self, "sequence")
		
		row = col.row()
		row.prop(self, "skip")
		row.prop(self, "loop")
		row.prop(self, "pingpong", toggle=True)
		
		if self.linked:
			row.prop(self, "unlink", toggle=True)
			
		row = col.row()
		row.prop(self, "clear", toggle=True)
		
	def execute(self, context):
		
		if self.error:
			return {"CANCELLED"}
			
		object_props = self.object.game.properties
		uv_textures = self.mesh.uv_textures
		uv_textures_names = [uv.name for uv in uv_textures]
		texts = bpy.data.texts
		area_type = context.area.type
		ops = bpy.ops
		
		def clear_data(self):
			
			for i in range(len(object_props)):
				ops.object.game_property_remove(i)
				
			ops.logic.controller_remove(controller=self.tool_name, object=self.object.name)
			ops.logic.sensor_remove(sensor=self.tool_name, object=self.object.name)
			
			objects = []
			for o in bpy.data.objects:
				if o.data != self.mesh:
					objects.append(o)
					
			for object in objects:
				for cont in object.game.controllers:
					if cont.name == self.tool_name:
						return
						
			if self.script_name in texts:
				texts.remove(texts[self.script_name], do_unlink=True)
				
		def add_properties(self):
			if "sprites" not in object_props:
				ops.object.game_property_new(type="STRING", name="sprites")
			if "sequence" not in object_props:
				ops.object.game_property_new(type="STRING", name="sequence")
			if "loop" not in object_props:
				ops.object.game_property_new(type="INT", name="loop")
			if "pingpong" not in object_props:
				ops.object.game_property_new(type="BOOL", name="pingpong")
			if "unlink" not in object_props:
				ops.object.game_property_new(type="BOOL", name="unlink")
				
		def set_properties(self):
			object_props["sprites"].value = str(list(self.sprites))[1:-1]
			object_props["sequence"].value = self.sequence
			object_props["loop"].value = self.loop
			object_props["pingpong"].value = self.pingpong
			object_props["unlink"].value = self.unlink
			
		def add_logic(self):
			
			if self.tool_name not in self.object.game.controllers:
				ops.logic.controller_add(type="PYTHON", name=self.tool_name, object=self.object.name)
				
			if self.tool_name not in self.object.game.sensors:
				ops.logic.sensor_add(type="ALWAYS", name=self.tool_name, object=self.object.name)
				
			sens = self.object.game.sensors[self.tool_name]
			sens.use_pulse_true_level = True
			sens.tick_skip = self.skip
			cont = self.object.game.controllers[self.tool_name]
			cont.mode = "MODULE"
			cont.module = self.module_name
			
			cont.link(sensor=sens)
			
		def add_script_internal(self):
			
			if self.script_name in texts:
				texts.remove(texts[self.script_name], do_unlink=True)
				
			addons_paths = bpy.utils.script_paths("addons")
			url = j(addons_paths[0], self.script_path)
			text = ops.text.open(filepath=url, internal=True)
			if text != {"FINISHED"}:
				url = j(addons_paths[1], self.script_path)
				ops.text.open(filepath=url, internal=True)
	
		def add_uv_texture(self):
			
			if not self.uv_tex_name:
				return
				
			if self.uv_tex_name in uv_textures_names:
				uv_textures.remove(uv_textures[self.uv_tex_name])
				
			uv_texture = uv_textures.new(name=self.uv_tex_name)
			uv_texture.active = True
			uv_texture.active_render = True
			ops.object.mode_set(mode="EDIT")
			ops.mesh.select_all(action="SELECT")
			context.area.type = "IMAGE_EDITOR"
			ops.uv.select_all(action="SELECT")
			ops.uv.cursor_set(location=(0.0, 0.0))
			context.space_data.pivot_point = "CURSOR"
			ops.transform.resize(value=[1/i for i in self.sprites] + [1])
			context.area.type = area_type
			ops.uv.select_all(action="DESELECT")
			ops.mesh.select_all(action="DESELECT")
			ops.object.mode_set(mode="OBJECT")
			
		if self.clear:
			clear_data(self)
		else:
			add_properties(self)
			set_properties(self)
			add_logic(self)
			add_script_internal(self)
			add_uv_texture(self)
			
		return {"PASS_THROUGH"}
		
def register():
	bpy.utils.register_class(UVScroll)
	
def unregister():
	bpy.utils.unregister_class(UVScroll)
	
if __name__ == "__main__":
	register()
	