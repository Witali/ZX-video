"""Protect exact archive reconstruction against damaged bases and malformed edits."""
import unittest

from trd_duplicates import digest, reconstruct, repository_path


class ArchiveReconstructionTest(unittest.TestCase):
    def setUp(self):
        self.base = b"0123456789"
        self.row = dict(path="old.trd", retained="retained.trd", bytes=10,
                        retained_sha256=digest(self.base), sha256=digest(b"0AB345Z789"),
                        changed_bytes=3, edits=[[1, b"AB".hex()], [6, b"Z".hex()]])

    def test_exact_reconstruction_and_alias(self):
        self.assertEqual(reconstruct(self.row, self.base), b"0AB345Z789")
        row = dict(self.row, edits=[], changed_bytes=0, sha256=digest(self.base))
        self.assertEqual(reconstruct(row, self.base), self.base)

    def test_wrong_base_or_target_hash_is_rejected(self):
        with self.assertRaises(ValueError):
            reconstruct(self.row, b"X123456789")
        with self.assertRaises(ValueError):
            reconstruct(dict(self.row, sha256="0" * 64), self.base)

    def test_invalid_ranges_and_counts_are_rejected(self):
        for edits in ([[1, "4142"], [2, "43"]], [[-1, "41"]], [[9, "4142"]], [[1, ""]]):
            with self.subTest(edits=edits), self.assertRaises(ValueError):
                reconstruct(dict(self.row, edits=edits), self.base)
        with self.assertRaises(ValueError):
            reconstruct(dict(self.row, changed_bytes=2), self.base)

    def test_path_must_stay_inside_repository(self):
        with self.assertRaises(ValueError):
            repository_path("../outside.trd")
        with self.assertRaises(ValueError):
            repository_path("C:/outside.trd")


if __name__ == "__main__":
    unittest.main()
