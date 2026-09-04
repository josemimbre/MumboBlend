# MumboBlend

*(fork of [ThatCowGuy/BinjoKazooie](https://github.com/ThatCowGuy/BinjoKazooie))*

Tools to parse, export and replace data within Banjo-Kazooie (N64) `Model BIN` files — the format the game uses to store level/room geometry, collision, materials, textures, skeletons and animation.

The project has two independent pieces:

|                                                        | Language      | What it does                                                                                                                                                                                                                      |
| ------------------------------------------------------ | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`BlenderAddOn/binjo_addon`](BlenderAddOn/binjo_addon) | Python        | Blender add-on: import a Model-BIN straight from a ROM (or a standalone `.bin`) into Blender as an editable, rigged mesh, apply the game's own animations to it, tweak collision flags / materials / vertex shading, then export back to a valid Model-BIN. |
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

### Import options

| Option | Default | What it does |
| --- | --- | --- |
| **Scale Factor** | 100 | Divides every coordinate on import so the model arrives at a workable size, and multiplies it back on export. |
| **Weld Seams** | on | Merges coincident vertices after import. See *Seams* below. |
| **Show Selector Defaults** | on | Picks which alternate appearance starts visible. See *Model variants* below. |
| **Highlight INVIS Mats** | off | Draws collision-only geometry in magenta instead of leaving it transparent. |

### Skeleton and animation

Models with a bone segment import as a rigged mesh: an Armature is built from the game's rest pose, every vertex is assigned to the bone that draws it, and an Armature modifier is added. The association is not a weight table — the game encodes it in the GeoLayout tree, where a `BONE` command wraps everything drawn under that bone's matrix — so the weighting is **rigid**: one bone per vertex, weight 1.0, exactly as the console does it.

To animate, pick an entry from the **Animation** dropdown and click **Apply Animation to Skeleton**. The `.anim.bin` curves are baked into a Blender Action on the last imported (or currently selected) Armature, on every frame of the clip's range.

Two caveats worth knowing:

- Animations are baked with **linear** sampling; the game interpolates its curves with Catmull-Rom splines. The two agree exactly at every keyed point and can differ slightly between them.
- The game varies playback **speed** with the player's real velocity while walking, running, swimming and climbing. Clips are imported at fixed duration, so the curve is right but the tempo is not tied to movement.

#### Seams

The BIN stores a **separate vertex on each side of a joint** — the neck's own ring and the body's ring sit in the same place but are distinct entries, each rigidly bound to its own bone. Animating therefore pulls them apart and opens the seam. With **Weld Seams** on (the default) those are merged after the vertex groups exist, so the surviving vertex carries both bones and the joint holds together. This is the same approach `fast64` takes for SM64/OoT.

Welding breaks the 1:1 correspondence with the BIN's vertex table, so turn it off if you need the mesh to match the file exactly for export.

### Model variants (alternate appearances)

Character models don't store a single fixed appearance. The GeoLayout's `SELECTOR` command (`0x0C`) is a **model swap**: it holds a list of children and the game draws exactly one of them — or none — picked at runtime from a state variable. That's how Kazooie shows bare feet or Turbo Trainers, how a head switches between eye states, and how Bottles' hand-held props appear and disappear.

Every child is imported. One of them stays in the main `import_Object` as the default appearance; the rest are split into their own objects inside a collection named **`import_Variants`**, hidden by default so the initial view matches what the game normally draws. Variants carry the same armature modifier and vertex groups as the main mesh, so they deform with the skeleton normally.

Each variant object is named `import_sel<N>_<M>`, where `<N>` is the selector ID (objects sharing it are alternatives to one another) and `<M>` is the child index.

Which child starts visible **cannot be derived from the BIN**: the runtime state array starts zeroed, and only the character's own game code raises it. Banjo's code raises the selectors holding his eyes; Bottles' explicitly zeroes the ones holding his props. Hence the **Show Selector Defaults** option — on, every multi-child selector shows its first child (what Banjo needs); off, only selector ID 1 does, matching the hardware defaults (what Bottles needs). Selectors with a single child are plain on/off switches and stay hidden either way.

To use a variant, enable the eye icon on it in the Outliner. When comparing one against what it replaces, hide the equivalent part of the main object too, or both will occupy the same space. To animate a swap, keyframe the object's **Show in Viewports** / **Show in Renders** properties.

Alternate **LOD** branches are handled differently: those are a redundant lower-detail copy of the whole model rather than distinct content, so the near/high-detail branch is kept and the rest dropped.

### What gets read from the model, and what doesn't

The importer walks the model's DisplayList and reproduces the RDP state that affects how a surface looks, rather than assuming it:

- **Textures** in every format the game uses (CI4, CI8, RGBA16, RGBA32, IA8), with the palette decoded and the image built in memory.
- **Wrapping**: the tile's clamp/mirror flags become the image node's extension mode. Leaving Blender's default would tile a clamped texture across any face whose UVs run past `[0,1]`.
- **Texture coordinate scale** from `G_TEXTURE`, so a model using a factor other than the usual one is not mapped at the wrong size.
- **Whether a surface is textured at all.** Much of the geometry is drawn from vertex colour alone; without this it would inherit whatever texture was last loaded and be painted in that texture's corner texel — a flat wrong colour, or nothing when that texel is transparent.
- **Backface culling**, per surface, from the geometry mode.
- **Vertex colour and alpha**, and under `G_LIGHTING` the **vertex normal** instead, since those four bytes carry one or the other.
- **Environment mapping**: with `G_TEXTURE_GEN` the console derives texture coordinates from the normal and ignores the vertex's own, so those materials sample from the normal rather than from the imported UVs.
- **The colour combiner.** Only four distinct combiner programs exist across the models measured, and three reduce to what the material already builds — texture times vertex colour, or vertex colour alone. The fourth outputs the texture untinted, and is recognised.

Not reproduced: mipmaps (the second texture of a trilinear blend is skipped), the exact render mode and alpha-compare settings (materials use dithered transparency), and the per-tile coordinate shift (unused by every model measured).

**Export is narrower than import.** It writes geometry, vertices, collision and textures, but synthesises a minimal GeoLayout: no bone hierarchy, no LOD, no selectors. A model imported from ROM and exported back will not preserve its skeleton or its variants.

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
