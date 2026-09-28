# Cardiac Lab

An English-language interactive cardiac conduction and ECG teaching site.

## Run

Requires Node.js 20.19+ or 22.12+.

```sh
npm install
npm run dev
```

Open the local URL printed by Vite. Production: `npm run build`, then
`npm run preview`. Simulation tests: `npm test`.

## Included

- Actual Z-Anatomy / BodyParts3D heart geometry: four chambers, valve leaflets,
  chordae, papillary muscles, coronary vessels and major vessels.
- Cutaway and exterior views; orbit, zoom, reset camera and expand controls.
- Clickable anatomy with English explanations and a keyboard-accessible list.
- Shared simulation clock for heart deformation, electrical propagation,
  ECG cursor and phase explanations.
- Play/pause, six phase steps, scrubbing, 40–120 bpm, and 0.25× / 0.5× / 1× speed.
- Responsive layout, keyboard controls and a usable ECG fallback without WebGL.

## Model provenance and limits

The initial procedural illustrative heart was replaced after review of the user's
MSD Manuals / BioDigital reference. **No BioDigital assets are included.**
The atlas-derived GLBs and attribution are in `public/models`.
They are adaptations under **CC BY-SA 4.0**; preserve the bundled attribution and
upstream notice when distributing them. The anatomy source contains upstream
BodyParts3D material; see the full provenance in `ATTRIBUTION.md`.

The mesh is anatomical atlas geometry, not a patient-specific scan. Cutaway,
regional contraction, conduction paths and timing are simplified teaching
adaptations. The synthetic Lead II waveform is not calculated from a cardiac
bidomain model and must not be used for diagnosis. The QT formula and valve
motion are illustrative, particularly at the heart-rate extremes.

The interventricular septum is a region of the atlas ventricular wall, rather
than a separate upstream object. Clicking its medial region selects its
explanation; selection from the list highlights the containing wall.

## Structure

- `src/simulation.ts`: deterministic timing, waveform, phase and mechanical state.
- `src/anatomy.ts`: English anatomy content.
- `src/components/Heart.tsx`: anatomical GLB rendering, shared morph targets for rendering and picking,
  motion-matched electrical overlays, selection, projected DOM labels.
- `src/useSimulation.ts`: requestAnimationFrame clock; background tabs do not
  accumulate catch-up time.
- `src/components/ECG.tsx`: calibrated synthetic ECG and scrubbing.
- `scripts/export_heart.py`: original atlas extraction recipe.
- `scripts/refine_heart.py`: coherent sections, edge thickness, vertex occlusion,
  and mesh-edge conduction paths for the v2 assets.
- `scripts/repair_vessel_contacts.py`: preserves all vessel branches while joining pulmonary junctions and correcting local vessel contacts for the v4 assets.

To regenerate the assets, download `Z-Anatomy.zip` from the linked upstream
repository and place its `Startup.blend` at `/private/tmp/cardiac-atlas/Startup.blend`.
The export script currently targets this workspace's `public/models` directory.
Do not execute upstream embedded Python; the script loads with `use_scripts=False`.
The atlas is not needed to run the website; the derived GLBs are already bundled.

The heart renderer loads separately from the UI. The two refined local GLBs total about
47 MB; the initial model may take a moment on a slow connection. Google Fonts
is optional; system fonts remain available when offline.

## Validation

Simulation tests verify full 40–120 bpm phase coverage, ECG landmark alignment,
mechanical delay, preserved QRS duration, speed scaling, and phase wrapping. New deformation tests check that the spatial map does not fold
across 40–120 bpm and that rendered morph vertices match raycast vertices.
Browser checks cover phase stepping, scrubbing, heart-rate adjustment, anatomy
selection, exterior/cutaway switching, keyboard dialogs and mobile overflow.

## GitHub Pages deployment

The GitHub Actions workflow builds and publishes the site when `main` is updated.
In repository Settings → Pages, select **GitHub Actions** as the build source.
Model, conduction and attribution URLs use the configured base path so they work
on a project site as well as at a domain root. To preview a project deployment:

```sh
VITE_BASE_PATH=/cardiac-conduction-lab/ npm run build
npm run preview
```

Earlier model exports stay local and are excluded from Git. The published v7
models include the complete current anatomy, with attribution and license notices.
