# Reviewer map

## Load-bearing statement

For every nonempty facet-connected union of the fixed 24 `A3` chambers whose
size divides 24, Euclidean congruence is exactly the left `S4` orbit relation.
Consequently the congruent-copy exact-cover problem reduces without loss to
the left-translate cover search, which yields 97 tiler classes: 15 convex and
82 nonconvex.

## Fast path

1. Run `python scripts/verify_public_package.py`.
2. Run `python scripts/recheck_frozen_artifacts.py` and
   `python scripts/recheck_catalogue.py`.
3. Inspect `artifacts/global_congruence_gate.json`, especially `enumeration`,
   `global_congruence_gate`, and `congruent_copy_exact_cover`.
4. Inspect the proof reduction and completeness appendix in
   `paper/The_Nonconvex_A3_Coxeter-Chamber_Atlas.pdf`.
5. Cross-check the 82 rows in `tables/nonconvex_atlas.csv` against
   `artifacts/nonconvex_tile_atlas.json`.
6. Review `docs/PUBLIC_CLAIM_BOUNDARY.md`, `docs/REFERENCE_AUDIT.md`, and
   `docs/RED_TEAM_REPORT.md` before assessing novelty or scope language.

## Full falsifier

Run the all-candidate replay and semantic comparator:

```bash
python scripts/verify_global_congruence.py
python scripts/compare_global_replay.py
```

The replay independently reconstructs 1,210,648 connected masks, 67,681
eligible masks, and 2,874 canonical left-orbit candidates; checks every edge
stratum; independently enumerates exact corner isometries in two lanes; rejects
every non-`S4` map; and reruns exact cover on the resulting congruence classes.

## Remaining gate

This package records an internal exact gate but no claim of independent external
approval.  Please treat the public repository as a release candidate until the
external red-team record and owner release decision are added.
