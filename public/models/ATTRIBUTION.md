# Cardiac anatomy asset attribution

The bundled heart-cutaway-v7.glb and heart-exterior-v7.glb files, and earlier local exports, are adaptations of:

**Z-Anatomy — The libre 3D atlas of anatomy**, by Gauthier Kervyn and contributors.
Source: https://github.com/Z-Anatomy/Models-of-human-anatomy
Original asset: Z-Anatomy.zip / Startup.blend (downloaded September 28, 2026).
License: Creative Commons Attribution-ShareAlike 4.0 International.
https://creativecommons.org/licenses/by-sa/4.0/

Upstream attribution as requested by Z-Anatomy:
**BodyParts3D — The Database Center for Life Science — CC-BY-SA 2.1 Japan**.
Original model: Kousaku Okubo and contributors.
https://dbarchive.biosciencedbc.jp/en/bodyparts3d/download.html
https://creativecommons.org/licenses/by-sa/2.1/jp/

## Adaptations in Cardiac Lab

Cardiac structures were extracted from the atlas, evaluated and smoothed,
recentered, scaled, and converted to glTF. Proximal vessels were cropped.
A front-wall section was made from the original chamber meshes.
Materials, illustrative motion and an illustrative conduction overlay were added.
These adapted anatomical assets are made available under **CC BY-SA 4.0**.
The supplied Z-Anatomy-License.txt preserves the upstream license notice.

This is an educational atlas model, not a patient scan or a diagnostic model.
Conduction paths and motion are explanatory approximations.
MSD Manuals / BioDigital was consulted as a visual reference only;
no BioDigital meshes, textures, animations or code are distributed here.

## Refined v2 assets

The v2 adaptations additionally weld mesh seams, smooth coarse source surfaces,
apply a coherent surgical section to related structures, add thin section rims,
bake vertex ambient occlusion, and derive the illustrative conduction paths by
walking the chamber mesh edges. The web viewer uses a shared, invertible regional
deformation for anatomy and overlays, including matching morph normals and picking.


## Refined contact-corrected v4 assets

The v4 files retain all source vessel branches and chamber structures. Pulmonary arterial junctions were merged into a continuous surface, and local coronary/caval contacts were repositioned using the original atlas centerlines. No vessel or heart structure was removed.

## Current v7 assets

The published v7 models incorporate the vessel junction repairs and inset caps at open vessel ends. All chamber, valve and vessel structures are retained. The shared illustrative deformation and conduction overlays move with the anatomy. These adaptations remain available under CC BY-SA 4.0.
