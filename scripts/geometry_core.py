#!/usr/bin/env python3
"""Exact A3 chamber geometry primitives for the public O1 replay.

This module is dependency-free and contains no repository-specific input logic.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Sequence

Permutation = tuple[int, int, int, int]
Point = tuple[Fraction, Fraction, Fraction, Fraction]
Mapping = tuple[int, ...]
Cover = tuple[int, ...]

G: tuple[Permutation, ...] = tuple(itertools.permutations(range(4)))
G_INDEX = {g: i for i, g in enumerate(G)}
WORDS = tuple("".join(str(x) for x in g) for g in G)
EVEN_INDICES = tuple(i for i, g in enumerate(G) if sum(g[a] > g[b] for a in range(4) for b in range(a + 1, 4)) % 2 == 0)
ODD_INDICES = tuple(i for i in range(24) if i not in EVEN_INDICES)
ALL_CHAMBERS = (1 << 24) - 1

ONE: Point = (Fraction(1),) * 4
VERTICES: tuple[Point, ...] = tuple(
    tuple(Fraction(int(i == j)) for i in range(4))  # type: ignore[misc]
    for j in range(4)
)
CENTROID: Point = (Fraction(1, 4),) * 4


def compose(p: Permutation, q: Permutation) -> Permutation:
    """Locked convention p*q = p after q."""
    return tuple(p[q[i]] for i in range(4))  # type: ignore[return-value]


def inverse(p: Permutation) -> Permutation:
    output = [0, 0, 0, 0]
    for i, value in enumerate(p):
        output[value] = i
    return tuple(output)  # type: ignore[return-value]


LEFT_MAPS = tuple(
    tuple(G_INDEX[compose(g, sigma)] for sigma in G)
    for g in G
)
RIGHT_MAPS = tuple(
    tuple(G_INDEX[compose(sigma, q)] for sigma in G)
    for q in G
)
MUL = tuple(tuple(G_INDEX[compose(p, q)] for q in G) for p in G)
INV = tuple(G_INDEX[inverse(g)] for g in G)
SIMPLE_RIGHT_GENERATORS = tuple(G_INDEX[tuple(int(x) for x in word)] for word in ("1023", "0213", "0132"))


def permutation_parity(index: int) -> int:
    g = G[index]
    inversions = sum(g[a] > g[b] for a in range(4) for b in range(a + 1, 4))
    return 1 if inversions % 2 == 0 else -1


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def render_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def add_payload_hash(value: dict[str, Any]) -> dict[str, Any]:
    value["payload_sha256_without_self_field"] = canonical_sha256(value)
    return value


def payload_self_hash_ok(value: dict[str, Any]) -> bool:
    clean = dict(value)
    stored = clean.pop("payload_sha256_without_self_field", None)
    return stored == canonical_sha256(clean)


def add_named_hash(value: dict[str, Any], field: str) -> dict[str, Any]:
    value[field] = canonical_sha256(value)
    return value


def named_self_hash_ok(value: dict[str, Any], field: str) -> bool:
    clean = dict(value)
    stored = clean.pop(field, None)
    return stored == canonical_sha256(clean)


def histogram(counter: Counter[int] | Counter[str]) -> dict[str, int]:
    return {str(key): counter[key] for key in sorted(counter)}


def fraction_pair(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def serial_point(point: Point) -> list[list[int]]:
    return [fraction_pair(value) for value in point]


def add(a: Point, b: Point) -> Point:
    return tuple(x + y for x, y in zip(a, b))  # type: ignore[return-value]


def sub(a: Point, b: Point) -> Point:
    return tuple(x - y for x, y in zip(a, b))  # type: ignore[return-value]


def scale(a: Sequence[Fraction], scalar: Fraction) -> Point:
    return tuple(x * scalar for x in a)  # type: ignore[return-value]


def dot(a: Iterable[Fraction | int], b: Iterable[Fraction | int]) -> Fraction:
    return sum((Fraction(x) * Fraction(y) for x, y in zip(a, b)), Fraction(0))


def distance_squared(a: Point, b: Point) -> Fraction:
    """Unit-edge normalized squared distance on the standard simplex."""
    delta = sub(a, b)
    return dot(delta, delta) / 2


def determinant(matrix: Sequence[Sequence[Fraction | int]]) -> Fraction:
    a = [list(map(Fraction, row)) for row in matrix]
    n = len(a)
    if any(len(row) != n for row in a):
        raise ValueError("determinant requires a square matrix")
    sign = 1
    output = Fraction(1)
    for column in range(n):
        pivot = next((row for row in range(column, n) if a[row][column]), None)
        if pivot is None:
            return Fraction(0)
        if pivot != column:
            a[column], a[pivot] = a[pivot], a[column]
            sign *= -1
        value = a[column][column]
        output *= value
        for row in range(column + 1, n):
            if not a[row][column]:
                continue
            factor = a[row][column] / value
            for j in range(column, n):
                a[row][j] -= factor * a[column][j]
    return output * sign


def rational_rank(vectors: Iterable[Sequence[Fraction | int]]) -> int:
    a = [list(map(Fraction, vector)) for vector in vectors if any(vector)]
    if not a:
        return 0
    columns = len(a[0])
    rank = 0
    for column in range(columns):
        pivot = next((row for row in range(rank, len(a)) if a[row][column]), None)
        if pivot is None:
            continue
        a[rank], a[pivot] = a[pivot], a[rank]
        value = a[rank][column]
        a[rank] = [entry / value for entry in a[rank]]
        for row in range(len(a)):
            if row == rank or not a[row][column]:
                continue
            factor = a[row][column]
            a[row] = [x - factor * y for x, y in zip(a[row], a[rank])]
        rank += 1
    return rank


def determinant3(matrix: tuple[tuple[Fraction, ...], ...]) -> Fraction:
    return (
        matrix[0][0] * (matrix[1][1] * matrix[2][2] - matrix[1][2] * matrix[2][1])
        - matrix[0][1] * (matrix[1][0] * matrix[2][2] - matrix[1][2] * matrix[2][0])
        + matrix[0][2] * (matrix[1][0] * matrix[2][1] - matrix[1][1] * matrix[2][0])
    )


def null_normal(u: Point, v: Point) -> Point:
    rows = (u, v, ONE)
    entries: list[Fraction] = []
    for column in range(4):
        minor = tuple(tuple(row[k] for k in range(4) if k != column) for row in rows)
        entries.append(((-1) ** column) * determinant3(minor))
    normal = tuple(entries)
    if not any(normal) or dot(normal, u) != 0 or dot(normal, v) != 0 or dot(normal, ONE) != 0:
        raise RuntimeError("exact boundary-plane normal construction failed")
    return normal  # type: ignore[return-value]


def primitive_integer_vector(vector: Iterable[Fraction]) -> tuple[int, int, int, int]:
    values = tuple(vector)
    denominator_lcm = 1
    for value in values:
        denominator_lcm = math.lcm(denominator_lcm, value.denominator)
    integers = [int(value * denominator_lcm) for value in values]
    divisor = 0
    for value in integers:
        divisor = math.gcd(divisor, abs(value))
    if divisor == 0:
        raise RuntimeError("cannot normalize zero normal")
    normalized = tuple(value // divisor for value in integers)
    first = next(value for value in normalized if value)
    if first < 0:
        normalized = tuple(-value for value in normalized)
    return normalized  # type: ignore[return-value]


def chamber_vertices(word: Permutation) -> tuple[Point, Point, Point, Point]:
    p0 = VERTICES[word[0]]
    p1 = scale(add(VERTICES[word[0]], VERTICES[word[1]]), Fraction(1, 2))
    p2 = scale(add(add(VERTICES[word[0]], VERTICES[word[1]]), VERTICES[word[2]]), Fraction(1, 3))
    return p0, p1, p2, CENTROID


CHAMBER_VERTICES = tuple(chamber_vertices(word) for word in G)
ALL_BARYCENTRIC_VERTICES = tuple(sorted({point for tetrahedron in CHAMBER_VERTICES for point in tetrahedron}))


def phi_point(g_index: int, point: Point) -> Point:
    """Coordinate permutation e_i -> e_{g(i)}."""
    output = [Fraction(0)] * 4
    for i, value in enumerate(point):
        output[G[g_index][i]] = value
    return tuple(output)  # type: ignore[return-value]


def translate_mask(mask: int, mapping: Sequence[int]) -> int:
    output = 0
    work = mask
    while work:
        bit = work & -work
        output |= 1 << mapping[bit.bit_length() - 1]
        work ^= bit
    return output


def apply_left_mask(g_index: int, mask: int) -> int:
    return translate_mask(mask, LEFT_MAPS[g_index])


def apply_right_mask(mask: int, q_index: int) -> int:
    """Used only by the locked 0213 negative control, never by the census."""
    return translate_mask(mask, RIGHT_MAPS[q_index])


def facet_component_sizes(mask: int) -> list[int]:
    remaining = {i for i in range(24) if (mask >> i) & 1}
    sizes: list[int] = []
    while remaining:
        start = min(remaining)
        remaining.remove(start)
        stack = [start]
        size = 0
        while stack:
            chamber = stack.pop()
            size += 1
            for generator in SIMPLE_RIGHT_GENERATORS:
                neighbor = RIGHT_MAPS[generator][chamber]
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
        sizes.append(size)
    return sorted(sizes, reverse=True)


def subgroup_normalizer(subgroup: Sequence[int]) -> tuple[int, ...]:
    members = set(subgroup)
    return tuple(
        g
        for g in range(24)
        if {MUL[MUL[g][h]][INV[g]] for h in subgroup} == members
    )


def image_cover(cover: Cover, g_index: int) -> Cover:
    return tuple(sorted(apply_left_mask(g_index, piece) for piece in cover))


def cover_key(cover: Cover, acting_indices: Sequence[int]) -> Cover:
    return min(image_cover(cover, g) for g in acting_indices)


def boundary_corner_locus(mask: int) -> dict[str, Any]:
    facets: dict[tuple[Point, ...], list[tuple[int, int]]] = defaultdict(list)
    for chamber_index, tetrahedron in enumerate(CHAMBER_VERTICES):
        if not (mask >> chamber_index) & 1:
            continue
        for omitted in range(4):
            triangle = tuple(sorted(tetrahedron[j] for j in range(4) if j != omitted))
            facets[triangle].append((chamber_index, omitted))

    invalid_facet_incidence = sum(len(occurrences) not in (1, 2) for occurrences in facets.values())
    normal_lines_at_vertex: dict[Point, set[tuple[int, int, int, int]]] = defaultdict(set)
    boundary_triangles: list[tuple[Point, Point, Point]] = []
    for triangle, occurrences in facets.items():
        if len(occurrences) != 1:
            continue
        chamber_index, omitted = occurrences[0]
        p0, p1, p2 = triangle
        normal = null_normal(sub(p1, p0), sub(p2, p0))
        opposite = CHAMBER_VERTICES[chamber_index][omitted]
        if dot(normal, sub(opposite, p0)) > 0:
            normal = tuple(-value for value in normal)  # type: ignore[assignment]
        normal_line = primitive_integer_vector(normal)
        boundary_triangles.append(triangle)  # type: ignore[arg-type]
        for point in triangle:
            normal_lines_at_vertex[point].add(normal_line)

    edge_incidence: Counter[tuple[Point, Point]] = Counter()
    for triangle in boundary_triangles:
        for a, b in itertools.combinations(triangle, 2):
            edge_incidence[tuple(sorted((a, b)))] += 1
    manifold_edge_failures = sum(value != 2 for value in edge_incidence.values())

    corners = tuple(
        sorted(
            point
            for point, normals in normal_lines_at_vertex.items()
            if rational_rank(normals) == 3
        )
    )
    affine_rank = rational_rank(sub(point, corners[0]) for point in corners[1:]) if corners else 0
    rank_histogram = histogram(Counter(rational_rank(normals) for normals in normal_lines_at_vertex.values()))
    return {
        "corners": corners,
        "boundary_triangles_exact": tuple(boundary_triangles),
        "normal_lines_at_vertex_exact": {
            point: tuple(sorted(normals))
            for point, normals in normal_lines_at_vertex.items()
        },
        "boundary_triangle_count": len(boundary_triangles),
        "boundary_mesh_vertex_count": len(normal_lines_at_vertex),
        "boundary_mesh_edge_count": len(edge_incidence),
        "invalid_facet_incidence": invalid_facet_incidence,
        "manifold_edge_failures": manifold_edge_failures,
        "affine_rank": affine_rank,
        "boundary_mesh_vertex_normal_rank_histogram": rank_histogram,
    }


def rank3_corner_locus_from_boundary_triangles(
    triangles: Sequence[tuple[Point, Point, Point]],
) -> tuple[Point, ...]:
    """Triangulation-presentation-independent normal-rank reconstruction."""
    normals_at_vertex: dict[Point, set[tuple[int, int, int, int]]] = defaultdict(set)
    for triangle in triangles:
        p0, p1, p2 = triangle
        normal_line = primitive_integer_vector(null_normal(sub(p1, p0), sub(p2, p0)))
        for point in triangle:
            normals_at_vertex[point].add(normal_line)
    return tuple(
        sorted(
            point
            for point, normals in normals_at_vertex.items()
            if rational_rank(normals) == 3
        )
    )


def subdivide_triangle_coplanarly(
    triangles: Sequence[tuple[Point, Point, Point]], index: int = 0
) -> tuple[tuple[Point, Point, Point], ...]:
    triangle = triangles[index]
    a, b, c = triangle
    center = scale(add(add(a, b), c), Fraction(1, 3))
    replacement = (
        tuple(sorted((a, b, center))),
        tuple(sorted((b, c, center))),
        tuple(sorted((c, a, center))),
    )
    return tuple(triangles[:index]) + replacement + tuple(triangles[index + 1 :])


def distance_matrix(points: Sequence[Point]) -> tuple[tuple[Fraction, ...], ...]:
    return tuple(tuple(distance_squared(a, b) for b in points) for a in points)


def vertex_profiles(matrix: Sequence[Sequence[Fraction]]) -> tuple[tuple[Fraction, ...], ...]:
    return tuple(tuple(sorted(row[j] for j in range(len(row)) if j != i)) for i, row in enumerate(matrix))


def global_distance_signature(matrix: Sequence[Sequence[Fraction]]) -> tuple[Fraction, ...]:
    return tuple(sorted(matrix[i][j] for i in range(len(matrix)) for j in range(i + 1, len(matrix))))


def distance_graph_isomorphisms(
    source_matrix: Sequence[Sequence[Fraction]],
    target_matrix: Sequence[Sequence[Fraction]],
) -> tuple[Mapping, ...]:
    """Independent exact edge-colored complete-graph backtracking lane."""
    n = len(source_matrix)
    if n != len(target_matrix) or global_distance_signature(source_matrix) != global_distance_signature(target_matrix):
        return ()
    source_profiles = vertex_profiles(source_matrix)
    target_profiles = vertex_profiles(target_matrix)
    profile_targets = {
        profile: tuple(i for i, candidate in enumerate(target_profiles) if candidate == profile)
        for profile in set(source_profiles)
    }
    mapping = [-1] * n
    used: set[int] = set()
    found: list[Mapping] = []

    def compatible(source: int, target: int) -> bool:
        return all(
            mapped < 0 or source_matrix[source][other] == target_matrix[target][mapped]
            for other, mapped in enumerate(mapping)
        )

    def visit() -> None:
        if len(used) == n:
            found.append(tuple(mapping))
            return
        choices: list[tuple[int, int, tuple[int, ...]]] = []
        for source in range(n):
            if mapping[source] >= 0:
                continue
            candidates = tuple(
                target
                for target in profile_targets.get(source_profiles[source], ())
                if target not in used and compatible(source, target)
            )
            if not candidates:
                return
            choices.append((len(candidates), source, candidates))
        _, source, candidates = min(choices)
        for target in candidates:
            mapping[source] = target
            used.add(target)
            visit()
            used.remove(target)
            mapping[source] = -1

    visit()
    return tuple(sorted(set(found)))


def affine_basis_indices(points: Sequence[Point]) -> tuple[int, int, int, int]:
    for indices in itertools.combinations(range(len(points)), 4):
        p0 = points[indices[0]]
        if rational_rank(sub(points[i], p0) for i in indices[1:]) == 3:
            return indices
    raise RuntimeError("corner locus does not affinely span H")


def coordinates_in_affine_basis(points: Sequence[Point], basis: Sequence[int], point: Point) -> tuple[Fraction, Fraction, Fraction]:
    p0 = points[basis[0]]
    columns = [sub(points[basis[j]], p0) for j in range(1, 4)]
    vector = sub(point, p0)
    augmented = [[columns[column][row] for column in range(3)] + [vector[row]] for row in range(4)]
    pivot_row = 0
    pivot_columns: list[int] = []
    for column in range(3):
        pivot = next((row for row in range(pivot_row, 4) if augmented[row][column]), None)
        if pivot is None:
            continue
        augmented[pivot_row], augmented[pivot] = augmented[pivot], augmented[pivot_row]
        value = augmented[pivot_row][column]
        augmented[pivot_row] = [entry / value for entry in augmented[pivot_row]]
        for row in range(4):
            if row == pivot_row or not augmented[row][column]:
                continue
            factor = augmented[row][column]
            augmented[row] = [x - factor * y for x, y in zip(augmented[row], augmented[pivot_row])]
        pivot_columns.append(column)
        pivot_row += 1
    if pivot_columns != [0, 1, 2]:
        raise RuntimeError("affine basis solve is singular")
    for row in range(pivot_row, 4):
        if not any(augmented[row][:3]) and augmented[row][3]:
            raise RuntimeError("point is outside the locked affine hull")
    solution = [Fraction(0)] * 3
    for row, column in enumerate(pivot_columns):
        solution[column] = augmented[row][3]
    return tuple(solution)  # type: ignore[return-value]


def affine_gram_isomorphisms(
    source_points: Sequence[Point],
    target_points: Sequence[Point],
    source_matrix: Sequence[Sequence[Fraction]],
    target_matrix: Sequence[Sequence[Fraction]],
) -> tuple[Mapping, ...]:
    """Independent affine-basis and exact Gram reconstruction lane."""
    if len(source_points) != len(target_points) or global_distance_signature(source_matrix) != global_distance_signature(target_matrix):
        return ()
    source_profiles = vertex_profiles(source_matrix)
    target_profiles = vertex_profiles(target_matrix)
    basis = affine_basis_indices(source_points)
    coordinates = [coordinates_in_affine_basis(source_points, basis, point) for point in source_points]
    candidate_lists = [
        tuple(j for j, profile in enumerate(target_profiles) if profile == source_profiles[i])
        for i in basis
    ]
    target_lookup = {point: i for i, point in enumerate(target_points)}
    found: set[Mapping] = set()
    for target_basis in itertools.product(*candidate_lists):
        if len(set(target_basis)) != 4:
            continue
        if any(
            source_matrix[basis[a]][basis[b]] != target_matrix[target_basis[a]][target_basis[b]]
            for a in range(4)
            for b in range(a + 1, 4)
        ):
            continue
        q0 = target_points[target_basis[0]]
        target_columns = [sub(target_points[target_basis[j]], q0) for j in range(1, 4)]
        mapping: list[int] = []
        valid = True
        for coefficients in coordinates:
            image = q0
            for coefficient, column in zip(coefficients, target_columns):
                image = add(image, scale(column, coefficient))
            target = target_lookup.get(image)
            if target is None:
                valid = False
                break
            mapping.append(target)
        if valid and len(set(mapping)) == len(source_points):
            found.add(tuple(mapping))
    return tuple(sorted(found))


def orientation_sign(points: Sequence[Point], target_points: Sequence[Point], mapping: Mapping) -> int:
    basis = affine_basis_indices(points)
    source_det = determinant([points[i] for i in basis])
    target_det = determinant([target_points[mapping[i]] for i in basis])
    if not source_det or not target_det:
        raise RuntimeError("orientation test received a singular affine basis")
    return 1 if source_det * target_det > 0 else -1


def coordinate_permutation_for_mapping(source: Sequence[Point], target: Sequence[Point], mapping: Mapping) -> int | None:
    matches = [
        g
        for g in range(24)
        if all(phi_point(g, source[i]) == target[mapping[i]] for i in range(len(source)))
    ]
    if len(matches) > 1:
        raise RuntimeError("affinely spanning corner map has multiple S4 realizations")
    return matches[0] if matches else None


def subgroup_orbit_on_cover(cover: Cover, subgroup: Sequence[int]) -> set[int]:
    return {apply_left_mask(g, cover[0]) for g in subgroup}
