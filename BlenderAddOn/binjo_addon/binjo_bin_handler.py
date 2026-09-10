
import os
import re

from . import binjo_utils
from . import binjo_model_LU
from . binjo_model_bin import ModelBIN


# Material names that come out of the parser are only unique within one model
# file (they are texture offsets into that file), so the importer prefixes them
# with the model they came from. For anything pulled out of the ROM that is the
# decomp asset uid, unique across maps and objects alike; maps are keyed by a
# local index that sits 0x146A below theirs (see binjo_model_LU).
MAP_ASSET_UID_BASE = 0x146A

def _scope_from_lookup_key(key, uid_base=0):
    match = re.match(r'\((0x[0-9A-Fa-f]+)\)', key)
    if (match is None):
        return re.sub(r'[^0-9a-z]+', '-', key.lower()).strip('-')[:24] or "model"
    return f"{uid_base + int(match.group(1), 16):04X}"




class BINjo_ModelBIN_Handler:

    def __init__(self, rom_filename=None):
        self.ROM_name = rom_filename
        self.ROM_data = None
        self.model_object = None
        # which model model_object was built from, see _scope_from_lookup_key
        self.model_scope = None

        if (rom_filename is None):
            return
        with open(rom_filename, mode="rb") as rom_file:
            self.ROM_data = rom_file.read()


    # change to a different ROM
    def change_source_ROM(self, rom_filename):
        self.ROM_name = rom_filename
        self.ROM_data = None
        if (rom_filename is None):
            return
        with open(rom_filename, mode="rb") as rom_file:
            self.ROM_data = rom_file.read()


    # load a model file from a ROM via model-filename
    def load_model_file_from_ROM(self, model_filename):
        model_file_data = binjo_utils.extract_model(self.ROM_data, model_filename)
        if (model_file_data is None or len(model_file_data) == 0):
            print(f"Model File \"{model_filename}\" could not be loaded !")
            print("Either Binjo straight up failed on it, or its empty !")
            print("Cancelling Model instantiation...")
            return

        self.model_scope = _scope_from_lookup_key(model_filename, MAP_ASSET_UID_BASE)
        self.model_object = ModelBIN()
        self.model_object.populate_from_data(model_file_data)
        self.model_object.arrange_mesh_data()


    # load a non-map model (character/prop/enemy, ...) from a ROM via model-filename
    def load_object_file_from_ROM(self, model_filename):
        model_file_data = binjo_utils.extract_model(self.ROM_data, model_filename, lookup=binjo_model_LU.object_model_lookup)
        if (model_file_data is None or len(model_file_data) == 0):
            print(f"Object Model File \"{model_filename}\" could not be loaded !")
            print("Either Binjo straight up failed on it, or its empty !")
            print("Cancelling Model instantiation...")
            return

        self.model_scope = _scope_from_lookup_key(model_filename)
        self.model_object = ModelBIN()
        self.model_object.populate_from_data(model_file_data)
        self.model_object.arrange_mesh_data()


    # load a model file from a BIN
    def load_model_file_from_BIN(self, bin_filename):
        
        with open(bin_filename, mode="rb") as bin_file:
            model_file_data = bin_file.read()
            
        if (model_file_data is None or len(model_file_data) == 0):
            print(f"Model File \"{bin_filename}\" could not be loaded !")
            print("Either Binjo straight up failed on it, or its empty !")
            print("Cancelling Model instantiation...")
            return

        # lower-cased so a file name can never contain the INVIS / NOCOLL markers
        # the importer searches material names for
        stem = os.path.splitext(os.path.basename(bin_filename))[0]
        self.model_scope = re.sub(r'[^0-9a-z]+', '-', stem.lower()).strip('-')[:24] or "bin"
        self.model_object = ModelBIN()
        self.model_object.populate_from_data(model_file_data)
        self.model_object.arrange_mesh_data()

    def dump_image_files_to(self, path):
        for IMG in self.model_object.TexSeg.tex_elements:
            IMG.export_as_file(path=path)
    



if __name__ == '__main__':
    
    ROM_list = [
        "banjo.us.v10.z64",
        "banjo.us.v10.z64.ext.z64",
    ]
    
    ROM_filename = ROM_list[1]
    print(f"Reading in ROM \"{ROM_filename}\"...")
    with open(ROM_filename, mode="rb") as rom_file:
        ROM = rom_file.read()

    filename = "TTC - Treasure Trove Cove"
    model_file = binjo_utils.extract_model(ROM, filename)

    model_object = ModelBIN(model_file)
