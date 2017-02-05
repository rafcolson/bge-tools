import struct, ctypes, bpy, sys, os, re, math, time, numpy, pickle, gzip, json, zlib
from collections import OrderedDict
from mathutils import Vector
from typing import Union, List, Tuple, Dict, Optional, Any
from bpy import types

# constants

ADDON_NAME = "bge-tools"
ADDONS_PATHS = bpy.utils.script_paths("addons")
GEN_PATH = os.path.join(ADDON_NAME, "gen")
ADDON_OT = "BGE_TOOLS_OT_"

class Utils(object):
	
	INVALID_CHARS = r'[$&;+<>:"/\\|?*\x00-\x1F]'
	RESERVED_NAMES = {
		"CON", "PRN", "AUX", "NUL",
		"COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
		"LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
	}

	# string utils

	@staticmethod
	def get_json(var_name: str, o: Any) -> str:
		s = str(o) if not isinstance(o, str) else '"{}"'.format(o)
		return var_name + " = " + json.dumps(o)

	@staticmethod
	def get_json_list(var_name, l: List[Any], indent: int = 4) -> str:
		s = ""
		for o in l:
			s += "{}{},\n".format(" " * indent, json.dumps(o))
		return "{} = [\n{}\n]".format(var_name, s.rstrip(",\n"))

	@staticmethod
	def get_json_dict(var_name, d: dict, indent: int = 4) -> str:
		s = ""
		for o in d.items():
			s += "{}{},\n".format(" " * indent, json.dumps(o))
		return "{} = {{\n{}\n}}".format(var_name, s.rstrip(",\n"))

	@staticmethod
	def stripped(bs: str, ss: str) -> str:
		return bs.replace(ss, "", 1)

	@staticmethod
	def get_formatted(
		obj: Union[int, float, List[Any], Vector],
		suffix: str = "",
		spacer: str = " ",
		num_digits: int = 2
	) -> str:
		if not isinstance(obj, (list, Vector)):
			if isinstance(obj, (int, float)):
				s = suffix
				d = str(obj)
				for i in range(num_digits - len(d)):
					s += spacer
				s += d
				return s
			raise ValueError(obj.__class__.__name__, "not suited for this application")
		f = 10 ** num_digits
		s = str(int(f * round(obj[0], num_digits)))
		s += suffix + str(int(f * round(obj[1], num_digits)))
		try:
			s += suffix + str(int(f * round(obj[2], num_digits)))
		except KeyError:
			pass
		return s

	@staticmethod
	def get_id(i: int, suffix: str = ".", num_digits: int = 3) -> str:
		return Utils.get_formatted(i, suffix, "0", num_digits)

	# math utils

	@staticmethod
	def clamped(f: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
		return max(min_val, min(max_val, f))

	@staticmethod
	def get_sign(f: float) -> int:
		return numpy.sign(int(f))

	@staticmethod
	def point_inside_rectangle(pnt: Vector, rect: Tuple[Vector, Vector]) -> bool:
		cen, dim = rect
		crn = Vector((cen.x - dim.x * 0.5, cen.y - dim.y * 0.5))
		return (crn.x <= pnt.x <= crn.x + dim.x and crn.y <= pnt.y <= crn.y + dim.y)

	@staticmethod
	def get_floor_factor(f: float, i: int) -> int:
		return 0 if i == 0 else f // i * i

	@staticmethod
	def get_grid_point(position: Tuple[float, ...], size: Tuple[int, ...], axis_range: str = "XYZ") -> List[Tuple[int, ...]]:
		l = []
		axis = "XYZ"[:len(position)]
		for i, a in enumerate(axis):
			if a in axis_range:
				l.append(Utils.get_floor_factor(position[i], size[i]) + size[i] // 2)
		return l

	@staticmethod
	def approximated(position: Tuple[float, float, float], num_digits: int = 3) -> Tuple[float, float, float]:
		return tuple(round(position[i], num_digits) for i in range(3))

	@staticmethod
	def lerp(x: float, y: float, f: float = 0.25) -> float:
		return (1 - f) * x + f * y

	@staticmethod
	def inv_lerp(x: float, y: float, v: float) -> float:
		return (v - x) / (y - x)

	@staticmethod
	def remap(i_min: float, i_max: float, o_min: float, o_max: float, v: float) -> float:
		return Utils.lerp(o_min, o_max, Utils.inv_lerp(i_min, i_max, v))

	@staticmethod
	def non_zero_natural(v: float) -> float:
		return max(abs(v), 0.00001)

	@staticmethod
	def get_table_incremented(v: float, f: float, n: int) -> List[int]:
		x = v / (f + 1)
		y = 2 * f
		l = [x * i + math.sqrt(y * x) * pow(y * i, 2) for i in range(1, n + 1)]
		z = l[0] / v
		l = [round(l[i] / z) for i in range(n)]
		return l

	# color utils

	@staticmethod
	def _apply_gamma(rgb: list, gamma: float, inverse=False) -> List[float]:
		return [Utils.clamped(pow(c, 1.0 / gamma) if inverse else pow(c, gamma)) for c in rgb]

	@staticmethod
	def _correct_linear_to_srgb(c: float) -> float:
		return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055

	@staticmethod
	def _correct_srgb_to_linear(c: float) -> float:
		return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

	@staticmethod
	def rgb_to_cmyk(rgb: List[float]) -> List[float]:
		*rgb, a = rgb if len(rgb) == 4 else (*rgb, 1.0)
		r, g, b = [x / 255.0 for x in rgb]
		k = 1 - max(r, g, b)
		if k < 1:
			c = (1 - r - k) / (1 - k)
			m = (1 - g - k) / (1 - k)
			y = (1 - b - k) / (1 - k)
		else:
			c = m = y = 0
		return [c, m, y, k, a]

	@staticmethod
	def cmyk_to_rgb(cmyk: List[float]) -> List[float]:
		*cmyk, a = cmyk if len(cmyk) == 5 else (*cmyk, 1.0)
		c, m, y, k = cmyk
		r = 1 - min(1, c * (1 - k) + k)
		g = 1 - min(1, m * (1 - k) + k)
		b = 1 - min(1, y * (1 - k) + k)
		return [r, g, b, a]

	@staticmethod
	def gamma_to_linear(rgb: list, gamma=2.2) -> List[float]:
		return Utils._apply_gamma(rgb, gamma, inverse=True)

	@staticmethod
	def linear_to_gamma(rgb: list, gamma=2.2) -> List[float]:
		return Utils._apply_gamma(rgb, gamma, inverse=False)

	@staticmethod
	def linear_to_srgb(clr: List[float]) -> List[float]:
		*clr, a = clr if len(clr) == 4 else (*clr, 1.0)
		return [Utils._correct_linear_to_srgb(c) for c in clr] + [a]

	@staticmethod
	def srgb_to_linear(clr: List[float]) -> List[float]:
		*clr, a = clr if len(clr) == 4 else (*clr, 1.0)
		return [Utils._correct_srgb_to_linear(c) for c in clr] + [a]

	@staticmethod
	def hex_to_linear(hex: str) -> List[float]:
		srgba = Utils.hex_to_srgba(hex)
		return Utils.srgb_to_linear(srgba)

	@staticmethod
	def hex_to_srgba(hex: str) -> List[float]:
		hex = hex.lstrip('#')
		rgb = [int(hex[i:i+2], 16) / 255.0 for i in (0, 2, 4)]
		a = int(hex[6:8], 16) / 255.0 if len(hex) == 8 else 1.0
		return rgb + [a]

	@staticmethod
	def hex_to_srgb(hex: str) -> List[float]:
		return Utils.hex_to_srgba(hex)[:3]

	@staticmethod
	def rgba_to_hex(rgba: list, gamma=None) -> str:
		rgb = [Utils.clamped(c) for c in rgba[:3]]
		if gamma is not None:
			gamma = max(1.0, gamma)
			rgb = Utils.linear_to_gamma(rgb, gamma)
		rgb = [int(c * 255) for c in rgb]
		alpha = int(Utils.clamped(rgba[3])) if len(rgba) == 4 else 255
		hex_full = '{:02X}{:02X}{:02X}'.format(*rgb)
		if all(hex_full[i] == hex_full[i+1] for i in range(0, 6, 2)):
			hex_full = hex_full[0] + hex_full[2] + hex_full[4]
		return '#' + hex_full + ('{:02X}'.format(alpha) if alpha < 255 else '')

	@staticmethod
	def rgb_to_hex(rgb: list, gamma=2.2) -> str:
		return Utils.rgba_to_hex(rgb + [1.0], gamma=gamma)

	@staticmethod
	def srgba_to_hex(srgba: list) -> str:
		return Utils.rgba_to_hex(srgba, gamma=None)

	@staticmethod
	def srgb_to_hex(srgb: list) -> str:
		return Utils.srgba_to_hex(srgb + [1.0])

	@staticmethod
	def linear_to_hex(rgb: list) -> str:
		rgb, a = rgb[:3], rgb[3] if len(rgb) == 4 else 1.0
		srgb = [int(round(Utils.clamped(c) * 255)) for c in Utils.linear_to_srgb(rgb)]
		a = int(round(Utils.clamped(a) * 255))
		return "#{:02X}{:02X}{:02X}{:02X}".format(*srgb, a)

	@staticmethod
	def rgb_to_float(ints: List[int]) -> List[float]:
		return [i / 255.0 for i in ints]

	@staticmethod
	def float_to_rgb(floats: List[float]) -> List[int]:
		return [round(Utils.clamped(f) * 255) for f in floats]

	@staticmethod
	def get_dominant_color(rgb: List[float], colors: List[List[float]]) -> List[float]:
		return min(colors, key=lambda color: sum((a - b) ** 2 for a, b in zip(rgb, color[:len(rgb)])))

	@staticmethod
	def get_uv_indices(img, clrs: List[List[float]]) -> numpy.ndarray:
		rgba_data = list(img.pixels)
		rgba_data_length = len(rgba_data)
		img_resolution = round(math.sqrt(rgba_data_length / 4))
		uv = [[] for _ in range(img_resolution)]
		for i in range(0, rgba_data_length, img_resolution * 4):
			for col in range(img_resolution):
				row_start = i + col * 4
				row_end = row_start + 4
				rgba = rgba_data[row_start:row_end]
				clr = Utils.get_dominant_color(rgba, clrs)
				idx = clrs.index(clr)
				uv[col].append(idx)
		return numpy.array(uv, dtype=numpy.int8)

	# text utils

	@staticmethod
	def add_text(name: str, intern: bool = True, new_name: str = "", ext: str = ".py", replace: bool = None) -> types.Text:
		text_name = new_name + ext if new_name else name + ext
		if text_name not in bpy.data.texts:
			text_source_name = name + ext
			text_source_path = os.path.join(ADDONS_PATHS[0], GEN_PATH, text_source_name)
			if bpy.ops.text.open(filepath=text_source_path, internal=intern) != {"FINISHED"}:
				text_source_path = os.path.join(ADDONS_PATHS[1], GEN_PATH, text_source_name)
				bpy.ops.text.open(filepath=text_source_path, internal=intern)
				if intern:
					text = bpy.data.texts[text_source_name]
					s = text.as_string()
					if replace is not None:
						old, new = replace
						s = s.replace(old, new)
					bpy.data.texts.remove(text, do_unlink=True)
					text = bpy.data.texts.new(text_name)
					text.from_string(s)
		return bpy.data.texts[text_name]

	@staticmethod
	def remove_text(name: str, all_users: bool = False, ext: str = ".py") -> bool:
		text_name = name + ext
		if text_name not in bpy.data.texts:
			return False
		text = bpy.data.texts[text_name]
		if not all_users and text.users_logic:
			return False
		bpy.data.texts.remove(bpy.data.texts[text_name], do_unlink=True)
		return True

	# object utils

	@staticmethod
	def add_logic_python(
		object: types.Object,
		script_name: str,
		module_name: str = "",
		use_pulse_true_level: bool = False,
		state: int = 1,
		delay: int = 0,
		tick_skip: int = 0,
		use_priority: bool = False
	):
		brick_name = module_name if module_name else script_name
		sensor_type = "DELAY" if delay else "ALWAYS"

		if brick_name not in object.game.sensors:
			bpy.ops.logic.sensor_add(type=sensor_type, name=brick_name, object=object.name)

		if brick_name not in object.game.controllers:
			bpy.ops.logic.controller_add(type="PYTHON", name=brick_name, object=object.name)

		sens = object.game.sensors[brick_name]
		if delay:
			sens.delay = delay
		sens.use_pulse_true_level = use_pulse_true_level
		if use_pulse_true_level:
			sens.tick_skip = tick_skip

		cont = object.game.controllers[brick_name]
		cont.states = state
		cont.use_priority = use_priority
		text = bpy.data.texts[script_name + ".py"]
		if module_name:
			cont.mode = "MODULE"
			cont.module = script_name + "." + module_name
		else:
			cont.mode = "SCRIPT"
			cont.text = text
		cont.link(sensor=sens)

	@staticmethod
	def remove_logic(object: types.Object, script_name: str):
		n = object.name
		for cont in object.game.controllers:
			s = cont.module if cont.mode == "MODULE" else Utils.get_dir_name_ext(cont.text.filepath)[1] if cont.text else ""
			if script_name in s:
				for actu in cont.actuators:
					bpy.ops.logic.controller_remove(actuator=actu.name, object=n)
				for sens in object.game.sensors:
					if cont in sens.controllers.values():
						bpy.ops.logic.sensor_remove(sensor=sens.name, object=n)
				bpy.ops.logic.controller_remove(controller=cont.name, object=n)

	@staticmethod
	def get_game_property_type(object: types.Object) -> str:
		t = object.__class__.__name__.upper()
		if t == "STR":
			t = "STRING"
		return t

	@staticmethod
	def add_game_property(object: types.Object, prop_name: str, prop_value: Any, show_debug: bool = False):
		properties = object.game.properties
		prop_type = Utils.get_game_property_type(prop_value)
		if prop_name not in properties:
			bpy.ops.object.game_property_new(type=prop_type, name=prop_name)
		else:
			properties[prop_name].type = prop_type
		properties[prop_name].value = prop_value
		properties[prop_name].show_debug = show_debug

	@staticmethod
	def remove_game_property(object: types.Object, prop_name: str):
		for i , k in enumerate(object.game.properties.keys()):
			if k == prop_name:
				bpy.ops.object.game_property_remove(index=i)

	@staticmethod
	def remove_game_properties(object: types.Object, prop_names: List[str]):
		for prop_name in prop_names:
			Utils.remove_game_property(object, prop_name)

	@staticmethod
	def copy(
		scene: types.Scene,
		object: types.Object,
		link: bool = False,
		suffix: str = "",
		apply_modifiers: bool = False,
		modifier_settings: str = "RENDER"
	) -> types.Object:
		if link:
			ob_copy = bpy.data.objects.new(object.name + suffix, object.data)
		else:
			me_copy = object.to_mesh(scene, apply_modifiers, modifier_settings)
			me_copy.name = object.data.name + suffix
			ob_copy = bpy.data.objects.new(object.name + suffix, me_copy)
		ob_copy.matrix_world = object.matrix_world
		scene.objects.link(ob_copy)
		return ob_copy

	@staticmethod
	def remove(obj: Union[types.Material, types.Mesh, types.Object, Any], remove_mesh: bool = True):
		if isinstance(obj, types.Material):
			bpy.data.materials.remove(obj)
		elif isinstance(obj, types.Mesh):
			bpy.data.meshes.remove(obj)
		elif isinstance(obj, types.Object):
			if remove_mesh:
				me = obj.data
				bpy.data.objects.remove(obj)
				bpy.data.meshes.remove(me)
			else:
				bpy.data.objects.remove(obj)
		else:
			del obj

	@staticmethod
	def dimensions(*objects: Tuple[types.Object, ...], include_transform: bool = False) -> Vector:
		bb_crns = []
		for ob in objects:
			if include_transform:
				bb_crns += [ob.matrix_world * Vector(corner) for corner in ob.bound_box]
			else:
				bb_crns += [Vector(corner) for corner in ob.bound_box]
		n = len(bb_crns)
		dim_x = max(bb_crns[i][0] for i in range(n)) - min(bb_crns[i][0] for i in range(n))
		dim_y = max(bb_crns[i][1] for i in range(n)) - min(bb_crns[i][1] for i in range(n))
		dim_z = max(bb_crns[i][2] for i in range(n)) - min(bb_crns[i][2] for i in range(n))
		return Vector((dim_x, dim_y, dim_z))

	@staticmethod
	def get_custom_normals(
		object: types.Object,
		approx_ndigits: int = -1,
		from_selected: bool = False
	) -> Dict[str, List[float]]:

		def triform(loop_indices: List[int]) -> List[int]:
			indices = list(loop_indices)
			if len(indices) < 4:
				return indices
			return [indices[i] for i in (0, 1, 2, 2, 3, 0)]

		mesh = object.data
		mesh.calc_normals_split()

		clnors = [0.0] * 3 * len(mesh.loops)
		mesh.loops.foreach_get("normal", clnors)
		loop_vert = {l.index: l.vertex_index for l in mesh.loops}

		normals = {}

		for poly in mesh.polygons:

			for li in triform(poly.loop_indices):
				vert = mesh.vertices[loop_vert[li]]

				if from_selected and not vert.select:
					continue

				vert_normal = [clnors[li*3], clnors[li*3+1], clnors[li*3+2]]
				if approx_ndigits != -1:
					vert_normal = [round(f, approx_ndigits) for f in vert_normal]

				id = str([round(f) for f in vert.co.xy])
				normals[id] = vert_normal

		return normals

	@staticmethod
	def get_dupli_parents(inst: types.Object) -> List[types.Object]:
		l = []
		if inst.dupli_group is not None:
			for ob in inst.dupli_group.objects:
				if ob.parent is None:
					l.append(ob)
		return l

	@staticmethod
	def get_children_recursive(object: types.Object) -> List[types.Object]:
		l = []
		for o in object.children:
			l.append(o)
			l.extend(get_children_recursive(o))
		return l

	@staticmethod
	def get_children_recursive(*objects: Tuple[types.Object, ...]) -> List[types.Object]:
		l = []
		roots = (o for o in objects if not o.parent)
		for o in roots:
			l.extend(get_children_recursive(object))
		return l

	# file utils

	@staticmethod
	def get_gen_path(bl_idname: str = "") -> str:
		if not bl_idname:
			return GEN_PATH
		script_name = bl_idname.replace("{}.".format(ADDON_NAME), "{}_".format(ADDON_OT))
		return Utils.get_path(GEN_PATH, "{}.py".format(script_name))

	@staticmethod
	def get_path(*args: Tuple[str, ...]) -> str:
		return os.path.join(*args)

	@staticmethod
	def get_dir_path() -> str:
		return bpy.path.abspath("//..\\")

	@staticmethod
	def get_dir_name(file_path: str = "") -> str:
		if not file_path:
			return Utils.get_dir_name(Utils.get_dir_path())
		return os.path.dirname(file_path)

	@staticmethod
	def get_dir_name_ext(file_path: str = "") -> Tuple[str, str, str]:
		dir_path, name = os.path.split(file_path)
		name_without_ext, ext = os.path.splitext(name)
		return dir_path, name_without_ext, ext

	@staticmethod
	def replace_ext(file_path: str, ext: str = "") -> str:
		return os.path.splitext(file_path)[0] + ext

	@staticmethod
	def sanitized(name: str, is_directory: bool = False) -> str:
		sanitized = re.sub(Utils.INVALID_CHARS, "_", name)
		sanitized = sanitized.rstrip(" .")
		base_name, ext = sanitized.split(".", 1) if "." in sanitized and not is_directory else (sanitized, "")
		if base_name.upper() in Utils.RESERVED_NAMES:
			base_name = "_" + base_name
		return base_name + ("." + ext if ext else "")

	@staticmethod
	def read_text(file_path: str, ext: str = ".txt") -> Optional[str]:
		path = Utils.replace_ext(file_path, ext)
		if not os.path.exists(path):
			return None
		with open(path, "r") as f:
			return f.read()

	@staticmethod
	def write_text(s, file_path: str, ext: str = ".txt"):
		path = Utils.replace_ext(file_path, ext)
		Utils.create_directories(path)
		with open(path, "w") as f:
			f.write(s)

	@staticmethod
	def read_pickled(file_path: str, ext: str = "") -> Optional[OrderedDict]:
		path = Utils.replace_ext(file_path, ext)
		if not os.path.exists(path):
			return None
		with open(path, "rb") as f:
			return OrderedDict(pickle.load(f))

	@staticmethod
	def write_pickled(file_path: str, data: Any, ext: str = ""):
		path = Utils.replace_ext(file_path, ext)
		Utils.create_directories(path)
		with open(path, "wb") as f:
			pickle.dump(data, f)

	@staticmethod
	def read_numpied(file_path: str, ext: str = ".npy") -> Optional[numpy.ndarray]:
		path = Utils.replace_ext(file_path, ext)
		if not os.path.exists(path):
			return None
		return numpy.load(path, "r", True, False, encoding="bytes")

	@staticmethod
	def write_numpied(file_path: str, data: Any, ext: str = ".npy"):
		path = Utils.replace_ext(file_path, ext)
		Utils.create_directories(path)
		numpy.save(path, data, True, False)

	@staticmethod
	def read_gzipped(file_path: str, ext: str = ".gz", mode: str = "r") -> Optional[numpy.ndarray]:
		path = Utils.replace_ext(file_path, ext)
		if not os.path.exists(path):
			return None
		f = gzip.GzipFile(path, mode)
		data = numpy.load(f)
		f.close()
		return data

	@staticmethod
	def write_gzipped(file_path: str, data: Any, ext: str = ".gz", mode: str = "w"):
		path = Utils.replace_ext(file_path, ext)
		Utils.create_directories(path)
		f = gzip.GzipFile(path, mode)
		numpy.save(f, data)
		f.close()

	@staticmethod
	def read_zlibbed(file_path, ext = ".zz", mode = "rb") -> Optional[Any]:
		path = Utils.replace_ext(file_path, ext)
		if not os.path.exists(path):
			return None
		with open(path, mode) as f:
			zz = f.read()
		data = pickle.loads(zlib.decompress(zz))
		return data

	@staticmethod
	def write_zlibbed(file_path, data, ext = ".zz", mode = "wb"):
		path = Utils.replace_ext(file_path, ext)
		Utils.create_directories(path)
		with open(path, mode) as f:
			zz = zlib.compress(pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL))
			f.write(zz)

	@staticmethod
	def create_directories(file_path: str):
		dir_path = os.path.dirname(file_path)
		if not os.path.exists(dir_path):
			os.makedirs(dir_path)

	# system utils

	@staticmethod
	def init_reloadable_addon(ops_modules: List[Any], locals: Dict[str, Any]) -> List[Any]:

		def register():
			for m in ops_modules:
				m.register()

			print("BGE Tools registered")

		def unregister():
			for m in ops_modules:
				m.unregister()

			print("BGE Tools unregistered")

		def reload():
			import importlib
			for m in ops_modules:
				importlib.reload(m)

			print("BGE Tools reloaded")

		if register.__name__ in locals:
			reload()

		return [register, unregister]

class Profiler(object):

	__AFFIX_LEN_MAX = 12
	__WIDTH_DEFAULT = 96
	__width = __WIDTH_DEFAULT
	__stderr = sys.stderr
	__null_fd = os.open(os.devnull, os.O_WRONLY)
	__saved_stdout = os.dup(1)
	__saved_stderr = os.dup(2)
	__error_buffer = []
	__prev_out = ""
	__start = time.clock()
	__delta = __start
	__spacing = " "

	@staticmethod
	def __hours_minutes_seconds(seconds: int) -> Tuple[int, int, int]:
		hours = seconds // 3600
		seconds %= 3600
		minutes = seconds // 60
		seconds %= 60
		return hours, minutes, seconds

	@classmethod
	def __timed(cls, *args: Tuple[str, ...]) -> str:
		out_args = cls.__spacing.join(str(arg) for arg in args).rsplit("\n", 1)
		out_args_end = "" if len(out_args) != 2 else ("\n" if not out_args[-1] else out_args[1])
		out_args = out_args[0].rsplit("\n", 1) if out_args else [""]
		out_args_start, out_args_body = out_args if len(out_args) == 2 else ("", out_args[0] if out_args else "")
		out_time = "".join(Utils.get_formatted(round(v)) + u for v, u in zip(cls.delta_time_in_hours_minutes_seconds(), "hms"))
		max_length = max(3, cls.__width - len(out_args_body) - len(out_time) - cls.__AFFIX_LEN_MAX)
		out_body = "{}{}{} {}".format(out_args_body, " " if args else ".", "." * (max_length - 2), out_time)
		affix = ""
		if cls.__prev_out:
			prev_out = cls.__prev_out.split("\n", 1)
			prev_out_body = prev_out[0]
			prev_out_rest = "\n" if not prev_out[-1] else prev_out[1] if len(prev_out) == 2 else ""
			values = [f for f in cls.delta_time_in_hours_minutes_seconds(True) if f]
			units = "hms"[3 - len(values):3]
			delta = "".join(Utils.get_formatted(round(v)) + u for v, u in zip(values, units))
			affix = "{}\r{} [{}]\n{}".format("\r" if prev_out_rest else "", prev_out_body, delta, prev_out_rest)
		else:
			out_body += out_args_end
		cls.__prev_out = out_body + out_args_end
		cls.__delta = time.clock()
		return affix + out_args_start + out_body

	@classmethod
	def __get_width(cls) -> int:
		try:
			h = ctypes.windll.kernel32.GetStdHandle(-11)
			csbi = ctypes.create_string_buffer(22)
			res = ctypes.windll.kernel32.GetConsoleScreenBufferInfo(h, csbi)
			i = struct.unpack("hhhhHhhhhhh", csbi.raw)[7]
			return i if isinstance(i, int) else cls.__WIDTH_DEFAULT if res else cls.__WIDTH_DEFAULT
		except:
			return cls.__WIDTH_DEFAULT

	@classmethod
	def __get_start(cls) -> float:
		return cls.__start

	@classmethod
	def __get_delta(cls) -> float:
		return cls.__delta

	@classmethod
	def __get_spacing(cls) -> str:
		return cls.__spacing

	@classmethod
	def __set_spacing(cls, value: str):
		cls.__spacing = value

	width = property(__width)
	start = property(__get_start)
	delta = property(__get_delta)
	spacing = property(__get_spacing, __set_spacing)

	@classmethod
	def delta_time(cls, since_timed_last: bool = False) -> float:
		t = time.clock()
		if since_timed_last:
			return t - cls.__delta
		return t - cls.__start

	@classmethod
	def delta_time_in_hours_minutes_seconds(cls, since_timed_last: bool = False) -> str:
		return cls.__hours_minutes_seconds(cls.delta_time(since_timed_last))

	@classmethod
	def capture_errors(cls):
		class ErrorCatcher:
			def write(self, msg):
				if msg.strip():
					cls.__error_buffer.append(msg)
				self.__original_stderr.write(msg)
			def flush(self):
				self.__original_stderr.flush()
		sys.stderr = ErrorCatcher()

	@classmethod
	def print_hidden_errors(cls):
		if not cls.__error_buffer:
			return
		sys.stderr = cls.__stderr
		cls.print_enabled(True)
		cls.print_timed("Hidden errors begin")
		print("\n".join(cls.__error_buffer))
		cls.print_timed("Hidden errors end")
		cls.__error_buffer = []

	@classmethod
	def print_enabled(cls, out: bool = True, err: bool = True):
		if out:
			os.dup2(cls.__saved_stdout, 1)
		else:
			os.dup2(cls.__null_fd, 1)
		if err:
			os.dup2(cls.__saved_stderr, 2)
		else:
			os.dup2(cls.__null_fd, 2)

	@classmethod
	def print_timed(cls, *args: Tuple[str, ...]):
		cls.print_enabled(True)
		s = cls.__timed(*args)
		cls.__prev_out = ""
		print(s)

	@classmethod
	def print_delta_timed(cls, *args: Tuple[str, ...]):
		cls.print_enabled(True)
		s = cls.__timed(*args)
		sys.stdout.write(s)
		sys.stdout.flush()
		cls.print_enabled(False)

	@classmethod
	def reset(cls, reset_clock: bool = True, print_enabled: bool = True, spacing: str = " "):
		cls.__width = cls.__get_width()
		cls.__spacing = spacing
		now = time.clock()
		if reset_clock:
			cls.__start = now
		cls.__delta = now
		cls.__prev_out = ""
		cls.print_enabled(print_enabled)
		print("\n{}\n".format("-" * max(3, cls.__width - cls.__AFFIX_LEN_MAX)))

def register():
	pass

def unregister():
	pass

if __name__ == "__main__":
	register()
