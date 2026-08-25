
import struct

# Layout reverse-engineered from the banjo-kazooie decomp (include/animation.h,
# src/core2/code_B3A80.c) and verified against 65 real .anim.bin files
# extracted from baserom.us.v10.z64: every one parses with monotonically
# increasing, in-range keyframe times and consumes the file exactly.
#
# AnimationFile header (8 bytes): start_frame:s16, end_frame:s16, elem_cnt:s16, pad:2 bytes
# AnimationElement (per bone+component curve): a packed u16 (bone_id:12 bits,
#   component:4 bits), then data_cnt:s16, then data_cnt keyframes.
# AnimationKeyframe (4 bytes): a packed u16 (flags:2 bits, frame:14 bits), then value:s16
#   (fixed-point, divide by 64 to get the real float value).
#
# component is 0-8, flattened over a 3x3 buffer: 0-2 rotation XYZ, 3-5 scale
# XYZ, 6-8 translation XYZ (see ANIMATION_NOTES.md, untracked, for how this
# was derived from animationFile_getBoneTransformList's indexing).

ROTATION_X, ROTATION_Y, ROTATION_Z = 0, 1, 2
SCALE_X, SCALE_Y, SCALE_Z = 3, 4, 5
TRANSLATION_X, TRANSLATION_Y, TRANSLATION_Z = 6, 7, 8


class AnimationKeyframe:
    def __init__(self, frame, value, flags):
        self.frame = frame
        self.value = value
        self.flags = flags

    def build_from_binary_data(file_data, file_offset):
        packed, raw_value = struct.unpack_from(">Hh", file_data, file_offset)
        return AnimationKeyframe(
            frame=(packed & 0x3FFF),
            value=(raw_value / 64.0),
            flags=((packed >> 14) & 0x3),
        )


class AnimationElement:
    SIZE_WITHOUT_KEYFRAMES = 0x04

    def __init__(self):
        self.bone_id = 0
        self.component = 0
        self.keyframes = []

    def build_from_binary_data(file_data, file_offset):
        elem = AnimationElement()
        packed, data_cnt = struct.unpack_from(">Hh", file_data, file_offset)
        elem.bone_id = (packed >> 4) & 0xFFF
        elem.component = packed & 0xF

        elem.keyframes = []
        for idx in range(data_cnt):
            file_offset_kf = file_offset + AnimationElement.SIZE_WITHOUT_KEYFRAMES + (idx * 0x04)
            elem.keyframes.append(AnimationKeyframe.build_from_binary_data(file_data, file_offset_kf))
        return elem

    def get_size(self):
        return AnimationElement.SIZE_WITHOUT_KEYFRAMES + (len(self.keyframes) * 0x04)


class AnimationFile:
    HEADER_SIZE = 0x08

    def __init__(self):
        self.valid = False

    def populate_from_data(self, file_data):
        self.start_frame, self.end_frame, self.elem_cnt = struct.unpack_from(">hhh", file_data, 0x00)

        self.elements = []
        cursor = AnimationFile.HEADER_SIZE
        for _ in range(self.elem_cnt):
            elem = AnimationElement.build_from_binary_data(file_data, cursor)
            self.elements.append(elem)
            cursor += elem.get_size()

        self.valid = True
        return
