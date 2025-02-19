import bpy
	
class BGE_TOOLS_OT_Test(bpy.types.Operator):
	bl_idname = "bge_tools.test"
	bl_label = "BGE-Tools: Test"
	bl_space_type = "VIEW_3D"
	bl_region_type = "VIEW_3D"
	bl_options = {"INTERNAL"}
	
	def __init__(self):
		super().__init__()
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self, 400)

	def draw(self, context):
		layout = self.layout

		# Preset menu
		row = layout.row()
		row.menu("BGE_TOOLS_MT_presets", text="Presets")

		# Existing UI elements...
		
	def execute(self, context):
		return {'FINISHED'}
	
	def check(self, context):
		return False

def register():
	bpy.utils.register_class(BGE_TOOLS_OT_Test)
	
def unregister():
	bpy.utils.unregister_class(BGE_TOOLS_OT_Test)

if __name__ == "__main__":
	register()
