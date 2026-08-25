# MumboBlend

*(fork of [ThatCowGuy/BinjoKazooie](https://github.com/ThatCowGuy/BinjoKazooie))*

Tools to parse, export and replace data within Banjo-Kazooie (N64) `Model BIN` files — the format the game uses to store level/room geometry, collision, materials and textures.

The project has two independent pieces:

|                                                        | Language      | What it does                                                                                                                                                                                                                      |
| ------------------------------------------------------ | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`BlenderAddOn/binjo_addon`](BlenderAddOn/binjo_addon) | Python        | Blender add-on: import a Model-BIN straight from a ROM (or a standalone `.bin`) into Blender as an editable mesh, tweak collision flags / materials / vertex shading, then export back to a valid Model-BIN.                      |
| [`BinjoAnalyzer`](BinjoAnalyzer) (`Binjo.exe`)         | C# / WinForms | Standalone desktop tool to inspect a Model-BIN's raw segments (header, textures, vertices, bones, collision, effects, GeoLayout) without opening Blender, replace individual textures, and export the model to glTF/OBJ/PNG/text. |

## Blender Add-on

This is the main, maintained part of the repo.

### Requirements

- Blender 3.4+ (tested up to current Blender 4.x/5.x releases — the material setup code auto-adapts to the API changes introduced in Blender 4.2 and 4.3).
- A Banjo-Kazooie ROM that **you legally own**. The tool ships with no game data or assets of any kind — it only knows how to read/write the format.

### Install

1. Download `BINjo_Kazooie.zip` from this repo (or zip the `BlenderAddOn/binjo_addon` folder yourself).
2. In Blender: `Edit > Preferences > Add-ons > Install...`, pick the zip, then enable "BINjo-Kazooie".
3. A new **BINjo Import / Export** panel appears in the 3D Viewport sidebar (`N` panel, "Tool" tab).

### Usage

1. Point **Source ROM** at your `.z64`/`.n64`/`.v64` file.
2. Pick a target model from either the **Map** dropdown (levels/rooms) or the **Targetted Object** dropdown (characters, props, enemies) — both open a searchable popup to filter the list as you type.
3. Click **Import from ROM** (or **Import Object from ROM** for the object selector; **Import from BIN** to load a standalone Model-BIN instead).
4. Edit the mesh, materials and collision flags as needed using the **BINjo Tools** panel (in the Material properties tab) and the **BINjo RGBA Shader** panel.
5. Set an **Export Path** and click **Export to BIN** to write the modified data back out.

See [`BlenderAddOn/explanations/`](BlenderAddOn/explanations) for example screenshots (collision flag shading, RGBA shader panel).

## BinjoAnalyzer

A standalone WinForms tool for poking at Model-BIN files directly, without going through Blender.

- **Load** a raw `.bin` model, or a previously-exported `.gltf`.
- **Inspect** the file's internal segments — header, textures, vertices, bones, collision, effects, animated textures, GeoLayout, display lists — as hex tables with human-readable interpretation (texture thumbnails, per-vertex XYZ/UV/RGBA, bone hierarchy, per-triangle floor/sound type, command chains).
- **Replace textures**: load a PNG and convert it to the game's native formats (RGBA32, RGBA16, CI4/CI8) before re-injecting it into the model.
- **Export**: the whole model to `.bin` or `.gltf`, individual textures to PNG, the collision mesh to `.obj`, and DisplayList/GeoLayout command listings to `.txt`. A separate "Texture Converter" panel converts arbitrary images to N64 texture formats independently of any loaded model.

Open [`BinjoAnalyzer/Binjo.sln`](BinjoAnalyzer/Binjo.sln) in Visual Studio (targets .NET Framework 4.7.2) and build, or run `BinjoAnalyzer/LAUNCH.bat` against a pre-built `BinjoAnalyzer/bin/Debug/Binjo.exe`.

## Notes

- No license file is currently published for this repository — treat it as all-rights-reserved by the original author ([ThatCowGuy](https://github.com/ThatCowGuy/BinjoKazooie)) unless/until one is added.
- Banjo-Kazooie is © Rare / Microsoft / Nintendo. This project contains no game assets and requires you to supply your own ROM.
