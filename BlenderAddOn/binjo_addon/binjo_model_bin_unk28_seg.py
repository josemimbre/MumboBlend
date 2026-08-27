
from . import binjo_utils

# BKModelUnk28List (game struct name, decomp doesn't have a better one) - a
# per-frame vertex-pinning table. For each entry, a fixed anchor coordinate
# (in the same bind-pose space as the raw Vertex segment's positions) gets
# transformed by ONE SPECIFIC bone's current matrix, and the result is
# stamped directly into the position of every vertex listed in that entry -
# overriding whatever bone(s) those vertices would otherwise be skinned to.
#
# Confirmed against the decomp (func_802E6BD0, code_5FB00.c): this runs
# every rendered frame, after that frame's bone matrices are computed and
# before the GeoLayout tree is walked/drawn - so the pinned vertices are
# what actually gets uploaded to the GPU that frame. Its purpose is to let
# vertices that are drawn OUTSIDE any GeoLayout BONE wrapper (so they'd
# otherwise sit frozen at their raw bind-pose position forever, since
# nothing would ever move them) track a specific bone's motion instead -
# used by the real game to weld/pin seams between rigid parts. Gated by
# the Header's `unk_2` field (0 means absent) - confirmed the same field as
# the game struct's `unk28` by cross-referencing struct offsets.
#
# `anim_index` is a bone ARRAY INDEX (same indexing scheme as
# ModelBIN_BoneElem.parent_ID and the GeoLayout BONE command - not an
# internal_ID lookup).
class ModelBIN_Unk28Seg:
    LIST_HEADER_SIZE = 0x04

    def __init__(self):
        self.valid = False

    def populate_from_data(self, file_data, file_offset):
        if file_offset == 0:
            print("No Unk28 (vertex-pinning) Segment")
            self.valid = False
            return

        self.file_offset = file_offset
        count = binjo_utils.read_bytes(file_data, file_offset, 2, type="signed")

        self.entry_list = []
        ptr = file_offset + ModelBIN_Unk28Seg.LIST_HEADER_SIZE
        for _ in range(0, count):
            entry = ModelBIN_Unk28Entry.build_from_binary_data(file_data, ptr)
            self.entry_list.append(entry)
            ptr += entry.SIZE()

        print(f"parsed {len(self.entry_list)} vertex-pinning (unk28) entries.")
        self.valid = True
        return


class ModelBIN_Unk28Entry:
    HEADER_SIZE = 0x08

    def __init__(self):
        self.x = 0
        self.y = 0
        self.z = 0
        self.anim_index = 0
        self.vtx_list = []

    def SIZE(self):
        return ModelBIN_Unk28Entry.HEADER_SIZE + (2 * len(self.vtx_list))

    def build_from_binary_data(file_data, file_offset):
        entry = ModelBIN_Unk28Entry()
        entry.x           = binjo_utils.read_bytes(file_data, file_offset + 0x00, 2, type="signed")
        entry.y           = binjo_utils.read_bytes(file_data, file_offset + 0x02, 2, type="signed")
        entry.z           = binjo_utils.read_bytes(file_data, file_offset + 0x04, 2, type="signed")
        entry.anim_index  = binjo_utils.read_bytes(file_data, file_offset + 0x06, 1, type="signed")
        vtx_cnt           = binjo_utils.read_bytes(file_data, file_offset + 0x07, 1)
        entry.vtx_list = [
            binjo_utils.read_bytes(file_data, file_offset + ModelBIN_Unk28Entry.HEADER_SIZE + (2 * idx), 2)
            for idx in range(0, vtx_cnt)
        ]
        return entry
