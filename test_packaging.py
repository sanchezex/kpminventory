import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app_resources import resource_path


class ResourcePathTests(unittest.TestCase):
    def test_resolves_bundled_resource_from_pyinstaller_directory(self) -> None:
        with tempfile.TemporaryDirectory() as bundle_directory:
            with patch("app_resources.sys._MEIPASS", bundle_directory, create=True):
                self.assertEqual(
                    resource_path("assets/trackright_logo.png"),
                    Path(bundle_directory) / "assets" / "trackright_logo.png",
                )

    def test_resolves_resource_relative_to_source_module(self) -> None:
        with patch("app_resources.sys._MEIPASS", None, create=True):
            self.assertEqual(
                resource_path("assets/trackright_logo.png"),
                Path(__file__).resolve().parent
                / "assets"
                / "trackright_logo.png",
            )


if __name__ == "__main__":
    unittest.main()
