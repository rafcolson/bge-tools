import os, numpy, gzip
from mathutils import Vector
from typing import Tuple, List, Optional, Any
from bge.types import SCA_PythonController, KX_GameObject, KX_PolyProxy
from bge import logic, render, events

# HIT_UV_TEX_PROPS, HIT_UV_TEXTURES, HIT_UV_GZ_DIRS

DEBUG_PROP_NAME = "BGE_TOOLS_DEBUG"

class UVTextureData:

	_F = 1 / pow(2, 13)

	class Properties:

		_keys = []
		_values = []

		def __init__(self, props: List[Tuple[str, str]]):
			for c, s in props:
				self._keys.append(c)
				self._values.append(s)

		def length(self) -> int:
			return len(self._keys)

		def keys(self) -> List[str]:
			return list(self._keys)

		def values(self) -> List[str]:
			return list(self._values)

		def items(self) -> List[Tuple[str, str]]:
			return list(zip(self._keys, self._values))

		def item(self, i: int) -> Tuple[str, str]:
			return self._keys[i], self._values[i]

		def put(self, k: str, v: str) -> bool:
			for i in range(self.length()):
				if self._keys[i] == k:
					self._values[i] = v
					return True
			return False

		def index_of(self, k: str) -> int:
			try:
				return self._keys.index(k)
			except ValueError:
				return -1

	def __init__(self, props: List[Tuple[str, str]], texture_names: List[str], dirs: str = "", ext: str = ".gz"):
		self.props = UVTextureData.Properties(props)
		self.lib = {}
		for texture_name in texture_names:
			file_name = "{}{}".format(os.path.splitext(texture_name)[0], ext)
			file_path = os.path.join(logic.expandPath("//"), dirs, file_name)
			indices = self._read_gzipped(file_path)
			self.lib[texture_name] = {
				"size": 0 if indices is None else len(indices),
				"indices": indices
			}

	def _read_gzipped(self, file_path: str) -> Optional[numpy.ndarray]:
		if not os.path.exists(file_path):
			return None
		with gzip.GzipFile(file_path, "r") as f:
			data = numpy.load(f)
		return data

	def ray_cast(
		self,
		obj: KX_GameObject,
		vec_to: Vector,
		vec_from: Optional[Vector] = None,
		dist: float = 0,
		prop: str = "",
		face: bool = True,
		xray: bool = False,
		draw_line: bool = False,
		draw_line_color: List[float] = [1, 1, 1]
	) -> Optional[
		Tuple[
			KX_GameObject,
			Tuple[float, float, float],
			Tuple[float, float, float],
			KX_PolyProxy,
			Tuple[float, float],
			Tuple[int, str, str]
		]
	]:
		if draw_line:
			render.drawLine(vec_to, vec_from, draw_line_color)
		hit_obj, hit_pos, hit_nor, hit_pol, hit_uv = obj.rayCast(vec_to, vec_from, dist, prop, face, xray, 2)
		if hit_pol is None:
			return None
		hit_pix = None
		hit_clr = None
		texture_name = hit_pol.getTextureName()
		if texture_name in self.lib.keys() and hit_uv is not None:
			size = self.lib[texture_name]["size"]
			indices = self.lib[texture_name]["indices"]
			u = min(int(size * (max(hit_uv.x, self._F) - self._F)), size - 1)
			v = min(int(size * hit_uv.y), size - 1)
			hit_pix = (u, v)
			hit_idx = int(indices[u][v])
			hit_cit = self.props.item(hit_idx)
			hit_clr = (hit_idx, hit_cit[0], hit_cit[1])
		return hit_obj, hit_pos, hit_nor, hit_pol, hit_uv, hit_pix, hit_clr

class UVTextureDataProp:

	def __init__(self, own: KX_GameObject):
		self.owner = own
		self.data = UVTextureData(HIT_UV_TEX_PROPS, HIT_UV_TEXTURES, HIT_UV_GZ_DIRS)

	def ray_cast(
		self
	) -> Optional[
		Tuple[
			KX_GameObject,
			Tuple[float, float, float],
			Tuple[float, float, float],
			KX_PolyProxy,
			Tuple[float, float],
			Tuple[int, str, str]
		]
	]:
		vec_from = self.owner.worldPosition
		vec_to = vec_from.copy()
		vec_to.z -= 1
		return self.data.ray_cast(self.owner, vec_to, vec_from)

	def init(self):
		self.owner.debug = True

	def update(self):
		hit_clr = None
		l = self.ray_cast()
		if l:
			hit_clr = l[6]
		self.owner[DEBUG_PROP_NAME] = str(hit_clr)

class CustomObject(KX_GameObject):

	SPEED = 0.05

	def __init__(self, old_owner: KX_GameObject):
		pass

	def init(self):
		pass

	def update(self):
		k_r = logic.keyboard.events[events.RIGHTARROWKEY] == logic.KX_INPUT_ACTIVE
		k_l = logic.keyboard.events[events.LEFTARROWKEY] == logic.KX_INPUT_ACTIVE
		k_u = logic.keyboard.events[events.UPARROWKEY] == logic.KX_INPUT_ACTIVE
		k_d = logic.keyboard.events[events.DOWNARROWKEY] == logic.KX_INPUT_ACTIVE
		x = (k_r - k_l) * self.SPEED
		y = (k_u - k_d) * self.SPEED
		self.applyMovement((x, y, 0), False)

def __init__(cont: SCA_PythonController):
	if not cont.sensors[0].positive:
		return

	old_obj = cont.owner
	new_obj = CustomObject(cont.owner)
	assert(old_obj is not new_obj)
	assert(old_obj.invalid)
	assert(new_obj is cont.owner)

	cont.owner[UVTextureDataProp.__name__] = UVTextureDataProp(cont.owner)

def init(cont: SCA_PythonController):
	if not cont.sensors[0].positive:
		return

	cont.owner[UVTextureDataProp.__name__].init()
	cont.owner.init()

def update(cont: SCA_PythonController):
	cont.owner.update()
	cont.owner[UVTextureDataProp.__name__].update()
