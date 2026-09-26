import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path("/opt/kirana")
SCRIPT = ROOT / "app/olya_review.py"


class OlyaReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="olya-test-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.path = self.directory / "register.json"
        self.records = [
            {
                "doi": "10.1234/test-reviewed",
                "title": "Проверенная тестовая работа",
                "review": {
                    "status": "full_text_reviewed",
                    "role": "core",
                    "evidence": "Искусственные данные для теста",
                    "notes": ["Тестовый тезис"],
                    "limits": "Тестовое ограничение",
                },
            },
            {
                "doi": "10.1234/test-candidate",
                "title": "Непроверенная тестовая работа",
                "review": {
                    "status": "candidate_not_reviewed",
                    "role": "undecided",
                    "evidence": None,
                    "notes": [],
                    "limits": None,
                },
            },
        ]
        spec = importlib.util.spec_from_file_location("olya_review_test", SCRIPT)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def run_review(self, path=None):
        self.path.write_text(
            json.dumps(
                {"schema_version": 1, "records": self.records},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(self.module, "DATA_DIR", self.directory):
            with patch("sys.argv", ["olya_review.py", str(path or self.path)]):
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    try:
                        self.module.main()
                        code = 0
                    except SystemExit as exc:
                        code = exc.code
        return code, stdout.getvalue(), stderr.getvalue()

    def test_statuses_are_separate(self):
        code, output, error = self.run_review()
        self.assertEqual(code, 0, error)
        self.assertIn("Всего работ: 2", output)
        self.assertIn("Проверены по полному тексту: 1", output)
        self.assertIn("Кандидаты без проверки: 1", output)

    def test_unknown_status_is_rejected(self):
        self.records[0]["review"]["status"] = "unknown_status"
        code, _, error = self.run_review()
        self.assertNotEqual(code, 0)
        self.assertIn("неизвестный статус", error)

    def test_duplicate_doi_is_rejected(self):
        self.records[1]["doi"] = self.records[0]["doi"]
        code, _, error = self.run_review()
        self.assertNotEqual(code, 0)
        self.assertIn("Повтор DOI", error)

    def test_incomplete_review_is_rejected(self):
        self.records[0]["review"]["notes"] = []
        code, _, error = self.run_review()
        self.assertNotEqual(code, 0)
        self.assertIn("неполная проверенная карточка", error)

    def test_file_outside_allowed_directory_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="olya-outside-") as outside:
            foreign = Path(outside) / "register.json"
            code, _, error = self.run_review(path=foreign)
        self.assertNotEqual(code, 0)
        self.assertIn("внутри каталога data/crossref", error)


if __name__ == "__main__":
    unittest.main()
