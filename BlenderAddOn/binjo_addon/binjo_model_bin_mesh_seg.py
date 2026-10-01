from . import binjo_utils

# BKMeshList (decomp: include/core2/model.h, header field mesh_list_offset,
# the one the Header calls FX_offset) - named groups of vertices that the game
# animates by id after loading a map. func_8034C6DC (core2/code_C5440.c) picks
# the effect from the id's range and hands it id minus the range's base:
#
#    101-199  scroll the texture in V             (core2/code_C61C0.c)
#    200-299  flicker the vertex colour 0.8-1.0   (core2/code_C5F00.c)
#    300-399  water: texture wobble + bobbing     (core2/code_C76D0.c)
#    400-499, 600-699, 500-599, 700-799, 800-899, 900-999, 1000-1099: others
#
# Layout: s16 count, then `count` meshes of
#    s16 uid; s16 vtx_count; s16 vertices[vtx_count]
# packed back to back, where vertices index the model's vertex segment.
#
# Only read: nothing here is written back on export to BIN yet.
class ModelBIN_MeshSeg:
    LIST_HEADER_SIZE = 0x02

    def __init__(self):
        self.valid = False
        self.mesh_list = []
        # vertex index -> uid of the first mesh that lists it
        self.uid_by_vertex = {}

    def populate_from_data(self, file_data, file_offset):
        self.mesh_list = []
        self.uid_by_vertex = {}

        if file_offset == 0:
            print("No Mesh-List (FX) Segment")
            self.valid = False
            return

        self.file_offset = file_offset
        count = binjo_utils.read_bytes(file_data, file_offset, 2, type="signed")

        ptr = file_offset + ModelBIN_MeshSeg.LIST_HEADER_SIZE
        shared = 0
        for _ in range(0, count):
            uid       = binjo_utils.read_bytes(file_data, ptr + 0x00, 2, type="signed")
            vtx_count = binjo_utils.read_bytes(file_data, ptr + 0x02, 2, type="signed")
            vertices = [
                binjo_utils.read_bytes(file_data, ptr + 0x04 + (2 * idx), 2)
                for idx in range(0, vtx_count)
            ]
            self.mesh_list.append((uid, vertices))
            for vtx in vertices:
                if (vtx in self.uid_by_vertex):
                    shared += 1
                else:
                    self.uid_by_vertex[vtx] = uid
            ptr += 0x04 + (2 * vtx_count)

        print(f"parsed {len(self.mesh_list)} meshes ({len(self.uid_by_vertex)} vertices) from the Mesh-List segment.")
        if (shared):
            print(f"  {shared} vertices appear in more than one mesh; the first mesh wins.")
        self.valid = True
        return
