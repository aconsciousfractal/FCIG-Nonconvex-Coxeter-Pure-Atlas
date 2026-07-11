from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PublicPackageTests(unittest.TestCase):
    def test_quick_verifier_executes(self):
        completed = subprocess.run(
            [sys.executable, "-B", "scripts/verify_public_package.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("PUBLIC_QUICK_VERIFY_PASS", completed.stdout)

    def test_row_joins_and_masks(self):
        atlas = json.loads((ROOT / "artifacts/nonconvex_tile_atlas.json").read_text(encoding="utf-8"))
        covers = json.loads((ROOT / "artifacts/cover_atlas.json").read_text(encoding="utf-8"))
        ambient = json.loads((ROOT / "artifacts/ambient_symmetry_atlas.json").read_text(encoding="utf-8"))
        ids = [row["row_id"] for row in atlas["rows"]]
        self.assertEqual(len(ids), 82)
        self.assertEqual(len(set(ids)), 82)
        self.assertEqual(set(ids), {row["row_id"] for row in covers["rows"]})
        self.assertEqual(set(ids), {row["row_id"] for row in ambient["rows"]})
        self.assertTrue(all(row["facet_connected"] for row in atlas["rows"]))
        self.assertTrue(all(not row["halfspace_convex"] for row in atlas["rows"]))
        self.assertTrue(all(row["left_translate_tiler"] for row in atlas["rows"]))

    def test_public_full_replay_is_standalone(self):
        script = (ROOT / "scripts/verify_global_congruence.py").read_text(encoding="utf-8")
        self.assertIn('ROOT / "scripts" / "geometry_core.py"', script)
        self.assertIn('ROOT / "data" / "bounded_census_source.json"', script)
        self.assertNotIn("ambient_congruence_and_transitivity", script)

    def test_latex_artifact_references_exist(self):
        pattern = re.compile(r"artifacts/[A-Za-z0-9_.-]+[.]json")
        references = set()
        for path in (ROOT / "paper").rglob("*.tex"):
            references.update(pattern.findall(path.read_text(encoding="utf-8")))
        self.assertTrue(references)
        missing = [rel for rel in sorted(references) if not (ROOT / rel).is_file()]
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
