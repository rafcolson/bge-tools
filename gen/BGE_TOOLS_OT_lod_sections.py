from bge import types, logic
from collections import OrderedDict
from mathutils import Matrix, Vector
from errno import ENOENT
import pickle
import os

ERR_MSG_PROPERTY_NOT_FOUND = "Sections property not found: "
ERR_MSG_NAME_NOT_FOUND = "Sections object not found: "

LOD_SECTIONS_PROP_NAME = "BGE_TOOLS_LOD_SECTIONS"
LOD_PROGRESS_PROP_NAME = "BGE_TOOLS_LOD_PROGRESS"
LOD_SIZE_PROP_NAME = "BGE_TOOLS_LOD_SIZE"

LIB_NEW_ID_PROP_NAME = "LIB_NEW_ID"

TERRAIN_CHILD_PROP_NAME = "_TERRAIN_CHILD"

SECT_SUFFIX = "_SECT"
PHYSICS_SUFFIX = "_PHYS"
LOD_SUFFIX = "_LOD"
EXTENSION = ".txt"

NAME = "NAME"
SIZE = "SIZE"
NUMBER = "NUMBER"
DIMENSIONS = "DIMENSIONS"
LOD_SIZE = "LOD_SIZE"
POINTS = "POINTS"
INSTANCES = "INSTANCES"
NORMALS = "NORMALS"

CHUNK_SIZE_MAX = 512
PART_SIZE_MAX = 32

class LODSections(types.KX_GameObject):
	
	__points_keys = None
	__points_values = None
	__normals = None
	__chunks = None
	__parts = None
	__num_chunks = None
	__num_parts = None
	__lod_size = None
	__index = 0
	
	size = Vector().to_2d()
	number = Vector().to_2d()
	dimensions = Vector().to_2d()
	points = OrderedDict()
	instances = {}
	
	sections = []
	visual_sections = []
	physical_sections = []
	num_lib_news = {}
	
	loading_progress = 0.0
	
	def __init__(self, own):
		if LOD_SECTIONS_PROP_NAME not in self:
			raise KeyError(ERR_MSG_PROPERTY_NOT_FOUND + LOD_SECTIONS_PROP_NAME)
		if self[LOD_SECTIONS_PROP_NAME] not in self.scene.objectsInactive:
			raise NameError(ERR_MSG_NAME_NOT_FOUND + self[LOD_SECTIONS_PROP_NAME])
			
		self.visible = False
		sections_parent = self.scene.objectsInactive[self[LOD_SECTIONS_PROP_NAME]]
		self.reinstancePhysicsMesh(sections_parent, sections_parent.meshes[0])
		for ob in self.children:
			if TERRAIN_CHILD_PROP_NAME in ob:
				ob.endObject()
			elif ob.groupMembers is not None:
				for o in ob.groupMembers:
					if o.parent is None:
						m = self.worldTransform * ob.worldTransform
						self.add_instance(o, m, {n : ob[n] for n in ob.getPropertyNames()})
				ob.endObject()
		self.state = logic.KX_STATE2
		
	def __update_progress(self, fac=1, step=1, num_steps=1):
		self[LOD_PROGRESS_PROP_NAME] = self.loading_progress = (fac + step - 1) / num_steps
		
	def load(self):
		
		def get_data():
			dir_path = logic.expandPath("//" + LOD_SECTIONS_PROP_NAME)
			if not os.path.exists(dir_path):
				raise FileNotFoundError(ENOENT, os.strerror(ENOENT), dir_path)
				
			file_path = os.path.join(dir_path, self.name + EXTENSION)
			with open(file_path, "rb") as f:
				data = pickle.load(f)
				
			return data
		
		def get_chunks():
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
			
		def get_parts():
			nl = []
			l = [n for n in self.__normals if LOD_SUFFIX not in n]
			n = len(l)
			i = 0
			while i + PART_SIZE_MAX < n:
				j = i + PART_SIZE_MAX
				nl.append(l[i:j])
				i = j
			nl.append(l[i:n])
			return nl
			
		data = get_data()
		
		self.size.xy = data[SIZE]
		self.number.xy = data[NUMBER]
		self.dimensions.xy = data[DIMENSIONS]
		self.__lod_size = data[LOD_SIZE]
		self.points = OrderedDict(data[POINTS])
		self.instances = data[INSTANCES]
		
		self.__points_keys = list(self.points.keys())
		self.__points_values = list(self.points.values())
		self.__normals = data[NORMALS]
		self.__chunks = get_chunks()
		self.__parts = get_parts()
		self.__num_chunks = len(self.__chunks)
		self.__num_parts = len(self.__parts)
		self.__update_progress(1, 1, 3)
		
		self.state = logic.KX_STATE3
		
	def edit(self):
		
		def copy_custom_normals(l):
			for ob_name in l:
				ob_normals = self.__normals[ob_name]
				ob = self.scene.objectsInactive[ob_name]
				mesh = ob.meshes[0]
				
				for mat_id in range(mesh.numMaterials):
					for vert_id in range(mesh.getVertexArrayLength(mat_id)):
						vert = mesh.getVertex(mat_id, vert_id)
						id = str([round(f) for f in vert.XYZ.xy])
						if id in ob_normals:
							vert.normal = ob_normals[id]
							
		if self.__index == self.__num_chunks:
			self.__index = 0
			self.state = logic.KX_STATE4
		else:
			copy_custom_normals(self.__chunks[self.__index])
			self.__index += 1
			self.__update_progress(self.__index / self.__num_chunks, 2, 3)

	def add(self):
		
		def add_section(l):
			for ob_name in l:
				inst = self.scene.addObject(ob_name)
				inst.setParent(self, False, False)
				inst.worldTransform = self.worldTransform * inst.worldTransform
				self.sections.append(inst)
				self.num_lib_news[ob_name] = {}
				
		if self.__index == self.__num_parts:
			self.__index = 0
			self.state = logic.KX_STATE5
		else:
			add_section(self.__parts[self.__index])
			self.__index += 1
			self.__update_progress(self.__index / self.__num_parts, 3, 3)
			
	def update(self):
		
		def get_group_parents(inst):
			if inst.groupMembers is None:
				return None
			l = []
			for ob in inst.groupMembers:
				if ob.parent is None:
					l.append(ob)
			return l
			
		def get_id(o, suffix=".", num_digits=3):
			s = suffix
			d = str(o)
			n = len(d)
			if n < num_digits:
				for i in range(num_digits - n):
					s += "0"
			s += d
			return s
			
		physical_sections = [sect.name for sect in self.sections if sect.currentLodLevel == 1]
		for sect in list(self.physical_sections):
			if sect not in physical_sections:
				self.physical_sections.remove(sect)
				self.scene.objects[sect + PHYSICS_SUFFIX].endObject()
				
		for sect in physical_sections:
			if sect not in self.physical_sections:
				self.physical_sections.append(sect)
				inst = self.scene.addObject(sect + PHYSICS_SUFFIX)
				if sect not in self.instances:
					continue
				for n, nl in self.instances[sect].items():
					if n + PHYSICS_SUFFIX not in self.scene.objectsInactive:
						continue
					for l in nl:
						o = self.scene.addObject(n + PHYSICS_SUFFIX)
						m = Matrix()
						m[:] = l[0]
						o.setParent(inst, False, False)
						o.worldTransform = self.worldTransform * m
						
		visual_sections = [sect.name for sect in self.sections if sect.name in self.instances and 0 < sect.currentLodLevel <= self.__lod_size]
		for sect in list(self.visual_sections):
			if sect not in visual_sections:
				self.visual_sections.remove(sect)
				for inst in self.scene.objects[sect].children:
					lib_new_name = None
					if LIB_NEW_ID_PROP_NAME in inst:
						sect_id = sect.split(SECT_SUFFIX)[1]
						lib_new_id = inst[LIB_NEW_ID_PROP_NAME]
						lib_new_name = SECT_SUFFIX + sect_id + lib_new_id
					inst.endObject()
					if lib_new_name is not None:
						logic.LibFree(lib_new_name)
				self.num_lib_news[sect].clear()
				
		for sect in visual_sections:
			if sect not in self.visual_sections:
				self.visual_sections.append(sect)
				for n, nl in self.instances[sect].items():
					for l in nl:
						inst = self.scene.addObject(n)
						inst.setParent(self.scene.objects[sect], True, False)
						m = Matrix()
						m[:] = l[0]
						gpl = get_group_parents(inst)
						if gpl is not None:
							for gp in gpl:
								gp.worldTransform = self.worldTransform * m
						else:
							inst.worldTransform = self.worldTransform * m
						for k, v in l[1].items():
							inst[k] = v
						if LIB_NEW_ID_PROP_NAME in inst:
							lib_new_id = inst[LIB_NEW_ID_PROP_NAME]
							if not lib_new_id:
								d = self.num_lib_news[sect]
								if n not in d:
									d[n] = 0
								inst[LIB_NEW_ID_PROP_NAME] = lib_new_id = n + get_id(d[n])
								d[n] += 1
							sect_id = sect.split(SECT_SUFFIX)[1]
							lib_new_name = SECT_SUFFIX + sect_id + lib_new_id
							new_mesh = logic.LibNew(lib_new_name, "Mesh", [inst.meshes[0].name])[0]
							inst.replaceMesh(new_mesh, True, True)
							
	def add_instance(self, ob, transform, properties={}):
		
		def get_floor_factor(f, n):
			if n == 0:
				return 0
			return f // n * n
			
		def get_grid_point(v, size, axis_range="XYZ"):
			l = list(v)
			axis = "XYZ"[:len(l)]
			for i, a in enumerate(axis):
				if a in axis_range:
					l[i] = get_floor_factor(l[i], size[i]) + size[i] // 2
			return l
			
		l = get_grid_point(transform.translation.xy, self.size)
		id = self.__points_keys[self.__points_values.index(l)]
		sect_name = self[LOD_SECTIONS_PROP_NAME] + SECT_SUFFIX + id
		if sect_name not in self.instances:
			self.instances[sect_name] = {}
		d = self.instances[sect_name]
		inst_name = ob.name
		if inst_name not in d:
			d[inst_name] = []
		d[inst_name].append([[list(v) for v in transform.row], properties])
		
def init(cont):
	LODSections(cont.owner)

def load(cont):
	cont.owner.load()
	
def edit(cont):
	cont.owner.edit()
	
def add(cont):
	cont.owner.add()
	
def update(cont):
	cont.owner.update()
	