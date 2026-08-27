
from . import binjo_utils
from . binjo_dicts import Dicts


class ModelBIN_GeoCommand:
    def __init__(self):
        pass

class ModelBIN_GeoCommandChain:
    def __init__(self):
        pass

    def build_default(self, min_x, min_y, min_z, max_x, max_y, max_z):
        self.entries = []

        self.entries.append(Dicts.GEO_CMD_NAMES["DRAW_DISTANCE"])
        self.entries.append(0x00000028) # full length of the chain (10 entries à 4B = 40 B = 0x28 B)
        self.entries.append((binjo_utils.get_2s_complement(min_x, 2) << 16) + binjo_utils.get_2s_complement(min_y, 2))
        self.entries.append((binjo_utils.get_2s_complement(min_z, 2) << 16) + binjo_utils.get_2s_complement(max_x, 2))
        self.entries.append((binjo_utils.get_2s_complement(max_y, 2) << 16) + binjo_utils.get_2s_complement(max_z, 2))
        self.entries.append(0x001808D3)

        self.entries.append(Dicts.GEO_CMD_NAMES["LOAD_DL"])
        self.entries.append(0x00000000) # 0x00 == final command of the chain
        self.entries.append(0x00000000) # this contains the offset
        self.entries.append(0x00000000) # just padding ?

    def get_bytes(self):
        output = bytearray()
        for entry in self.entries:
            output += binjo_utils.int_to_bytes(entry, 4)
        return output



class ModelBIN_GeoSeg:

    # python class constructor basically also serves as my member declaration...
    def __init__(self):
        self.valid = False

    # Walks the GeoLayout command tree (see ANIMATION_NOTES.md, untracked, for
    # the reverse-engineering trail) to figure out which DisplayList
    # sub-section (by starting command-list index) is drawn under which
    # bone. Every command has an 8-byte header (cmd_0, size_4); siblings at
    # the same level are a flat chain ended by size_4==0, and branching
    # commands recurse into a sub-chain at a command-relative byte offset.
    #
    # BONE (0x02) is the only command that changes "whose matrix applies
    # here"; its unk9 (s8) is a direct index into the bone list (same
    # indexing as ModelBIN_BoneElem.parent_ID), and its unk8 (u8) sub-chain
    # is everything drawn under that bone. LOAD_DL (0x03) and the still-
    # unnamed 0x07 both point at a DisplayList_Command starting index -
    # those are recorded against whatever bone is currently active.
    # SKINNING (0x05) lists several DL indices; only the first is given the
    # active bone with full confidence (see notes - the rest are an
    # approximation, since the exact sequential-matrix-cursor semantics
    # aren't fully resolved yet).
    #
    # Branching-but-not-bone-related commands (billboard, sort, branch, LOD,
    # selector) are all descended into unconditionally, since this is a
    # static, ROM-wide analysis rather than a runtime trace with a single
    # active branch - visiting every possible branch is what we want so no
    # DL index is missed.
    def populate_from_data(self, file_data, file_offset):
        if file_offset == 0:
            print("No GeoLayout Segment")
            self.valid = False
            return

        self.file_offset = file_offset
        self.dl_bone_assignments = {}
        # DL indices reached only through a non-first sibling LOD command -
        # see the LOD handling below for why these need excluding entirely,
        # not just left bone-untagged (build_complete_tri_list skips them).
        self.excluded_dl_indices = set()
        self._walk(file_data, file_offset, [])
        print(f"parsed GeoLayout: {len(self.dl_bone_assignments)} bone-tagged DisplayList sections.")
        self.valid = True
        return

    def _walk(self, file_data, offset, bone_stack, is_excluded=False):
        # LOD (0x08) commands can appear as consecutive SIBLINGS in the same
        # flat chain, each with its own single sub-chain - confirmed against
        # this specific ROM's data: there is exactly ONE such pair in the
        # entire GeoLayout tree, sitting at the very root (file_offset
        # itself), and BOTH siblings turned out to contain a complete
        # parallel copy of the ENTIRE bone hierarchy (traced via a real
        # symptom: Kazooie's leg bone ending up with 2x the expected vertex
        # count, and Banjo's arm getting holes/overlapping geometry where
        # the two copies' triangles didn't line up exactly - almost
        # certainly near/far detail-level variants of the whole model,
        # picked at runtime by a distance check this static data doesn't
        # encode). Unlike SELECTOR, LOD has no explicit "choose 1 of N"
        # field - it's just sibling commands - so there's no way to
        # generalize this beyond "first LOD sibling in a chain wins, treat
        # later ones as excluded alternates", which held up here because
        # this file has only one such pair, isolated (nothing else shares
        # its parent chain). An earlier, broader attempt at excluding
        # non-first SELECTOR branches too caused a real regression (an
        # unrelated bone absorbing content from a branch it did need) and
        # was reverted; this LOD-only version does not touch SELECTOR at
        # all, since SELECTOR branches are NOT confirmed to be mutually
        # exclusive the way this LOD pair specifically is.
        seen_lod_sibling = False
        while True:
            cmd_0 = binjo_utils.read_bytes(file_data, offset + 0x00, 4)
            size_4 = binjo_utils.read_bytes(file_data, offset + 0x04, 4)
            active_bone = bone_stack[-1] if (bone_stack and bone_stack[-1] != -1) else None

            if (cmd_0 == Dicts.GEO_CMD_NAMES["BONE"]):
                sub_offset = binjo_utils.read_bytes(file_data, offset + 0x08, 1)
                bone_idx   = binjo_utils.read_bytes(file_data, offset + 0x09, 1, type="signed")
                if (sub_offset != 0):
                    self._walk(file_data, offset + sub_offset, bone_stack + [bone_idx], is_excluded)

            elif (cmd_0 == Dicts.GEO_CMD_NAMES["LOAD_DL"]):
                dl_idx = binjo_utils.read_bytes(file_data, offset + 0x08, 2)
                if (is_excluded):
                    self.excluded_dl_indices.add(dl_idx)
                else:
                    self.dl_bone_assignments[dl_idx] = active_bone

            elif (cmd_0 == 0x07):
                dl_idx = binjo_utils.read_bytes(file_data, offset + 0x0A, 2)
                if (is_excluded):
                    self.excluded_dl_indices.add(dl_idx)
                else:
                    self.dl_bone_assignments[dl_idx] = active_bone

            elif (cmd_0 == Dicts.GEO_CMD_NAMES["SKINNING"]):
                dl_idx = binjo_utils.read_bytes(file_data, offset + 0x08, 2)
                if (is_excluded):
                    self.excluded_dl_indices.add(dl_idx)
                else:
                    self.dl_bone_assignments[dl_idx] = active_bone
                idx = 1
                while True:
                    extra_dl_idx = binjo_utils.read_bytes(file_data, offset + 0x08 + (idx * 2), 2)
                    if (extra_dl_idx == 0):
                        break
                    # approximation: assumed to follow the same active bone
                    # as the first entry, see the class-level note above
                    if (is_excluded):
                        self.excluded_dl_indices.add(extra_dl_idx)
                    else:
                        self.dl_bone_assignments[extra_dl_idx] = active_bone
                    idx += 1

            elif (cmd_0 == 0x00):
                sub_offset = binjo_utils.read_bytes(file_data, offset + 0x08, 2, type="signed")
                if (sub_offset != 0):
                    self._walk(file_data, offset + sub_offset, bone_stack, is_excluded)

            elif (cmd_0 == Dicts.GEO_CMD_NAMES["SORT"]):
                sub_offset_A = binjo_utils.read_bytes(file_data, offset + 0x22, 2, type="signed")
                sub_offset_B = binjo_utils.read_bytes(file_data, offset + 0x24, 4, type="signed")
                if (sub_offset_A != 0):
                    self._walk(file_data, offset + sub_offset_A, bone_stack, is_excluded)
                if (sub_offset_B != 0):
                    self._walk(file_data, offset + sub_offset_B, bone_stack, is_excluded)

            elif (cmd_0 == Dicts.GEO_CMD_NAMES["BRANCH"]):
                sub_offset = binjo_utils.read_bytes(file_data, offset + 0x08, 4, type="signed")
                if (sub_offset != 0):
                    self._walk(file_data, offset + sub_offset, bone_stack, is_excluded)

            elif (cmd_0 == Dicts.GEO_CMD_NAMES["LOD"]):
                sub_offset = binjo_utils.read_bytes(file_data, offset + 0x1C, 4, type="signed")
                if (sub_offset != 0):
                    self._walk(file_data, offset + sub_offset, bone_stack, is_excluded or seen_lod_sibling)
                seen_lod_sibling = True

            elif (cmd_0 == Dicts.GEO_CMD_NAMES["SELECTOR"]):
                child_cnt = binjo_utils.read_bytes(file_data, offset + 0x08, 2)
                for idx in range(0, child_cnt):
                    child_offset = binjo_utils.read_bytes(file_data, offset + 0x0C + (idx * 4), 4, type="signed")
                    if (child_offset != 0):
                        self._walk(file_data, offset + child_offset, bone_stack, is_excluded)

            # every other command (unknown/opaque or purely cosmetic, e.g.
            # DRAW_DISTANCE, REFERENCE_POINT) has no sub-chain to recurse into

            if (size_4 == 0):
                return
            offset += size_4

    def build_from_minmax(self, min_x, min_y, min_z, max_x, max_y, max_z):
        self.command_chains = []

        chain = ModelBIN_GeoCommandChain()
        chain.build_default(
            min_x=min_x, min_y=min_y, min_z=min_z,
            max_x=max_x, max_y=max_y, max_z=max_z
        )
        self.command_chains.append(chain)

        self.valid = True

    def get_bytes(self):
        output = bytearray()
        for chain in self.command_chains:
            output += chain.get_bytes()
        return output
