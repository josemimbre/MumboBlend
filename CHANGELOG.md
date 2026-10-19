# Changelog

All notable changes to the **BINjo-Kazooie** Blender add-on are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Entries are written by hand under `## [Unreleased]`; `make bump-patch` /
`bump-minor` / `bump-major` close that section into a dated release and stamp the
same version into `blender_manifest.toml` and `binjo_addon/__init__.py`.

## [Unreleased]

## [0.4.0] - 2026-10-19

### Added

- **Export Map Objects** also writes the sprite props the map's setup file
  places (flowers, weeds...) under `sprites`, read straight from the ROM:
  asset id and name, position in game units, scale, mirroring and frame.
- **Export Material Data** writes `textureGen` for the materials drawn with
  G_TEXTURE_GEN, whose texture is looked up by the normal as seen from the
  camera (sphere mapping) rather than by UVs: the shine on honeycombs, jiggies
  and notes. The import already showed it in Blender; an engine needs to know.
- Names for entries the lists had as unknown, from what the decomp does with
  them: **(0x04F0) Topper Leaf** and **(0x04F1) Bawl Leaf** (the leaves that fly
  off when they die), **(0x07CF) Transition Circle** (the circle transition
  between maps), and the animations **(0x0223) Topper Hop**, **(0x0224) Topper
  Die**, **(0x0225) Collywobble Float**, **(0x0226) Bawl Hop**, **(0x0227) Bawl
  Die** and **(0x02B9) Rock Trapping Grunty**. The pieces Collywobble breaks
  into are named for what they are: **(0x04F2) Collywobble Large Leaf**,
  **(0x04F3) Collywobble Small Leaf** and **(0x04F4) Collywobble Floret** (a
  piece of the head, not the stem, as the decomp's name had it). The
  animations Banjo's house plays through its actors' path events (code_B9770.c,
  in map 0x8C's setup) are **(0x01CE) Banjos Curtains Sway**, **(0x0208)
  Fishbowl Swim**, **(0x0209) Cuckoo Clock Idle** (held for 4 seconds) and
  **(0x020A) Cuckoo Clock Cuckoo** (2 seconds, then back to idle). The
  models map 0x8C's setup places as props, which the decomp leaves unnamed
  but the stove, are named for what they are: **(0x0330) Banjos Armchair**,
  **(0x0331) Banjos Towel Rail**, **(0x0333) Banjos Flower Vase**,
  **(0x0336) Banjos Side Table** (the table, with a taller invisible box for
  collision), **(0x0343) Tootys Picture**, **(0x0349) Cuckoo Clock
  Collision** (invisible, round the clock) and **(0x034B) Banjos Bed**.
  The models other setups place as props, from the decomp's notes on the
  asset enum: **(0x02DA) TTC Palm Tree**, **(0x02DF) TTC Light Crate**,
  **(0x02E0) TTC Dark Crate**, **(0x02E1) TTC Light And Dark Crate**,
  **(0x02ED) Banjos House Dustbin** and **(0x02FF) MM Tree** (Spiral
  Mountain's trees too).
- **Smooth Normals** (on by default, with a **Smooth Angle** of 60 degrees)
  gives the faces drawn without G_LIGHTING smooth normals by angle. Those
  faces have no normal in the BIN, so they came in flat; the game never
  needed one, lighting them with the colour painted into their vertices, but
  real-time lighting in an engine does, and every triangle of a hill lit
  differently. Corners are matched by position, so the smoothing crosses
  unwelded seams too, and faces with a G_LIGHTING normal keep it. Which
  faces those are is kept as a `binjo_lit` face attribute.

- **Import Map Objects** (under Import Map Exits) adds an empty for
  everything the map's setup file places: actors (characters, enemies,
  collectables), static model props (trees, bins), sprite props (weeds,
  flowers) and the other nodes (camera and warp triggers, enemy boundaries,
  paths, flags), each kind in its own collection under `import_MapObjects`,
  the nodes hidden. They are named after the decomp (`A_<actor>_<name>`,
  `M_<asset>_<name>`, `S_<asset>_<name>`), keep the raw values as custom
  properties, and are turned the way the game turns them (yaw, and roll for
  model props). The names come from a new `binjo_names.py`, generated from
  the decomp's enums. The setup reader now reads the prop list as well as
  the NodeProps. With **Place Models** (on by default) every model a prop
  uses is imported once into `import_MapObjects_Library`, excluded from the
  view layer, and each `M_` empty instances it at the prop's placement and
  scale. Export Material Data includes what those empties instance, so a
  selection holding them writes the props' materials too. **Place Actors**
  does the same for actors, with the model their `ActorInfo` draws them with:
  `binjo_names.ACTOR_MODELS`, generated from every `ActorInfo` initialiser in
  the decomp (563 actors with a model). They show in their rest pose and
  default appearance (selector variants stay hidden in the library), and
  their setup scale is kept as a property but not applied, as what it means
  isn't clear yet.
- **Export Map Objects** writes the actors Import Map Objects placed to a
  `.actors.json`, for an engine to place its own versions of them apart from
  the level's FBX: actor id and name, model, position in game units, yaw,
  and the raw scale, selector and marker id. The scene's exits go in too, in
  the same units, so the engine can line its conversion up with the
  `Exit_0xNN` empties that came in through the level's FBX. The empties of
  Import Map Exits and Import Map Objects now keep their position in game
  units (`binjo_position`) for it.

- **Import Map Exits** (next to a **Map ID** field in the Import / Export
  panel) reads the map's setup file from the ROM and adds an empty for every
  point the player can enter it through: `Exit_0xNN`, where the game spawns
  the player for exit `NN`, with a child `Exit_0xNN_Facing` one unit away in
  the direction they face. Exported with the level, an engine gets them
  through the same coordinate conversion as the geometry. The setup reader
  (`binjo_setup.py`) only goes as far as the placements for now.

- **Export Material Data** button in the Import / Export panel. It writes a JSON
  file with what the import learnt about each material of the selected
  objects: texture, whether it is drawn on both sides, how it blends
  (`opaque`, `clip`, `dithered` or `translucent`), whether it is visible, and
  its collision flags. FBX carries none of this, so it is meant to go next to
  an FBX export for an engine to read back. `meshEffects` lists the mesh ids
  found on each material's vertices, and `depthWrite` whether the game writes
  depth when drawing it: the opaque half of a map does even for its blended
  materials, the translucent half never does. Texture names are written
  without the `.001`-style suffix Blender adds when a level is imported again
  into the same file, so they match the saved PNGs.
- The mesh list (header offset `0x24`, called `FX_offset` here and
  `mesh_list_offset` in the decomp) is read on import: the vertex groups the
  game animates by id after loading a map - scrolling waterfalls, wobbling
  water, flickering lights. Each imported mesh gets a second UV layer,
  `BK_MeshFX`, with the id in U and the effect's parameter in V (scroll speed
  in UV per second, water bobbing height in Blender units), so it survives an
  FBX export. Read-only for now: exporting to BIN does not write it back.

### Changed

- A selector variant nested inside another's branch is named after the
  whole path, `import_sel10_0-sel36_0-sel20_1`, instead of only its own
  selector. The game only reaches a nested selector while every branch
  above it is drawn (Kazooie's Turbo Trainers sit inside her bare feet,
  inside her legs), and the plain name lost that, so an engine showing the
  variants had her shoes floating on their own.

### Fixed

- The GeoLayout walk goes into the children of DRAW_DISTANCE, 0x0E and CAMERA
  commands, which hold most of a map's geometry. Their LODs and SELECTORs were
  never seen, so every LOD level and every variant came in stacked on top of
  each other: Mad Monster Mansion, Mumbo's Mountain, Bubblegloop Swamp and
  Rusty Bucket Bay among 28 models, and Mumbo's Skull's 175 variant pieces.
- Exported BINs draw each triangle once. Every triangle was sent as both
  halves of a G_TRI2, so it was drawn twice, and twice blended when
  translucent; pairs now share a G_TRI2 and an odd one gets a G_TRI1.
- Exported BINs fill in the header's triangle count (0x30), which was always 0.
- SELECTOR variants that are also part of the model's collision are split off
  like any other. The collision triangles are listed first, with no variant,
  and the drawn ones were matched to them and kept that, so the variants went
  into the main mesh: Quarrie's four eye states (selector 1) all came in as one.
- **Selector 1** follows **Show Selector Defaults** like every other selector.
  Its first child was always merged into the main mesh, because the game
  starts it at 1, but actors step it on from there: their blinking eyes go
  from 1 (open) to 4 (shut), so with the open eyes merged in, the shut ones
  were drawn on top of them and fought with them. Whatever drives the
  selectors has to start ID 1 at 1 to show it.
- Textures that clamp on one axis and repeat on the other are drawn as the
  game draws them. The RDP sets clamp and mirror per axis, but Blender's
  Image Texture node has one mode for both, and the import used EXTEND
  whenever either axis clamped. Banjo's house walls in Spiral Mountain clamp
  vertically and repeat along the wall, so their edge texels were smeared
  into stripes. The node now clamps (or repeats) and the other axis is
  folded with a FRACT or PINGPONG node on the UVs. The modes are kept on the
  material, and Export Material Data writes them as `textureExtensionU` and
  `textureExtensionV`, next to the old single `textureExtension`.
- **Weld Seams** no longer deletes faces. Two-sided fences, ropes and nets
  are modelled with a second set of triangles facing the other way on their
  own vertices, and some surfaces layer a second texture over the first;
  welding gave those faces the same vertices as the ones they overlap, and
  Blender keeps only one face per set of vertices. Spiral Mountain's
  translucent model lost 56 of its 413 tris (fences turned see-through from
  behind, the rope posts vanished). Vertices of overlapping faces are now
  left unwelded; every other seam still closes. On a rigged model they take
  the bone weights a merge would have given them, so they still follow their
  joints: Kazooie's wings, two-sided throughout, came apart at every joint
  when animated.
- Imported textures keep their transparency when saved. Their Blender images
  were created without an alpha channel, so saving them, by hand or by
  exporting to FBX with the textures copied, wrote RGB PNGs and dropped every
  transparent texel: grass, fences and leaves came out as solid blocks.

## [0.3.1] - 2026-09-10

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
