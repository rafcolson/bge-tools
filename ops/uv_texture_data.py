import bpy.utils.previews as previews
import bpy, math, os, json
from pathlib import Path
from typing import Tuple, Set, Any
from bpy import types
from .utils import Utils as ut
from .utils import Profiler as pr

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
DEBUG_PROP_NAME = "BGE_TOOLS_DEBUG"

LABEL_IMAGE = "Image:"
LABEL_UV_MAP = "UV Map:"
PROP_COLOR_PREF = "color_"
PROP_TEXTURE_PREF = "texture_"

DEFAULT_COLORS_CODE = "WRGBCMYKOLTAPHSD"
TO_BE_REPLACED = ["HIT_UV_TEX_PROPS", "HIT_UV_TEXTURES", "HIT_UV_GZ_DIRS"]

class BGE_TOOLS_MT_UVTextureDataPresets(types.Menu):
	bl_idname = "bge_tools.uv_texture_data_presets"
	bl_label = "UV Texture Data Presets"
	bl_description = "UV Texture Data Presets"
	bl_options = {"INTERNAL"}

	def draw(self, context: types.Context):
		layout = self.layout
		preset_dir = bpy.utils.user_resource("SCRIPTS", path="presets\\bge_tools_uv_tex_data", create=True)
		if os.path.exists(preset_dir):
			for preset in sorted(os.listdir(preset_dir)):
				if preset.endswith(".json"):
					preset_name = os.path.splitext(preset)[0]
					op = layout.operator("bge_tools.uv_texture_data_load_preset", text=preset_name)
					op.preset_name = preset_name
					op.preset_path = os.path.join(preset_dir, preset)

class BGE_TOOLS_OT_UVTextureDataRestoreDefaults(types.Operator):
	bl_idname = "bge_tools.uv_texture_data_restore_defaults"
	bl_label = "UV Texture Data - Restore Defaults"
	bl_description = "Restore UV Texture Data Defaults"
	bl_options = {"INTERNAL"}

	def execute(self, context: types.Context) -> Set[str]:
		context.scene.bge_tools_uv_tex_data_number_of_colors = 4
		context.scene.bge_tools_uv_tex_data_subdirectories = ""
		default_colors = [ut.rgb_to_float(c[2]) + [1.0] for c in BGE_TOOLS_OT_UVTextureDataProps.get_colors(DEFAULT_COLORS_CODE)]
		for i in range(len(default_colors)):
			clr_name = "{}{}".format(PROP_COLOR_PREF, i)
			tex_name = "{}{}".format(PROP_TEXTURE_PREF, i)
			setattr(context.scene.bge_tools_uv_tex_data_props, clr_name, default_colors[i])
			setattr(context.scene.bge_tools_uv_tex_data_props, tex_name, "")

		check_number(self, context)
		check_subdirectories(self, context)

		self.report({'INFO'}, "Defaults restored.")
		return {'FINISHED'}

class BGE_TOOLS_OT_UVTextureDataSavePreset(types.Operator):
	bl_idname = "bge_tools.uv_texture_data_save_preset"
	bl_label = "UV Texture Data Preset"
	bl_description = "Save UV Texture Data Preset"
	bl_options = {"INTERNAL"}

	preset_name = bpy.props.StringProperty(name="Name", default="")

	def execute(self, context: types.Context) -> Set[str]:
		preset_dir = bpy.utils.user_resource('SCRIPTS', path="presets/bge_tools_uv_tex_data", create=True)
		preset_path = os.path.join(preset_dir, "{}.json".format(self.preset_name))
		preset_data = {
			"number_of_colors": context.scene.bge_tools_uv_tex_data_number_of_colors,
			"subdirectories": context.scene.bge_tools_uv_tex_data_subdirectories,
			"colors": [],
			"textures": []
		}
		context.scene.bge_tools_uv_tex_data_current_preset = self.preset_name

		for i in range(context.scene.bge_tools_uv_tex_data_number_of_colors):
			clr_name = "{}{}".format(PROP_COLOR_PREF, i)
			tex_name = "{}{}".format(PROP_TEXTURE_PREF, i)
			clr_value = getattr(context.scene.bge_tools_uv_tex_data_props, clr_name)
			tex_value = getattr(context.scene.bge_tools_uv_tex_data_props, tex_name)
			preset_data["colors"].append(list(clr_value))
			preset_data["textures"].append(str(tex_value))

		with open(preset_path, 'w') as f:
			json.dump(preset_data, f, indent=4)

		self.report({'INFO'}, "Preset '{}' saved.".format(self.preset_name))
		return {'FINISHED'}

	def invoke(self, context: types.Context, event: types.Event) -> Set[str]:
		return context.window_manager.invoke_props_dialog(self)

class BGE_TOOLS_OT_UVTextureDataLoadPreset(types.Operator):
	bl_idname = "bge_tools.uv_texture_data_load_preset"
	bl_label = "UV Texture Data - Load Preset"
	bl_description = "Load UV Texture Data Preset"
	bl_options = {"INTERNAL"}

	preset_name = bpy.props.StringProperty()
	preset_path = bpy.props.StringProperty()

	def execute(self, context: types.Context) -> Set[str]:
		context.scene.bge_tools_uv_tex_data_current_preset = self.preset_name

		with open(self.preset_path, 'r') as f:
			preset_data = json.load(f)

		context.scene.bge_tools_uv_tex_data_number_of_colors = preset_data["number_of_colors"]
		context.scene.bge_tools_uv_tex_data_subdirectories = preset_data["subdirectories"]

		for i, clr_value in enumerate(preset_data["colors"]):
			clr_name = "{}{}".format(PROP_COLOR_PREF, i)
			setattr(context.scene.bge_tools_uv_tex_data_props, clr_name, clr_value)

		for i, tex_value in enumerate(preset_data["textures"]):
			tex_name = "{}{}".format(PROP_TEXTURE_PREF, i)
			setattr(context.scene.bge_tools_uv_tex_data_props, tex_name, tex_value)

		check_number(self, context)
		check_subdirectories(self, context)

		self.report({'INFO'}, "Preset '{}' loaded.".format(self.preset_name))
		return {'FINISHED'}

class BGE_TOOLS_OT_UVTextureDataDeletePreset(types.Operator):
	bl_idname = "bge_tools.uv_texture_data_delete_preset"
	bl_label = "UV Texture Data - Delete Preset"
	bl_description = "Delete the most recently loaded UV Texture Data Preset"
	bl_options = {"INTERNAL"}

	def execute(self, context: types.Context) -> Set[str]:
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

class BGE_TOOLS_OT_UVTextureData(types.Operator):
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
		self.image = None
		bpy.context.scene.bge_tools_uv_tex_data_preview = None
		self.prop_number = int(bpy.context.scene.bge_tools_uv_tex_data_number_of_colors)
		self.prop_subdirectories = str(bpy.context.scene.bge_tools_uv_tex_data_subdirectories)

	def invoke(self, context: types.Context, event: types.Event) -> Set[str]:
		active_object = context.scene.objects.active
		n = len(context.selected_editable_objects)
		if n > 1:
			self.err_msg = ERR_MSG_MORE_THAN_ONE_OBJECT_SELECTED
		elif n == 1:
			selected_object = context.selected_editable_objects[0]
			if active_object != selected_object:
				self.err_msg = ERR_MSG_SELECTED_OBJECT_NOT_ACTIVE
			elif not isinstance(active_object.data, types.Mesh):
				self.err_msg = ERR_MSG_NO_MESH_DATA
			elif not active_object.active_material:
				self.err_msg = ERR_MSG_NO_ACTIVE_MATERIAL
			elif not active_object.active_material.active_texture:
				self.err_msg = ERR_MSG_NO_ACTIVE_TEXTURE
			elif not active_object.active_material.active_texture.image:
				self.err_msg = ERR_MSG_NO_IMAGE
			else:
				self.object = active_object
				self.image = active_object.active_material.active_texture.image
				if not self.image.preview:
					self.image.preview_ensure()
				context.scene.bge_tools_uv_tex_data_preview = self.image

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

	def draw(self, context: types.Context):
		def cat_box(label_name: str = "", icon: str = "NONE"):
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
		row.prop_search(self, "prop_uv_texture_name", context.object.data, "uv_textures", "", "", False)
		row.operator("mesh.uv_texture_remove", text="", icon="ZOOMOUT")
		row.operator("mesh.uv_texture_add", text="", icon="ZOOMIN")

		box = cat_box("Subdirectories:")
		row = box.row()
		row.prop(context.scene, "bge_tools_uv_tex_data_subdirectories")

		box = cat_box("Game Logic:")
		row = box.row()
		row.prop_search(context.scene, "bge_tools_uv_tex_data_logic_object", context.scene, "objects", text="")

		box = cat_box("Colors:")
		row = box.row()
		row.prop(context.scene, "bge_tools_uv_tex_data_number_of_colors")

		for i in range(context.scene.bge_tools_uv_tex_data_number_of_colors):
			clr_name = "{}{}".format(PROP_COLOR_PREF, i)
			tex_name = "{}{}".format(PROP_TEXTURE_PREF, i)
			clr_prop = getattr(context.scene.bge_tools_uv_tex_data_props, clr_name)
			hex = ut.linear_to_hex(clr_prop)
			row = box.row()
			split = row.split(0.4, True)
			split.label("{}: {}".format(i, hex))
			split.prop(context.scene.bge_tools_uv_tex_data_props, clr_name, text="")
			split.prop(context.scene.bge_tools_uv_tex_data_props, tex_name, text="")

		box.separator()

	def check(self, context: types.Context) -> bool:
		if context.scene.bge_tools_uv_tex_data_redraw:
			context.scene.bge_tools_uv_tex_data_redraw = False
			return True
		return not self.err_msg

	def execute(self, context: types.Context) -> Set[str]:
		if self.err_msg:
			return {"CANCELLED"}

		pr.reset()
		
		pr.print_timed("Start executing", self.bl_idname)

		clrs = []
		texs = []
		for i in range(context.scene.bge_tools_uv_tex_data_number_of_colors):
			clr_name = "{}{}".format(PROP_COLOR_PREF, i)
			tex_name = "{}{}".format(PROP_TEXTURE_PREF, i)
			clr_prop = getattr(context.scene.bge_tools_uv_tex_data_props, clr_name)
			tex_prop = getattr(context.scene.bge_tools_uv_tex_data_props, tex_name)
			clrs.append(list(clr_prop))
			texs.append(str(tex_prop))

		img = context.scene.bge_tools_uv_tex_data_preview
		img_tex_name = "IM{}".format(img.name)
		img_tex_name_without_ext = ut.replace_ext(img_tex_name)
		dirs = Path(context.scene.bge_tools_uv_tex_data_subdirectories)
		relp = os.path.join(str(dirs), img_tex_name_without_ext)
		absp = os.path.join(str(dirs.absolute()), img_tex_name_without_ext)

		pr.print_timed("Getting indices of", img.name)

		l = ut.get_uv_indices(img, clrs)
		n = len(l)

		pr.print_timed("Writing compressed file: '//{}.gz'".format(relp))

		ut.write_gzipped(absp, l)

		pr.print_timed("Generating game logic")

		old = "# {}".format(", ".join(TO_BE_REPLACED))
		props = ut.get_json_list(TO_BE_REPLACED[0], [[ut.linear_to_hex(clr), tex] for clr, tex in zip(clrs, texs)])
		img_tex_names = ut.get_json(TO_BE_REPLACED[1], [img_tex_name])
		dirs = ut.get_json(TO_BE_REPLACED[2], str(dirs))
		new = "\n".join([props, img_tex_names, dirs])
		ut.remove_text(TOOL_NAME)
		ut.add_text(self.bl_idname, True, TOOL_NAME, replace=[old, new])

		logic_object_name = context.scene.bge_tools_uv_tex_data_logic_object
		if logic_object_name:
			objects_names = [o.name for o in set(bpy.context.selectable_objects).intersection(bpy.context.editable_objects)]
			if logic_object_name in objects_names:
				logic_object = context.scene.objects[logic_object_name]
				if logic_object == self.object:
					self.report({'WARNING'}, "No logic generated. Object should not be the active object.")
					context.scene.bge_tools_uv_tex_data_logic_object = ""
				else:
					self.object.select = False
					context.scene.objects.active = logic_object
					logic_object.select = True
					ut.add_game_property(logic_object, DEBUG_PROP_NAME, "", True)
					ut.remove_logic(logic_object, TOOL_NAME)
					ut.add_logic_python(logic_object, TOOL_NAME, "__init__", use_priority=True)
					ut.add_logic_python(logic_object, TOOL_NAME, "init")
					ut.add_logic_python(logic_object, TOOL_NAME, "update", True)

		pr.print_timed("Finished generating and storing {} X {} indices".format(n, n))
		pr.reset(False)

		return {"FINISHED"}

class BGE_TOOLS_OT_UVTextureDataProps(types.PropertyGroup):

	PRIMARY_COLORS = {
		"C": ("#00FFFF", "Cyan", (0, 255, 255)),
		"M": ("#FF00FF", "Magenta", (255, 0, 255)),
		"Y": ("#FFFF00", "Yellow", (255, 255, 0)),
	}
	SECONDARY_COLORS = {
		"R": ("#FF0000", "Red", (255, 0, 0)),
		"G": ("#00FF00", "Green", (0, 255, 0)),
		"B": ("#0000FF", "Blue", (0, 0, 255)),
	}
	TERTIARY_COLORS = {
		"O": ("#FFBC00", "Orange", (255, 128, 0)),
		"L": ("#BCFF00", "Lime", (128, 255, 0)),
		"T": ("#00FFBC", "Turquoise", (0, 255, 128)),
		"A": ("#00BCFF", "Azure", (0, 128, 255)),
		"P": ("#BC00FF", "Purple", (128, 0, 255)),
		"H": ("#FF00BC", "Hot Pink", (255, 0, 128)),
	}
	NEUTRAL_COLORS = {
		"K": ("#000000", "Black", (0, 0, 0)),
		"W": ("#FFFFFF", "White", (255, 255, 255)),
		"S": ("#E1E1E1", "Silver", (192, 192, 192)),
		"D": ("#898989", "Dark Gray", (64, 64, 64)),
	}
	COLORS = {**PRIMARY_COLORS, **SECONDARY_COLORS, **TERTIARY_COLORS, **NEUTRAL_COLORS}

	@staticmethod
	def get_colors(s: str) -> Tuple[str, str, Tuple[int, int, int]]:
		return tuple(__class__.COLORS[c] for c in s)

for i, color_code in enumerate(DEFAULT_COLORS_CODE):
	hex, name, rgb = BGE_TOOLS_OT_UVTextureDataProps.COLORS[color_code]
	rgba = ut.rgb_to_float(rgb) + [1.0]
	clr_name = "{}{}".format(PROP_COLOR_PREF, i)
	tex_name = "{}{}".format(PROP_TEXTURE_PREF, i)
	clr_prop = bpy.props.FloatVectorProperty(name=hex, default=(0,0,0,1), min=0, max=1, size=4, precision=6, subtype="COLOR")
	tex_prop = bpy.props.StringProperty(description="Name of the corresponding texture")
	setattr(BGE_TOOLS_OT_UVTextureDataProps, clr_name, clr_prop)
	setattr(BGE_TOOLS_OT_UVTextureDataProps, tex_name, tex_prop)

preview_collections = {}

def check_number(self, context: types.Context):
	context.scene.bge_tools_uv_tex_data_redraw = True

def check_subdirectories(self, context: types.Context):
	input = str(context.scene.bge_tools_uv_tex_data_subdirectories)
	parts = Path(input).parts
	sanitized_parts = [ut.sanitized(part) for part in parts]
	subdirectories = str(Path(*sanitized_parts).as_posix())
	subdirectories = subdirectories.rstrip("./")
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
	bpy.utils.register_class(BGE_TOOLS_OT_UVTextureDataProps)
	bpy.utils.register_class(BGE_TOOLS_OT_UVTextureData)
	types.Scene.bge_tools_uv_tex_data_current_preset = bpy.props.StringProperty()
	types.Scene.bge_tools_uv_tex_data_logic_object = bpy.props.StringProperty(description="Generate logic on this object")
	types.Scene.bge_tools_uv_tex_data_preview = bpy.props.PointerProperty(type=types.Image)
	types.Scene.bge_tools_uv_tex_data_redraw = bpy.props.BoolProperty(default=True)
	types.Scene.bge_tools_uv_tex_data_props = bpy.props.PointerProperty(type=BGE_TOOLS_OT_UVTextureDataProps)
	types.Scene.bge_tools_uv_tex_data_number_of_colors = bpy.props.IntProperty(
		name="Number of colors",
		default=4,
		min=1,
		max=16,
		update=check_number
	)
	types.Scene.bge_tools_uv_tex_data_subdirectories = bpy.props.StringProperty(
		name="",
		description=(
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
	bpy.utils.unregister_class(BGE_TOOLS_OT_UVTextureDataProps)
	bpy.utils.unregister_class(BGE_TOOLS_OT_UVTextureData)
	del types.Scene.bge_tools_uv_tex_data_current_preset
	del types.Scene.bge_tools_uv_tex_data_logic_object
	del types.Scene.bge_tools_uv_tex_data_props
	del types.Scene.bge_tools_uv_tex_data_preview
	del types.Scene.bge_tools_uv_tex_data_redraw
	del types.Scene.bge_tools_uv_tex_data_number_of_colors
	del types.Scene.bge_tools_uv_tex_data_subdirectories
	if "main" in preview_collections:
		previews.remove(preview_collections["main"])
		del preview_collections["main"]

if __name__ == "__main__":
	register()
