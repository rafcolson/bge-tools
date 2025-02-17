from bge import logic, types, render
from mathutils import Vector
import os, numpy, gzip, typing

class UVTextureData:
	
	_F = 1 / pow(2, 13)

	class StencilLibrary():

		_CLRS = dict(
			{
				"W":"#000000",
				"R":"#FF0000",
				"G":"#00FF00",
				"B":"#0000FF",
				"C":"#00FFFF",
				"M":"#FF00FF",
				"Y":"#FFFF00",
				"K":"#FFFFFF",
			}
		)
		_hexes = []
		_props = []
		
		def _validate(self, descr: str):
			for d in descr:
				if d not in self._CLRS:
					raise ValueError("Invalid descriptor: one or more characters not in 'WRGBCMYK'")
		
		def __init__(self, descr_or_prop_dict: typing.Union[str, dict]):
			t = type(descr_or_prop_dict)
			if t == str:
				self._validate(descr_or_prop_dict)
				for d in descr_or_prop_dict:
					self._hexes.append(self._CLRS[d])
					self._props.append("")
			elif t == dict:
				self._validate("".join(descr_or_prop_dict))
				for descr, prop in descr_or_prop_dict.items():
					hex = self._CLRS[descr]
					self._hexes.append(hex)
					self._props.append(prop)
			else:
				raise TypeError("Invalid descriptor: type should be either 'string' or 'dict'")
		
		def count(self):
			return len(self._hexes)

		def hexes(self):
			return list(self._hexes)

		def props(self):
			return list(self._props)

		def items(self):
			return list(zip(self._hexes, self._props))

		def item(self, i: int):
			return tuple((self._hexes[i], self._props[i]))
		
		def put_prop(self, hex: str, prop: str):
			for i in range(self.length):
				if self._hexes[i] == hex:
					self._props[i] = prop
					return True
			return False
		
		def index_of(self, hex: str):
			try:
				return self._hexes.index(hex)
			except ValueError:
				return -1
			
	def __init__(self, obj: types.KX_GameObject, lib: StencilLibrary, dirs: list = [], ext: str = ".gz"):
		self.object = obj
		self.texture_name = obj.meshes[0].getTextureName(0)
		l = dirs.copy()
		l.append(os.path.splitext(self.texture_name)[0] + ext)
		self.path = os.path.join(logic.expandPath("//"), *l)
		self.indices = self._read_gzipped(ext)
		self.size = 0 if self.indices is None else len(self.indices)
		self.library=lib

	def _read_gzipped(self, ext: str=".gz"):
		if not os.path.exists(self.path):
			return None
		f = gzip.GzipFile(self.path, "r")
		data = numpy.load(f)
		f.close()
		return data

	def ray_cast(
			self,
			obj: types.KX_GameObject,
			vec_to: Vector,
			vec_from: Vector = None,
			dist: float = 0,
			prop: str = "",
			face: bool = True,
			xray: bool = False,
			draw_line: bool = False,
			draw_line_color: list = [1,1,1]
		):
		if draw_line:
			render.drawLine(vec_to, vec_from, draw_line_color)
		hit_obj, hit_pos, hit_nor, hit_pol, hit_uv = obj.rayCast(vec_to, vec_from, dist, prop, face, xray, 2)
		if hit_pol is None:
			return None
		hit_pix = None
		hit_clr = None
		if self.texture_name == hit_pol.getTextureName() and hit_uv is not None:
			u = min(int(self.size * (max(hit_uv.x, self._F) - self._F)), self.size - 1)
			v = min(int(self.size * hit_uv.y), self.size - 1)
			hit_pix = Vector((u, v))
			hit_idx = self.indices[u][v]
			hit_cit = self.library.item(hit_idx)
			hit_clr = [hit_idx, hit_cit[0], hit_cit[1]]
		return [hit_obj, hit_pos, hit_nor, hit_pol, hit_uv, hit_pix, hit_clr]
		
class CustomObject(types.KX_GameObject):

	def __init__(self, own: types.KX_GameObject):
		obj_name = self["UV_DATA_TEX_OBJ_NAME"]
		obj_dirs = self["UV_DATA_TEX_DIR_NAMES"]
		lib = UVTextureData.StencilLibrary("WRGBCMYK")
		self.data = UVTextureData(self.scene.objects[obj_name], lib, obj_dirs.split(", "))
		
	def init(self):
		self.state = logic.KX_STATE2
		
	def update(self):
		if logic.keyboard.events["space"] != logic.KX_INPUT_JUST_ACTIVATED:
			return
		
		vec_from = self.worldPosition
		vec_to = vec_from.copy()
		vec_to.z -= 1.0
		ray_hit = self.data.ray_cast(self, vec_to, vec_from)
		
		if ray_hit is None:
			return
		
		hit_clr = ray_hit[6]
		if hit_clr is not None:
			print(str(hit_clr))
				
def init(cont: types.SCA_PythonController):
	if not cont.sensors[0].positive:
		return
	CustomObject(cont.owner)
	
def update(cont: types.SCA_PythonController):
	cont.owner.update()
	