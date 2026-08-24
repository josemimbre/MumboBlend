ADDON_DIR  := BlenderAddOn/binjo_addon
ADDON_SRC  := $(shell find $(ADDON_DIR) -type f \( -name '*.py' -o -name '*.toml' \))
ZIP_NAME   := BINjo_Kazooie.zip

.PHONY: zip clean

zip: $(ZIP_NAME)

$(ZIP_NAME): $(ADDON_SRC)
	rm -f $(ZIP_NAME)
	cd BlenderAddOn && zip -r ../$(ZIP_NAME) binjo_addon \
		-x '*__pycache__*' -x '*.pyc'

clean:
	rm -f $(ZIP_NAME)
