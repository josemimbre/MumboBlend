# Changelog

All notable changes to the **BINjo-Kazooie** Blender add-on are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Entries are written by hand under `## [Unreleased]`; `make bump-patch` /
`bump-minor` / `bump-major` close that section into a dated release and stamp the
same version into `blender_manifest.toml` and `binjo_addon/__init__.py`.

## [Unreleased]

### Added

- Render mode and alpha compare are read from the model instead of assumed.
  A draw picks its blending by branching into the engine's render mode table
  (segment 3), and the models that need a cutout switch alpha compare to
  `G_AC_THRESHOLD` around it. Translucent surfaces now blend properly instead of
  being dithered, and cutouts clip at half alpha. Whether a material is drawn
  opaque follows from whether it carries any alpha at all - a transparent texel,
  a vertex alpha below 255, or a cutout - rather than from the render mode,
  which belongs to whichever triangle opened the material.

### Fixed

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
