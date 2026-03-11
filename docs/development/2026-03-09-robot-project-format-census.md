# Robot Project Format Census

Date: 2026-03-09  
Scope:
- `/Users/xuhehong/Desktop/r-mos/开源机器人`
- `/Users/xuhehong/Desktop/r-mos/r-mos-frontend/public/models`

## 1. Why This Exists

Task 0 requires freezing a real format support matrix before any parser implementation.  
The sample package is not a clean "CAD only" bundle. It mixes:

- CAD assemblies and parts
- mesh assets
- URDF / MJCF structure descriptions
- documents
- videos
- training/runtime code
- model weights and binary artifacts

So phase 1 cannot assume "upload a robot project" means "parse every file".

## 2. Measured Inventory

### Open Source Robot Package

Source:
- `/Users/xuhehong/Desktop/r-mos/开源机器人/Fourier-N1开源资料`

Observed total:
- `1799` files

Top extensions:
- `.sldprt` `200`
- `.py` `188`
- `.stl` `182`
- `.obj` `164`
- `.so` `134`
- `.slddrw` `100`
- `.txt` `77`
- `[no_ext]` `73`
- `.sample` `70`
- `.mtl` `68`
- `.pyc` `52`
- `.glslfx` `42`
- `.png` `41`
- `.urdf` `39`
- `.dae` `33`
- `.xml` `31`
- `.json` `30`
- `.html` `28`
- `.sldasm` `21`
- `.md` `19`

Key subtrees:

| Subtree | Total | Main formats | Interpretation |
|---|---:|---|---|
| `FourierN1模型总装` | 355 | `SLDPRT`, `SLDDRW`, `SLDASM`, `STEP`, `STP`, `PDF` | Main mechanical package, best ingest target |
| `Wiki-GRx-Gym` | 1169 | `OBJ`, `STL`, `PY`, `SO`, `URDF`, `TXT` | Simulation/training repo, not all files belong in knowledge ingest |
| `Wiki-GRx-Models` | 65 | `STL`, `URDF` | Structure + mesh references, useful for asset graph |
| `Wiki-GRx-Mujoco` | 78 | `STL`, `XML`, `PY` | Structure + simulation config |
| `FourierN1安装指南_V1.0` | 6 | `MP4` | Video manual, not phase 1 parse target |

### Existing R-MOS Frontend Model Store

Source:
- `/Users/xuhehong/Desktop/r-mos/r-mos-frontend/public/models`

Observed total:
- `1090` files

Top extensions:
- `.glb` `364`
- `.tmp` `216`
- `.step` `178`
- `.sldprt` `156`
- `.stl` `124`
- `.stp` `38`
- `.sldasm` `12`
- `.json` `2`

Interpretation:
- The current frontend can directly consume `GLB`.
- Repo-local `STEP/SLDPRT/STL/SLDASM` are source assets or export intermediates, not directly executable viewer inputs.
- `.tmp` is export noise and should not drive ingest logic.

## 3. Phase 1 Format Strategy

### Supported In Phase 1

| Family | Extensions | Strategy | Reason |
|---|---|---|---|
| Plain docs | `MD`, `TXT`, `PDF`, `HTML`, `JSON`, `YAML`, `YML` | `TEXT_EXTRACT` | Can feed chunking / citations |
| Robot structure | `URDF`, `XML` | `STRUCTURE_SOURCE` | Useful for building part tree / structure graph |
| Viewer-ready assets | `GLB` | `VIEWER_READY` | Already compatible with current frontend viewer |

### Metadata-Only In Phase 1

| Family | Extensions | Strategy | Reason |
|---|---|---|---|
| SolidWorks assembly | `SLDASM` | `METADATA_ONLY` | Parse filename, folder graph, references; no geometry promise in phase 1 |
| SolidWorks part | `SLDPRT` | `METADATA_ONLY` | Same as above |
| SolidWorks drawing | `SLDDRW` | `METADATA_ONLY` | Useful as evidence of part naming / revision, not direct 3D source |
| Neutral CAD | `STEP`, `STP` | `METADATA_ONLY` | Preserve for later conversion; no direct viewer support yet |
| Mesh source | `STL`, `OBJ`, `DAE`, `WRL`, `USDA`, `MTL` | `METADATA_ONLY` | Useful for mapping and provenance, but not direct phase 1 interaction target |
| Preview/reference media | `PNG`, `JPG`, `JPEG`, `HDR` | `METADATA_ONLY` | Keep as preview/reference attachments |

### Explicitly Deferred In Phase 1

| Family | Extensions | Strategy | Reason |
|---|---|---|---|
| Video manuals | `MP4` | `DEFERRED` | Needs separate transcript/media pipeline |
| Policy / weights | `PT` | `DEFERRED` | Not knowledge ingest input |
| Source/runtime code | `PY`, `SO`, `PYC` | `DEFERRED` | Out of maintenance knowledge MVP scope |
| Repo artifacts | `SAMPLE`, `TMP`, `P2M`, `P2S`, `CWR`, `[no_ext]` | `DEFERRED` | Noise / binary aux files / unsupported metadata |

## 4. Parser Rules Frozen By This Census

1. No phase 1 code may assume all CAD files are parseable into a complete 3D hierarchy.
2. `SLDASM/SLDPRT/STEP/STP/STL/OBJ/DAE` only produce metadata graph nodes in phase 1.
3. Only `GLB` is treated as viewer-ready without conversion.
4. `URDF/XML` may inform the structure tree, but still need review if part mapping is incomplete.
5. `MP4`, `PT`, `PY`, `SO`, `TMP`, and unknown binary artifacts must be recorded but not parsed.

## 5. Immediate Impact On Later Tasks

- Task 2 classifier must use this matrix instead of ad-hoc extension guesses.
- Task 3 ingest worker may chunk text documents and build metadata graph for CAD, but must not claim full geometry parsing.
- Task 7-8 frontend must expect `needs_review` nodes because phase 1 manifest generation is intentionally conservative.
