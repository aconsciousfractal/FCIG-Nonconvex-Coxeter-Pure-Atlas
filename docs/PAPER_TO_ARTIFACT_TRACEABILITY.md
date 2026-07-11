# Paper-to-artifact traceability

| Paper component | Exact artifact | Replay/check |
|---|---|---|
| Finite carrier and connected census | `bounded_census.json` | quick verifier; full gate |
| Congruence-to-left-orbit reduction | `global_congruence_gate.json` | `verify_global_congruence.py` |
| 15+82 exact-cover theorem | bounded census + global gate | global semantic comparator |
| 82-row catalogue | `nonconvex_tile_atlas.json` | `nonconvex_atlas.csv` cross-join |
| Patterson separation | tile atlas intrinsic fingerprints | quick verifier |
| Cover and selector structure | `cover_atlas.json` | quick verifier |
| Static contact obstructions | `contact_obstructions.json` | quick verifier |
| Boundary presentation comparison | `boundary_presentations.json` | quick verifier |
| Ambient symmetry and chirality | `ambient_symmetry_atlas.json` | quick verifier |
| Appendix catalogue | `paper/generated/atlas_catalogue.tex` | manuscript build |
