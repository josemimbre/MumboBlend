import struct

from . import binjo_utils

# A map's setup file (decomp: gsworld_load in core2/gsworld.c) lists what is
# placed in it: actors, props, the points the player enters through. It is
# the asset map_id + 0x71C (file_openMap in core2/file.c), compressed like a
# model.
#
# Read here only as far as the "cubes" section, which holds the placements:
#    0x01, then two s32 triples: the first and last cube on each axis
#    then for every cube, in x, y, z order, until a 0x01 separator:
#       0x00 + six s32 (skipped), 0x02 + three s32 (skipped), or
#       0x03 + the cube's contents (code7AF80_initCubeFromFile, core2/code_A5BC0.c):
#          0x0A, u8 count, 0x0B, count NodeProps (20 bytes each)
#          or 0x06, u8 count, 0x07, count of another 20-byte node kind
#          then optionally 0x08, u8 count, 0x09, count Props (12 bytes each)
# The format peeks one byte ahead: a byte that didn't match the indicator
# being tested stays pending for the next test (file_isNextByteExpected).
#
# NodeProp (include/prop.h), big-endian:
#    s16 x, y, z   position, in game units
#    u16           selector/radius:9, category:6, bit0:1
#    u16 actorId
#    u8  markerId, u8 pad
#    u32           yaw:9 (degrees), scale:23
#    u32           other flags

# Pointer table of the ROM's assets: entry N at ASSET_TABLE + N * 8 holds
# the asset's start, and the next entry its end. Derived from the model
# lookup: SM's opaque model, asset 0x14CF, sits at 0x10510.
ASSET_TABLE = 0x10510 - 0x14CF * 8
SETUP_ASSET_BASE = 0x71C

# Exit number (what a warp names) -> the actor id of the NodeProp marking it
# in the setup file; the player spawns at that node, facing its yaw
# (nodeprop_getExitActorId in core2/gccube.c, player_spawnAtMapExit in
# core2/code_7060.c). Exits from 0x80 up are hardcoded instead.
EXIT_ACTOR_IDS = {
    0x01: 0x001, 0x02: 0x002, 0x03: 0x015, 0x04: 0x076, 0x05: 0x077,
    0x06: 0x078, 0x07: 0x079, 0x08: 0x07A, 0x09: 0x07B, 0x0A: 0x07C,
    0x0B: 0x07D, 0x0C: 0x07E, 0x0D: 0x07F, 0x0E: 0x075, 0x0F: 0x074,
    0x10: 0x073, 0x11: 0x072, 0x12: 0x103, 0x13: 0x104, 0x14: 0x105,
    0x15: 0x106, 0x16: 0x107, 0x17: 0x158, 0x18: 0x15A, 0x19: 0x15C,
    0x5B: 0x1CD, 0x5C: 0x1CE, 0x5D: 0x1CF, 0x5E: 0x1D0, 0x5F: 0x1D1,
    0x60: 0x1D2, 0x61: 0x1D3, 0x62: 0x1D4, 0x65: 0x379,
}


class _Reader:
    def __init__(self, data):
        self.data = data
        self.pos = 0
        self.pending = None

    def byte(self):
        value = self.data[self.pos]
        self.pos += 1
        return value

    def expect(self, indicator):
        if (self.pending is None):
            value = self.byte()
            if (value == indicator):
                return True
            self.pending = value
            return False
        if (self.pending == indicator):
            self.pending = None
            return True
        return False

    def words(self, count):
        values = struct.unpack(f">{count}i", self.data[self.pos:self.pos + (4 * count)])
        self.pos += 4 * count
        return values

    def raw(self, count):
        values = self.data[self.pos:self.pos + count]
        self.pos += count
        return values


def extract_setup(rom_data, map_id):
    asset_id = SETUP_ASSET_BASE + map_id
    return binjo_utils.extract_model(
        rom_data, "setup", lookup={"setup": (0, ASSET_TABLE + (asset_id * 8))}
    )


# Every NodeProp in the setup file, as dicts with position, actor_id,
# category and yaw.
def read_node_props(setup_data):
    reader = _Reader(setup_data)
    nodes = []

    while (not reader.expect(0x00)):
        if (reader.expect(0x02)):
            continue
        if (not reader.expect(0x01)):
            # cameras (0x03) and lighting (0x04) follow the cubes; not needed
            break

        reader.expect(0x01)
        first = reader.words(3)
        last = reader.words(3)
        for _ in range((last[0] - first[0] + 1) * (last[1] - first[1] + 1) * (last[2] - first[2] + 1)):
            while (not reader.expect(0x01)):
                if (reader.expect(0x00)):
                    reader.words(6)
                elif (reader.expect(0x02)):
                    reader.words(3)
                elif (reader.expect(0x03)):
                    _read_cube(reader, nodes)
        break

    return nodes


def _read_cube(reader, nodes):
    if (reader.expect(0x0A)):
        count = reader.byte()
        reader.expect(0x0B)
        blob = reader.raw(count * 20)
        for idx in range(count):
            x, y, z, bits, actor_id, _marker, _pad, yaw_scale, _flags = struct.unpack(
                ">hhhHHBBII", blob[idx * 20:(idx + 1) * 20]
            )
            nodes.append({
                "position": (x, y, z),
                "actor_id": actor_id,
                "category": (bits >> 1) & 0x3F,
                "yaw": yaw_scale >> 23,
            })
    elif (reader.expect(0x06)):
        count = reader.byte()
        reader.expect(0x07)
        reader.raw(count * 20)

    if (reader.expect(0x08)):
        count = reader.byte()
        reader.expect(0x09)
        reader.raw(count * 12)


# NodeProp category of placed actors (PROP_1_CATEGORY_6_ACTOR). Other
# categories reuse the same id numbers for unrelated things.
CATEGORY_ACTOR = 6


# exit number -> its NodeProp, for the exits this map has. Like the game
# (cube_findNodePropByActorId, core2/code_A5BC0.c): the first actor node with
# the exit's actor id, cubes in file order.
def find_exits(nodes):
    by_actor = {}
    for node in nodes:
        if (node["category"] == CATEGORY_ACTOR):
            by_actor.setdefault(node["actor_id"], node)
    return {
        exit_id: by_actor[actor_id]
        for exit_id, actor_id in EXIT_ACTOR_IDS.items()
        if actor_id in by_actor
    }
