import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path("/opt/kirana")
DATA_DIR = ROOT / "projects/layered-barrier-optimization/data/crossref"
SOURCE = DATA_DIR / "review-20260926.json"
SCRIPT = ROOT / "app/olya_review.py"


class OlyaReviewTests(unittest.TestCase):
    def run_review(self, path):
        return subprocess.run(
            ["python3", str(SCRIPT), str(path)],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_real_register_counts(self):
        result = self.run_review(SOURCE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Проверены по полному тексту: 2", result.stdout)
        self.assertIn("Кандидаты без проверки: 3", result.stdout)

    def test_unknown_status_is_rejected_without_changing_source(self):
        original = SOURCE.read_bytes()
        data = json.loads(original)
        data["records"][0]["review"]["status"] = "unknown_status"

        with tempfile.TemporaryDirectory(dir=DATA_DIR, prefix="olya-test-") as directory:
            path = Path(directory) / "register.json"
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            result = self.run_review(path)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("неизвестный статус", result.stderr)
        self.assertEqual(SOURCE.read_bytes(), original)

    def test_duplicate_doi_is_rejected(self):
        data = json.loads(SOURCE.read_text(encoding="utf-8"))
        data["records"][1]["doi"] = data["records"][0]["doi"]

        with tempfile.TemporaryDirectory(dir=DATA_DIR, prefix="olya-test-") as directory:
            path = Path(directory) / "register.json"
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            result = self.run_review(path)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Повтор DOI", result.stderr)


if __name__ == "__main__":
    unittest.main()
