# Source and artifact map

| Public artifact | Role | Runtime inputs |
|---|---|---|
| `data/bounded_census_source.json` | Pinned exact bounded-census source for the slow gate | none |
| `artifacts/bounded_census.json` | Public census and tiler records | derived at export |
| `artifacts/nonconvex_tile_atlas.json` | 82 enriched tile rows | derived at export |
| `artifacts/contact_obstructions.json` | Frozen exact selected-cover static incidence panels | parent-pinned; public structural recheck |
| `artifacts/boundary_presentations.json` | Frozen exact boundary-profile lanes | parent-pinned; public structural recheck |
| `artifacts/cover_atlas.json` | Frozen complete cover and selector inventory | parent-pinned; public structural recheck |
| `artifacts/ambient_symmetry_atlas.json` | Frozen tile/partition congruence and chirality | parent-pinned; public structural recheck |
| `artifacts/global_congruence_gate.json` | All-candidate carrier-rigidity certificate | derived at export |
| `scripts/geometry_core.py` | Exact standard-simplex geometry | Python standard library |
| `scripts/verify_global_congruence.py` | Full all-candidate replay | geometry core + pinned census |
| `scripts/recheck_frozen_artifacts.py` | Self-hash, schema/status, parent-pin, and complete-join recheck | public frozen artifacts |
| `scripts/recheck_catalogue.py` | Regeneration/byte-check of the 82-row LaTeX table | public joined atlas |

No sibling repository, network service, workstation path, or unpublished
project is a runtime dependency.  T2 appears only as a cited source and figure
provenance; see `THIRD_PARTY_NOTICES.md`.

The frozen secondary artifacts are reproducible evidence snapshots, not claims
that their original internal production pipelines are part of this repository.
Their integrity and cross-parent coherence are publicly rechecked; the O1
headline theorem gate is additionally fully replayable here.
