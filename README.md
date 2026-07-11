# The Nonconvex A3 Coxeter-Chamber Atlas

[![Exact package CI](https://github.com/aconsciousfractal/FCIG-Nonconvex-Coxeter-Pure-Atlas/actions/workflows/ci.yml/badge.svg)](https://github.com/aconsciousfractal/FCIG-Nonconvex-Coxeter-Pure-Atlas/actions/workflows/ci.yml)

Public companion repository for:

> [The Nonconvex A3 Coxeter-Chamber Atlas: Congruence Rigidity, Exact Covers, and Patterson Separation](paper/The_Nonconvex_A3_Coxeter-Chamber_Atlas.pdf)
>
> Oleksiy Babanskyy, 2026

The fixed carrier is the regular tetrahedron subdivided into its 24 closed
`A3` Coxeter chambers.  Among all nonempty facet-connected chamber unions
whose chamber count divides 24, exact exhaustive computation gives 2,874
left-`S4` orbit representatives.  Exact boundary-corner rigidity proves that
free Euclidean congruence produces no identifications beyond the left `S4`
action.  Exact cover then gives 97 congruent-copy tiler classes: 15 convex and
82 nonconvex.

The 82-row nonconvex atlas splits by chamber count as `k=6: 14`,
`k=8: 18`, and `k=12: 50`.  It contains
786 raw covers grouped into
86 global left-cover orbits.
The accompanying panels record Patterson-style fingerprints, static contact
obstructions, two boundary-presentation lanes, and a complete ambient
symmetry/chirality classification of
86 partition classes.

## Claim boundary

This is an exact finite theorem on the fixed 24-chamber carrier.  It is not a
classification of arbitrary tetrahedron dissections, disconnected chamber
unions, or non-Coxeter-aligned pieces. The public repository has passed its
external mathematical and packaging red-team gate with no mathematical
blocker. This status is not a claim of journal peer review or archival
publication, and no DOI has yet been assigned.

## Quick verification

Python 3.10+ is sufficient; runtime scripts use only the standard library.

```bash
python scripts/verify_public_package.py
python scripts/recheck_frozen_artifacts.py
python scripts/recheck_catalogue.py
python -m unittest discover -s tests -v
```

The full all-candidate congruence replay is intentionally separate and slower:

```bash
python scripts/verify_global_congruence.py
python scripts/compare_global_replay.py
```

## Repository map

```text
paper/          manuscript source, figures, bibliography, title-named PDF
artifacts/      public theorem, atlas, cover, contact, boundary, symmetry data
data/           pinned bounded-census input for the full replay
tables/         flat CSV views of the atlas and all eligible candidates
scripts/        quick verifier, exact geometry core, full congruence replay
tests/          package-level regression tests
certificates/   theorem replay and package-preflight certificates
docs/           claim, source, traceability, red-team, and review records
```

See `README_REVIEWER.md` for the shortest referee path, `REPRODUCE.md` for all
commands, `LICENSE_SCOPE.md` for the mixed-license map, and
`THIRD_PARTY_NOTICES.md` for figure attribution.
