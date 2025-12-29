import math, os, sys, pickle, zlib
from mathutils import Matrix, Vector
from collections import OrderedDict
from typing import Union, Type, Iterable, Tuple, List, Dict, Optional, Any
from bge.types import SCA_PythonController, KX_Scene, KX_GameObject
from bge import logic

LOD_SECTIONS_GZ_DIRS = "data"

ERR_MSG_PROPERTY_NOT_FOUND = "Sections property not found: "
ERR_MSG_NAME_NOT_FOUND = "Sections object not found: "

ADDON_PFX = "BGE_TOOLS_LOD_"
PART_PROP_NAME = ADDON_PFX + "PART"
SECT_PROP_NAME = ADDON_PFX + "SECTIONS"
PROG_PROP_NAME = ADDON_PFX + "PROGRESS"
LIB_NEW_ID_PROP_NAME = ADDON_PFX + "LIB_NEW_ID"

SECT_SFX = "_SECT"
PHYSICS_SFX = "_PHYS"
LOD_SFX = "_LOD"
BOUNDS_SFX = "_BOUNDS"

NAME = "NAME"
SIZE = "SIZE"
NUMBER = "NUMBER"
DIMENSIONS = "DIMENSIONS"
HAS_PHYSICS = "HAS_PHYSICS"
LOD_DISTANCES = "LOD_DISTANCES"
LOD_SIZE = "LOD_SIZE"
POINTS = "POINTS"
NORMALS = "NORMALS"
INSTANCES = "INSTANCES"

CHUNK_SIZE_MAX = 2048
PART_SIZE_MAX = 128
OBJ_BOUNDS_MARGIN = 0.04

class LODSectionsUtils(object):

	CUST_PROP_NAME = "CUST"
	ID_PROP_NAME = "ID"
	INST_ATTR_NAME = "instances"

	# math utils

	@staticmethod
	def clamped(f: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
		return max(min_val, min(max_val, f))

	@staticmethod
	def get_floor_factor(f: float, i: int) -> int:
		return 0 if i == 0 else f // i * i

	@staticmethod
	def get_grid_point(position: Tuple[float, ...], size: Tuple[int, ...], axis_range: str = "XYZ") -> List[Tuple[int, ...]]:
		l = []
		axis = "XYZ"[:len(position)]
		for i, a in enumerate(axis):
			if a in axis_range:
				l.append(LODSectionsUtils.get_floor_factor(position[i], size[i]) + size[i] // 2)
		return l

	# string utils

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
		return LODSectionsUtils.get_formatted(i, suffix, "0", num_digits)
	
	@staticmethod
	def get_available_id(excluded: List[str], suffix: str = ".", num_digits: int = 3) -> str:
		i = 0
		id = LODSectionsUtils.get_id(i, suffix, num_digits)
		while id in excluded:
			i += 1
			id = LODSectionsUtils.get_id(i, suffix, num_digits)
		return id

	@staticmethod
	def get_name_id(name: str, excluded: List[str]):
		id_list = []
		for n in excluded:
			l = n.rsplit(".")
			if len(l) == 2:
				id_list.append(".{}".format(l[1]))
		return name + LODSectionsUtils.get_available_id(id_list)

	# class | module utils

	@staticmethod
	def get_module(module_name: str) -> Any:
		return sys.modules.get(module_name) or __import__(module_name)

	@staticmethod
	def get_module_and_class(path: str) -> Tuple[Any, Type[Any]]:
		result = path.rsplit(".", 1)
		if not result[0] or len(result) == 1:
			print("Invalid path: {}".format(path))
			return None
		mod_name, cls_name = result
		mod = LODSectionsUtils.get_module(mod_name)
		if not mod:
			print("Invalid module name: {}".format(mod_name))
			return None
		cls = getattr(mod, cls_name, None)
		if not cls:
			print("Invalid class name: {}".format(cls_name))
			return None
		return mod, cls

	@staticmethod
	def get_class(obj: Any) -> str:
		return obj.__class__

	@staticmethod
	def get_class_name(obj: Any) -> str:
		return LODSectionsUtils.get_class(obj).__name__

	@staticmethod
	def get_module_name(cls: Type[Any]) -> Any:
		return cls.__module__

	@staticmethod
	def get_class_module(cls: Type[Any]) -> Any:
		return LODSectionsUtils.get_module(LODSectionsUtils.get_module_name(cls))

	# object utils

	@staticmethod
	def clamp(obj: KX_GameObject, precision: int = 2):
		if not ut.has_dynamic_or_rigid_body_physics(obj):
			return
		obj.worldPosition = [round(f, precision) for f in obj.worldPosition]

	@staticmethod
	def get_median_point_and_dimensions(object: KX_GameObject):
		mesh = object.meshes[0]
		nl = [[], [], []]
		for mat_index in range(mesh.numMaterials):
			for vert_index in range(mesh.getVertexArrayLength(mat_index)):
				v = mesh.getVertex(mat_index, vert_index).XYZ
				[nl[i].append(v[i]) for i in range(3)]
		if not len(nl[1]):
			return Vector(), Vector()
		median_point = Vector([sum(axis) / len(axis) for axis in nl])
		dimensions = Vector([abs(max(axis)) + abs(min(axis)) for axis in nl])
		return median_point, dimensions

	@staticmethod
	def has_dynamic_or_rigid_body_physics(obj: KX_GameObject) -> bool:
		return obj.getPhysicsId() and obj.mass

	@staticmethod
	def get_base_id(object: KX_GameObject) -> Tuple[str, Optional[str]]:
		base = object.name
		id = None
		l = base.rstrip(".")
		if len(l) == 2:
			base, id = l
			id = ".{}".format(id)
		return base, id

	@staticmethod
	def get_props(object: KX_GameObject) -> Dict[str, Any]:
		return {n : object[n] for n in object.getPropertyNames()}

	@staticmethod
	def get_mutated_id(object: KX_GameObject) -> Optional[str]:
		if LODSectionsUtils.ID_PROP_NAME in object.getPropertyNames():
			return object[LODSectionsUtils.ID_PROP_NAME]
		return None

	@staticmethod
	def get_mutated(
		handle: Union[KX_GameObject, SCA_PythonController],
		cls: Union[str, Type[KX_GameObject]],
		id: str = None,
		*args: Tuple[str, ...]
	) -> Optional[Union[Any, KX_GameObject]]:
		if isinstance(handle, KX_GameObject):
			old_obj = handle
			mod = None
			if isinstance(cls, str):
				result = LODSectionsUtils.get_module_and_class(cls)
				if not result:
					return None
				mod, cls = result
			else:
				mod = LODSectionsUtils.get_class_module(cls)
			mod_instances = LODSectionsUtils.get_module_instances(cls, True)
			cls_name = cls.__name__
			if cls_name not in mod_instances:
				mod_instances[cls_name] = OrderedDict()
			d = mod_instances[cls_name]
			if not id:
				id = LODSectionsUtils.get_mutated_id(old_obj)
			if not id:
				id = old_obj.name
			if id in d:
				new_obj = d[id]
			else:
				new_obj = cls(old_obj, *args)
				cp = "{}.{}".format(mod.__name__, cls_name)
				new_obj[LODSectionsUtils.CUST_PROP_NAME] = cp
				new_obj[LODSectionsUtils.ID_PROP_NAME] = id
				d[id] = new_obj
		elif isinstance(handle, SCA_PythonController):
			cont = handle
			old_obj = cont.owner
			new_obj = cls(old_obj, *args)
			assert(old_obj is not new_obj)
			assert(old_obj.invalid)
			assert(new_obj is cont.owner)
		else:
			print("Invalid handle: {}".format(LODSectionsUtils.get_class_name(handle)))
			return None
		return new_obj

	@staticmethod
	def end_mutated(object: KX_GameObject) -> bool:
		id = LODSectionsUtils.get_mutated_id(object)
		if id:
			mod_instances = LODSectionsUtils.get_module_instances(object)
			if mod_instances and id in mod_instances:
				mod_instances[id].endObject()
				del mod_instances[id]
				return True
		return False

	@staticmethod
	def end_object(object: KX_GameObject) -> Dict[str, Any]:
		props = LODSectionsUtils.get_props(object)
		if LODSectionsUtils.CUST_PROP_NAME in props:
			LODSectionsUtils.end_mutated(object)
		else:
			object.endObject()
		return props

	@staticmethod
	def end_objects(objects: Iterable[KX_GameObject]):
		objects = set(objects)
		while objects:
			parents = set(o for o in objects if not o.parent)
			if not parents:
				for obj in objects:
					LODSectionsUtils.end_object(obj)
				break
			objects.difference_update(parents)
			for obj in objects:
				LODSectionsUtils.end_object(obj)

	@staticmethod
	def get_group_parents(instance: KX_GameObject) -> Optional[List[KX_GameObject]]:
		l = []
		if instance.groupMembers:
			for obj in instance.groupMembers:
				if obj.parent is None:
					l.append(obj)
		return l

	@staticmethod
	def get_group_parent(instance: KX_GameObject) -> Optional[KX_GameObject]:
		l = LODSectionsUtils.get_group_parents(instance)
		return l[0] if l else None

	@staticmethod
	def get_module_instances(handle: Union[Type[KX_GameObject], KX_GameObject, Any], create: bool = False) -> Optional[Dict[str, Union[KX_GameObject, Any]]]:
		cls = handle if isinstance(handle, type) else LODSectionsUtils.get_class(handle)
		mod = LODSectionsUtils.get_class_module(cls)
		if not hasattr(mod, LODSectionsUtils.INST_ATTR_NAME):
			if not create:
				return None
			setattr(mod, LODSectionsUtils.INST_ATTR_NAME, {})
		return getattr(mod, LODSectionsUtils.INST_ATTR_NAME)

	@staticmethod
	def remove_from_module_instances(object: Union[KX_GameObject, Any]) -> bool:
		result = False
		if LODSectionsUtils.ID_PROP_NAME in object.getPropertyNames():
			mod_instances = LODSectionsUtils.get_module_instances(object)
			if mod_instances:
				cls_name = LODSectionsUtils.get_class_name(object)
				if cls_name in mod_instances:
					d = mod_instances[cls_name]
					id = object[LODSectionsUtils.ID_PROP_NAME]
					if id in d:
						del d[id]
						result = True
						if not len(d):
							del mod_instances[cls_name]
						print("Removed module instance of {}: {}".format(cls_name, id))
				if not len(mod_instances):
					mod = LODSectionsUtils.get_class_module(LODSectionsUtils.get_class(object))
					delattr(mod, LODSectionsUtils.INST_ATTR_NAME)
					print("Removed: {}.{}".format(mod.__name__, LODSectionsUtils.INST_ATTR_NAME))
		return result

	@staticmethod
	def remove_module_instances(handle: Union[Type[KX_GameObject], KX_GameObject, Any]) -> bool:
		cls = handle if isinstance(handle, type) else LODSectionsUtils.get_class(handle)
		mod = LODSectionsUtils.get_class_module(cls)
		if hasattr(mod, LODSectionsUtils.INST_ATTR_NAME):
			delattr(mod, LODSectionsUtils.INST_ATTR_NAME)
			return True
		return False

	# scene utils

	@staticmethod
	def add_object(
		scene: KX_Scene,
		object: Union[str, KX_GameObject],
		ref: Optional[Union[str, KX_GameObject]] = None,
		time: int = 0,
		props: Optional[Dict[str, str]] = None,
		matrix_world: Optional[Matrix] = None
	) -> KX_GameObject:
		obj = scene.addObject(object, ref, time)
		if matrix_world:
			obj.worldTransform = matrix_world
		if props:
			for k, v in props.items():
				obj[k] = v
		return obj

	@staticmethod
	def add_mutated(
			scene: KX_Scene,
			object: Union[str, KX_GameObject],
			cls: Union[str, Type[KX_GameObject]],
			id: str = None,
			ref: Optional[Union[str, KX_GameObject]] = None,
			time: int = 0,
			props: Optional[Dict[str, str]] = None,
			matrix_world: Optional[Matrix] = None
		) -> Optional[Union[Any, KX_GameObject]]:
			obj = LODSectionsUtils.add_object(scene, object, ref, time, props, matrix_world)
			return LODSectionsUtils.get_mutated(obj, cls, id)

	# file utils

	@staticmethod
	def read_zlibbed(file_path):
		if not os.path.exists(file_path):
			return None
		with open(file_path, "rb") as f:
			zz = f.read()
		data = pickle.loads(zlib.decompress(zz))
		return data

ut = LODSectionsUtils

class LODSections(KX_GameObject):
	
	STATE_INIT = logic.KX_STATE2
	STATE_LOAD = logic.KX_STATE3
	STATE_EDIT = logic.KX_STATE4
	STATE_ADD = logic.KX_STATE5
	STATE_POPULATE = logic.KX_STATE6
	STATE_SETTLE = logic.KX_STATE7
	STATE_UPDATE = logic.KX_STATE8
	STATE_END = logic.KX_STATE9

	LOADING_WEIGHTS = [0.05, 0.75, 0.1, 0.1]

	def endObject(self):
		self.__bounds.collisionCallbacks.clear()
		self.state = self.STATE_END

	def __init__(self, own):
		self.__points_keys = None
		self.__points_values = None
		self.__normals = None
		self.__chunks = None
		self.__parts = None
		self.__num_chunks = None
		self.__num_parts = None
		self.__lod_size = None
		self.__index = 0
		self.__tmp = []
		self.__size = Vector().to_2d()
		self.__number = Vector().to_2d()
		self.__dimensions = Vector()
		self.__points = OrderedDict()
		self.__instances = {}
		self.__dynamic_instances = {}
		self.__lib_news = {}
		self.__target_position = Vector()
		self.__has_physics = False
		self.__lod_distances = []
		self.__bounds = None
		self.__target = None
		self.__loading_progress = 0.0
		self.__visual_sections = []
		self.__physical_sections = []

		self.state = self.STATE_INIT

	def __update_progress(self, value: float, step_idx: int):
		accumulated_weight = sum(self.LOADING_WEIGHTS[:step_idx])
		step_weight = self.LOADING_WEIGHTS[step_idx]
		self.__loading_progress = round(accumulated_weight + value * step_weight, 3)
		self[PROG_PROP_NAME] = self.__loading_progress
	
	def __get_data(self, ext=".zz"):
		file_name = "{}{}".format(self.name, ext)
		file_path = os.path.join(logic.expandPath("//"), LOD_SECTIONS_GZ_DIRS, file_name)
		return ut.read_zlibbed(file_path)

	def __get_chunks(self):
		nl = []
		l = []
		i = 0
		for ob_name, ob_normals in self.__normals.items():
			num_ob_normals = len(ob_normals)
			if i + num_ob_normals > CHUNK_SIZE_MAX:
				nl.append(l.copy())
				l.clear()
				i = 0
			else:
				i += num_ob_normals
			l.append(ob_name)
		if len(l):
			nl.append(l)
		return nl
		
	def __get_parts(self):
		nl = []
		l = [n for n in self.__normals if LOD_SFX not in n]
		n = len(l)
		i = 0
		while i + PART_SIZE_MAX < n:
			j = i + PART_SIZE_MAX
			nl.append(l[i:j])
			i = j
		nl.append(l[i:n])
		return nl
	
	def __init_lib_news(self):
		for l in self.__chunks:
			for sect_name in l:
				self.__lib_news[sect_name] = {}

	def __add_instance(self, name: str, id: str, transform: Matrix, properties: Dict[str, Any] = {}, has_dynamics: bool = False):
		t = transform.translation.xy
		sect_name = self.get_section_name(t)
		if not sect_name:
			return
		data = [[list(v) for v in transform.row], properties]
		if not has_dynamics:
			if sect_name not in self.__instances:
				self.__instances[sect_name] = {}
			d = self.__instances[sect_name]
			if name not in d:
				d[name] = []
			d[name].append(data)
		else:
			if sect_name not in self.__dynamic_instances:
				self.__dynamic_instances[sect_name] = {}
			d = self.__dynamic_instances[sect_name]
			if name not in d:
				d[name] = {}
			if name not in self.__tmp:
				self.__tmp[name] = []
			if not id:
				id = ut.get_name_id(name, self.__tmp[name])
			else:
				self.__tmp[name].append(id)
			d[name][id] = [None, data]

	def __add_instances(self):
		l = self.__tmp
		self.__tmp = {}
		for n, id, m, d, b in l:
			self.__add_instance(n, id, m, d, b)
		self.__tmp.clear()

	def __remove_physical_sections(self, physical_sections: List[str] = []):
		for sect_name in list(self.__physical_sections):
			if sect_name in physical_sections:
				continue

			self.__physical_sections.remove(sect_name)
			self.scene.objects[sect_name + PHYSICS_SFX].endObject()

	def __add_physical_sections(self, physical_sections: List[str], init: bool = False):
		for sect_name in physical_sections:
			if not init:
				if sect_name in self.__physical_sections:
					continue

			self.__physical_sections.append(sect_name)
			inst = self.scene.addObject(sect_name + PHYSICS_SFX)
			inst.setParent(self, False, False)
			inst.worldTransform = self.worldTransform * inst.worldTransform
			if sect_name not in self.__instances:
				continue

			for n, nl in self.__instances[sect_name].items():
				if n + PHYSICS_SFX not in self.scene.objectsInactive:
					continue

				for l in nl:
					o = self.scene.addObject(n + PHYSICS_SFX)
					o.setParent(inst, False, False)
					o.worldTransform = Matrix(l[0])

	def __remove_visual_sections(self, visual_sections: List[str] = []):
		for sect_name in list(self.__visual_sections):
			if sect_name in visual_sections:
				continue

			self.__visual_sections.remove(sect_name)
			if sect_name in self.__dynamic_instances:
				for name, d in self.__dynamic_instances[sect_name].items():
					for id in d.copy():
						self.__update_dynamics(sect_name, name, id, visual_sections)

			sect = self.scene.objects[sect_name]
			for inst in sect.children:
				lib_new_name = None
				if LIB_NEW_ID_PROP_NAME in inst.getPropertyNames():
					sect_id = sect_name.split(SECT_SFX)[1]
					lib_new_id = inst[LIB_NEW_ID_PROP_NAME]
					lib_new_name = SECT_SFX + sect_id + lib_new_id
				inst.endObject()
				if lib_new_name:
					logic.LibFree(lib_new_name)
			self.__lib_news[sect_name].clear()

			sect.endObject()

	def __add_dynamic_instances(self, sect_name: str, init: bool = False):
		if sect_name in self.__dynamic_instances:
			for name, d in self.__dynamic_instances[sect_name].items():
				for id, l in d.items():
					inst, data = l
					if init and inst:
						continue
					transform, properties = data
					m = self.worldTransform * Matrix(transform)
					if ut.CUST_PROP_NAME in properties:
						cls = properties[ut.CUST_PROP_NAME]
						id = properties[ut.ID_PROP_NAME]
						inst = ut.add_mutated(self.scene, name, cls, id, props=properties, matrix_world=m)
						if inst:
							print("Added mutated to {}: {}".format(sect_name, id))
					else:
						inst = ut.add_object(self.scene, name, props=properties, matrix_world=m)
						print("Added to {}: {}".format(sect_name, id))
					if init and inst:
						inst.suspendDynamics()
					l[0] = inst
		
	def __add_static_instances(self, sect_name: str):
			if sect_name in self.__instances:
				for name, nl in self.__instances[sect_name].items():
					for l in nl:
						inst = self.scene.addObject(name)
						inst.setParent(self.scene.objects[sect_name], False, False)
						transform, properties = l
						m = Matrix(transform)
						gpl = ut.get_group_parents(inst)
						if gpl:
							for gp in gpl:
								gp.worldTransform = m
						else:
							inst.worldTransform = m
						for k, v in properties.items():
							inst[k] = v
						if LIB_NEW_ID_PROP_NAME in inst:
							lib_new_id = inst[LIB_NEW_ID_PROP_NAME]
							if not lib_new_id:
								d = self.__lib_news[sect_name]
								if name not in d:
									d[name] = []
								inst[LIB_NEW_ID_PROP_NAME] = lib_new_id = LODSectionsUtils.get_name_id(name, d.keys())
							sect_id = sect_name.split(SECT_SFX)[1]
							lib_new_name = SECT_SFX + sect_id + lib_new_id
							new_mesh = logic.LibNew(lib_new_name, "Mesh", [inst.meshes[0].name])[0]
							inst.replaceMesh(new_mesh, True, True)
	
	def __add_visual_sections(self, visual_sections: List[str], init: bool = False):
		for sect_name in visual_sections:
			if sect_name in self.__visual_sections:
				continue

			self.__visual_sections.append(sect_name)
			sect = self.scene.addObject(sect_name)
			sect.setParent(self, False, True)
			sect.worldTransform = self.worldTransform * sect.worldTransform

			self.__add_static_instances(sect_name)

		if init:
			return

		for sect_name in visual_sections:
			self.__add_dynamic_instances(sect_name, True)

	def __update_dynamics(self, sect_name: str, name: str, id: str, sections: List[str] = None, suspend: bool = False):
		d = self.__dynamic_instances[sect_name][name]
		if id not in d:
			return
		inst = d[id][0]
		if inst:
			m = self.worldTransform.inverted() * inst.worldTransform
			transform = [list(v) for v in m.row]
			properties = ut.get_props(inst)
			sect_new = self.get_section_name(m.translation.xy)
			is_moved = sect_name != sect_new
			if is_moved:
				del d[id]
				if sect_new not in self.__dynamic_instances:
					self.__dynamic_instances[sect_new] = {}
				items = self.__dynamic_instances[sect_new]
				if name not in items:
					items[name] = {}
				d = items[name]
				sect_name = sect_new
			if sections and sect_name not in sections:
				self.__suspend_instance(inst)
				inst.endObject()
				inst = None
			elif suspend:
				self.__suspend_instance(inst)
			d[id] = [inst, [transform, properties]]
			print("Suspended and {} {}: {}".format("moved to" if is_moved else "updated in" if inst else "removed from", sect_name, id))

	def __suspend_instance(self, inst: Union[KX_GameObject, Any]):
		inst.worldLinearVelocity.zero()
		inst.worldAngularVelocity.zero()
		inst.suspendDynamics()

	def __damp_instance(self, inst: KX_GameObject, damping: float, precision: int) -> float:
		f = 1.0 - damping
		inst.worldAngularVelocity *= f
		inst.worldLinearVelocity.x *= f
		inst.worldLinearVelocity.y *= f
		ut.clamp(inst, precision)

	def __settle_instance_register(self, inst: KX_GameObject, sect_name: str, id: str):
		self.__tmp[inst] = [sect_name, id, inst.linearDamping, inst.angularDamping]
		inst.setDamping(0.0, 0.0)

	def __settle_instances(self, damping: float = 0.999):
		d = self.__tmp.copy()
		precision = math.ceil(-math.log10(1.0 - damping))
		mag_max = 0.2
		for inst, (sect_name, id, lin_damping, ang_damping) in d.items():
			try:
				if inst.worldLinearVelocity.magnitude < mag_max:
					inst.setDamping(lin_damping, ang_damping)
					self.__update_dynamics(sect_name, inst.name, id, self.__visual_sections, True)
					del self.__tmp[inst]
				else:
					self.__damp_instance(inst, damping, precision)
			except SystemError:
				del self.__tmp[inst]
		d.clear()

	def __suspend_instances(self):
		self.__settle_instances()

		max_dist = self.__lod_distances[1] if len(self.__lod_distances) > 1 else min(self.__size.x, self.__size.y)
		for sect_name in self.__visual_sections:
			if sect_name not in self.__dynamic_instances:
				continue

			for d in self.__dynamic_instances[sect_name].values():
				for id, (inst, _) in d.items():
					if inst and not inst.isSuspendDynamics:
						dist = inst.getDistanceTo(self.__target_position)
						if dist < max_dist:
							continue

						inst.worldAngularVelocity.zero()
						if ut.CUST_PROP_NAME in inst.getPropertyNames():
							self.__suspend_instance(inst)
							print("Suspended mutated in {}: {}".format(sect_name, id))
						else:
							self.__settle_instance_register(inst, sect_name, id)

	def __restore_instances(self):
		min_dist = self.__lod_distances[1] * 0.25 if len(self.__lod_distances) > 1 else min(self.__size.x, self.__size.y) * 0.25
		for sect_name in self.__physical_sections:
			if sect_name not in self.__dynamic_instances:
				continue

			for d in self.__dynamic_instances[sect_name].values():
				for id, (inst, _) in d.items():
					if inst and inst.isSuspendDynamics:
						dist = inst.getDistanceTo(self.__target_position)
						if dist > min_dist:
							continue

						if not ut.CUST_PROP_NAME in inst.getPropertyNames():
							inst.worldPosition.z += OBJ_BOUNDS_MARGIN
						inst.restoreDynamics()
						print("Restored in {}: {}".format(sect_name, id))

	def __bounds_ccb(self, hit_obj: KX_GameObject):
		hit_obj_name = hit_obj.name

		print("Out of bounds: {}".format(hit_obj_name))

		if ut.ID_PROP_NAME in hit_obj.getPropertyNames():
			hit_obj_id = hit_obj[ut.ID_PROP_NAME]
			for sect_name, sect_dict in self.__dynamic_instances.items():
				if not sect_dict:
					continue
				for name, d in sect_dict.items():
					if hit_obj_name != name:
						continue
					for id, (inst, data) in d.items():
						if hit_obj_id != id or hit_obj is not inst:
							continue
						hit_obj.worldLinearVelocity.zero()
						hit_obj.worldAngularVelocity.zero()
						v_mp, v_dim = ut.get_median_point_and_dimensions(hit_obj)
						t = self.worldTransform * Matrix(data[0])
						t.translation.z += v_dim.z * 0.5 + v_mp.z + OBJ_BOUNDS_MARGIN
						hit_obj.worldTransform = t

						print("Set within bounds of {}: {}".format(sect_name, id))
						return

		elif hit_obj.parent is not None:
			self.__bounds_ccb(hit_obj.parent)
			return

		hit_obj.endObject()

		print("Ended: {}".format(hit_obj_name))

	def __get_physical_sections(self) -> List[str]:
		return [n for n in self.__visual_sections if self.scene.objects[n].currentLodLevel == 1]

	def get_section_name(self, position_xy: Tuple[float, float]) -> Optional[str]:
		l = ut.get_grid_point(position_xy, self.__size)
		try:
			v = self.__points_values.index(l)
		except ValueError:
			return None
		id = self.__points_keys[v]
		return self[SECT_PROP_NAME] + SECT_SFX + id

	def get_sections(self, position_xy: Tuple[float, float], level: int) -> List[str]:
		d = max(self.__size.x, self.__size.y)
		r = self.__lod_distances[level]
		cx, cy = position_xy
		i = round(r / d)
		s = set()
		for dx in range(-i - 1, i + 1):
			for dy in range(-i - 1, i + 1):
				x = dx * d
				y = dy * d
				if math.hypot(x, y) < r:
					n = self.get_section_name((cx + x, cy + y))
					if n:
						s.add(n)
		return list(s)

	def init(self):
		if SECT_PROP_NAME not in self:
			raise KeyError(ERR_MSG_PROPERTY_NOT_FOUND + SECT_PROP_NAME)
		sections_parent_name = self[SECT_PROP_NAME]
		if sections_parent_name not in self.scene.objectsInactive:
			raise NameError(ERR_MSG_NAME_NOT_FOUND + sections_parent_name)

		self.visible = False
		sections_parent = self.scene.objectsInactive[sections_parent_name]
		self.replaceMesh(sections_parent.meshes[0], True, False)
		mat_inv = self.worldTransform.inverted()
		for obj in self.children:
			if PART_PROP_NAME in obj:
				obj.endObject()
			else:
				m = mat_inv * obj.worldTransform
				l = ut.get_group_parents(obj)
				if not l:
					l.append(obj)
				_, id = ut.get_base_id(obj)
				o = l[0]
				n = o.name
				b_id = "{}{}".format(n, id) if id else obj.name
				d = ut.get_props(obj)
				d[LODSectionsUtils.ID_PROP_NAME] = b_id
				b = ut.has_dynamic_or_rigid_body_physics(o)
				self.__tmp.append([n, b_id, m, d, b])
				obj.endObject()

		self.__bounds = self.scene.addObject(self[SECT_PROP_NAME] + BOUNDS_SFX)
		self.__bounds.setParent(self, False, False)
		self.__bounds.collisionCallbacks.append(self.__bounds_ccb)

		self.__target = self.scene.active_camera
		self.state = self.STATE_LOAD

	def load(self):
		data = self.__get_data()
		
		self.__size.xy = data[SIZE]
		self.__number.xy = data[NUMBER]
		self.__dimensions.xyz = data[DIMENSIONS]
		self.__has_physics = data[HAS_PHYSICS]
		self.__lod_distances = data[LOD_DISTANCES]
		self.__points = OrderedDict(data[POINTS])
		self.__instances = data[INSTANCES]
		
		self.__lod_size = data[LOD_SIZE]
		self.__points_keys = list(self.__points.keys())
		self.__points_values = list(self.__points.values())
		self.__normals = data[NORMALS]
		self.__chunks = self.__get_chunks()
		self.__parts = self.__get_parts()
		self.__num_chunks = len(self.__chunks)
		self.__num_parts = len(self.__parts)

		self.__init_lib_news()
		self.__add_instances()

		self.__update_progress(1, 0)
		
		self.state = self.STATE_EDIT if self.__has_physics else self.STATE_UPDATE
		
	def edit(self):
		
		def copy_custom_normals(l: List[str]):
			for sect_name in l:
				sect_normals = self.__normals[sect_name]
				sect = self.scene.objectsInactive[sect_name]
				sect_mesh = sect.meshes[0]
				
				for mat_id in range(sect_mesh.numMaterials):
					for vert_id in range(sect_mesh.getVertexArrayLength(mat_id)):
						vert = sect_mesh.getVertex(mat_id, vert_id)
						id = str([round(f) for f in vert.XYZ.xy])
						if id in sect_normals:
							vert.normal = sect_normals[id]
							
		if self.__index == self.__num_chunks:
			self.__index = 0
			self.state = self.STATE_ADD
		else:
			copy_custom_normals(self.__chunks[self.__index])
			self.__index += 1
			self.__update_progress(self.__index / self.__num_chunks, 1)

	def add(self):
		
		def add_part(l: List[str]):
			self.__add_visual_sections(l, True)
			self.__add_physical_sections(l, True)
				
		if self.__index == self.__num_parts:
			self.__index = 0
			self.state = self.STATE_POPULATE
		else:
			add_part(self.__parts[self.__index])
			self.__index += 1
			self.__update_progress(self.__index / self.__num_parts, 2)
			
	def populate(self):
        
		def populate_part(l: List[str]):
			for sect_name in l:
				self.__add_dynamic_instances(sect_name, True)

		if self.__index == self.__num_parts:
			self.__index = 0
			print("Restoring dynamics for unsettled instances")
			for sect_name in self.visual_sections:
				if sect_name in self.__dynamic_instances:
					for _, d in self.__dynamic_instances[sect_name].items():
						for _, l in d.items():
							inst, _ = l
							if inst:
								inst.restoreDynamics()
			self.state = self.STATE_SETTLE
		else:
			populate_part(self.__parts[self.__index])
			self.__index += 1
			self.__update_progress(self.__index / self.__num_parts, 3)
			
	def settle(self):
		self.__settle_instances()

		unsettled_count = 0
		for sect_name in self.__physical_sections:
			if sect_name not in self.__dynamic_instances:
				continue

			for d in self.__dynamic_instances[sect_name].values():
				for id, (inst, _) in d.items():
					if id in self.__tmp or inst.isSuspendDynamics:
						continue

					self.__settle_instance_register(inst, sect_name, id)
					unsettled_count += 1

		if unsettled_count + len(self.__tmp) == 0:
			print("Settled all dynamic instances")
			self.__tmp.clear()
			if self.__target:
				self.__target_position = self.__target.worldPosition.copy()
			visual_sections = self.get_sections(self.__target_position.xy, self.__lod_size)
			self.__remove_visual_sections(visual_sections)
			if self.__has_physics:
				physical_sections = self.__get_physical_sections()
				self.__remove_physical_sections(physical_sections)
			print("Starting update state with {}/{} of physical/visual sections".format(len(self.physical_sections), len(self.visual_sections)))
			self.state = self.STATE_UPDATE

	def update(self):
		if self.__target:
			self.__target_position = self.__target.worldPosition.copy()
		visual_sections = self.get_sections(self.__target_position.xy, self.__lod_size)
		self.__remove_visual_sections(visual_sections)
		self.__add_visual_sections(visual_sections)
		if self.__has_physics:
			physical_sections = self.__get_physical_sections()
			self.__suspend_instances()
			self.__remove_physical_sections(physical_sections)
			self.__add_physical_sections(physical_sections)
			self.__restore_instances()

	def end(self):
		self.__remove_physical_sections()
		self.__remove_visual_sections()
		ut.remove_from_module_instances(self)
		KX_GameObject.endObject(self)

	@property
	def has_physics(self):
		return self.__has_physics

	@property
	def lod_distances(self):
		return list(self.__lod_distances)

	@property
	def loading_progress(self):
		return self.__loading_progress

	@property
	def visual_sections(self):
		return self.__visual_sections

	@property
	def physical_sections(self):
		return self.__physical_sections

	@property
	def bounds(self):
		return self.__bounds

	@property
	def target(self):
		return self.__target

	@target.setter
	def target(self, value: KX_GameObject):
		self.__target = value if value and value in self.scene.objects else self.scene.active_camera

def __init__(cont: SCA_PythonController):
	if not cont.sensors[0].positive:
		return
	ut.get_mutated(cont.owner, LODSections)

def init(cont: SCA_PythonController):
	if not cont.sensors[0].positive:
		return
	cont.owner.init()

def load(cont: SCA_PythonController):
	if not cont.sensors[0].positive:
		return
	cont.owner.load()
	
def edit(cont: SCA_PythonController):
	cont.owner.edit()
	
def add(cont: SCA_PythonController):
	cont.owner.add()
	
def populate(cont: SCA_PythonController):
	cont.owner.populate()
	
def settle(cont: SCA_PythonController):
	cont.owner.settle()

def update(cont: SCA_PythonController):
	cont.owner.update()

def end(cont: SCA_PythonController):
	if not cont.sensors[0].positive:
		return
	cont.owner.end()
