
from . import binjo_utils

# Layout documented by Unalive (see BinjoAnalyzer/Bone_Segment.cs), ported here.

class ModelBIN_BoneSeg:
    HEADER_SIZE = 0x08

    def __init__(self):
        self.valid = False

    def populate_from_data(self, file_data, file_offset):
        if file_offset == 0:
            print("No Bone Segment")
            self.valid = False
            return

        self.file_offset = file_offset
        self.file_offset_data = file_offset + ModelBIN_BoneSeg.HEADER_SIZE
        # parsing properties
        self.scaling_factor = binjo_utils.read_float(file_data, file_offset + 0x00)
        self.bone_cnt       = binjo_utils.read_bytes(file_data, file_offset + 0x04, 2)
        self.padding        = binjo_utils.read_bytes(file_data, file_offset + 0x06, 2)

        self.bone_list = []
        for idx in range(0, self.bone_cnt):
            file_offset_bone = self.file_offset_data + (idx * ModelBIN_BoneElem.SIZE)
            bone = ModelBIN_BoneElem.build_from_binary_data(file_data, file_offset_bone)
            self.bone_list.append(bone)

        print(f"parsed {self.bone_cnt} bones.")
        self.valid = True
        return

    def get_bytes(self):
        output = bytearray()
        output += binjo_utils.float_to_bytes(self.scaling_factor)
        output += binjo_utils.int_to_bytes(self.bone_cnt, 2)
        output += binjo_utils.int_to_bytes(self.padding, 2)
        for bone in self.bone_list:
            output += bone.get_bytes()
        return output




class ModelBIN_BoneElem:
    SIZE = 0x10

    def __init__(self):
        # offset relative to the parent bone
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        self.internal_ID = 0
        self.parent_ID = 0

    def build_from_binary_data(file_data, file_offset):
        bone = ModelBIN_BoneElem()
        bone.x           = binjo_utils.read_float(file_data, file_offset + 0x00)
        bone.y           = binjo_utils.read_float(file_data, file_offset + 0x04)
        bone.z           = binjo_utils.read_float(file_data, file_offset + 0x08)
        bone.internal_ID = binjo_utils.read_bytes(file_data, file_offset + 0x0C, 2)
        bone.parent_ID   = binjo_utils.read_bytes(file_data, file_offset + 0x0E, 2)
        return bone

    def get_bytes(self):
        output = bytearray()
        output += binjo_utils.float_to_bytes(self.x)
        output += binjo_utils.float_to_bytes(self.y)
        output += binjo_utils.float_to_bytes(self.z)
        output += binjo_utils.int_to_bytes(self.internal_ID, 2)
        output += binjo_utils.int_to_bytes(self.parent_ID, 2)
        return output
