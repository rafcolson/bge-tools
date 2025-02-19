import bpy.utils.previews as previews
import bpy, re, math, os, json
from pathlib import Path

ERR_MSG_MORE_THAN_ONE_OBJECT_SELECTED = "More than one object selected"
ERR_MSG_NO_MESH_DATA = "Object not containing mesh data"
ERR_MSG_SELECTED_OBJECT_IN_HIDDEN_LAYER = "Selected object not in active layer"
ERR_MSG_ACTIVE_OBJECT_IN_HIDDEN_LAYER = "Active object not in active layer"
ERR_MSG_NO_ACTIVE_SELECTED_OBJECT = "No active selected object"
ERR_MSG_SELECTED_OBJECT_NOT_ACTIVE = "Selected object not active"
ERR_MSG_ACTIVE_OBJECT_NOT_SELECTED = "Active object not selected"
ERR_MSG_NO_ACTIVE_MATERIAL = "No active material on mesh"
ERR_MSG_NO_ACTIVE_TEXTURE = "No active texture on material"
ERR_MSG_NO_IMAGE = "Active texture not containing image"

TOOL_NAME = "bge_tools_uv_texture_data"
LABEL_IMAGE = "Image:"
LABEL_UV_MAP = "UV Map:"

INVALID_CHARS = r'[<>:"|?*$&;]'

class BGE_TOOLS_MT_UVTextureDataPresets(bpy.types.Menu):
	bl_idname = "bge_tools.uv_texture_data_presets"
	bl_label = "UV Texture Data Presets"
	bl_description = "UV Texture Data Presets"
	bl_options = {"INTERNAL"}

	def draw(self, context):
		layout = self.layout
		preset_dir = bpy.utils.user_resource("SCRIPTS", path="presets\\bge_tools_uv_tex_data", create=True)
		if os.path.exists(preset_dir):
			for preset in sorted(os.listdir(preset_dir)):
				if preset.endswith(".json"):
					preset_name = os.path.splitext(preset)[0]
					op = layout.operator("bge_tools.uv_texture_data_load_preset", text=preset_name)
					op.preset_name = preset_name
					op.preset_path = os.path.join(preset_dir, preset)

class BGE_TOOLS_OT_UVTextureDataRestoreDefaults(bpy.types.Operator):
	bl_idname = "bge_tools.uv_texture_data_restore_defaults"
	bl_label = "UV Texture Data - Restore Defaults"
	bl_description = "Restore UV Texture Data Defaults"
	bl_options = {"INTERNAL"}

	def execute(self, context):
		context.scene.bge_tools_uv_tex_data_number_of_colors = 3
		context.scene.bge_tools_uv_tex_data_subdirectories = ""
		default_colors = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)]
		for i in range(3):  
			prop_name = "color_{}".format(i)
			setattr(context.scene.bge_tools_uv_tex_data_colors, prop_name, default_colors[i])

		check_number(self, context)
		check_subdirectories(self, context)

		self.report({'INFO'}, "Defaults restored.")
		return {'FINISHED'}
		
class BGE_TOOLS_OT_UVTextureDataSavePreset(bpy.types.Operator):
	bl_idname = "bge_tools.uv_texture_data_save_preset"
	bl_label = "UV Texture Data Preset"
	bl_description = "Save UV Texture Data Preset"
	bl_options = {"INTERNAL"}

	preset_name = bpy.props.StringProperty(name="Name", default="")

	def execute(self, context):
		preset_dir = bpy.utils.user_resource('SCRIPTS', path="presets/bge_tools_uv_tex_data", create=True)
		preset_path = os.path.join(preset_dir, "{}.json".format(self.preset_name))
		preset_data = {
			"number_of_colors": context.scene.bge_tools_uv_tex_data_number_of_colors,
			"subdirectories": context.scene.bge_tools_uv_tex_data_subdirectories,
			"colors": []
		}
		context.scene.bge_tools_uv_tex_data_current_preset = self.preset_name

		for i in range(context.scene.bge_tools_uv_tex_data_number_of_colors):
			prop_name = "color_{}".format(i)
			color_value = getattr(context.scene.bge_tools_uv_tex_data_colors, prop_name)
			preset_data["colors"].append(list(color_value))

		with open(preset_path, 'w') as f:
			json.dump(preset_data, f, indent=4)

		self.report({'INFO'}, "Preset '{}' saved.".format(self.preset_name))
		return {'FINISHED'}
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
class BGE_TOOLS_OT_UVTextureDataLoadPreset(bpy.types.Operator):
	bl_idname = "bge_tools.uv_texture_data_load_preset"
	bl_label = "UV Texture Data - Load Preset"
	bl_description = "Load UV Texture Data Preset"
	bl_options = {"INTERNAL"}

	preset_name = bpy.props.StringProperty()
	preset_path = bpy.props.StringProperty()

	def execute(self, context):
		context.scene.bge_tools_uv_tex_data_current_preset = self.preset_name
		
		with open(self.preset_path, 'r') as f:
			preset_data = json.load(f)

		context.scene.bge_tools_uv_tex_data_number_of_colors = preset_data["number_of_colors"]
		context.scene.bge_tools_uv_tex_data_subdirectories = preset_data["subdirectories"]

		for i, color_value in enumerate(preset_data["colors"]):
			prop_name = "color_{}".format(i)
			setattr(context.scene.bge_tools_uv_tex_data_colors, prop_name, color_value)

		check_number(self, context)
		check_subdirectories(self, context)

		self.report({'INFO'}, "Preset '{}' loaded.".format(self.preset_name))
		return {'FINISHED'}
	
class BGE_TOOLS_OT_UVTextureDataDeletePreset(bpy.types.Operator):
	bl_idname = "bge_tools.uv_texture_data_delete_preset"
	bl_label = "UV Texture Data - Delete Preset"
	bl_description = "Delete the most recently loaded UV Texture Data Preset"
	bl_options = {"INTERNAL"}

	def execute(self, context):
		preset_dir = bpy.utils.user_resource("SCRIPTS", path="presets\\bge_tools_uv_tex_data", create=True)
		preset_path = os.path.join(preset_dir, "{}.json".format(context.scene.bge_tools_uv_tex_data_current_preset))
		if os.path.exists(preset_path):
			os.remove(preset_path)
			context.scene.bge_tools_uv_tex_data_current_preset = ""
			self.report({'INFO'}, "Preset deleted.")
		elif context.scene.bge_tools_uv_tex_data_current_preset == "":
			self.report({'WARNING'}, "No preset deleted. Load a preset first.")
		else:
			self.report({'WARNING'}, "No preset deleted because it does not exist.")
		return {'FINISHED'}

class BGE_TOOLS_OT_UVTextureDataColors(bpy.types.PropertyGroup):
    color_0 = bpy.props.FloatVectorProperty(name="Red", subtype="COLOR", min=0, max=1, size=3, default=(1, 0, 0))
    color_1 = bpy.props.FloatVectorProperty(name="Green", subtype="COLOR", min=0, max=1, size=3, default=(0, 1, 0))
    color_2 = bpy.props.FloatVectorProperty(name="Blue", subtype="COLOR", min=0, max=1, size=3, default=(0, 0, 1))
    color_3 = bpy.props.FloatVectorProperty(name="Yellow", subtype="COLOR", min=0, max=1, size=3, default=(1, 1, 0))
    color_4 = bpy.props.FloatVectorProperty(name="Cyan", subtype="COLOR", min=0, max=1, size=3, default=(0, 1, 1))
    color_5 = bpy.props.FloatVectorProperty(name="Magenta", subtype="COLOR", min=0, max=1, size=3, default=(1, 0, 1))
    color_6 = bpy.props.FloatVectorProperty(name="Black", subtype="COLOR", min=0, max=1, size=3, default=(0, 0, 0))
    color_7 = bpy.props.FloatVectorProperty(name="White", subtype="COLOR", min=0, max=1, size=3, default=(1, 1, 1))

class BGE_TOOLS_OT_UVTextureData(bpy.types.Operator):
	
	bl_description = "Writes uv texture color data for casting rays on a surface in the Blender Game Engine"
	bl_idname = "bge_tools.uv_texture_data"
	bl_label = "BGE-Tools: UV Texture Data"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'VIEW_3D'
	bl_category = "Tool"
	bl_context = "object"
	bl_options = {"REGISTER", "UNDO"}

	prop_uv_texture_name = bpy.props.StringProperty(name="", description="UV Map to be reset.")

	def __init__(self):
		super().__init__()
		self.err_msg = ""
		self.object = None
		bpy.context.scene.bge_tools_uv_tex_data_preview = None
		self.prop_number = int(bpy.context.scene.bge_tools_uv_tex_data_number_of_colors)
		self.prop_subdirectories = str(bpy.context.scene.bge_tools_uv_tex_data_subdirectories)

	def invoke(self, context, event):
		
		active_object = context.scene.objects.active
		n = len(context.selected_editable_objects)
		if n > 1:
			self.err_msg = ERR_MSG_MORE_THAN_ONE_OBJECT_SELECTED
			
		elif n == 1:
			selected_object = context.selected_editable_objects[0]
			if active_object != selected_object:
				self.err_msg = ERR_MSG_SELECTED_OBJECT_NOT_ACTIVE

			elif not isinstance(active_object.data, bpy.types.Mesh):
				self.err_msg = ERR_MSG_NO_MESH_DATA

			elif not active_object.active_material:
				self.err_msg = ERR_MSG_NO_ACTIVE_MATERIAL

			elif not active_object.active_material.active_texture:
				self.err_msg = ERR_MSG_NO_ACTIVE_TEXTURE

			elif not active_object.active_material.active_texture.image:
				self.err_msg = ERR_MSG_NO_IMAGE

			else:
				self.object = active_object

				image = active_object.active_material.active_texture.image
				if not image.preview:
					image.preview_ensure()
				context.scene.bge_tools_uv_tex_data_preview = image

				uv_textures = active_object.data.uv_textures
				self.prop_uv_texture_name = uv_textures[0].name if uv_textures else ""
				
		elif context.selected_objects:
			self.err_msg = ERR_MSG_SELECTED_OBJECT_IN_HIDDEN_LAYER

		elif not active_object:
			self.err_msg = ERR_MSG_NO_ACTIVE_SELECTED_OBJECT

		elif active_object in context.editable_objects:
			self.err_msg = ERR_MSG_ACTIVE_OBJECT_NOT_SELECTED

		else:
			self.err_msg = ERR_MSG_ACTIVE_OBJECT_IN_HIDDEN_LAYER
    		
		return context.window_manager.invoke_props_dialog(self, context.user_preferences.system.dpi * 8)
			
	def draw(self, context):

		def cat_box(label_name="", icon="NONE"):
			box = layout.box()
			box.separator()
			row = box.row()
			if label_name:
				row.label(label_name, icon=icon)
			return box

		layout = self.layout
		if self.err_msg:
			layout.separator()
			layout.label(self.err_msg, icon="CANCEL")
			return
		
		row = layout.row(True)
		row.menu("bge_tools.uv_texture_data_presets", text="Presets")
		row.operator("bge_tools.uv_texture_data_save_preset", text="", icon="ZOOMIN")
		row.operator("bge_tools.uv_texture_data_delete_preset", text="", icon="ZOOMOUT")
		row.operator("bge_tools.uv_texture_data_restore_defaults", text="", icon="FILE_REFRESH")

		box = cat_box(LABEL_IMAGE)
		col = box.column()
		n = math.sqrt(len(bpy.data.images))
		n_r = round(n)
		n_c = math.ceil(n)		
		col.template_ID_preview(context.scene, "bge_tools_uv_tex_data_preview", unlink="None", rows=n_r, cols=n_c)

		box = cat_box(LABEL_UV_MAP)
		row = box.row()
		row.prop_search(self, "prop_uv_texture_name",  context.object.data, "uv_textures", "", "", False)
		row.operator("mesh.uv_texture_remove", text="", icon="ZOOMOUT")
		row.operator("mesh.uv_texture_add", text="", icon="ZOOMIN")

		box = cat_box("Subdirectories:")
		row = box.row()
		row.prop(context.scene, "bge_tools_uv_tex_data_subdirectories")

		box = cat_box("Colors:")
		row = box.row()
		row.prop(context.scene, "bge_tools_uv_tex_data_number_of_colors")

		for i in range(context.scene.bge_tools_uv_tex_data_number_of_colors):
			prop_name = "color_{}".format(i)
			prop = getattr(context.scene.bge_tools_uv_tex_data_colors, prop_name)
			row = box.row()
			split = row.split(0.3, True)
			split.label("{}: {}".format(i, "#000000"))
			split.prop(context.scene.bge_tools_uv_tex_data_colors, prop_name, text="")

		box.separator()

	def check(self, context):
		if context.scene.bge_tools_uv_tex_data_redraw:
			context.scene.bge_tools_uv_tex_data_redraw = False
			return True
		return not self.err_msg
	
	def execute(self, context):
		if self.err_msg:
			return {"CANCELLED"}
		
		abs_path = str((Path(context.scene.bge_tools_uv_tex_data_subdirectories) / "file.gz").absolute())
		print(abs_path)
		print("")
		for i in range(context.scene.bge_tools_uv_tex_data_number_of_colors):
			prop_name = "color_{}".format(i)
			clr = getattr(context.scene.bge_tools_uv_tex_data_colors, prop_name)
			print(clr)
		return {"PASS_THROUGH"}
	
preview_collections = {}

def check_number(self, context):
	context.scene.bge_tools_uv_tex_data_redraw = True

def check_subdirectories(self, context):
	input = str(context.scene.bge_tools_uv_tex_data_subdirectories)
	parts = Path(input).parts
	sanitized_parts = [re.sub(INVALID_CHARS, "_", part) for part in parts]
	subdirectories = str(Path(*sanitized_parts).as_posix())
	subdirectories = subdirectories.rstrip(" ./")
	if context.scene.bge_tools_uv_tex_data_subdirectories != subdirectories:
		context.scene.bge_tools_uv_tex_data_subdirectories = subdirectories
		context.scene.bge_tools_uv_tex_data_redraw = True

def register():
	global preview_collections
	preview_collections["main"] = previews.new()
	bpy.utils.register_class(BGE_TOOLS_OT_UVTextureDataRestoreDefaults)
	bpy.utils.register_class(BGE_TOOLS_OT_UVTextureDataSavePreset)
	bpy.utils.register_class(BGE_TOOLS_OT_UVTextureDataLoadPreset)
	bpy.utils.register_class(BGE_TOOLS_OT_UVTextureDataDeletePreset)
	bpy.utils.register_class(BGE_TOOLS_MT_UVTextureDataPresets)
	bpy.utils.register_class(BGE_TOOLS_OT_UVTextureDataColors)
	bpy.utils.register_class(BGE_TOOLS_OT_UVTextureData)
	bpy.types.Scene.bge_tools_uv_tex_data_current_preset = bpy.props.StringProperty()
	bpy.types.Scene.bge_tools_uv_tex_data_preview = bpy.props.PointerProperty(type=bpy.types.Image)
	bpy.types.Scene.bge_tools_uv_tex_data_redraw = bpy.props.BoolProperty(default=True)
	bpy.types.Scene.bge_tools_uv_tex_data_colors = bpy.props.PointerProperty(type=BGE_TOOLS_OT_UVTextureDataColors)
	bpy.types.Scene.bge_tools_uv_tex_data_number_of_colors = bpy.props.IntProperty(
		name="Number of colors",
		default=3,
		min=1,
		max=8,
		update=check_number
	)
	bpy.types.Scene.bge_tools_uv_tex_data_subdirectories = bpy.props.StringProperty(
		name="",
		description = (
			"The full path of all subdirectories. If any do not exist, they will be created automatically.\n"
			"Example: 'images/data'"
		),
		update=check_subdirectories
	)
	
def unregister():
	global preview_collections
	bpy.utils.unregister_class(BGE_TOOLS_OT_UVTextureDataRestoreDefaults)
	bpy.utils.unregister_class(BGE_TOOLS_OT_UVTextureDataSavePreset)
	bpy.utils.unregister_class(BGE_TOOLS_OT_UVTextureDataLoadPreset)
	bpy.utils.unregister_class(BGE_TOOLS_OT_UVTextureDataDeletePreset)
	bpy.utils.unregister_class(BGE_TOOLS_MT_UVTextureDataPresets)
	bpy.utils.unregister_class(BGE_TOOLS_OT_UVTextureDataColors)
	bpy.utils.unregister_class(BGE_TOOLS_OT_UVTextureData)
	del bpy.types.Scene.bge_tools_uv_tex_data_current_preset
	del bpy.types.Scene.bge_tools_uv_tex_data_colors
	del bpy.types.Scene.bge_tools_uv_tex_data_preview
	del bpy.types.Scene.bge_tools_uv_tex_data_redraw
	del bpy.types.Scene.bge_tools_uv_tex_data_number_of_colors
	del bpy.types.Scene.bge_tools_uv_tex_data_subdirectories
	previews.remove(preview_collections["main"])
	preview_collections.clear()

if __name__ == "__main__":
	register()
