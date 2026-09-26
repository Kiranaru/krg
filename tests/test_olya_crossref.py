import contextlib
import importlib.util
import io
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path("/opt/kirana/app/olya_crossref.py")


class OlyaCrossrefTests(unittest.TestCase):
    def test_network_error_does_not_reveal_contact_email(self):
        spec = importlib.util.spec_from_file_location("olya_crossref_test", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        test_email = "private-test@example.invalid"
        error = urllib.error.URLError(f"Сбой для {test_email}")
        stderr = io.StringIO()

        with patch.object(module, "contact_email", return_value=test_email):
            with patch.object(module.urllib.request, "urlopen", side_effect=error) as mocked:
                with contextlib.redirect_stderr(stderr):
                    result = module.main()

        self.assertEqual(result, 1)
        mocked.assert_called_once()
        self.assertNotIn(test_email, stderr.getvalue())
        self.assertIn("адрес запроса скрыт", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
