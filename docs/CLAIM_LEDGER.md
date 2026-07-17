# Claim ledger

The `CL` column uses the official PAPP taxonomy (`Gate-Disciplined-Computational-Mathematics/docs/CLAIM_LEVELS.md`); added 2026-07-17 (ledger A-1). It maps the existing `Level` wording without altering any claim text, IDs, evidence pointers, or scope caveats.

| ID | Level | CL | Public statement | Evidence | Boundary |
|---|---|---|---|---|---|
| C1 | exact finite theorem | CL5 | The eligible connected carrier has 2,874 left-orbit representatives. | `bounded_census.json`, global gate | Fixed 24-chamber carrier only. |
| C2 | internal theorem + exact certificate | CL5 | Euclidean congruence equals the left `S4` orbit on every eligible carrier object. | `global_congruence_gate.json`, full replay | No arbitrary dissections or disconnected unions. |
| C3 | exact finite theorem | CL5 | Exactly 97 congruent-copy tiler classes occur: 15 convex and 82 nonconvex. | global gate, bounded census | Same carrier and connectivity hypotheses. |
| C4 | certified finite atlas | CL3 | The 82 nonconvex rows split 14/18/50 at `k=6/8/12`. | `nonconvex_tile_atlas.json` | Classification up to full Euclidean congruence. |
| C5 | certified finite atlas | CL3 | The rows support 786 raw covers, 86 cover orbits, 1,148 multiplier sets, and 102 multiplier orbits. | `cover_atlas.json` | Algebraic selector data is not mechanical geometry. |
| C6 | certified finite atlas | CL3 | Patterson, contact, boundary, and ambient-symmetry panels have the counts recorded in the paper. | public artifacts and tables | Each invariant retains its stated quantifier and completeness scope. |

The package records exact finite evidence and a machine-assisted proof
reduction. External adversarial review found no mathematical blocker. It does
not claim formal verification, journal peer review, or an archival DOI.
