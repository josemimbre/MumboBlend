
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

    # Import policy for SELECTOR, set from the addon's UI before parsing (see
    # the SELECTOR handler for what it decides). A class attribute rather than
    # a parameter because it would otherwise have to be threaded through
    # ModelBIN and the BIN handler, neither of which knows anything about
    # Blender or user preferences.
    show_selector_defaults = True

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
    # Branching-but-not-bone-related commands (billboard, sort, branch) are
    # descended into unconditionally, since this is a static, ROM-wide
    # analysis rather than a runtime trace - visiting every branch is what we
    # want so no DL index is missed. The two exceptions are LOD (0x08) and
    # SELECTOR (0x0C), whose branches are mutually exclusive at runtime:
    # walking all of them stacks alternate versions of the same geometry in
    # the same place, so the losing branches go into excluded_dl_indices.
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
        # DL index -> tag of the SELECTOR variant it belongs to. Unlike the LOD
        # alternates above these are not redundant copies but genuinely
        # different content, so they're kept and split off into their own
        # objects instead of being thrown away.
        self.variant_dl_indices = {}
        self._walk(file_data, file_offset, [])
        print(f"parsed GeoLayout: {len(self.dl_bone_assignments)} bone-tagged DisplayList sections.")
        self.valid = True
        return

    def _walk(self, file_data, offset, bone_stack, is_excluded=False, variant_key=None):
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
        # encode). LOD has no explicit "choose 1 of N" field - it's just
        # sibling commands - so the winner is picked by threshold instead
        # (smallest min_C = nearest/highest detail), see the handler below.
        #
        # lod_run_offsets holds the sibling run whose winner is currently
        # cached in lod_winner_offset. A chain can hold SEVERAL independent
        # LOD runs, so the scan re-runs whenever a LOD command outside the
        # cached run shows up; caching one winner per _walk instead would
        # exclude every sibling of the second and later runs.
        lod_run_offsets = set()
        lod_winner_offset = None
        while True:
            cmd_0 = binjo_utils.read_bytes(file_data, offset + 0x00, 4)
            size_4 = binjo_utils.read_bytes(file_data, offset + 0x04, 4)
            active_bone = bone_stack[-1] if (bone_stack and bone_stack[-1] != -1) else None

            if (cmd_0 == Dicts.GEO_CMD_NAMES["BONE"]):
                sub_offset = binjo_utils.read_bytes(file_data, offset + 0x08, 1)
                bone_idx   = binjo_utils.read_bytes(file_data, offset + 0x09, 1, type="signed")
                if (sub_offset != 0):
                    self._walk(file_data, offset + sub_offset, bone_stack + [bone_idx], is_excluded, variant_key)

            elif (cmd_0 == Dicts.GEO_CMD_NAMES["LOAD_DL"]):
                dl_idx = binjo_utils.read_bytes(file_data, offset + 0x08, 2)
                if (is_excluded):
                    self.excluded_dl_indices.add(dl_idx)
                else:
                    self.dl_bone_assignments[dl_idx] = active_bone
                    if (variant_key is not None):
                        self.variant_dl_indices[dl_idx] = variant_key

            elif (cmd_0 == 0x07):
                dl_idx = binjo_utils.read_bytes(file_data, offset + 0x0A, 2)
                if (is_excluded):
                    self.excluded_dl_indices.add(dl_idx)
                else:
                    self.dl_bone_assignments[dl_idx] = active_bone
                    if (variant_key is not None):
                        self.variant_dl_indices[dl_idx] = variant_key

            elif (cmd_0 == Dicts.GEO_CMD_NAMES["SKINNING"]):
                dl_idx = binjo_utils.read_bytes(file_data, offset + 0x08, 2)
                if (is_excluded):
                    self.excluded_dl_indices.add(dl_idx)
                else:
                    self.dl_bone_assignments[dl_idx] = active_bone
                    if (variant_key is not None):
                        self.variant_dl_indices[dl_idx] = variant_key
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
                        if (variant_key is not None):
                            self.variant_dl_indices[extra_dl_idx] = variant_key
                    idx += 1

            elif (cmd_0 == 0x00):
                sub_offset = binjo_utils.read_bytes(file_data, offset + 0x08, 2, type="signed")
                if (sub_offset != 0):
                    self._walk(file_data, offset + sub_offset, bone_stack, is_excluded, variant_key)

            elif (cmd_0 == Dicts.GEO_CMD_NAMES["SORT"]):
                sub_offset_A = binjo_utils.read_bytes(file_data, offset + 0x22, 2, type="signed")
                sub_offset_B = binjo_utils.read_bytes(file_data, offset + 0x24, 4, type="signed")
                if (sub_offset_A != 0):
                    self._walk(file_data, offset + sub_offset_A, bone_stack, is_excluded, variant_key)
                if (sub_offset_B != 0):
                    self._walk(file_data, offset + sub_offset_B, bone_stack, is_excluded, variant_key)

            elif (cmd_0 == Dicts.GEO_CMD_NAMES["BRANCH"]):
                sub_offset = binjo_utils.read_bytes(file_data, offset + 0x08, 4, type="signed")
                if (sub_offset != 0):
                    self._walk(file_data, offset + sub_offset, bone_stack, is_excluded, variant_key)

            elif (cmd_0 == Dicts.GEO_CMD_NAMES["LOD"]):
                # confirmed against the decomp (func_80338B50, "Cmd8_LOD",
                # modelRender.c): each sibling only draws when
                # min_C < distance <= max_8 (min_C at +0x0C, max_8 at +0x08,
                # both f32) - real data has these ranges contiguous/
                # non-overlapping across the sibling run, so the sibling
                # with the SMALLEST min_C is always the near/high-detail
                # level, independent of file order (verified: on Banjo Low
                # Poly the first sibling does happen to be the near one,
                # [0, 670], with the second covering [670, 10000] - but
                # that's this file's authoring order, not a format
                # guarantee, so pick by threshold instead of position)
                if (offset not in lod_run_offsets):
                    run_offset = offset
                    lod_run_offsets = set()
                    best_min_c, lod_winner_offset = None, None
                    while True:
                        run_cmd_0 = binjo_utils.read_bytes(file_data, run_offset + 0x00, 4)
                        if (run_cmd_0 != Dicts.GEO_CMD_NAMES["LOD"]):
                            break
                        lod_run_offsets.add(run_offset)
                        run_min_c = binjo_utils.read_float(file_data, run_offset + 0x0C)
                        if (best_min_c is None or run_min_c < best_min_c):
                            best_min_c, lod_winner_offset = run_min_c, run_offset
                        run_size_4 = binjo_utils.read_bytes(file_data, run_offset + 0x04, 4)
                        if (run_size_4 == 0):
                            break
                        run_offset += run_size_4

                sub_offset = binjo_utils.read_bytes(file_data, offset + 0x1C, 4, type="signed")
                if (sub_offset != 0):
                    self._walk(file_data, offset + sub_offset, bone_stack, is_excluded or (offset != lod_winner_offset), variant_key)

            elif (cmd_0 == Dicts.GEO_CMD_NAMES["SELECTOR"]):
                # SELECTOR is a model-SWAP, not a group: confirmed against the
                # decomp (func_80338CD0, "CmdC_SELECTOR", modelRender.c). It
                # reads a runtime state indexed by the selector ID at +0x0A and
                # draws exactly ONE child (state-1), or none (state 0), or a
                # bitmask-selected subset (negative state) - never all of them.
                # Its children are alternate appearances of the same piece: the
                # eye states of a head, Kazooie's bare feet vs her Turbo
                # Trainers, a prop in Bottles' hand. Walking them all stacks
                # every variant in the same place, so only one is taken as the
                # default appearance and the rest are TAGGED, not dropped -
                # they get built into their own hidden objects further down.
                #
                # Which one is the default cannot be read from the BIN. The
                # state array starts zeroed and modelRender_reset() raises only
                # ID 1 (to state 1, i.e. its child 0), so strictly every other
                # selector draws nothing until the character's OWN C code
                # raises it - and that goes both ways: Banjo's raises the ones
                # holding his eyes (func_8029DD6C, code_16C60.c), while
                # Bottles' explicitly zeroes the ones holding his hand-held
                # props (func_802D94B4, ch/mole.c). Per-character code, not
                # data, hence show_selector_defaults only picking which way to
                # lean.
                #
                # A single-child selector is the one unambiguous case: it is a
                # plain on/off switch, since drawing its only child
                # unconditionally would make the command pointless. It stays
                # hidden either way.
                child_cnt = binjo_utils.read_bytes(file_data, offset + 0x08, 2)
                selector_id = binjo_utils.read_bytes(file_data, offset + 0x0A, 2)
                shows_default = (child_cnt > 1) and (
                    ModelBIN_GeoSeg.show_selector_defaults or selector_id == 1
                )
                for idx in range(0, child_cnt):
                    child_offset = binjo_utils.read_bytes(file_data, offset + 0x0C + (idx * 4), 4, type="signed")
                    if (child_offset != 0):
                        if (idx == 0 and shows_default):
                            # a nested selector inside a variant keeps the outer tag
                            child_key = variant_key
                        else:
                            child_key = f"sel{selector_id}_{idx}"
                        self._walk(file_data, offset + child_offset, bone_stack, is_excluded, child_key)

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
