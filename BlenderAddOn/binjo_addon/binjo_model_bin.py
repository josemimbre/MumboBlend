
from . import binjo_utils
from . binjo_model_bin_header import ModelBIN_Header
from . binjo_model_bin_texture_seg import ModelBIN_TexSeg
from . binjo_model_bin_vertex_seg import ModelBIN_VtxSeg
from . binjo_model_bin_bone_seg import ModelBIN_BoneSeg
from . binjo_model_bin_collision_seg import ModelBIN_ColSeg, ModelBIN_TriElem
from . binjo_model_bin_displaylist_seg import ModelBIN_DLSeg, TileDescriptor
from . binjo_model_bin_geolayout_seg import ModelBIN_GeoSeg

from timeit import default_timer as timer

class ModelBIN:
    # Header                done
    # Texture               done
    # Vertex                done
    # Bone                  done
    # Collision             done
    # DisplayList           wip
    # Effects
    # FX_END
    # Animated Textures
    # GeoLayout

    def __init__(self):
        self.Header = ModelBIN_Header()
        self.TexSeg = ModelBIN_TexSeg()
        self.VtxSeg = ModelBIN_VtxSeg()
        self.BoneSeg = ModelBIN_BoneSeg()
        self.ColSeg = ModelBIN_ColSeg()
        self.DLSeg  = ModelBIN_DLSeg()
        # FX
        # FX_END
        # AnimTex
        self.GeoSeg = ModelBIN_GeoSeg()

    def populate_from_data(self, bin_data):
        populate_timer_start = timer()
        populate_timer = timer()

        self.Header = ModelBIN_Header(bin_data)
        populate_timer = binjo_utils.report_time(populate_timer, "Header Segment Populated")

        self.TexSeg.populate_from_data(bin_data, self.Header.tex_offset)
        populate_timer = binjo_utils.report_time(populate_timer, "Tex Segment Populated")

        self.VtxSeg.populate_from_data(bin_data, self.Header.vtx_offset, bin_header_vtx_cnt=self.Header.vtx_cnt)
        populate_timer = binjo_utils.report_time(populate_timer, "VTX Segment Populated")

        self.BoneSeg.populate_from_data(bin_data, self.Header.bone_offset)
        populate_timer = binjo_utils.report_time(populate_timer, "Bone Segment Populated")

        self.ColSeg.populate_from_data(bin_data, self.Header.coll_offset)
        self.ColSeg.link_vertex_objects_for_all_tris(self.VtxSeg.vtx_list)
        populate_timer = binjo_utils.report_time(populate_timer, "Collision Segment Populated")

        self.DLSeg.populate_from_data(bin_data, self.Header.DL_offset)
        populate_timer = binjo_utils.report_time(populate_timer, "DL Segment Populated")

        # FX
        # FX_END
        # AnimTex

        self.GeoSeg.populate_from_data(bin_data, self.Header.geo_offset)
        populate_timer = binjo_utils.report_time(populate_timer, "GeoLayout Segment Populated")

        self.build_complete_tri_list()
        populate_timer = binjo_utils.report_time(populate_timer, "Tri-List completed")

        populate_timer_start = binjo_utils.report_time(populate_timer_start, "ModelBIN fully populated.")
        return

    def export_to_BIN(self, filename="default.bin"):
        output = bytearray()
        current_filesize = 0

        def write_segment(seg, header_offset_attr):
            nonlocal output, current_filesize
            if (seg.valid):
                seg.file_offset = current_filesize
                setattr(self.Header, header_offset_attr, seg.file_offset)
                output += seg.get_bytes()
                current_filesize = len(output)

        # write the incomplete Header (offsets are missing)
        # to determine the offsets during export
        if (self.Header.valid):
            output += self.Header.get_bytes()
            current_filesize = len(output)

        write_segment(self.TexSeg, "tex_offset")

        write_segment(self.VtxSeg, "vtx_offset")
        if (self.VtxSeg.valid):
            self.Header.vtx_cnt = self.VtxSeg.vtx_cnt

        write_segment(self.BoneSeg, "bone_offset")

        write_segment(self.ColSeg, "coll_offset")

        write_segment(self.DLSeg, "DL_offset")
        # self.Header.tri_cnt = self.DLSeg.DL_tri_cnt # might be neccessary at some point

        # FX
        # FX_END
        # AnimTex

        write_segment(self.GeoSeg, "geo_offset")

        # I need to overwrite the incomplete Header
        for (idx, byte) in enumerate(self.Header.get_bytes()):
            output[idx] = byte

        with open(filename, "wb") as output_file:
            output_file.write(output)
    
    # combine the data from the Collision and DL Segments into one comprehensive list
    def build_complete_tri_list(self, TexSeg=None, ColSeg=None, DLSeg=None, GeoSeg=None):
        if (TexSeg is None):
            TexSeg = self.TexSeg
        if (ColSeg is None):
            ColSeg = self.ColSeg
        if (DLSeg is None):
            DLSeg = self.DLSeg
        if (GeoSeg is None):
            GeoSeg = self.GeoSeg

        if (ColSeg.valid):
            # start of by grabbing all the tris from the coll segment
            self.complete_tri_list = ColSeg.unique_tri_list.copy()
        else:
            self.complete_tri_list = []

        # vertex_index -> bone array index (see ModelBIN_GeoSeg.dl_bone_assignments);
        # None means no bone claims this vertex (rigid, unanimated)
        self.vertex_bone_assignments = {}

        if (DLSeg.valid):
            # then walk through the DLs with a TileDescriptor and a simulated VTX-Buffer to scan for visual tris;
            # the descriptor holds meta data for the GPU and handles the VTX-Buffer, which has a capacity of 32 tri-IDs
            descriptor_array = []
            for idx in range(0, 10):
                descriptor_array.append(TileDescriptor())
            active_descriptor = 0
            vertex_buffer = [0] * 0x20
            # GeoLayout's bone-switch points are keyed by DL command-list index and,
            # empirically, come in ascending contiguous runs matching a single linear
            # walk of the DL - so one pass tracking "whichever switch point we most
            # recently passed" is enough, no need to jump around per bone.
            active_bone = None
            for cmd_idx, cmd in enumerate(DLSeg.command_list):
                if (GeoSeg.valid and cmd_idx in GeoSeg.dl_bone_assignments):
                    active_bone = GeoSeg.dl_bone_assignments[cmd_idx]

                if (cmd.command_name == "G_TEXTURE"):
                    active_descriptor = cmd.parameters[1]
                    continue

                if (cmd.command_name == "G_SETTIMG"):
                    # find the tex that corresponds to this address (and only update the descriptor if it was actual data)
                    potential_tex_idx = TexSeg.get_tex_ID_from_datasection_offset(cmd.parameters[3])
                    if (potential_tex_idx != -1):
                        descriptor_array[active_descriptor].tex_idx = potential_tex_idx
                        descriptor_array[active_descriptor].tex_width  = TexSeg.tex_elements[descriptor_array[active_descriptor].tex_idx].width
                        descriptor_array[active_descriptor].tex_height = TexSeg.tex_elements[descriptor_array[active_descriptor].tex_idx].height
                    else:
                        pass
                        # descriptor_array[active_descriptor].tex_idx = None
                        # descriptor_array[active_descriptor].tex_width  = 0
                        # descriptor_array[active_descriptor].tex_height = 0
                    continue
                
                if (cmd.command_name == "G_VTX"):
                    first_vtx_idx = (cmd.parameters[4] // 0x10)
                    vtx_load_cnt = cmd.parameters[1]
                    # write the corresponding vtx into the simulated buffer
                    buffer_offset = cmd.parameters[0]
                    for idx in range(0, vtx_load_cnt):
                        vertex_buffer[buffer_offset + idx] = (first_vtx_idx + idx)
                        self.vertex_bone_assignments[first_vtx_idx + idx] = active_bone
                    continue

                if (cmd.command_name == "G_TRI1"):
                    tmp_tri = ModelBIN_TriElem()
                    tmp_tri.build_from_parameters(
                        vertex_buffer[cmd.parameters[0]],
                        vertex_buffer[cmd.parameters[1]],
                        vertex_buffer[cmd.parameters[2]]
                    )
                    self.add_and_transform_tri(tmp_tri, descriptor_array[active_descriptor])
                    continue

                if (cmd.command_name == "G_TRI2"):
                    tmp_tri = ModelBIN_TriElem()
                    tmp_tri.build_from_parameters(
                        vertex_buffer[cmd.parameters[0]],
                        vertex_buffer[cmd.parameters[1]],
                        vertex_buffer[cmd.parameters[2]]
                    )
                    self.add_and_transform_tri(tmp_tri, descriptor_array[active_descriptor])
                    tmp_tri = ModelBIN_TriElem()
                    tmp_tri.build_from_parameters(
                        vertex_buffer[cmd.parameters[3]],
                        vertex_buffer[cmd.parameters[4]],
                        vertex_buffer[cmd.parameters[5]]
                    )
                    self.add_and_transform_tri(tmp_tri, descriptor_array[active_descriptor])
                    continue

    # this func figures out if the new DL-Segment tri is already part of the tri-list (from ColSeg), and if
    # so, applys all the visual information to this already existing tri instead of using the new one.
    # this is VERY slow unfortunately...
    # this func also needs the entire existing-tri list aswell as the vtx-seg, so its in the collection class...
    def add_and_transform_tri(self, new_tri, tile_descriptor):
        # first, check if the tri already exists in our list
        # matching_tri_index = -1
        # for idx, existing_tri in enumerate(self.complete_tri_list):
        #     if (existing_tri.compare_only_indices(new_tri) == True):
        #         matching_tri_index = idx
        #         new_tri = existing_tri
        #         break
        
        # python trick to find the "next" (or earliest in this case) matching element from a list OR a default
        matching_tri = next((existing_tri for existing_tri in self.complete_tri_list if existing_tri.compare_only_indices(new_tri)), None)

        # if the tri wasnt found, it's new; So the vertex objects wont be linked yet and we have to add it
        if (matching_tri is None):
            matching_tri = new_tri
            matching_tri.link_vertex_objects(self.VtxSeg.vtx_list)
            self.complete_tri_list.append(matching_tri)
        # this is ALWAYS true if the tri was found in the DLs; Textured or not
        matching_tri.visible = True
        # finally, link the tex ID and calculate the Blender-UVs with the help of the descriptor
        matching_tri.tex_idx = tile_descriptor.tex_idx
        matching_tri.vtx_1.calc_transformed_UVs(tile_descriptor)
        matching_tri.vtx_2.calc_transformed_UVs(tile_descriptor)
        matching_tri.vtx_3.calc_transformed_UVs(tile_descriptor)



    # arrange the model data into lists that Blender can convert into a mesh
    def arrange_mesh_data(self):
        self.vertex_coord_list = []
        self.vertex_shade_list = []
        scale_factor = 1.0
        for vtx in self.VtxSeg.vtx_list:
            # NOTE: Im swapping Y and Z in here, and flipping Z afterwards,
            #       because BK uses a different coord system than blender
            self.vertex_coord_list.append((
                + vtx.x * scale_factor,
                - vtx.z * scale_factor, # swapped and flipped
                + vtx.y * scale_factor  # swapped
            ))

        self.face_idx_list = []
        self.edge_idx_list = []
        self.mat_list = []
        for tri in self.complete_tri_list:
            self.face_idx_list.append((tri.index_1, tri.index_2, tri.index_3))
            self.edge_idx_list.append((tri.index_1, tri.index_2))
            self.edge_idx_list.append((tri.index_2, tri.index_3))
            self.edge_idx_list.append((tri.index_3, tri.index_1))

            if (not tri.visible):
                img_alias = "INVIS"
            if (tri.visible and tri.tex_idx is None):
                img_alias = "FLAT"
            if (tri.visible and tri.tex_idx is not None):
                datasection_offset_data = self.TexSeg.tex_elements[tri.tex_idx].datasection_offset_data
                img_alias = f"{binjo_utils.to_decal_hex(datasection_offset_data, 4)}"

            coll_encoding = "NOCOLL"
            if (tri.collision_type is not None):
                coll_encoding = f"{binjo_utils.to_decal_hex(tri.collision_type, 4)}"

            mat = BinjoMaterial(img_alias, coll_encoding)
            
            if mat not in self.mat_list:
                mat.link_image_object(self.TexSeg)
                self.mat_list.append(mat)
            tri.mat_index = self.mat_list.index(mat)
        return

class BinjoMaterial:
    def __init__(self, img_alias, coll_encoding):
        self.img_alias = img_alias
        self.coll_encoding = coll_encoding
        self.name = f"{img_alias}_{coll_encoding}"
    
    def link_image_object(self, TexSeg):
        if (self.img_alias == "INVIS"):
            self.Blender_IMG = None
            return
        if (self.img_alias == "FLAT"):
            self.Blender_IMG = None
            return
        tex_id = TexSeg.get_tex_ID_from_datasection_offset(int(self.img_alias, base=16))
        self.Blender_IMG = TexSeg.tex_elements[tex_id].Blender_IMG

    def __eq__(self, other):
        return (self.name == other.name)
