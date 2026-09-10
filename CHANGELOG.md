# Changelog

All notable changes to the **BINjo-Kazooie** Blender add-on are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Entries are written by hand under `## [Unreleased]`; `make bump-patch` /
`bump-minor` / `bump-major` close that section into a dated release and stamp the
same version into `blender_manifest.toml` and `binjo_addon/__init__.py`.

## [Unreleased]

### Changed

- Object and animation names were reviewed against the decomp's own code, not
  only its asset enum. Zone prefixes are upper-case like the map list (`TTC`,
  `GL`, `CCW`...). Where the enum gave two models the same name, the code that
  uses them tells them apart: `0x3B7` is TTC Stairs 2, `0x4D8` the right leaf
  of the FP entrance door, `0x444` the Summer Zubba door, `0x7C2`/`0x7C3` the
  two layers of MMM's sky, and `0x412` the engine fan's propeller switch.
  159 animations that only had a number now name the character whose code plays
  them (Final Boss, Boggy, Slappa, Tanktup Leg...), and four also say what they
  do where the code makes it plain - Banjo's walrus recoil, Mr. Vile's croc
  munch, Gobi crying and the Eyrie egg hatching.

## [0.3.0] - 2026-09-10

### Added

- Render mode and alpha compare are read from the model instead of assumed.
  A draw picks its blending by branching into the engine's render mode table
  (segment 3), and the models that need a cutout switch alpha compare to
  `G_AC_THRESHOLD` around it. Translucent surfaces now blend properly instead of
  being dithered, and cutouts clip at half alpha. Whether a material is drawn
  opaque follows from whether it carries any alpha at all - a transparent texel,
  a vertex alpha below 255, or a cutout - rather than from the render mode,
  which belongs to whichever triangle opened the material.

### Changed

- Map names now come from the decomp, checked against its own level table
  (`core2/mapModel.c`). 53 were vague or plain wrong: most of Gruntilda's Lair
  was numbered floors rather than named rooms, and `0xA5`/`0xA9` ("GL - First
  Cutscene Inside" / "GL - Floor 9") are the Dingpot room. The old `A`/`B`
  suffixes turn out to have meant OPA/XLU: every level ships as two model files,
  the opaque bulk and a small translucent one (water, glass, cobwebs), so the
  translucent halves now say so. The 8 entries that are empty slots in the ROM
  are marked as such.

### Fixed

- Exported `.bin` files could not be read back, by the addon or by the game. The
  exporter's GeoLayout ended in a root command with `size_4 = 0x28`, but that
  field is the jump to the next sibling and 0 ends the chain, so the walk ran
  past the end of the file. It is now 0.
- Importing a second model into the same scene could repaint the first one.
  Material names are texture offsets within their own model file, so the first
  texture of every model was `0x00000000`, and the importer reused an existing
  material by that name and swapped in its own image - importing TTC's skybox
  changed textures on the level. Materials are now prefixed with the model they
  came from (its asset uid, or the `.bin` file name), and images are named the
  same way instead of all being `tmp`, which also stops their saved copies
  overwriting each other.
- Importing the same model twice produced different face order and different
  material settings, because the collision segment deduplicated its triangles
  through a set whose order depended on `hash(None)`.

## [0.2.0] - 2026-09-06

### Added

- Skeleton import: models with a Bone segment arrive as a rigged mesh, with the
  rest-pose Armature built from the game's own hierarchy and rigid vertex groups
  derived from the GeoLayout tree (one bone per vertex, weight 1.0).
- Animation import: `.anim.bin` curves are baked onto the Armature as a Blender
  Action, including the scale channel the game uses to hide and show sub-parts.
- Import of non-map Model assets (characters, props, enemies), with searchable
  popup dropdowns for both the map and the object selectors.
- SELECTOR variants import as hidden objects instead of being dropped, with a
  **Show Selector Defaults** option to choose which appearance starts visible.
- Vertex normals and environment mapping on import, plus a catalogue of the
  colour combiners the game ships.
- BKModelUnk28 vertex pinning (seam welding) segment.
- RDP texture clamp/mirror flags mapped to Blender's extension mode, `G_TEXTURE`
  scale factor and enable bit honoured, and backface culling read from the
  geometry mode.
- Tooling: `Makefile` to rebuild `BINjo_Kazooie.zip`, ruff linting and a zizmor
  security scan in CI, and a build workflow that publishes the add-on zip as a
  GitHub Actions artifact.

### Fixed

- GeoLayout LOD handling: the winner is selected correctly and alternate detail
  branches are excluded.
- Untextured geometry no longer inherits whatever texture was left in TMEM.
- Bone parenting (`parent_ID` is an array index, not a bone-id lookup), bone
  scale application, bone axes, and rest-pose tails that stretched away from the
  mesh.
- Animation transforms: rotation order and composition, translation in the
  bone's local space, and joint separation while animating (fixed by welding
  seams).
- `map_model_lookup` offsets now match the real in-ROM asset table.
- The UV formula no longer applies the tile-shift terms.
- `System.Text.Json` bumped to 8.0.6 in BinjoAnalyzer, fixing two high-severity
  DoS CVEs.

### Changed

- `model_filename_enum` items are generated from `map_model_lookup` instead of
  being maintained by hand.
- The built `BINjo_Kazooie.zip` is no longer committed; rebuild it with
  `make zip`.

## [0.1.3] - 2026-08-24

- First version packaged for the Blender 4.2+ Extensions Platform via
  `blender_manifest.toml`.
- Baseline forked from [ThatCowGuy/BinjoKazooie](https://github.com/ThatCowGuy/BinjoKazooie);
  changes made before this fork are not tracked in this file.
