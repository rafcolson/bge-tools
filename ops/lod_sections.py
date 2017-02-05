import bpy, bmesh, math
from mathutils import Vector
from collections import OrderedDict
from . import utils as ut

ERR_MSG_SELECTED_NO_MESH_DATA = "Selected object(s) not containing mesh data"
ERR_MSG_ACTIVE_NO_MESH_DATA = "Active object not containing mesh data"
ERR_MSG_SELECTED_INACTIVE_LAYER = "Selected object(s) not in active layer"
ERR_MSG_ACTIVE_INACTIVE_LAYER = "Active object not in active layer"
ERR_MSG_NO_ACTIVE_OR_SELECTED = "No active or selected object"
ERR_MSG_OBJECT_NOT_FOUND = "Object not found"

PREF = "_"
PART = "_PART"
TEMP = "_TEMP"
BASE = "_BASE"
SECT = "_SECT"
LOD = "_LOD"
PHYS = "_PHYS"
NUMB = ".000"
BOUNDS = "_BOUNDS"

SIZE = "SIZE"
NUMBER = "NUMBER"
DIMENSIONS = "DIMENSIONS"
LOD_SIZE = "LOD_SIZE"
POINTS = "POINTS"
INSTANCES = "INSTANCES"
NORMALS = "NORMALS"

TERRAIN_CHILD_PROP = "_TERRAIN_CHILD"
SECT_PROP = "BGE_TOOLS_LOD_SECTIONS"
PROG_PROP = "BGE_TOOLS_LOD_PROGRESS"

TOOL_NAME = "bge_tools_lod_sections"

PHYS_COLLAPSE_RATIO = 0.25
REMOVE_DOUBLES_THRESHOLD = 0.0001

class LODSections(bpy.types.Operator):
	
	bl_description = "Generates sections with level of detail"
	bl_idname = "bge_tools.lod_sections"
	bl_label = "BGE-Tools: LOD Sections"
	bl_options = {"REGISTER", "UNDO", "PRESET"}
	
	prop_update_or_clear = bpy.props.EnumProperty(
		items=[
			("update", "Update", ""),
			("clear", "Clear", "")
		],
		name="",
		description="Update or clear",
		default="clear"
	)
	prop_number_or_size = bpy.props.EnumProperty(
		items=[
			("generate_by_number", "Generate by number", ""),
			("generate_by_size", "Generate by size", "")
		],
		name="",
		description="Generate by number or size",
		default="generate_by_size"
	)
	prop_number = bpy.props.IntVectorProperty(
		name="",
		description="Number of sections",
		default=(8, 8),
		min=1,
		soft_min=2,
		soft_max=32,
		max=64,
		size=2
	)
	prop_size = bpy.props.FloatVectorProperty(
		name="",
		description="Section size",
		default=(32, 32),
		size=2
	)
	prop_number_mode = bpy.props.EnumProperty(
		items=[
			("use_automatic_numbering", "Use Automatic Numbering", ""),
			("use_even_numbers", "Use Even Numbers", ""),
			("use_odd_numbers", "Use Odd Numbers", "")
		],
		name="",
		description="Mode for numbering",
		default="use_even_numbers"
	)
	prop_use_decimate_dissolve = bpy.props.BoolProperty(
		name="Decimate Dissolve",
		description="Apply planar decimation",
		default=False
	)
	prop_decimate_dissolve_angle_limit = bpy.props.FloatProperty(
		name="",
		description="Decimate Dissolve angle limit",
		default=math.radians(2),
		min=0,
		max=math.pi,
		subtype="ANGLE"
	)
	prop_use_lod = bpy.props.BoolProperty(
		name="Level of detail",
		description="Use level of detail",
		default=True
	)
	prop_lod_number = bpy.props.IntProperty(
		name="",
		description="Number of levels to be added",
		default=4,
		min=1,
		soft_max=5,
		max=8
	)
	prop_lod_decimate_factor = bpy.props.FloatProperty(
		name="",
		description="Additive Decimate Collapse factor",
		default=0.25,
		min=0,
		max=1,
		subtype="FACTOR"
	)
	prop_lod_use_custom_profile = bpy.props.BoolProperty(
		name="Distance",
		description="Use custom lod distance profile",
		default=True
	)
	prop_lod_distance_initial = bpy.props.FloatProperty(
		name="",
		description="Distance of initial lod level",
		default=48,
		subtype="DISTANCE"
	)
	prop_lod_distance_factor = bpy.props.FloatProperty(
		name="",
		description="Factor by which distance is incremented",
		default=0.75,
		min=0.0,
		soft_max=1.0,
		subtype="FACTOR"
	)
	prop_lod_use_physics = bpy.props.BoolProperty(
		name="Physics",
		description="Use physics",
		default=True
	)
	prop_use_approx = bpy.props.BoolProperty(
		name="Approximate",
		description="Use approximation",
		default=True
	)
	prop_approx_num_digits = bpy.props.IntProperty(
		name="",
		description="Maximum number of digits used with coordinates",
		default=2,
		min=0,
		soft_min=2,
		soft_max=5,
		max=15
	)
	prop_use_custom_prefix = bpy.props.BoolProperty(
		name="Prefix",
		description="Use custom prefix",
		default=False
	)
	prop_custom_prefix = bpy.props.StringProperty(
		name="",
		description="Custom prefix",
		default=PREF
	)
	
	err_msg = ""
	log_msg = ""

	def invoke(self, context, event):
		self.scene = context.scene
		self.active_object = self.scene.objects.active
		self.selected_objects = []
		
		objects = []
		for ob in context.selected_editable_objects:
			if isinstance(ob.data, bpy.types.Mesh):
				objects.append(ob)
				
		if objects:
			if self.active_object in objects:
				for ob in objects:
					if ob != self.active_object:
						self.selected_objects.append(ob)
				self.selected_objects.append(self.active_object)
				
		elif context.selected_editable_objects:
			self.err_msg = ERR_MSG_SELECTED_NO_MESH_DATA
			
		elif context.selected_objects:
			self.err_msg = ERR_MSG_SELECTED_INACTIVE_LAYER
			
		elif self.active_object:
			if isinstance(self.active_object.data, bpy.types.Mesh):
				if self.active_object not in context.editable_objects:
					self.err_msg = ERR_MSG_ACTIVE_INACTIVE_LAYER
				else:
					self.selected_objects.append(self.active_object)
			else:
				self.err_msg = ERR_MSG_ACTIVE_NO_MESH_DATA
				
		else:
			self.err_msg = ERR_MSG_NO_ACTIVE_OR_SELECTED
			
		system_dpi = bpy.context.user_preferences.system.dpi
		
		return context.window_manager.invoke_props_dialog(self, width=system_dpi*5)
		
	def draw(self, context):
		layout = self.layout
		box = layout.box
		row = box().row
		
		if self.log_msg:
			row().label(self.log_msg, icon="INFO")
			return
			
		if self.err_msg:
			row().label(self.err_msg, icon="CANCEL")
			return
			
		if SECT_PROP in self.active_object.game.properties:
			row().prop(self, "prop_update_or_clear")
			return
			
		row().prop(self, "prop_number_or_size")
		
		col = row().column
		col_numb = col()
		col_numb.prop(self, "prop_number")
		col_size = col()
		col_size.prop(self, "prop_size")
		col_size.prop(self, "prop_number_mode")
		
		if self.prop_number_or_size == "generate_by_number":
			col_size.active = False
		else:
			col_numb.active = False
			
		row = box().row
		col = row().column
		col().prop(self, "prop_use_decimate_dissolve")
		col_deci = col()
		col_deci.prop(self, "prop_decimate_dissolve_angle_limit")
		if not self.prop_use_decimate_dissolve:
			col_deci.active = False
			
		row = box().row
		col = row().column
		col().prop(self, "prop_use_lod")
		col_lod = col()
		col_lod.prop(self, "prop_lod_number")

		row_lod = row()
		col = row_lod.column
		col().prop(self, "prop_lod_use_physics", toggle=True)
		col().prop(self, "prop_lod_decimate_factor")
		
		row_prof = row()
		col = row_prof.column
		col().prop(self, "prop_lod_use_custom_profile", toggle=True)
		col_dist = col()
		col_dist.prop(self, "prop_lod_distance_initial")
		col_dist.prop(self, "prop_lod_distance_factor")
		if not self.prop_lod_use_custom_profile:
			col_dist.active = False
			
		if not self.prop_use_lod:
			col_lod.active = False
			row_prof.active = False
			row_lod.active = False
			
		row = box().row
		col = row().column
		col().prop(self, "prop_use_approx")
		col_ndig = col()
		col_ndig.prop(self, "prop_approx_num_digits")
		if not self.prop_use_approx:
			col_ndig.active = False
			
		col = row().column
		col().prop(self, "prop_use_custom_prefix", toggle=True)
		col_pref = col()
		col_pref.prop(self, "prop_custom_prefix")
		if not self.prop_use_custom_prefix:
			col_pref.active = False
			
	def check(self, context):
		if self.err_msg:
			return False
		return True
		
	def execute(self, context):
		
		def store_initial_state():
			
			print(self.profiler.timed("Storing initial state"))
			
			bpy.ops.object.mode_set(mode="OBJECT")
			
			self.undo = context.user_preferences.edit.use_global_undo
			context.user_preferences.edit.use_global_undo = False
			
			self.matrix_world = self.active_object.matrix_world.copy()
			self.physics_type = self.active_object.game.physics_type
			self.active_object.game.physics_type = "NO_COLLISION"
			self.cursor_location = self.scene.cursor_location.copy()
			self.scene.cursor_location = Vector()
			
			bpy.ops.object.editmode_toggle()
			self.mesh_select_mode = list(bpy.context.scene.tool_settings.mesh_select_mode)
			bpy.ops.object.editmode_toggle()
			bpy.context.scene.tool_settings.mesh_select_mode = False, False, True
			
		def create_bases():
			selected_and_children = set()
			selected_and_children.update(self.selected_objects)
			selected_and_children.remove(self.active_object)
			selected_and_children.difference_update(self.active_object.children)
			for child in self.active_object.children:
				if TERRAIN_CHILD_PROP in child.game.properties:
					selected_and_children.add(child)
					selected_and_children.union(ut.get_children_recursive(child))

			bpy.ops.object.select_all(action="DESELECT")
			
			self.active_object.matrix_world.identity()
			
			self.objects.append(self.active_object)
			for ob in selected_and_children:
				pl = ut.get_dupli_parents(ob)
				if pl:
					for p in pl:
						n = p.name
						if n not in self.lod_tmps:
							self.lod_tmps[n] = []
						m = ob.matrix_world
						d = {ob.name : ob.value for ob in ob.game.properties}
						self.lod_tmps[n].append([m, d])
				else:
					self.objects.append(ob)

			print(self.profiler.timed("Creating bases"))
			
			for ob in self.objects:
				self.scene.objects.active = ob
				ob.select = True
				bpy.ops.object.duplicate()
				ob.select = False
				
				base = self.scene.objects.active
				base.data.name = base.name = self.prefix + self.active_object.name + BASE + NUMB
				base.game.physics_type = "NO_COLLISION"
				
				for mod in base.modifiers:
					mod_type = mod.type
					
					if not mod.show_render or mod_type == "PARTICLE_SYSTEM":
						bpy.ops.object.modifier_remove(modifier=mod.name)
						continue
						
					print(self.profiler.timed("Applying ", mod.name))
					
					bpy.ops.object.modifier_apply(apply_as="DATA", modifier=mod.name)
					
				for vertex_group in list(base.vertex_groups):
					base.vertex_groups.remove(vertex_group)
					
				bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
				bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
				
				bpy.ops.mesh.separate(type="LOOSE")
				self.bases.extend(context.selected_objects)
				bpy.ops.object.select_all(action="DESELECT")
				
				base.select = False
				
			print(self.profiler.timed("Cleaning up bases"))
			
			for base in self.bases:
				self.scene.objects.active = base
				base.select = True
				
				bpy.ops.object.editmode_toggle()
				bpy.ops.mesh.select_all(action="SELECT")
				bpy.ops.mesh.remove_doubles(threshold=REMOVE_DOUBLES_THRESHOLD)
				bpy.ops.mesh.quads_convert_to_tris()
				bpy.ops.mesh.beautify_fill()
				bpy.ops.mesh.tris_convert_to_quads()
				bpy.ops.mesh.select_all(action="DESELECT")
				bpy.ops.object.editmode_toggle()
				#bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY")

				base.select = False
				
		def dissolve_bases():
			for base in self.bases:
				self.scene.objects.active = base
				base.select = True
				
				if self.prop_use_decimate_dissolve:
					
					print(self.profiler.timed("Decimating base:", base.name))

					bpy.ops.object.editmode_toggle()
					bpy.ops.mesh.select_all(action="SELECT")
					bpy.ops.mesh.dissolve_limited(
						angle_limit=self.prop_decimate_dissolve_angle_limit,
						delimit={"NORMAL", "MATERIAL", "SEAM", "SHARP", "UV"}
					)
					bpy.ops.mesh.select_all(action="SELECT")
					bpy.ops.mesh.quads_convert_to_tris()
					bpy.ops.mesh.beautify_fill()
					bpy.ops.mesh.select_all(action="DESELECT")
					bpy.ops.object.editmode_toggle()

				bpy.ops.mesh.customdata_custom_splitnormals_add()
				base.data.use_auto_smooth = True
				base.select = False
				
		def collect_data():
			
			print(self.profiler.timed("Collecting data"))
			
			for base in self.bases:
				self.materials.update(set(base.data.materials))
				
			self.dimensions.xy = ut.dimensions(*self.bases, include_transform=True).xy
			
			if self.prop_number_or_size == "generate_by_number":
				self.number.x = self.prop_number[0]
				self.number.y = self.prop_number[1]
				self.size.x = self.dimensions.x / self.number.x
				self.size.y = self.dimensions.y / self.number.y
			else:
				self.size.x = self.prop_size[0]
				self.size.y = self.prop_size[1]
				n_x = math.ceil(abs(self.active_object.location.x) + self.dimensions.x / self.size.x)
				n_y = math.ceil(abs(self.active_object.location.y) + self.dimensions.y / self.size.y)
				
				if self.prop_number_mode == "use_automatic_numbering":
					self.number.x = n_x
					self.number.y = n_y
				else:
					i = 0 if self.prop_number_mode == "use_even_numbers" else 1
					self.number.x = n_x + 1 - i if n_x % 2 else n_x + i
					self.number.y = n_y + 1 - i if n_y % 2 else n_y + i
					
			self.ndigits = len(str(int(self.number.x * self.number.y)))
			
			n = 1
			for j in range(int(self.number.y)):
				y = 0.5 * self.size.y * (2 * j + 1 - self.number.y)
				for i in range(int(self.number.x)):
					x = 0.5 * self.size.x * (2 * i + 1 - self.number.x)
					id = ut.get_id(n, "", self.ndigits)
					self.points[id] = [x, y]
					n += 1
					
			self.points_keys = list(self.points.keys())
			self.points_values = list(self.points.values())
			
		def generate_sections():
			
			print(self.profiler.timed("Multisecting bases"))
			
			bpy.ops.mesh.primitive_plane_add()
			self.sections = self.scene.objects.active
			self.sections.game.physics_type = "NO_COLLISION"
			self.sections.draw_type = "WIRE"
			self.sections.hide_render = True
			self.sections.name = self.prefix + self.active_object.name
			self.sections.data.name = self.sections.name
			self.sections.dimensions.xy = self.dimensions.xy
			bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
			self.sections.select = False
			
			tmp_bases = []
			
			for base in self.bases:
				self.scene.objects.active = base
				base.select = True
				
				self.scene.objects.active = tmp_base = ut.copy(self.scene, base)
				tmp_base.data.name = tmp_base.name = self.sections.name + TEMP + NUMB
				tmp_base.show_all_edges = True
				tmp_base.show_wire = True
				base.select = False
				tmp_base.select = True
				
				bpy.ops.object.editmode_toggle()
				bm = bmesh.from_edit_mesh(tmp_base.data)
				
				for i in range(int(self.number.x) + 1):
					try:
						l = bm.verts[:] + bm.edges[:] + bm.faces[:]
						co = ((i - 0.5 * self.number.x) * self.size.x, 0, 0)
						no = (1, 0, 0)
						d = bmesh.ops.bisect_plane(bm, geom=l, plane_co=co, plane_no=no)
						bmesh.ops.split_edges(bm, edges=[e for e in d["geom_cut"] if isinstance(e, bmesh.types.BMEdge)])
					except RuntimeError:
						continue
						
				for i in range(int(self.number.y) + 1):
					try:
						l = bm.verts[:] + bm.edges[:] + bm.faces[:]
						co = (0, (i - 0.5 * self.number.y) * self.size.y, 0)
						no = (0, 1, 0)
						d = bmesh.ops.bisect_plane(bm, geom=l, plane_co=co, plane_no=no)
						bmesh.ops.split_edges(bm, edges=[e for e in d["geom_cut"] if isinstance(e, bmesh.types.BMEdge)])
					except RuntimeError:
						continue
						
				bmesh.update_edit_mesh(tmp_base.data)
				bpy.ops.object.editmode_toggle()
				
				bm.free()
				del bm
				
				tmp_bases.append(tmp_base)
				
				tmp_base.select = False
				
			meshes_to_be_removed = []
			
			for i, ob in enumerate(self.bases):
				if i == 0:
					self.scene.objects.active = self.base = ob
				else:
					meshes_to_be_removed.append(ob.data)
				ob.select = True
				
			if len(self.bases) > 1:
				bpy.ops.object.join()
			self.base.select = False
			
			print(self.profiler.timed("Separating into sections"))
			
			tmps_data = {id : [] for id in self.points_keys}
			
			for tmp_base in tmp_bases:
				self.scene.objects.active = tmp_base
				tmp_base.select = True
				
				bpy.ops.mesh.separate(type="LOOSE")
				tmps = context.selected_objects
				bpy.ops.object.select_all(action="DESELECT")
				
				for tmp in tmps:
					self.scene.objects.active = tmp
					tmp.select = True
					
					bpy.ops.object.editmode_toggle()
					bpy.ops.mesh.select_all(action="SELECT")
					
					if not tmp.data.total_face_sel:
						ut.remove(tmp)
						continue
						
					bpy.ops.mesh.remove_doubles(threshold=REMOVE_DOUBLES_THRESHOLD)
					bpy.ops.mesh.beautify_fill()
					bpy.ops.mesh.select_all(action="DESELECT")
					bpy.ops.object.editmode_toggle()
					bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY")
					
					l = ut.get_grid_point(tmp.location.xy, self.size)
					try:
						id = self.points_keys[self.points_values.index(l)]
						tmps_data[id].append(tmp)
						tmp.select = False
					except ValueError:
						ut.remove(tmp)
						
						
			for id, l in tmps_data.items():
				if not l:
					continue
					
				for i, tmp in enumerate(l):
					if i == 0:
						self.scene.objects.active = tmp
					else:
						meshes_to_be_removed.append(tmp.data)
					tmp.select = True
					
				if len(l) > 1:
					bpy.ops.object.join()
					
				self.scene.cursor_location.xy = self.points[id]
				
				sect = self.scene.objects.active
				sect.data.name = sect.name = self.sections.name + SECT + id
				sect.vertex_groups.new(BOUNDS)
				
				bpy.ops.object.editmode_toggle()
				bpy.ops.mesh.select_all(action="SELECT")
				bpy.ops.mesh.region_to_loop()
				bpy.ops.object.vertex_group_assign()
				bpy.ops.mesh.select_all(action="DESELECT")
				bpy.ops.object.editmode_toggle()
				
				bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
				sect.parent = self.sections
				sect.select = False
				
				self.data[id] = sect
				
			for m in meshes_to_be_removed:
				ut.remove(m)
				
		def generate_lod():
			
			if not self.prop_use_lod:
				return
				
			lod = {id: [sect] for id, sect in self.data.items()}
			
			id = ut.get_id(0, "", self.ndigits)
			lod_id = ut.get_id(self.prop_lod_number, "_", 1)
			me_name = self.sections.name + SECT + id + LOD + lod_id
			sect_lod_me_linked = bpy.data.meshes.new(me_name)
			sect_lod_me_linked.name = self.sections.name + SECT + id + LOD + lod_id
			
			for i in range(1, self.prop_lod_number + 1):
				
				print(self.profiler.timed("Generating LOD ", i, " of ", self.prop_lod_number))
				
				lod_id = ut.get_id(i, "_", 1)
				
				for id, sect in self.data.items():
					sect_lod_name = sect.name + LOD + lod_id
					sect_lod_me_name = sect.data.name + LOD + lod_id
					
					if i == self.prop_lod_number:
						sect_lod = bpy.data.objects.new(sect_lod_name, sect_lod_me_linked)
						sect_lod.show_bounds = True
						sect_lod.draw_type = "BOUNDS"
						sect_lod.game.physics_type = "NO_COLLISION"
						self.scene.objects.link(sect_lod)
					else:
						self.scene.objects.active = sect
						sect.select = True
						bpy.ops.object.duplicate()
						sect.select = False
						
						sect_lod = self.scene.objects.active
						sect_lod.name = sect_lod_name
						sect_lod.data.name = sect_lod_me_name
						
						mod_decimate_collapse = sect_lod.modifiers.new("Decimate Collapse", "DECIMATE")
						mod_decimate_collapse.decimate_type = "COLLAPSE"
						mod_decimate_collapse.ratio = self.prop_lod_decimate_factor / i
						mod_decimate_collapse.vertex_group = BOUNDS
						mod_decimate_collapse.invert_vertex_group = True
						bpy.ops.object.modifier_apply(apply_as="DATA", modifier="Decimate Collapse")
						
					sect_lod.location = sect.location
					sect_lod.select = False
					sect_lod.parent = self.sections
					
					lod[id].append(sect_lod)
					
			print(self.profiler.timed("Configuring LOD"))
			
			if self.prop_lod_use_custom_profile:
				lod_dist_init = self.prop_lod_distance_initial
				lod_dist_fact = self.prop_lod_distance_factor
			else:
				lod_dist_init = max(self.size.x, self.size.y)
				lod_dist_fact = 0.5
			d = ut.get_table_incremented(lod_dist_init, lod_dist_fact, self.prop_lod_number + 1)
			
			for id, l in lod.items():
				sect = self.data[id]
				self.scene.objects.active = sect
				sect.select = True
				for i, sect_lod in enumerate(l):
					bpy.ops.object.lod_add()
					lod_level = sect.lod_levels[i + 1]
					lod_level.distance = d[i] - lod_dist_init
					lod_level.use_material = True
					lod_level.object = sect_lod
				sect.select = False
				
		def collect_particles():
			for i, ob in enumerate(self.objects):
				
				m = ob.matrix_world
				psml = []
				for mod in ob.modifiers:
					if not mod.type == "PARTICLE_SYSTEM":
						continue
						
					if not (mod.show_render):
						continue
						
					settings = mod.particle_system.settings
					
					if not settings.dupli_object:
						continue
						
					mod.show_viewport = False
					mod.show_render = False
					psml.append(mod)
					
				instances = []
				particles = {}
				for psm in psml:
					
					print(self.profiler.timed("Converting ", psm.name))
					
					psm.show_viewport = True
					psm.show_render = True
					
					self.scene.objects.active = ob
					ob.select = True
					bpy.ops.object.duplicates_make_real()
					ob.select = False
					selected_objects = context.selected_objects
					bpy.ops.object.select_all(action="DESELECT")
					
					settings = psm.particle_system.settings
					
					for o in selected_objects:
						if settings.dupli_object.lod_levels:
							n = settings.dupli_object.name
							if n not in self.lod_tmps:
								self.lod_tmps[n] = []
							self.lod_tmps[n].append([m * o.matrix_world, {}])
							ut.remove(o, False)
							continue
							
						instances.append(o)
						
					psm.show_viewport = False
					psm.show_render = False
					
				for psm in psml:
					psm.show_viewport = True
					psm.show_render = True
					
				for o in instances:
					o.select = True
					
					bpy.ops.object.make_single_user(type="SELECTED_OBJECTS", obdata=True)
					m = o.matrix_world
					l = ut.get_grid_point(m.translation.xy, self.size)
					
					try:
						id = self.points_keys[self.points_values.index(l)]
						if id not in particles:
							particles[id] = []
						particles[id].append(o)
						o.matrix_world = m
						self.materials.update(settings.dupli_object.data.materials)
						
					except ValueError:
						ut.remove(o)
						
					o.select = False
							
				for id, objects in particles.items():
					self.particles[id] = p = objects[0]
					p.data.name = p.name = self.sections.name + PART + id
					
					if len(objects) > 1:
						self.scene.objects.active = p
						meshes = []
						
						for ob in objects:
							ob.select = True
							if ob is not p:
								meshes.append(ob.data)
								
						bpy.ops.object.join()
						p.select = False
						for me in meshes:
							ut.remove(me)
							
		def join_particles():
			
			if not self.particles:
				return
				
			for id, sect in self.data.items():
				
				if id not in self.particles:
					continue
					
				l = self.points[id]
				part = self.particles[id]
				part_me = part.data
				
				if self.prop_use_lod:
					
					lod = [ll.object for ll in sect.lod_levels[2:-1]]
					
					for i, sect_lod in enumerate(lod):
						
						self.scene.objects.active = part
						part.select = True
						bpy.ops.object.duplicate()
						part.select = False
						part_lod = self.scene.objects.active
						part_lod_me = part_lod.data
						
						#mod_decimate_unsubdivide = part_lod.modifiers.new("Decimate Unsubdivide", "DECIMATE")
						#mod_decimate_unsubdivide.decimate_type = "UNSUBDIV"
						#mod_decimate_unsubdivide.iterations = i + 1
						#bpy.ops.object.modifier_apply(apply_as="DATA", modifier="Decimate Unsubdivide")
						
						mod_decimate_collapse = part_lod.modifiers.new("Decimate Collapse", "DECIMATE")
						mod_decimate_collapse.decimate_type = "COLLAPSE"
						mod_decimate_collapse.ratio = self.prop_lod_decimate_factor / (i + 1)
						bpy.ops.object.modifier_apply(apply_as="DATA", modifier="Decimate Collapse")
						
						self.scene.objects.active = sect_lod
						sect_lod.select = True
						bpy.ops.object.join()
						self.scene.cursor_location.xy = l
						bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
						sect_lod.select = False
						
						ut.remove(part_lod_me)
						
				self.scene.objects.active = sect
				sect.select = True
				part.select = True
				bpy.ops.object.join()
				self.scene.cursor_location.xy = l
				bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
				sect.select = False
				
				ut.remove(part_me)
				
		def map_lod_objects():
			for n, nl in self.lod_tmps.copy().items():
				for l in nl:
					m, pl = l
					gp = ut.get_grid_point(m.translation.xy, self.size)
					try:
						id = self.points_keys[self.points_values.index(gp)]
						sect_name = self.sections.name + SECT + id
						if sect_name not in self.lod_instances:
							self.lod_instances[sect_name] = {}
						if n not in self.lod_instances[sect_name]:
							self.lod_instances[sect_name][n] = []
						d = self.lod_instances[sect_name]
						d[n].append([[list(v) for v in m.row], pl])
					except ValueError:
						print("warning:", n, "at", list(m.translation), "not within bounds")
						
		def generate_lod_physics():
			for n in self.lod_tmps:
				
				if n not in self.scene.objects:
					continue
					
				if self.scene.objects[n].game.physics_type != "NO_COLLISION":
					continue
					
				if n + PHYS not in self.scene.objects:
					
					print(self.profiler.timed("Generating physics for ", n))
					
					lod_ob = self.scene.objects[n]
					self.scene.objects.active = lod_ob_physics = ut.copy(self.scene, lod_ob, False, PHYS)
					lod_ob_physics.layers = lod_ob.layers
					lod_ob_physics.parent = lod_ob.parent
					lod_ob_physics.hide_render = True
					
					mod_decimate_collapse = lod_ob_physics.modifiers.new("Decimate Collapse", "DECIMATE")
					mod_decimate_collapse.decimate_type = "COLLAPSE"
					mod_decimate_collapse.ratio = PHYS_COLLAPSE_RATIO
					mod_decimate_collapse.vertex_group = BOUNDS
					mod_decimate_collapse.invert_vertex_group = True
					bpy.ops.object.modifier_apply(apply_as="DATA", modifier="Decimate Collapse")
					
					lod_ob_physics.game.physics_type = "STATIC"
					lod_ob_physics.game.use_collision_bounds = True
					lod_ob_physics.game.collision_bounds_type = "TRIANGLE_MESH"
					lod_ob_physics.select = False
					
		def copy_normals():
			
			print(self.profiler.timed("Copying custom normals"))
			
			objects = []
			for sect in self.data.values():
				objects.append(sect)
				if not self.prop_use_lod:
					continue
				for lod_level in sect.lod_levels[2:-1]:
					objects.append(lod_level.object)
					
			for ob in objects:
				self.scene.objects.active = ob
				ob.select = True
				
				ob.data.use_auto_smooth = True
				ob.data.create_normals_split()
				
				mod_copy_cust_norm = ob.modifiers.new(name="Copy Custom Normals", type="DATA_TRANSFER")
				mod_copy_cust_norm.object = self.base
				mod_copy_cust_norm.use_loop_data = True
				mod_copy_cust_norm.data_types_loops = {"CUSTOM_NORMAL"}
				mod_copy_cust_norm.vertex_group = BOUNDS
				
				bpy.ops.object.modifier_apply(apply_as="DATA", modifier="Copy Custom Normals")
				
				ob.select = False
				
			ut.remove(self.base)
			
		def adjust_materials():
			
			for mat in self.materials:
				mat.use_shadows = True
				mat.use_transparent_shadows = True
				mat.use_cast_shadows = True
				mat.use_cast_buffer_shadows = True
				mat.game_settings.physics = True
				
		def generate_lod_materials():
			
			if not self.prop_use_lod:
				return
				
			if self.prop_lod_number == 1:
				return
				
			print(self.profiler.timed("Generating lod materials"))
			
			materials_lod = {}
			for mat in self.materials:
				materials_lod[mat.name] = mat_lod = mat.copy()
				mat_lod.name = self.prefix + mat.name + LOD
				mat_lod.use_shadows = False
				mat_lod.use_transparent_shadows = False
				mat_lod.use_cast_shadows = False
				mat_lod.use_cast_buffer_shadows = False
				mat_lod.game_settings.physics = False
				
			for sect in self.data.values():
				for lod_level in sect.lod_levels[3:-1]:
					sect_lod = lod_level.object
					for j, mat in enumerate(sect_lod.data.materials):
						sect_lod.active_material_index = j
						sect_lod.active_material = materials_lod[mat.name]
						
		def export_data():
			
			print(self.profiler.timed("Exporting data"))
			
			normals = {}
			
			data = {
				SIZE : list(self.size),
				NUMBER : list(self.number),
				DIMENSIONS : list(self.dimensions),
				LOD_SIZE : self.prop_lod_number,
				POINTS : self.points,
				INSTANCES : self.lod_instances,
				NORMALS : normals,
			}
			
			objects = []
			
			for sect in self.data.values():
				objects.append(sect)
				if not self.prop_use_lod:
					continue
				for lod_level in sect.lod_levels[2:-1]:
					objects.append(lod_level.object)
					
			approx_ndigits = self.prop_approx_num_digits if self.prop_use_approx else -1
			for ob in objects:
				self.scene.objects.active = ob
				ob.select = True
				
				bpy.ops.object.editmode_toggle()
				bpy.ops.mesh.select_all(action="DESELECT")
				bpy.ops.object.vertex_group_select()
				bpy.ops.object.editmode_toggle()
				
				normals[ob.name] = ut.get_custom_normals(ob, approx_ndigits, True)
				
				bpy.ops.object.editmode_toggle()
				bpy.ops.mesh.select_all(action="DESELECT")
				bpy.ops.object.editmode_toggle()
				for vertex_group in list(ob.vertex_groups):
					ob.vertex_groups.remove(vertex_group)
					
				ob.select = False
				
			ut.save_txt(data, SECT_PROP, self.active_object.name)
			
		def generate_physics():
			
			if not (self.prop_use_lod and self.prop_lod_use_physics):
				return
				
			print(self.profiler.timed("Generating Physics"))
			
			for sect in self.data.values():
				sect_physics = ut.copy(self.scene, sect, True, PHYS)
				sect_physics.game.physics_type = "STATIC"
				sect_physics.game.use_collision_bounds = True
				sect_physics.game.collision_bounds_type = "TRIANGLE_MESH"
				sect_physics.select = False
				
				sect_physics.parent = self.sections
				
		def finalize():
			
			print(self.profiler.timed("Finalizing sections"))
			
			sections = self.data.values()
			for ob in self.sections.children:
				v = ob.location.xyz
				ob.location.xyz = round(v.x), round(v.y), round(v.z)
				if ob not in sections:
					ob.hide_render = True
					ob.hide = True
					
			self.sections.matrix_world = self.matrix_world
			bpy.ops.transform.translate()
			self.sections.select = False
			layer_twenty = [False for i in range(19)] + [True]
			for ob in self.sections.children:
				ob.layers = layer_twenty
			self.sections.layers = layer_twenty
			
		def generate_game_logic():
			
			print(self.profiler.timed("Generating game logic"))
			
			self.scene.objects.active = self.active_object
			self.active_object.select = True
			
			ut.add_game_property(self.active_object, SECT_PROP, self.sections.name)
			ut.add_game_property(self.active_object, PROG_PROP, 0.0, True)
			ut.add_text(self.bl_idname, True, TOOL_NAME)
			ut.add_logic_python(self.active_object, TOOL_NAME, "init", False, 1)
			ut.add_logic_python(self.active_object, TOOL_NAME, "load", False, 2)
			ut.add_logic_python(self.active_object, TOOL_NAME, "edit", True, 3)
			ut.add_logic_python(self.active_object, TOOL_NAME, "add", True, 4)
			ut.add_logic_python(self.active_object, TOOL_NAME, "update", True, 5)
			
			self.active_object.game.use_all_states = True
			
		def restore_initial_state():
			
			print(self.profiler.timed("Restoring initial state"))
			
			bpy.ops.object.editmode_toggle()
			bpy.context.scene.tool_settings.mesh_select_mode = self.mesh_select_mode
			bpy.ops.object.editmode_toggle()
			
			self.active_object.game.physics_type = self.physics_type
			self.active_object.matrix_world = self.matrix_world
			self.scene.cursor_location = self.cursor_location
			context.user_preferences.edit.use_global_undo = self.undo
			
		def update_log_msg():
			
			self.log_msg = self.profiler.timed("Finished generating ", len(self.data), " (", round(self.size.x, 1), " X ", round(self.size.y, 1), ") sections in")
			
			print(self.log_msg)
			
		if self.err_msg:
			return {"CANCELLED"}
			
		print("\nLOD Sections\n------------\n")
		
		self.profiler = ut.Profiler()
		self.prefix = self.prop_custom_prefix if self.prop_use_custom_prefix else PREF
		
		if SECT_PROP in self.active_object.game.properties:
			
			if self.prop_update_or_clear == "update":
				self.err_msg = "Update: not implemented yet"
				return {"CANCELLED"}
				
			sections_name = self.active_object.game.properties[SECT_PROP].value
			
			try:
				ut.remove_game_properties(self.active_object, [SECT_PROP, PROG_PROP])
				ut.remove_logic(self.active_object, TOOL_NAME)
				ut.remove_text(TOOL_NAME)
				
				sections = self.scene.objects[sections_name]
				
				meshes = set()
				materials = set()
				
				for ob in sections.children:
					meshes.add(ob.data)
					ut.remove(ob, False)
					
				for me in meshes:
					for mat in me.materials:
						
						if not mat.name.startswith(self.prefix):
							continue
							
						materials.add(mat)
					ut.remove(me)
					
				for mat in materials:
					ut.remove(mat)
					
				ut.remove(sections, False)
				
				print(self.profiler.timed("Finished clearing existing lod sections in "))
				
				if self.prop_update_or_clear == "clear":
					return {"FINISHED"}
					
			except KeyError:
				self.err_msg = ERR_MSG_OBJECT_NOT_FOUND + ": " + sections_name
				
				return {"CANCELLED"}
				
		self.undo = None
		self.physics_type = None
		self.mesh_select_mode = None
		self.cursor_location = None
		
		self.ndigits = None
		self.matrix_world = Vector()
		self.size = Vector().to_2d()
		self.number = Vector().to_2d()
		self.dimensions = Vector().to_2d()
		self.points = OrderedDict()
		self.points_values = []
		self.points_keys = []
		self.objects = []
		self.bases = []
		self.transforms = []
		self.materials = set()
		self.lod_instances = {}
		self.particles = {}
		self.lod_tmps = {}
		self.data = {}
		
		store_initial_state()
		create_bases()
		dissolve_bases()
		collect_data()
		generate_sections()
		generate_lod()
		collect_particles()
		join_particles()
		map_lod_objects()
		adjust_materials()
		generate_lod_physics()
		copy_normals()
		generate_lod_materials()
		export_data()
		generate_physics()
		finalize()
		generate_game_logic()
		restore_initial_state()
		update_log_msg()
		
		return {"FINISHED"}
		
def register():
	bpy.utils.register_class(LODSections)
	
def unregister():
	bpy.utils.unregister_class(LODSections)
	
if __name__ == "__main__":
	register()
	