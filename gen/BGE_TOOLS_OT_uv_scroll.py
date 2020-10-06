from bge import logic
from mathutils import Vector, Matrix

ERR_MSG_SEQUENCE_EMPTY = "UV Scroll Sequence is empty"
ERR_MSG_SEQUENCE_INVALID = "UV Scroll Sequence is not valid at: "
ERR_MSG_ROW_OUT_OF_RANGE = "UV Scroll Set Sequence row is out of range: "

class UVScroll:
	
	def __init__(self, cont):
		
		# expose a reference to the owner
		# get the mesh; create a new mesh with an indexed name if not in an active layer
		# store material id; if the identifier is not found, all materials on the mesh will be affected
		# expose sprite count, size
		# expose sequence as an array of valid id's
		# expose loop and pingpong
		# store reference to the always sensor
		# initialize variables
		# if the sequence is not empty scroll to the first id
		
		ERR_MSG_SEQUENCE_ILLEGAL_VALUE = "UV Scroll Sequence contains illegal value:\t"
		ERR_MSG_SEQUENCE_OUT_OF_RANGE = "UV Scroll Sequence is out of range:\t"
		
		PROP_NAME_SPRITES_X = "SPRITES_X"
		PROP_NAME_SPRITES_Y = "SPRITES_Y"
		PROP_NAME_SEQUENCE = "SEQUENCE"
		PROP_NAME_LOOP = "LOOP"
		PROP_NAME_PINGPONG = "PINGPONG"
		PROP_NAME_LINKED = "LINKED"
		
		MAT_IDENTIFIER = "_UVScroll_"
		LIBS_INDEX_LENGTH = 3
		
		def get_sprite_data(self):
			sprite_count = [self.own[PROP_NAME_SPRITES_X], self.own[PROP_NAME_SPRITES_Y]]
			sprite_size = Vector([1 / sprite_count[i] for i in range(2)]).to_3d()
			sprite_coords = []
			for y in range(sprite_count[1]):
				for x in range(sprite_count[0]):
					sprite_coords.append(Vector([x * sprite_size[0], y * sprite_size[1]]).to_3d())
			return sprite_count, sprite_size, sprite_coords
			
		def get_properties(self):
			sequence = self.get_sequence(self.own[PROP_NAME_SEQUENCE])
			loop = self.own[PROP_NAME_LOOP]
			pingpong = self.own[PROP_NAME_PINGPONG]
			return sequence, loop, pingpong
		
		def get_id(i, prefix=".", length=LIBS_INDEX_LENGTH):
			dgts = str(i)
			max_length = len(dgts)
			num_zeros = max(length, max_length) - max_length
			return prefix + num_zeros * "0" + dgts
			
		def get_mesh(obj):
			mesh = obj.meshes[0]
			if obj.name not in obj.scene.objectsInactive and obj[PROP_NAME_LINKED]:
				return mesh
			if not hasattr(logic, "libnews"):
				logic.libnews = {}
			mesh_name = mesh.name
			if mesh_name not in logic.libnews:
				logic.libnews[mesh_name] = 0
			id = get_id(logic.libnews[mesh_name])
			new_mesh = logic.LibNew((mesh_name + id), "Mesh", [mesh_name])[0]
			obj.replaceMesh(new_mesh)
			logic.libnews[mesh_name] += 1
			return new_mesh
			
		def get_mat_id(mesh, identifier=MAT_IDENTIFIER):
			for mat_id in range(mesh.numMaterials):
				if identifier in mesh.getMaterialName(mat_id):
					return mat_id
			return -1
			
		self.own = cont.owner
		self.sprite_count, self.sprite_size, self.sprite_coords = get_sprite_data(self)
		self.sequence, self.loop, self.pingpong = get_properties(self)
		
		mesh = get_mesh(self.own)
		self.__mat_id = get_mat_id(mesh)
		self.__always_sensor = cont.sensors[0]
		self.reset()
		
	def reset(self):
		self.__direction = 1
		self.__end = False
		self.__id = 0
		self.__seq_id_curr = 0
		self.__seq_id_next = 0
		if not self.sequence:
			return
		self.scroll(self.sequence[0])
		
	def restart(self):
		self.reset()
		self.resume()
		
	def pause(self):
		self.__always_sensor.usePosPulseMode = False
		
	def resume(self):
		self.__always_sensor.usePosPulseMode = True
		
	def get_sequence(self, string=None):
		if string is None:
			return list(self.sequence)
			
		if not len(string):
			print(ERR_MSG_SEQUENCE_EMPTY)
			return [0]
		sequence = []
		for s in [s for s in string.replace(" ", "").split(",") if s != ""]:
			try:
				if "-" in s:
					first, last = [int(dgts) for dgts in s.split("-")]
					dir = -1 if first > last else 1
					for i in range(first, last + dir, dir):
						sequence.append(i)
				elif "*" in s:
					id, num = [int(dgts) for dgts in s.split("*")]
					for i in range(num):
						sequence.append(id)
				else:
					sequence.append(int(s))
			except ValueError:
				print(ERR_MSG_SEQUENCE_INVALID + s)
		return sequence
		
	def set_sequence(self, s, row=0):
		l = self.get_sequence(s)
		if row:
			if row >= self.sprite_count[1]:
				print(ERR_MSG_ROW_OUT_OF_RANGE + row)
				return
			o = row * self.sprite_count[0]
			for i in l:
				i += o
		self.sequence = l
		
	def scroll(self, id):
		
		# if the current id didn't change, do nothing
		# calculate offset between current and next id
		# scroll uv coordinates to offset
		# update current id
		
		if id == self.__id:
			return
		current_coords = self.sprite_coords[self.__id]
		next_coords = self.sprite_coords[id]
		offset = Matrix.Translation(next_coords - current_coords)
		self.own.meshes[0].transformUV(self.__mat_id, offset, 0)
		self.__id = id
		
	def scroll_sequence(self, seq_id):
		
		# if for any reason the sequence is empty, do nothing
		# when scrolling to the given id, update the current and next id's
		
		def get_seq_id_next():
			
			# if the next id is the first or the last, adjust loop and pingpong if looping, else end
			# otherwize, if it is out of range, adjust and if the loop ended, end
			
			seq_id_next = self.__seq_id_curr + self.__direction
			len_seq = len(self.sequence)
			if seq_id_next in [0, len_seq - 1]:
				if self.loop:
					if self.loop > 0:
						self.loop -= 1
					if self.pingpong:
						self.__direction *= -1
			elif seq_id_next in [-1, len_seq]:
				if self.loop:
					seq_id_next = 0
				else:
					seq_id_next = self.__seq_id_curr
					self.__end = True
			return seq_id_next
			
		if not self.sequence:
			return
		self.__seq_id_curr = seq_id
		self.scroll(self.sequence[seq_id])
		self.__seq_id_next = get_seq_id_next()
		
	def update(self):
		
		# if ended, pause
		# otherwise, scroll to the next id
		
		if self.__end:
			self.pause()
			return
		self.scroll_sequence(self.__seq_id_next)
		
def update(cont):
	if not cont.sensors[0].positive:
		return
	own = cont.owner
	if "uv_scroll" not in own:
		own["uv_scroll"] = UVScroll(cont)
	own["uv_scroll"].update()
	